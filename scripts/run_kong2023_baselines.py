"""
run_kong2023_baselines.py
=========================
Cross-dataset validation: train on Smillie SCP259 (UC vs Healthy),
test on Kong 2023 CD (Crohn disease vs Healthy).

This script evaluates whether models trained on ulcerative colitis donors
generalize to Crohn disease — a related but distinct IBD phenotype.

Usage
-----
# Composition features (after building Kong donor tables):
python scripts/run_kong2023_baselines.py \
    --train-features  results/uc_scp259/benchmarks/donor_cluster_props.tsv \
    --train-metadata  data/processed/uc_scp259/donor_metadata.tsv \
    --test-features   data/processed/kong2023_cd/donor_cluster_props.tsv \
    --test-metadata   data/processed/kong2023_cd/donor_metadata.tsv \
    --run-name        kong_cross_dataset_composition \
    --output-dir      results/kong2023_cd/cross_dataset

# Pseudobulk features:
python scripts/run_kong2023_baselines.py \
    --train-features  results/uc_scp259/benchmarks/donor_pseudobulk_top1000.tsv \
    --train-metadata  data/processed/uc_scp259/donor_metadata.tsv \
    --test-features   data/processed/kong2023_cd/donor_pseudobulk_top1000.tsv \
    --test-metadata   data/processed/kong2023_cd/donor_metadata.tsv \
    --run-name        kong_cross_dataset_pseudobulk \
    --output-dir      results/kong2023_cd/cross_dataset \
    --max-features    1000

Notes
-----
- Train set: Smillie SCP259, 30 donors (12 Healthy, 18 UC), label col = 'label' ('Healthy'/'UC')
- Test set:  Kong 2023,       ~80 donors (34–40 Healthy, 12 CD per compartment),
             label col = 'label' ('Healthy'/'CD')
- Feature alignment: inner join on shared cluster/gene names; missing columns zero-filled.
- CLR transform applied train-only, then applied to test with train parameters (no leakage).
- Models: LogReg, LinearSVM, XGBoost (same as run_uc_baselines.py).
- Outputs: metrics TSV, predictions TSV, feature importance TSV.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import softmax
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    accuracy_score,
    f1_score,
)
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import LinearSVC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clr_transform(X: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Centered log-ratio transform (operates on non-negative proportions)."""
    X_eps = X + eps
    log_X = np.log(X_eps)
    geo_mean = log_X.mean(axis=1, keepdims=True)
    return log_X - geo_mean


