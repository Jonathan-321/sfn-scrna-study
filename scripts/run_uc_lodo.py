#!/usr/bin/env python3

"""Run leave-one-donor-out baselines for the UC SCP259 benchmark."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneOut

from run_uc_baselines import (
    load_table,
    run_linear_svm,
    run_logreg,
    run_xgb,
    select_top_variance_features,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run leave-one-donor-out baseline models on UC donor tables."
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
        help="Directory for LODO outputs.",
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
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


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

    loo = LeaveOneOut()
    run_name = args.run_name or args.features.name.replace(".tsv.gz", "").replace(".tsv", "")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pred_rows = []

    for fold_idx, (train_idx, test_idx) in enumerate(loo.split(x, y)):
        x_train, x_test, selected = select_top_variance_features(
            x.iloc[train_idx],
            x.iloc[test_idx],
            max_features=args.max_features,
        )
        y_train = y[train_idx]
        y_test = y[test_idx]
        donor_id = ids[test_idx][0]

        for model_name in models:
            start = time.time()
            if model_name == "logreg":
                prob, pred, _ = run_logreg(x_train, y_train, x_test, args.seed)
            elif model_name == "linear_svm":
                prob, pred, _ = run_linear_svm(x_train, y_train, x_test, args.seed)
            else:
                prob, pred, _ = run_xgb(x_train, y_train, x_test, args.seed)

            pred_rows.append(
                {
                    "fold": int(fold_idx),
                    "model": model_name,
                    "donor_id": donor_id,
                    "y_true": int(y_test[0]),
                    "y_pred": int(pred[0]),
                    "y_prob": float(prob[0]),
                    "correct": int(pred[0] == y_test[0]),
                    "runtime_s": float(time.time() - start),
                    "n_features_selected": int(len(selected)),
                }
            )

    pred_df = pd.DataFrame(pred_rows).sort_values(["model", "fold"]).reset_index(drop=True)

    summary_rows = []
    for model_name, part in pred_df.groupby("model", sort=True):
        y_true = part["y_true"].to_numpy()
        y_prob = part["y_prob"].to_numpy()
        y_pred = part["y_pred"].to_numpy()
        summary_rows.append(
            {
                "model": model_name,
                "n_test_donors": int(len(part)),
                "roc_auc": float(roc_auc_score(y_true, y_prob)),
                "pr_auc": float(average_precision_score(y_true, y_prob)),
                "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
                "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
                "accuracy": float(part["correct"].mean()),
                "runtime_total_s": float(part["runtime_s"].sum()),
                "runtime_mean_s": float(part["runtime_s"].mean()),
                "n_features_selected_mean": float(part["n_features_selected"].mean()),
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values("roc_auc", ascending=False)

    pred_path = args.output_dir / f"{run_name}_lodo_predictions.tsv"
    summary_path = args.output_dir / f"{run_name}_lodo_summary.tsv"
    pred_df.to_csv(pred_path, sep="\t", index=False)
    summary_df.to_csv(summary_path, sep="\t", index=False)

    print(f"[ok] Wrote LODO predictions: {pred_path}")
    print(f"[ok] Wrote LODO summary: {summary_path}")
    with pd.option_context("display.max_columns", None, "display.width", 160):
        print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
