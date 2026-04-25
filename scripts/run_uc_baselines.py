#!/usr/bin/env python3

"""Run donor-level conventional baselines for the UC SCP259 benchmark."""

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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run donor-level baseline models on UC donor tables."
    )
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Feature table path (TSV/TSV.GZ/CSV). Must contain donor_id.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_metadata.tsv"),
        help="Donor metadata table used to derive labels.",
    )
    parser.add_argument(
        "--folds",
        type=Path,
        required=True,
        help="Locked donor folds JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/uc_scp259/benchmarks"),
        help="Directory for summary and per-fold outputs.",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Prefix for output file names. Defaults to the feature table stem.",
    )
    parser.add_argument(
        "--models",
        default="logreg,linear_svm,xgb",
        help="Comma-separated list from: logreg,linear_svm,xgb",
    )
    parser.add_argument("--id-col", default="donor_id")
    parser.add_argument("--label-col", default="donor_label")
    parser.add_argument("--positive-label", default="UC")
    parser.add_argument(
        "--max-features",
        type=int,
        default=1000,
        help="Train-only variance filter cap; <=0 disables filtering.",
    )
    parser.add_argument(
        "--save-predictions",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write per-fold prediction table.",
    )
    parser.add_argument(
        "--save-importances",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write per-fold feature importance tables when supported.",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_table(path: Path) -> pd.DataFrame:
    suffix = "".join(path.suffixes[-2:]) if len(path.suffixes) >= 2 else path.suffix
    if suffix in {".tsv", ".tsv.gz"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".csv", ".csv.gz"}:
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table format for {path}")


def load_folds(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_top_variance_features(
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    max_features: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    if max_features <= 0 or x_train.shape[1] <= max_features:
        selected = x_train.columns.tolist()
        return x_train, x_test, selected

    variances = np.nanvar(x_train.to_numpy(dtype=float), axis=0)
    order = np.argsort(-variances)
    keep_idx = order[:max_features]
    selected = x_train.columns[keep_idx].tolist()
    return x_train[selected], x_test[selected], selected


def run_logreg(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    x_test: pd.DataFrame,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=5000, random_state=seed)),
        ]
    )
    pipe.fit(x_train, y_train)
    prob = pipe.predict_proba(x_test)[:, 1]
    pred = (prob >= 0.5).astype(int)
    coef = pipe.named_steps["model"].coef_.ravel()
    return prob, pred, coef


def run_linear_svm(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    x_test: pd.DataFrame,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pipe = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", SVC(kernel="linear", probability=True, random_state=seed)),
        ]
    )
    pipe.fit(x_train, y_train)
    prob = pipe.predict_proba(x_test)[:, 1]
    pred = (prob >= 0.5).astype(int)
    coef = pipe.named_steps["model"].coef_.ravel()
    return prob, pred, coef


def run_xgb(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    x_test: pd.DataFrame,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from xgboost import XGBClassifier

    imputer = SimpleImputer(strategy="median")
    x_train_i = imputer.fit_transform(x_train)
    x_test_i = imputer.transform(x_test)
    model = XGBClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="auc",
        random_state=seed,
        n_jobs=1,
        tree_method="hist",
    )
    model.fit(x_train_i, y_train)
    prob = model.predict_proba(x_test_i)[:, 1]
    pred = (prob >= 0.5).astype(int)
    importance = model.feature_importances_
    return prob, pred, importance


def compute_metrics(y_true: np.ndarray, prob: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(y_true, prob)),
        "pr_auc": float(average_precision_score(y_true, prob)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, pred)),
        "macro_f1": float(f1_score(y_true, pred, average="macro")),
    }


