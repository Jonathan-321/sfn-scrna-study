"""
build_clean_features.py — Feature engineering / data cleaning for Kong 2023 composition tables.

Two filtering steps applied in sequence:
  1. Rare-type filter: drop any cell type present in fewer than MIN_PREVALENCE fraction
     of donors (default 0.20 = must appear in at least 20% of donors).
  2. Low-variance filter: drop any cell type with std < STD_THRESHOLD across donors
     in the raw proportion space (default 0.005).

Rationale: the raw Kong composition tables contain 20-25 near-constant features
(std < 0.005) per region. These carry no discriminative information, inflate the
feature space dimensionality relative to n_donors, and can destabilize CFN
dependency matrix inference. Filtering before CLR transformation removes these
without touching the CLR normalization itself.

Outputs:
  data/processed/kong2023_cd/donor_cluster_props_clean.tsv
  data/processed/kong2023_cd/donor_TI_cluster_props_clean.tsv
  data/processed/kong2023_cd/donor_colon_cluster_props_clean.tsv
  data/processed/kong2023_cd/feature_filter_report.tsv   (which features were dropped and why)

Usage:
  python scripts/build_clean_features.py
  python scripts/build_clean_features.py --min-prevalence 0.15 --std-threshold 0.003
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed" / "kong2023_cd"


def filter_composition_table(
    df: pd.DataFrame,
    min_prevalence: float = 0.20,
    std_threshold: float = 0.005,
    table_name: str = "",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply rare-type and low-variance filters to a donor × cell-type composition table.

    Returns:
        df_clean: filtered DataFrame
        report: DataFrame describing each dropped feature and the reason
    """
    n_donors, n_types = df.shape
    report_rows = []

    # ── Step 1: Rare-type filter ───────────────────────────────────────────────
    prevalence = (df > 0).mean(axis=0)  # fraction of donors where this type > 0
    rare_mask = prevalence < min_prevalence
    rare_types = df.columns[rare_mask].tolist()
    for t in rare_types:
        report_rows.append({
            "table": table_name,
            "feature": t,
            "filter": "rare_type",
            "prevalence": round(prevalence[t], 4),
            "std": round(df[t].std(), 6),
            "reason": f"present in {prevalence[t]:.1%} donors < threshold {min_prevalence:.0%}",
        })

    df_after_rare = df.drop(columns=rare_types)

    # ── Step 2: Low-variance filter ───────────────────────────────────────────
    stds = df_after_rare.std(axis=0)
    lowvar_mask = stds < std_threshold
    lowvar_types = df_after_rare.columns[lowvar_mask].tolist()
    for t in lowvar_types:
        report_rows.append({
            "table": table_name,
            "feature": t,
            "filter": "low_variance",
            "prevalence": round(prevalence.get(t, (df_after_rare[t] > 0).mean()), 4),
            "std": round(stds[t], 6),
            "reason": f"std={stds[t]:.6f} < threshold {std_threshold}",
        })

    df_clean = df_after_rare.drop(columns=lowvar_types)

    n_dropped = n_types - df_clean.shape[1]
    print(f"  {table_name}: {n_types} → {df_clean.shape[1]} features "
          f"(dropped {n_dropped}: {len(rare_types)} rare-type, {len(lowvar_types)} low-variance)")

    report = pd.DataFrame(report_rows)
    return df_clean, report


def main(min_prevalence: float = 0.20, std_threshold: float = 0.005):
    configs = [
        ("donor_cluster_props.tsv",       "donor_cluster_props_clean.tsv",       "all"),
        ("donor_TI_cluster_props.tsv",    "donor_TI_cluster_props_clean.tsv",    "TI"),
        ("donor_colon_cluster_props.tsv", "donor_colon_cluster_props_clean.tsv", "colon"),
    ]

    all_reports = []

    for src_name, dst_name, region in configs:
        src = PROCESSED / src_name
        dst = PROCESSED / dst_name

        df = pd.read_csv(src, sep="\t", index_col=0)
        print(f"\n[{region}] Loaded {src_name}: {df.shape[0]} donors × {df.shape[1]} types")

        df_clean, report = filter_composition_table(
            df,
            min_prevalence=min_prevalence,
            std_threshold=std_threshold,
            table_name=region,
        )

        df_clean.to_csv(dst, sep="\t")
        print(f"  Saved → {dst.name}")

        all_reports.append(report)

    # ── Combined filter report ─────────────────────────────────────────────────
    combined_report = pd.concat(all_reports, ignore_index=True)
    report_path = PROCESSED / "feature_filter_report.tsv"
    combined_report.to_csv(report_path, sep="\t", index=False)
    print(f"\nFilter report saved → {report_path.name}")
    print(combined_report.to_string(index=False))

    # ── Summary statistics ─────────────────────────────────────────────────────
    print("\n=== Summary ===")
    for region, grp in combined_report.groupby("table"):
        rare = (grp["filter"] == "rare_type").sum()
        lowvar = (grp["filter"] == "low_variance").sum()
        print(f"  {region}: {rare} rare-type + {lowvar} low-variance = {len(grp)} total dropped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean Kong 2023 composition feature tables.")
    parser.add_argument("--min-prevalence", type=float, default=0.20,
                        help="Min fraction of donors a cell type must appear in (default 0.20)")
    parser.add_argument("--std-threshold", type=float, default=0.005,
                        help="Min std across donors in proportion space (default 0.005)")
    args = parser.parse_args()
    main(min_prevalence=args.min_prevalence, std_threshold=args.std_threshold)