def align_features(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    fill_value: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Align train and test feature matrices to share the same columns.
    Returns (train_aligned, test_aligned) with inner-union approach:
    - Shared columns: kept as-is in both.
    - Train-only columns: zero-filled in test.
    - Test-only columns: dropped (model was never trained on them).
    """
    shared = train_df.columns.intersection(test_df.columns)
    train_only = train_df.columns.difference(test_df.columns)
    test_only  = test_df.columns.difference(train_df.columns)

    log.info(f"Feature alignment: {len(shared)} shared, "
             f"{len(train_only)} train-only (zero-filled in test), "
             f"{len(test_only)} test-only (dropped from test)")

    # Fill test with zeros for train-only features
    for col in train_only:
        test_df[col] = fill_value

    # Align column order to match train
    test_df = test_df[train_df.columns]
    return train_df, test_df


def load_features_and_labels(
    features_path: str,
    metadata_path: str,
    label_col: str = "label",
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Load TSV features + metadata, return (features_df, labels, donor_ids)."""
    feat = pd.read_csv(features_path, sep="\t", index_col=0)
    meta = pd.read_csv(metadata_path, sep="\t", index_col=0)
    # Ensure donor IDs are strings in both (Kong TSVs may have integer index)
    feat.index = feat.index.astype(str)
    meta.index = meta.index.astype(str)

    # Align on donor index
    common = feat.index.intersection(meta.index)
    if len(common) == 0:
        raise ValueError(
            f"No common donors between features ({features_path}) "
            f"and metadata ({metadata_path}). Check index columns."
        )
    feat = feat.loc[common]
    meta = meta.loc[common]

    if label_col not in meta.columns:
        raise ValueError(f"Label column '{label_col}' not found in {metadata_path}. "
                         f"Available: {list(meta.columns)}")

    labels = meta[label_col]
    donor_ids = list(common)
    log.info(f"  Loaded {len(donor_ids)} donors from {Path(features_path).name}. "
             f"Label distribution: {labels.value_counts().to_dict()}")
    return feat, labels, donor_ids


def select_top_features(
    X_train: np.ndarray,
    feature_names: list[str],
    max_features: int,
) -> tuple[np.ndarray, list[str], list[int]]:
    """Select top-variance features from train set."""
    if max_features >= len(feature_names):
        return X_train, feature_names, list(range(len(feature_names)))
    variances = X_train.var(axis=0)
    top_idx = np.argsort(variances)[::-1][:max_features]
    top_idx_sorted = sorted(top_idx)
    selected_names = [feature_names[i] for i in top_idx_sorted]
    log.info(f"  Selected top {max_features} features by variance (from {len(feature_names)})")
    return X_train[:, top_idx_sorted], selected_names, top_idx_sorted


# ---------------------------------------------------------------------------
# Model runners
# ---------------------------------------------------------------------------

def run_logreg(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
    le: LabelEncoder,
) -> dict:
    clf = LogisticRegression(
        C=1.0,
        max_iter=2000,
        solver="saga",
        penalty="l2",
        random_state=42,
    )
    clf.fit(X_train, y_train)
    proba = clf.predict_proba(X_test)
    pred  = clf.predict(X_test)

    pos_class = le.transform(["CD"])[0] if "CD" in le.classes_ else le.transform(["UC"])[0]
    proba_pos = proba[:, pos_class]

    metrics = _compute_metrics(y_test, pred, proba_pos, le, "logreg")

    # Feature importances (log-odds of positive class)
    coef = clf.coef_[0]
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": coef,
    }).sort_values("importance", key=abs, ascending=False)

    return {"metrics": metrics, "predictions": _pred_df(y_test, pred, proba_pos, le),
            "importance": importance_df}


def run_linear_svm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
    le: LabelEncoder,
) -> dict:
    clf = LinearSVC(C=1.0, max_iter=5000, random_state=42)
    clf.fit(X_train, y_train)
    pred     = clf.predict(X_test)
    decision = clf.decision_function(X_test)
    # Convert decision scores to pseudo-probabilities via softmax for AUROC
    if decision.ndim == 1:
        proba_pos = 1 / (1 + np.exp(-decision))
    else:
        pos_class = le.transform(["CD"])[0] if "CD" in le.classes_ else le.transform(["UC"])[0]
        proba_pos = softmax(decision, axis=1)[:, pos_class]

    metrics = _compute_metrics(y_test, pred, proba_pos, le, "linear_svm")
    coef = clf.coef_[0]
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": coef,
    }).sort_values("importance", key=abs, ascending=False)

    return {"metrics": metrics, "predictions": _pred_df(y_test, pred, proba_pos, le),
            "importance": importance_df}


def run_xgb(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
    le: LabelEncoder,
) -> dict:
    try:
        from xgboost import XGBClassifier
    except ImportError:
        log.warning("xgboost not installed, skipping XGBoost.")
        return {}

    clf = XGBClassifier(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    clf.fit(X_train, y_train)
    proba = clf.predict_proba(X_test)
    pred  = clf.predict(X_test)

    pos_class = le.transform(["CD"])[0] if "CD" in le.classes_ else le.transform(["UC"])[0]
    proba_pos = proba[:, pos_class]

    metrics = _compute_metrics(y_test, pred, proba_pos, le, "xgb")
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": clf.feature_importances_,
    }).sort_values("importance", ascending=False)

    return {"metrics": metrics, "predictions": _pred_df(y_test, pred, proba_pos, le),
            "importance": importance_df}


