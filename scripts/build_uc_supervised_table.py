#!/usr/bin/env python3

"""Build a model-ready donor table with binary target from donor features."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge donor labels into a feature table and emit a model-ready supervised table."
    )
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Donor-level feature table containing donor_id.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_metadata.tsv"),
        help="Donor metadata table with donor labels.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output CSV/TSV path.",
    )
    parser.add_argument("--id-col", default="donor_id")
    parser.add_argument("--label-col", default="donor_label")
    parser.add_argument("--positive-label", default="UC")
    parser.add_argument("--target-col", default="uc_binary")
    return parser.parse_args()


def load_table(path: Path) -> pd.DataFrame:
    suffix = "".join(path.suffixes[-2:]) if len(path.suffixes) >= 2 else path.suffix
    if suffix in {".tsv", ".tsv.gz"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".csv", ".csv.gz"}:
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table format for {path}")


def save_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = "".join(path.suffixes[-2:]) if len(path.suffixes) >= 2 else path.suffix
    if suffix in {".tsv", ".tsv.gz"}:
        df.to_csv(path, sep="\t", index=False)
        return
    if suffix in {".csv", ".csv.gz"}:
        df.to_csv(path, index=False)
        return
    raise ValueError(f"Unsupported output format for {path}")


def main() -> None:
    args = parse_args()
    features = load_table(args.features)
    meta = load_table(args.metadata)

    if args.id_col not in features.columns:
        raise ValueError(f"Feature table missing '{args.id_col}'")
    if args.id_col not in meta.columns or args.label_col not in meta.columns:
        raise ValueError(f"Metadata table must contain '{args.id_col}' and '{args.label_col}'")

    dataset = meta[[args.id_col, args.label_col]].merge(
        features, on=args.id_col, how="inner", validate="one_to_one"
    )
    dataset[args.target_col] = (dataset[args.label_col] == args.positive_label).astype(int)
    feature_cols = [
        column
        for column in dataset.columns
        if column not in {args.id_col, args.label_col, args.target_col}
    ]
    dataset[feature_cols] = dataset[feature_cols].apply(pd.to_numeric, errors="coerce")
    output_df = dataset[[args.id_col, args.target_col] + feature_cols].copy()
    save_table(output_df, args.output)

    print(f"[ok] Wrote supervised table: {args.output} {output_df.shape}")


if __name__ == "__main__":
    main()
