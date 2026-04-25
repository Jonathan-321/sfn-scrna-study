#!/usr/bin/env python3

"""Run repeated donor-level CV baselines for the UC SCP259 benchmark."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from run_uc_baselines import (
    compute_metrics,
    load_table,
    run_linear_svm,
    run_logreg,
    run_xgb,
    select_top_variance_features,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeated stratified donor-level CV baselines on UC donor tables."
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
        "--output-dir",
        type=Path,
        default=Path("results/uc_scp259/benchmarks"),
        help="Directory for repeated-CV outputs.",
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
        "--n-splits",
        type=int,
        default=5,
        help="Number of CV folds per repeat.",
    )
    parser.add_argument(
        "--n-repeats",
        type=int,
        default=10,
        help="Number of repeated stratified CV runs.",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def repeat_summary(frame: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "roc_auc",
        "pr_auc",
        "balanced_accuracy",
        "macro_f1",
        "runtime_s",
        "n_features_selected",
    ]
    rows: list[dict[str, Any]] = []
    for model_name, part in frame.groupby("model", sort=True):
        row: dict[str, Any] = {"model": model_name, "n_repeats": int(part["repeat"].nunique())}
        for col in numeric_cols:
            values = part[col].to_numpy(dtype=float)
            row[f"{col}_mean"] = float(values.mean())
            row[f"{col}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            row[f"{col}_ci95_low"] = float(np.quantile(values, 0.025))
            row[f"{col}_ci95_high"] = float(np.quantile(values, 0.975))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("roc_auc_mean", ascending=False)


def main() -> None:
    args = parse_args()
    models = [model.strip() for model in args.models.split(",") if model.strip()]
    valid_models = {"logreg", "linear_svm", "xgb"}
    unknown = set(models) - valid_models
    if unknown:
        raise ValueError(f"Unsupported model(s): {sorted(unknown)}")

    features = load_table(args.features)
    donor_meta = load_table(args.metadata)

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
    ids = dataset[args.id_col].astype(str).to_numpy()
    feature_cols = [column for column in dataset.columns if column not in {args.id_col, args.label_col}]
    x = dataset[feature_cols].apply(pd.to_numeric, errors="coerce")

    class_counts = pd.Series(y).value_counts().to_dict()
    minority_count = min(class_counts.values())
    if args.n_splits > minority_count:
        raise ValueError(
            f"Cannot build {args.n_splits} folds because the minority class only has "
            f"{minority_count} donors."
        )

    run_name = args.run_name or args.features.name.replace(".tsv.gz", "").replace(".tsv", "")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    fold_rows: list[dict[str, Any]] = []

    for repeat_idx in range(args.n_repeats):
        splitter = StratifiedKFold(
            n_splits=args.n_splits,
            shuffle=True,
            random_state=args.seed + repeat_idx,
        )

        for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(ids, y)):
            x_train, x_test, selected = select_top_variance_features(
                x.iloc[train_idx],
                x.iloc[test_idx],
                max_features=args.max_features,
            )
            y_train = y[train_idx]
            y_test = y[test_idx]

            for model_name in models:
                start = time.time()
                model_seed = args.seed + repeat_idx
                if model_name == "logreg":
                    prob, pred, _ = run_logreg(x_train, y_train, x_test, model_seed)
                elif model_name == "linear_svm":
                    prob, pred, _ = run_linear_svm(x_train, y_train, x_test, model_seed)
                else:
                    prob, pred, _ = run_xgb(x_train, y_train, x_test, model_seed)

                metrics = compute_metrics(y_test, prob, pred)
                fold_rows.append(
                    {
                        "repeat": int(repeat_idx),
                        "fold": int(fold_idx),
                        "model": model_name,
                        "train_size": int(len(train_idx)),
                        "test_size": int(len(test_idx)),
                        "test_positive_rate": float(y_test.mean()),
                        "runtime_s": float(time.time() - start),
                        "n_features_selected": int(len(selected)),
                        **metrics,
                    }
                )

    fold_df = pd.DataFrame(fold_rows).sort_values(["model", "repeat", "fold"]).reset_index(drop=True)
    repeat_df = (
        fold_df.groupby(["model", "repeat"], as_index=False)
        .agg(
            roc_auc=("roc_auc", "mean"),
            pr_auc=("pr_auc", "mean"),
            balanced_accuracy=("balanced_accuracy", "mean"),
            macro_f1=("macro_f1", "mean"),
            runtime_s=("runtime_s", "sum"),
            n_features_selected=("n_features_selected", "mean"),
        )
        .sort_values(["model", "repeat"])
        .reset_index(drop=True)
    )
    summary_df = repeat_summary(repeat_df)

    fold_path = args.output_dir / f"{run_name}_repeated_fold_metrics.tsv"
    repeat_path = args.output_dir / f"{run_name}_repeated_repeat_summary.tsv"
    summary_path = args.output_dir / f"{run_name}_repeated_summary.tsv"

    fold_df.to_csv(fold_path, sep="\t", index=False)
    repeat_df.to_csv(repeat_path, sep="\t", index=False)
    summary_df.to_csv(summary_path, sep="\t", index=False)

    print(f"[ok] Wrote repeated fold metrics: {fold_path}")
    print(f"[ok] Wrote repeat summary: {repeat_path}")
    print(f"[ok] Wrote repeated summary: {summary_path}")
    with pd.option_context("display.max_columns", None, "display.width", 160):
        print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
