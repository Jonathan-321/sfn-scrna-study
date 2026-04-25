#!/usr/bin/env python3

"""Build donor-level wide compartment tables from donor-location features."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pivot donor-location feature tables into donor x (location x feature) tables."
    )
    parser.add_argument(
        "--location-metadata",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_location_metadata.tsv"),
        help="Donor-location metadata table.",
    )
    parser.add_argument(
        "--composition-features",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_location_cluster_props.tsv"),
        help="Donor-location composition feature table.",
    )
    parser.add_argument(
        "--pseudobulk-features",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_location_gene_log1p_cpm.tsv.gz"),
        help="Donor-location pseudobulk feature table.",
    )
    parser.add_argument(
        "--output-composition",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_compartment_cluster_props.tsv"),
        help="Output donor-wide compartment composition table.",
    )
    parser.add_argument(
        "--output-pseudobulk",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_compartment_gene_log1p_cpm.tsv.gz"),
        help="Output donor-wide compartment pseudobulk table.",
    )
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


def pivot_wide(feature_df: pd.DataFrame, meta_df: pd.DataFrame) -> pd.DataFrame:
    merged = meta_df[["donor_location_id", "donor_id", "location"]].merge(
        feature_df,
        on="donor_location_id",
        how="inner",
        validate="one_to_one",
    )
    feature_cols = [
        column
        for column in merged.columns
        if column not in {"donor_location_id", "donor_id", "location"}
    ]
    merged[feature_cols] = merged[feature_cols].apply(pd.to_numeric, errors="coerce")
    wide = merged.pivot(index="donor_id", columns="location", values=feature_cols)
    wide.columns = [f"{location}__{feature}" for feature, location in wide.columns]
    wide = wide.reset_index().sort_values("donor_id").reset_index(drop=True)
    return wide


def main() -> None:
    args = parse_args()
    meta_df = load_table(args.location_metadata)
    comp_df = load_table(args.composition_features)
    pseudo_df = load_table(args.pseudobulk_features)

    comp_wide = pivot_wide(comp_df, meta_df)
    pseudo_wide = pivot_wide(pseudo_df, meta_df)

    save_table(comp_wide, args.output_composition)
    save_table(pseudo_wide, args.output_pseudobulk)

    print(f"[ok] Wrote compartment composition table: {args.output_composition} {comp_wide.shape}")
    print(f"[ok] Wrote compartment pseudobulk table: {args.output_pseudobulk} {pseudo_wide.shape}")


if __name__ == "__main__":
    main()