def _compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    proba_pos: np.ndarray,
    le: LabelEncoder,
    model_name: str,
) -> dict:
    try:
        auroc = roc_auc_score(y_true, proba_pos)
    except Exception:
        auroc = float("nan")
    try:
        pr_auc = average_precision_score(y_true, proba_pos)
    except Exception:
        pr_auc = float("nan")

    acc = accuracy_score(y_true, y_pred)
    f1  = f1_score(y_true, y_pred, average="macro")

    return {
        "model": model_name,
        "auroc": round(auroc, 4),
        "pr_auc": round(pr_auc, 4),
        "accuracy": round(acc, 4),
        "f1_macro": round(f1, 4),
        "n_train": None,   # filled later
        "n_test": len(y_true),
    }


def _pred_df(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    proba_pos: np.ndarray,
    le: LabelEncoder,
) -> pd.DataFrame:
    return pd.DataFrame({
        "true_label": le.inverse_transform(y_true),
        "pred_label": le.inverse_transform(y_pred),
        "proba_positive": proba_pos,
    })


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Cross-dataset validation: train on SCP259 UC, test on Kong 2023 CD."
    )
    parser.add_argument("--train-features", required=True,
                        help="TSV: donors × features (train set, SCP259).")
    parser.add_argument("--train-metadata", required=True,
                        help="TSV: donor metadata with 'label' column (train).")
    parser.add_argument("--test-features", required=True,
                        help="TSV: donors × features (test set, Kong 2023).")
    parser.add_argument("--test-metadata", required=True,
                        help="TSV: donor metadata with 'label' column (test).")
    parser.add_argument("--run-name", default="kong_cross_dataset",
                        help="Run name prefix for output files.")
    parser.add_argument("--output-dir", default="results/kong2023_cd/cross_dataset",
                        help="Directory to write results.")
    parser.add_argument("--models", nargs="+",
                        default=["logreg", "linear_svm", "xgb"],
                        choices=["logreg", "linear_svm", "xgb"],
                        help="Models to evaluate.")
    parser.add_argument("--max-features", type=int, default=0,
                        help="Max features by variance (0 = use all; useful for pseudobulk).")
    parser.add_argument("--apply-clr", action="store_true",
                        help="Apply CLR transform (for composition features).")
    parser.add_argument("--label-col", default="label",
                        help="Column name for disease label in metadata files.")
    parser.add_argument("--train-label-col", default=None,
                        help="Override label col for train metadata only.")
    parser.add_argument("--test-label-col", default=None,
                        help="Override label col for test metadata only.")
    args = parser.parse_args()

    train_label_col = args.train_label_col or args.label_col
    test_label_col  = args.test_label_col  or args.label_col

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info(f"Cross-dataset validation: {args.run_name}")
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    log.info("Loading train features (SCP259)...")
    train_feat, train_labels, train_donors = load_features_and_labels(
        args.train_features, args.train_metadata, label_col=train_label_col
    )

    log.info("Loading test features (Kong 2023)...")
    test_feat, test_labels, test_donors = load_features_and_labels(
        args.test_features, args.test_metadata, label_col=test_label_col
    )

    # ------------------------------------------------------------------
    # Feature alignment
    # ------------------------------------------------------------------
    log.info("Aligning features across datasets...")
    train_feat, test_feat = align_features(train_feat.copy(), test_feat.copy())
    feature_names = list(train_feat.columns)

    X_train = train_feat.values.astype(np.float32)
    X_test  = test_feat.values.astype(np.float32)

    # ------------------------------------------------------------------
    # Label encoding — must handle mismatched class sets (UC vs CD)
    # Train: Healthy / UC     Test: Healthy / CD
    # We binarize: 0 = Healthy, 1 = disease (UC or CD)
    # ------------------------------------------------------------------
    DISEASE_LABELS = {"UC", "CD", "Crohn disease", "ulcerative colitis"}
    def binarize(labels: pd.Series) -> np.ndarray:
        return (labels.isin(DISEASE_LABELS)).astype(int).values

    y_train_bin = binarize(train_labels)
    y_test_bin  = binarize(test_labels)

    # Also keep a simple LabelEncoder for reporting
    le = LabelEncoder()
    le.classes_ = np.array(["Healthy", "Disease"])
    # We'll use binary 0/1 directly; adapt _pred_df for binary case
    def _pred_df_binary(y_true, y_pred, proba_pos):
        class_names = {0: "Healthy", 1: "Disease"}
        return pd.DataFrame({
            "true_label": [class_names[v] for v in y_true],
            "pred_label": [class_names[v] for v in y_pred],
            "proba_positive": proba_pos,
        })

    log.info(f"  Train: {(y_train_bin == 0).sum()} Healthy, {(y_train_bin == 1).sum()} Disease (UC)")
    log.info(f"  Test:  {(y_test_bin == 0).sum()} Healthy, {(y_test_bin == 1).sum()} Disease (CD)")

    # ------------------------------------------------------------------
    # Feature selection (train-set variance only — no leakage)
    # ------------------------------------------------------------------
    if args.max_features and args.max_features > 0:
        X_train, feature_names, top_idx = select_top_features(
            X_train, feature_names, args.max_features
        )
        X_test = X_test[:, top_idx]

    # ------------------------------------------------------------------
    # CLR transform (train-set parameters only)
    # ------------------------------------------------------------------
    if args.apply_clr:
        log.info("Applying CLR transform (train-fit, test-apply)...")
        X_train = clr_transform(X_train)
        X_test  = clr_transform(X_test)

    # ------------------------------------------------------------------
    # Run models
    # ------------------------------------------------------------------
    all_metrics     = []
    all_predictions = []
    all_importances = []

    model_runners = {
        "logreg":     _run_logreg_binary,
        "linear_svm": _run_lsvm_binary,
        "xgb":        _run_xgb_binary,
    }

    for model_name in args.models:
        log.info(f"\n--- {model_name.upper()} ---")
        runner = model_runners[model_name]
        result = runner(X_train, y_train_bin, X_test, y_test_bin, feature_names)
        if not result:
            continue

        metrics = result["metrics"]
        metrics["n_train"] = len(y_train_bin)
        metrics["n_test"]  = len(y_test_bin)
        metrics["run_name"] = args.run_name
        all_metrics.append(metrics)

        preds = result["predictions"]
        preds["model"]    = model_name
        preds["run_name"] = args.run_name
        preds["donor_id"] = test_donors
        all_predictions.append(preds)

        imp = result.get("importance")
        if imp is not None:
            imp["model"]    = model_name
            imp["run_name"] = args.run_name
            all_importances.append(imp)

        log.info(f"  AUROC={metrics['auroc']:.4f}  PR-AUC={metrics['pr_auc']:.4f}  "
                 f"Acc={metrics['accuracy']:.4f}  F1={metrics['f1_macro']:.4f}")

    # ------------------------------------------------------------------
    # Save results
    # ------------------------------------------------------------------
    prefix = out_dir / args.run_name

    metrics_df = pd.DataFrame(all_metrics)
    metrics_path = f"{prefix}_metrics.tsv"
    metrics_df.to_csv(metrics_path, sep="\t", index=False)
    log.info(f"\nMetrics saved to: {metrics_path}")

    if all_predictions:
        pred_df = pd.concat(all_predictions, ignore_index=True)
        pred_path = f"{prefix}_predictions.tsv"
        pred_df.to_csv(pred_path, sep="\t", index=False)
        log.info(f"Predictions saved to: {pred_path}")

    if all_importances:
        imp_df = pd.concat(all_importances, ignore_index=True)
        imp_path = f"{prefix}_feature_importance.tsv"
        imp_df.to_csv(imp_path, sep="\t", index=False)
        log.info(f"Feature importances saved to: {imp_path}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log.info("\n" + "=" * 60)
    log.info("CROSS-DATASET VALIDATION SUMMARY")
    log.info(f"  Train: SCP259 (UC), n={len(y_train_bin)}")
    log.info(f"  Test:  Kong 2023 (CD), n={len(y_test_bin)}")
    log.info(f"  Features: {len(feature_names)}")
    log.info("-" * 60)
    for m in all_metrics:
        log.info(f"  {m['model']:12s}  AUROC={m['auroc']:.4f}  PR-AUC={m['pr_auc']:.4f}")
    log.info("=" * 60)

    print("\nDone. Results in:", out_dir)
    return metrics_df


# ---------------------------------------------------------------------------
# Binary-label model runners (no LabelEncoder dependency)
# ---------------------------------------------------------------------------

def _run_logreg_binary(X_train, y_train, X_test, y_test, feature_names):
    clf = LogisticRegression(
        C=1.0, max_iter=2000, solver="saga", penalty="l2", random_state=42
    )
    clf.fit(X_train, y_train)
    proba     = clf.predict_proba(X_test)[:, 1]
    pred      = clf.predict(X_test)
    metrics   = _binary_metrics(y_test, pred, proba, "logreg")
    imp = pd.DataFrame({"feature": feature_names, "importance": clf.coef_[0]})
    imp = imp.reindex(imp["importance"].abs().sort_values(ascending=False).index)
    return {"metrics": metrics, "predictions": _binary_pred_df(y_test, pred, proba),
            "importance": imp}


def _run_lsvm_binary(X_train, y_train, X_test, y_test, feature_names):
    clf = LinearSVC(C=1.0, max_iter=5000, random_state=42)
    clf.fit(X_train, y_train)
    decision  = clf.decision_function(X_test)
    proba     = 1 / (1 + np.exp(-decision))   # sigmoid
    pred      = clf.predict(X_test)
    metrics   = _binary_metrics(y_test, pred, proba, "linear_svm")
    imp = pd.DataFrame({"feature": feature_names, "importance": clf.coef_[0]})
    imp = imp.reindex(imp["importance"].abs().sort_values(ascending=False).index)
    return {"metrics": metrics, "predictions": _binary_pred_df(y_test, pred, proba),
            "importance": imp}


def _run_xgb_binary(X_train, y_train, X_test, y_test, feature_names):
    try:
        from xgboost import XGBClassifier
    except ImportError:
        log.warning("xgboost not installed, skipping.")
        return {}
    clf = XGBClassifier(
        n_estimators=300, max_depth=3, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric="logloss",
        random_state=42, verbosity=0,
    )
    clf.fit(X_train, y_train)
    proba   = clf.predict_proba(X_test)[:, 1]
    pred    = clf.predict(X_test)
    metrics = _binary_metrics(y_test, pred, proba, "xgb")
    imp = pd.DataFrame({"feature": feature_names, "importance": clf.feature_importances_})
    imp = imp.sort_values("importance", ascending=False)
    return {"metrics": metrics, "predictions": _binary_pred_df(y_test, pred, proba),
            "importance": imp}


def _binary_metrics(y_true, y_pred, proba_pos, model_name):
    try:
        auroc = roc_auc_score(y_true, proba_pos)
    except Exception:
        auroc = float("nan")
    try:
        pr_auc = average_precision_score(y_true, proba_pos)
    except Exception:
        pr_auc = float("nan")
    return {
        "model":    model_name,
        "auroc":    round(auroc, 4),
        "pr_auc":   round(pr_auc, 4),
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "f1_macro": round(f1_score(y_true, y_pred, average="macro"), 4),
        "n_train":  None,
        "n_test":   int(len(y_true)),
    }


def _binary_pred_df(y_true, y_pred, proba_pos):
    class_map = {0: "Healthy", 1: "Disease"}
    return pd.DataFrame({
        "true_label":     [class_map[v] for v in y_true],
        "pred_label":     [class_map[v] for v in y_pred],
        "proba_positive": proba_pos,
    })


if __name__ == "__main__":
    main()
