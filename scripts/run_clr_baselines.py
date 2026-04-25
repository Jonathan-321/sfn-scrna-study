#!/usr/bin/env python3

"""Run donor-level baselines with CLR-transformed composition features.

Adds two new models vs. run_uc_baselines.py:
  - elasticnet  : ElasticNet logistic regression (handles correlated proportions)
  - catboost    : CatBoost gradient boosting (completes the GBDT triad)

Applies Centered Log-Ratio (CLR) transform to raw proportion inputs before
fitting.  CLR is the standard transformation for compositional data (Aitchison
1982): it moves proportions out of the simplex into real-valued Euclidean space,
making Euclidean-geometry models (LR, SVM, elastic net) statistically valid.

Usage (from repo root):
    python scripts/run_clr_baselines.py \\
        --features data/processed/uc_scp259/donor_cluster_props.tsv \\
        --metadata data/processed/uc_scp259/donor_metadata.tsv \\
        --folds    data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \\
        --output-dir results/uc_scp259/benchmarks \\
        --run-name donor_cluster_props_clr_baselines \\
        --models logreg,linear_svm,xgb,elasticnet,catboost

For repeated CV (10x5):
    python scripts/run_clr_baselines.py \\
        --features data/processed/uc_scp259/donor_cluster_props.tsv \\
        --metadata data/processed/uc_scp259/donor_metadata.tsv \\
        --folds    data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \\
        --output-dir results/uc_scp259/benchmarks \\
        --run-name donor_cluster_props_clr_baselines \\
        --models logreg,linear_svm,xgb,elasticnet,catboost \\
        --repeated --n-splits 5 --n-repeats 10

Also accepts compartment composition:
    python scripts/run_clr_baselines.py \\
        --features data/processed/uc_scp259/donor_compartment_cluster_props.tsv \\
        --run-name donor_compartment_cluster_props_clr_baselines ...
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# ---------------------------------------------------------------------------
# CLR transform
# ---------------------------------------------------------------------------

def clr_transform(df: pd.DataFrame, pseudocount: float = 0.5) -> pd.DataFrame:
    """Apply Centered Log-Ratio (CLR) transform to a proportion table.

    Each row (donor) is treated as a composition.  A pseudocount is added to
    replace zeros before taking logs, as required by the Aitchison geometry.

    CLR_i = log(x_i / geom_mean(x))
           = log(x_i) - mean(log(x))

    Args:
        df:           DataFrame with shape (n_donors, n_features).
                      Values should be proportions (sum ~ 1 per row), but
                      raw counts also work -- CLR is scale-invariant.
        pseudocount:  Small value added to every cell before log to handle
                      structural zeros.  0.5 is a standard choice (half-unit
                      pseudocount on the count scale).

    Returns:
        DataFrame with same shape; values are CLR-transformed, mean-zero
        per row (up to floating-point error).
    """
    arr = df.to_numpy(dtype=float)
    arr = arr + pseudocount * (1.0 / arr.shape[1])   # add pseudocount proportional to cell
    log_arr = np.log(arr)
    clr_arr = log_arr - log_arr.mean(axis=1, keepdims=True)
    return pd.DataFrame(clr_arr, index=df.index, columns=df.columns)


# ---------------------------------------------------------------------------
# Model runners
# ---------------------------------------------------------------------------

def load_table(path: Path) -> pd.DataFrame:
    suffix = "".join(path.suffixes[-2:]) if len(path.suffixes) >= 2 else path.suffix
    if suffix in {".tsv", ".tsv.gz"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".csv", ".csv.gz"}:
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table format: {path}")


def load_folds(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_top_variance_features(
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    max_features: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    if max_features <= 0 or x_train.shape[1] <= max_features:
        return x_train, x_test, x_train.columns.tolist()
    variances = np.nanvar(x_train.to_numpy(dtype=float), axis=0)
    order = np.argsort(-variances)[:max_features]
    selected = x_train.columns[order].tolist()
    return x_train[selected], x_test[selected], selected


def run_logreg(x_train, y_train, x_test, seed):
    pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("m",   LogisticRegression(max_iter=5000, random_state=seed)),
    ])
    pipe.fit(x_train, y_train)
    prob = pipe.predict_proba(x_test)[:, 1]
    return prob, (prob >= 0.5).astype(int), pipe.named_steps["m"].coef_.ravel()


def run_linear_svm(x_train, y_train, x_test, seed):
    pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("m",   SVC(kernel="linear", probability=True, random_state=seed)),
    ])
    pipe.fit(x_train, y_train)
    prob = pipe.predict_proba(x_test)[:, 1]
    return prob, (prob >= 0.5).astype(int), pipe.named_steps["m"].coef_.ravel()


def run_elasticnet(x_train, y_train, x_test, seed):
    """Elastic-net penalised logistic regression.

    L1_ratio=0.5 balances L1 (sparsity) and L2 (ridge) penalties.  Handles
    correlated composition features better than plain L2 logistic regression.
    """
    pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("m",   LogisticRegression(
            penalty="elasticnet",
            solver="saga",
            l1_ratio=0.5,
            max_iter=10_000,
            random_state=seed,
        )),
    ])
    pipe.fit(x_train, y_train)
    prob = pipe.predict_proba(x_test)[:, 1]
    return prob, (prob >= 0.5).astype(int), pipe.named_steps["m"].coef_.ravel()


def run_xgb(x_train, y_train, x_test, seed):
    from xgboost import XGBClassifier
    imp = SimpleImputer(strategy="median")
    x_tr = imp.fit_transform(x_train)
    x_te = imp.transform(x_test)
    m = XGBClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9,
        eval_metric="auc", random_state=seed,
        n_jobs=1, tree_method="hist",
    )
    m.fit(x_tr, y_train)
    prob = m.predict_proba(x_te)[:, 1]
    return prob, (prob >= 0.5).astype(int), m.feature_importances_


def run_catboost(x_train, y_train, x_test, seed):
    """CatBoost gradient boosting — completes the GBDT triad (XGB / CatBoost).

    CatBoost uses ordered boosting which can reduce overfitting on small samples.
    No scaling needed; handles missing values natively.
    """
    try:
        from catboost import CatBoostClassifier
    except ImportError:
        raise ImportError(
            "CatBoost is not installed.  Run: pip install catboost"
        )
    imp = SimpleImputer(strategy="median")
    x_tr = imp.fit_transform(x_train)
    x_te = imp.transform(x_test)
    m = CatBoostClassifier(
        iterations=300,
        depth=4,
        learning_rate=0.05,
        eval_metric="AUC",
        random_seed=seed,
        verbose=0,
    )
    m.fit(x_tr, y_train)
    prob = m.predict_proba(x_te)[:, 1]
    return prob, (prob >= 0.5).astype(int), m.get_feature_importance()


MODEL_DISPATCH = {
    "logreg":     run_logreg,
    "linear_svm": run_linear_svm,
    "elasticnet": run_elasticnet,
    "xgb":        run_xgb,
    "catboost":   run_catboost,
}


def compute_metrics(y_true, prob, pred):
    return {
        "roc_auc":            float(roc_auc_score(y_true, prob)),
        "pr_auc":             float(average_precision_score(y_true, prob)),
        "balanced_accuracy":  float(balanced_accuracy_score(y_true, pred)),
        "macro_f1":           float(f1_score(y_true, pred, average="macro")),
    }


# ---------------------------------------------------------------------------
# Single-pass (locked folds) runner
# ---------------------------------------------------------------------------

def run_single_pass(
    x: pd.DataFrame,
    y: np.ndarray,
    ids: pd.Series,
    folds_payload: dict[str, Any],
    models: list[str],
    max_features: int,
    seed: int,
    apply_clr: bool,
) -> tuple[list[dict], list[dict], list[dict]]:
    fold_rows: list[dict] = []
    pred_rows: list[dict] = []
    imp_rows:  list[dict] = []

    for fold in folds_payload["folds"]:
        train_mask = ids.isin({str(v) for v in fold["train_ids"]}).to_numpy()
        test_mask  = ids.isin({str(v) for v in fold["test_ids"]}).to_numpy()

        x_tr_raw = x.loc[train_mask]
        x_te_raw = x.loc[test_mask]

        if apply_clr:
            # Fit CLR on train-only (no leakage from test proportions)
            x_tr_raw = clr_transform(x_tr_raw)
            x_te_raw = clr_transform(x_te_raw)

        x_tr, x_te, selected = select_top_variance_features(x_tr_raw, x_te_raw, max_features)
        y_tr = y[train_mask]
        y_te = y[test_mask]
        test_ids = ids.loc[test_mask].tolist()

        for model_name in models:
            t0 = time.time()
            prob, pred, importance = MODEL_DISPATCH[model_name](x_tr, y_tr, x_te, seed)
            metrics = compute_metrics(y_te, prob, pred)
            fold_rows.append({
                "model": model_name,
                "fold": int(fold["fold"]),
                "n_train": int(train_mask.sum()),
                "n_test": int(test_mask.sum()),
                "n_features": int(len(selected)),
                "clr": apply_clr,
                **metrics,
                "runtime_s": time.time() - t0,
            })
            for did, yt, yp, ypr in zip(test_ids, y_te, pred, prob):
                pred_rows.append({
                    "model": model_name, "fold": int(fold["fold"]),
                    "donor_id": did, "y_true": int(yt),
                    "y_pred": int(yp), "y_prob": float(ypr), "clr": apply_clr,
                })
            abs_imp = np.abs(np.asarray(importance, dtype=float))
            order = np.argsort(-abs_imp)[: min(50, len(selected))]
            for idx in order:
                imp_rows.append({
                    "model": model_name, "fold": int(fold["fold"]),
                    "feature": selected[idx], "importance": float(abs_imp[idx]),
                    "clr": apply_clr,
                })

    return fold_rows, pred_rows, imp_rows


# ---------------------------------------------------------------------------
# Repeated CV runner
# ---------------------------------------------------------------------------

def repeat_summary(frame: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = ["roc_auc", "pr_auc", "balanced_accuracy", "macro_f1",
                    "runtime_s", "n_features"]
    rows = []
    for (model_name, clr_flag), part in frame.groupby(["model", "clr"], sort=True):
        row: dict[str, Any] = {
            "model": model_name, "clr": clr_flag,
            "n_repeats": int(part["repeat"].nunique()),
        }
        for col in numeric_cols:
            vals = part[col].to_numpy(dtype=float)
            row[f"{col}_mean"] = float(vals.mean())
            row[f"{col}_std"]  = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
            row[f"{col}_ci95_low"]  = float(np.quantile(vals, 0.025))
            row[f"{col}_ci95_high"] = float(np.quantile(vals, 0.975))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["clr", "roc_auc_mean"], ascending=[True, False])


def run_repeated(
    x: pd.DataFrame,
    y: np.ndarray,
    models: list[str],
    max_features: int,
    n_splits: int,
    n_repeats: int,
    seed: int,
    apply_clr: bool,
) -> list[dict]:
    fold_rows = []
    for repeat_idx in range(n_repeats):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed + repeat_idx)
        for fold_idx, (tr_idx, te_idx) in enumerate(skf.split(np.arange(len(y)), y)):
            x_tr_raw = x.iloc[tr_idx]
            x_te_raw = x.iloc[te_idx]
            if apply_clr:
                x_tr_raw = clr_transform(x_tr_raw)
                x_te_raw = clr_transform(x_te_raw)
            x_tr, x_te, selected = select_top_variance_features(x_tr_raw, x_te_raw, max_features)
            y_tr, y_te = y[tr_idx], y[te_idx]
            for model_name in models:
                t0 = time.time()
                prob, pred, _ = MODEL_DISPATCH[model_name](x_tr, y_tr, x_te, seed + repeat_idx)
                metrics = compute_metrics(y_te, prob, pred)
                fold_rows.append({
                    "repeat": repeat_idx, "fold": fold_idx,
                    "model": model_name, "clr": apply_clr,
                    "n_features": len(selected),
                    **metrics,
                    "runtime_s": time.time() - t0,
                })
    return fold_rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run donor-level baselines with CLR transform + new models."
    )
    p.add_argument("--features",    type=Path, required=True)
    p.add_argument("--metadata",    type=Path,
                   default=Path("data/processed/uc_scp259/donor_metadata.tsv"))
    p.add_argument("--folds",       type=Path, default=None,
                   help="Locked folds JSON (required unless --repeated is set).")
    p.add_argument("--output-dir",  type=Path,
                   default=Path("results/uc_scp259/benchmarks"))
    p.add_argument("--run-name",    default=None)
    p.add_argument("--models",
                   default="logreg,linear_svm,elasticnet,xgb,catboost")
    p.add_argument("--id-col",      default="donor_id")
    p.add_argument("--label-col",   default="donor_label")
    p.add_argument("--positive-label", default="UC")
    p.add_argument("--max-features", type=int, default=0,
                   help="Top-variance cap; <=0 keeps all features (correct for composition).")
    p.add_argument("--no-clr",      action="store_true",
                   help="Skip CLR transform (run raw proportions for comparison).")
    p.add_argument("--repeated",    action="store_true",
                   help="Run 10x5 repeated CV instead of locked folds.")
    p.add_argument("--n-splits",    type=int, default=5)
    p.add_argument("--n-repeats",   type=int, default=10)
    p.add_argument("--seed",        type=int, default=42)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    unknown = set(models) - set(MODEL_DISPATCH)
    if unknown:
        raise ValueError(f"Unknown model(s): {sorted(unknown)}")

    features    = load_table(args.features)
    donor_meta  = load_table(args.metadata)
    apply_clr   = not args.no_clr
    # Ensure donor_id is string in both tables (numeric IDs like Kong 2023 get inferred as int)
    if args.id_col in features.columns:
        features[args.id_col] = features[args.id_col].astype(str)
    if args.id_col in donor_meta.columns:
        donor_meta[args.id_col] = donor_meta[args.id_col].astype(str)

    dataset = donor_meta[[args.id_col, args.label_col]].merge(
        features, on=args.id_col, how="inner", validate="one_to_one"
    )
    y   = (dataset[args.label_col] == args.positive_label).astype(int).to_numpy()
    ids = dataset[args.id_col].astype(str)
    fc  = [c for c in dataset.columns if c not in {args.id_col, args.label_col}]
    x   = dataset[fc].apply(pd.to_numeric, errors="coerce")

    run_name = args.run_name or (args.features.stem + ("_clr" if apply_clr else "_raw"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    clr_label = "clr" if apply_clr else "raw"
    print(f"[run] {run_name}  transform={clr_label}  models={models}")

    if args.repeated:
        fold_rows = run_repeated(
            x, y, models, args.max_features,
            args.n_splits, args.n_repeats, args.seed, apply_clr,
        )
        fold_df = pd.DataFrame(fold_rows)
        repeat_df = (
            fold_df.groupby(["model", "clr", "repeat"], as_index=False)
            .agg(roc_auc=("roc_auc","mean"), pr_auc=("pr_auc","mean"),
                 balanced_accuracy=("balanced_accuracy","mean"),
                 macro_f1=("macro_f1","mean"),
                 runtime_s=("runtime_s","sum"),
                 n_features=("n_features","mean"))
        )
        summary_df = repeat_summary(repeat_df)
        fold_df.to_csv(args.output_dir / f"{run_name}_repeated_fold_metrics.tsv",
                       sep="\t", index=False)
        repeat_df.to_csv(args.output_dir / f"{run_name}_repeated_repeat_summary.tsv",
                         sep="\t", index=False)
        summary_df.to_csv(args.output_dir / f"{run_name}_repeated_summary.tsv",
                          sep="\t", index=False)
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(summary_df.to_string(index=False))
    else:
        if args.folds is None:
            raise ValueError("--folds is required when not using --repeated")
        folds_payload = load_folds(args.folds)
        fold_rows, pred_rows, imp_rows = run_single_pass(
            x, y, ids, folds_payload, models,
            args.max_features, args.seed, apply_clr,
        )
        fold_df = pd.DataFrame(fold_rows)
        summary = (
            fold_df.groupby(["model", "clr"], as_index=False)
            .agg(
                roc_auc_mean=("roc_auc","mean"), roc_auc_std=("roc_auc","std"),
                pr_auc_mean=("pr_auc","mean"),   pr_auc_std=("pr_auc","std"),
                balanced_accuracy_mean=("balanced_accuracy","mean"),
                macro_f1_mean=("macro_f1","mean"),
                runtime_mean_s=("runtime_s","mean"),
                n_features_mean=("n_features","mean"),
            )
            .sort_values("roc_auc_mean", ascending=False)
        )
        fold_df.to_csv(args.output_dir / f"{run_name}_fold_metrics.tsv", sep="\t", index=False)
        summary.to_csv(args.output_dir / f"{run_name}_summary.tsv", sep="\t", index=False)
        pd.DataFrame(pred_rows).to_csv(args.output_dir / f"{run_name}_predictions.tsv",
                                       sep="\t", index=False)
        pd.DataFrame(imp_rows).to_csv(args.output_dir / f"{run_name}_feature_importance.tsv",
                                      sep="\t", index=False)
        with pd.option_context("display.max_columns", None, "display.width", 200):
            print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