def main() -> None:
    args = parse_args()
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    valid_models = {"logreg", "linear_svm", "xgb"}
    unknown = set(models) - valid_models
    if unknown:
        raise ValueError(f"Unsupported model(s): {sorted(unknown)}")

    features = load_table(args.features)
    donor_meta = load_table(args.metadata)
    folds_payload = load_folds(args.folds)

    for column in (args.id_col,):
        if column not in features.columns:
            raise ValueError(f"Feature table missing '{column}'")
        if column not in donor_meta.columns:
            raise ValueError(f"Metadata table missing '{column}'")
    if args.label_col not in donor_meta.columns:
        raise ValueError(f"Metadata table missing '{args.label_col}'")

    dataset = donor_meta[[args.id_col, args.label_col]].merge(
        features, on=args.id_col, how="inner", validate="one_to_one"
    )
    if dataset.shape[0] != donor_meta[args.id_col].nunique():
        raise ValueError("Merged benchmark table does not cover every donor exactly once.")

    y = (dataset[args.label_col] == args.positive_label).astype(int).to_numpy()
    ids = dataset[args.id_col].astype(str)
    feature_cols = [column for column in dataset.columns if column not in {args.id_col, args.label_col}]
    x = dataset[feature_cols].apply(pd.to_numeric, errors="coerce")

    run_name = args.run_name or args.features.name.replace(".tsv.gz", "").replace(".tsv", "")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    fold_rows: list[dict[str, Any]] = []
    pred_rows: list[dict[str, Any]] = []
    importance_rows: list[dict[str, Any]] = []

    for fold in folds_payload["folds"]:
        train_mask = ids.isin({str(value) for value in fold["train_ids"]}).to_numpy()
        test_mask = ids.isin({str(value) for value in fold["test_ids"]}).to_numpy()

        x_train, x_test, selected = select_top_variance_features(
            x.loc[train_mask],
            x.loc[test_mask],
            max_features=args.max_features,
        )
        y_train = y[train_mask]
        y_test = y[test_mask]
        test_ids = ids.loc[test_mask].tolist()

        for model_name in models:
            start = time.time()
            if model_name == "logreg":
                prob, pred, importance = run_logreg(x_train, y_train, x_test, args.seed)
            elif model_name == "linear_svm":
                prob, pred, importance = run_linear_svm(x_train, y_train, x_test, args.seed)
            else:
                prob, pred, importance = run_xgb(x_train, y_train, x_test, args.seed)

            metrics = compute_metrics(y_test, prob, pred)
            runtime = time.time() - start
            fold_rows.append(
                {
                    "run_name": run_name,
                    "model": model_name,
                    "fold": int(fold["fold"]),
                    "n_train": int(train_mask.sum()),
                    "n_test": int(test_mask.sum()),
                    "n_features_selected": int(len(selected)),
                    "roc_auc": metrics["roc_auc"],
                    "pr_auc": metrics["pr_auc"],
                    "balanced_accuracy": metrics["balanced_accuracy"],
                    "macro_f1": metrics["macro_f1"],
                    "runtime_s": runtime,
                }
            )

            if args.save_predictions:
                for donor_id, y_true, y_prob, y_pred in zip(test_ids, y_test, prob, pred):
                    pred_rows.append(
                        {
                            "run_name": run_name,
                            "model": model_name,
                            "fold": int(fold["fold"]),
                            "donor_id": donor_id,
                            "y_true": int(y_true),
                            "y_prob": float(y_prob),
                            "y_pred": int(y_pred),
                        }
                    )

            if args.save_importances:
                abs_importance = np.abs(np.asarray(importance, dtype=float))
                order = np.argsort(-abs_importance)[: min(50, len(selected))]
                for idx in order:
                    importance_rows.append(
                        {
                            "run_name": run_name,
                            "model": model_name,
                            "fold": int(fold["fold"]),
                            "feature": selected[idx],
                            "importance": float(abs_importance[idx]),
                        }
                    )

    fold_df = pd.DataFrame(fold_rows)
    summary = (
        fold_df.groupby("model", as_index=False)
        .agg(
            roc_auc_mean=("roc_auc", "mean"),
            roc_auc_std=("roc_auc", "std"),
            pr_auc_mean=("pr_auc", "mean"),
            pr_auc_std=("pr_auc", "std"),
            balanced_accuracy_mean=("balanced_accuracy", "mean"),
            balanced_accuracy_std=("balanced_accuracy", "std"),
            macro_f1_mean=("macro_f1", "mean"),
            macro_f1_std=("macro_f1", "std"),
            runtime_mean_s=("runtime_s", "mean"),
            runtime_std_s=("runtime_s", "std"),
            n_features_selected_mean=("n_features_selected", "mean"),
        )
        .sort_values("roc_auc_mean", ascending=False)
    )

    fold_path = args.output_dir / f"{run_name}_fold_metrics.tsv"
    summary_path = args.output_dir / f"{run_name}_summary.tsv"
    fold_df.to_csv(fold_path, sep="\t", index=False)
    summary.to_csv(summary_path, sep="\t", index=False)

    if args.save_predictions:
        pred_path = args.output_dir / f"{run_name}_predictions.tsv"
        pd.DataFrame(pred_rows).to_csv(pred_path, sep="\t", index=False)
    if args.save_importances:
        importance_path = args.output_dir / f"{run_name}_feature_importance.tsv"
        pd.DataFrame(importance_rows).to_csv(importance_path, sep="\t", index=False)

    print(f"[ok] Wrote fold metrics: {fold_path}")
    print(f"[ok] Wrote summary: {summary_path}")
    if args.save_predictions:
        print(f"[ok] Wrote predictions: {args.output_dir / f'{run_name}_predictions.tsv'}")
    if args.save_importances:
        print(
            f"[ok] Wrote feature importances: "
            f"{args.output_dir / f'{run_name}_feature_importance.tsv'}"
        )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
