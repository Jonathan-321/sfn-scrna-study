#!/usr/bin/env python3

"""Generate foundation-level UC dataset summaries before modeling."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


CLUSTER_LOG2_FC_PSEUDOCOUNT = 1e-6

CLUSTER_FAMILY_MAP = {
    "Best4+ Enterocytes": "epithelial",
    "CD4+ Activated Fos-hi": "immune",
    "CD4+ Activated Fos-lo": "immune",
    "CD4+ Memory": "immune",
    "CD4+ PD1+": "immune",
    "CD69+ Mast": "immune",
    "CD69- Mast": "immune",
    "CD8+ IELs": "immune",
    "CD8+ IL17+": "immune",
    "CD8+ LP": "immune",
    "Cycling B": "immune",
    "Cycling Monocytes": "immune",
    "Cycling T": "immune",
    "Cycling TA": "epithelial",
    "DC1": "immune",
    "DC2": "immune",
    "Endothelial": "stromal_vascular_neural",
    "Enterocyte Progenitors": "epithelial",
    "Enterocytes": "epithelial",
    "Enteroendocrine": "epithelial",
    "Follicular": "immune",
    "GC": "immune",
    "Glia": "stromal_vascular_neural",
    "Goblet": "epithelial",
    "ILCs": "immune",
    "Immature Enterocytes 1": "epithelial",
    "Immature Enterocytes 2": "epithelial",
    "Immature Goblet": "epithelial",
    "Inflammatory Fibroblasts": "stromal_vascular_neural",
    "Inflammatory Monocytes": "immune",
    "M cells": "epithelial",
    "MT-hi": "cautionary_state",
    "Macrophages": "immune",
    "Microvascular": "stromal_vascular_neural",
    "Myofibroblasts": "stromal_vascular_neural",
    "NKs": "immune",
    "Pericytes": "stromal_vascular_neural",
    "Plasma": "immune",
    "Post-capillary Venules": "stromal_vascular_neural",
    "RSPO3+": "stromal_vascular_neural",
    "Secretory TA": "epithelial",
    "Stem": "epithelial",
    "TA 1": "epithelial",
    "TA 2": "epithelial",
    "Tregs": "immune",
    "Tuft": "epithelial",
    "WNT2B+ Fos-hi": "stromal_vascular_neural",
    "WNT2B+ Fos-lo 1": "stromal_vascular_neural",
    "WNT2B+ Fos-lo 2": "stromal_vascular_neural",
    "WNT5B+ 1": "stromal_vascular_neural",
    "WNT5B+ 2": "stromal_vascular_neural",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write UC donor, sample, location, and cluster exploration tables."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/uc_scp259"),
        help="Directory containing all.meta2.txt",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed/uc_scp259"),
        help="Directory containing donor tables",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/uc_scp259/exploration"),
        help="Directory where exploration outputs will be written",
    )
    return parser.parse_args()


def check_required_files(raw_dir: Path, processed_dir: Path) -> None:
    required = {
        raw_dir / "all.meta2.txt": "Missing raw metadata file. Build or copy the UC raw files first.",
        processed_dir
        / "donor_metadata.tsv": "Missing donor metadata. Run scripts/build_uc_donor_tables.py first.",
        processed_dir
        / "donor_cluster_counts.tsv": "Missing donor cluster counts. Run scripts/build_uc_donor_tables.py first.",
        processed_dir
        / "donor_cluster_props.tsv": "Missing donor cluster proportions. Run scripts/build_uc_donor_tables.py first.",
    }
    missing = [(path, message) for path, message in required.items() if not path.exists()]
    if missing:
        details = "\n".join(f"- {path}: {message}" for path, message in missing)
        raise FileNotFoundError(f"Required UC inputs are missing:\n{details}")


def load_cell_metadata(metadata_path: Path) -> pd.DataFrame:
    metadata = pd.read_csv(metadata_path, sep="\t", skiprows=[1])
    metadata = metadata.rename(
        columns={
            "NAME": "cell_id",
            "Cluster": "cluster",
            "nGene": "n_gene",
            "nUMI": "n_umi",
            "Subject": "donor_id",
            "Health": "sample_health",
            "Location": "location",
            "Sample": "sample_id",
        }
    )
    return metadata


def load_sample_overview(cell_metadata: pd.DataFrame) -> pd.DataFrame:
    sample_df = (
        cell_metadata[["sample_id", "donor_id", "sample_health", "location"]]
        .drop_duplicates()
        .sort_values(["donor_id", "sample_id"])
        .reset_index(drop=True)
    )
    return sample_df


def median_abs_deviation(series: pd.Series) -> float:
    median = series.median()
    return float((series - median).abs().median())


def build_donor_dispersion_summary(donor_meta: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "n_cells",
        "n_samples",
        "total_nUMI_obs",
        "mean_nUMI_obs",
        "mean_nGene_obs",
    ]
    rows: list[dict[str, object]] = []
    for donor_label, subset in donor_meta.groupby("donor_label"):
        for metric in metrics:
            values = subset[metric]
            rows.append(
                {
                    "donor_label": donor_label,
                    "metric": metric,
                    "count": int(values.shape[0]),
                    "mean": float(values.mean()),
                    "std": float(values.std(ddof=1)),
                    "median": float(values.median()),
                    "mad": median_abs_deviation(values),
                    "min": float(values.min()),
                    "max": float(values.max()),
                }
            )
    return pd.DataFrame(rows)


def build_donor_location_tables(
    donor_meta: pd.DataFrame, cell_metadata: pd.DataFrame, sample_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    donor_cell_location_counts = pd.crosstab(cell_metadata["donor_id"], cell_metadata["location"])
    donor_cell_location_counts.index.name = "donor_id"
    donor_cell_location_props = donor_cell_location_counts.div(
        donor_cell_location_counts.sum(axis=1), axis=0
    ).round(8)
    donor_cell_location_props.index.name = "donor_id"

    donor_sample_location_counts = pd.crosstab(sample_df["donor_id"], sample_df["location"])
    donor_sample_location_counts.index.name = "donor_id"

    donor_location_overview = donor_meta[
        ["donor_id", "donor_label", "n_cells", "n_samples"]
    ].merge(
        donor_cell_location_counts.reset_index().rename(
            columns={"Epi": "n_cells_epi", "LP": "n_cells_lp"}
        ),
        on="donor_id",
        how="left",
    ).merge(
        donor_cell_location_props.reset_index().rename(
            columns={"Epi": "prop_cells_epi", "LP": "prop_cells_lp"}
        ),
        on="donor_id",
        how="left",
    ).merge(
        donor_sample_location_counts.reset_index().rename(
            columns={"Epi": "n_samples_epi", "LP": "n_samples_lp"}
        ),
        on="donor_id",
        how="left",
    )
    donor_location_overview["location_profile"] = donor_location_overview.apply(
        lambda row: "LP_only"
        if row["n_cells_epi"] == 0
        else "Epi_only"
        if row["n_cells_lp"] == 0
        else "Mixed",
        axis=1,
    )
    return (
        donor_sample_location_counts,
        donor_cell_location_counts,
        donor_cell_location_props,
        donor_location_overview,
    )


def build_cluster_label_summary(
    donor_meta: pd.DataFrame, cluster_counts: pd.DataFrame, cluster_props: pd.DataFrame
) -> pd.DataFrame:
    cluster_long = cluster_props.merge(
        donor_meta[["donor_id", "donor_label"]], on="donor_id", how="left"
    )
    value_columns = [
        col for col in cluster_long.columns if col not in {"donor_id", "donor_label"}
    ]
    cluster_means = cluster_long.groupby("donor_label")[value_columns].mean().T
    cluster_means = cluster_means.rename(
        columns={"Healthy": "mean_prop_healthy", "UC": "mean_prop_uc"}
    )
    cluster_means["delta_uc_minus_healthy"] = (
        cluster_means["mean_prop_uc"] - cluster_means["mean_prop_healthy"]
    )
    cluster_means["abs_delta"] = cluster_means["delta_uc_minus_healthy"].abs()
    cluster_means["log2_fc_uc_vs_healthy"] = np.log2(
        (cluster_means["mean_prop_uc"] + CLUSTER_LOG2_FC_PSEUDOCOUNT)
        / (cluster_means["mean_prop_healthy"] + CLUSTER_LOG2_FC_PSEUDOCOUNT)
    )
    cluster_means["abs_log2_fc_uc_vs_healthy"] = cluster_means[
        "log2_fc_uc_vs_healthy"
    ].abs()
    cluster_means["n_donors_present"] = (
        cluster_counts.set_index("donor_id")[value_columns] > 0
    ).sum(axis=0).values
    cluster_means.index.name = "cluster"
    cluster_means = cluster_means.sort_values(
        ["abs_delta", "abs_log2_fc_uc_vs_healthy"], ascending=False
    )
    return cluster_means.reset_index()


def build_cluster_family_outputs(
    donor_meta: pd.DataFrame, cluster_counts: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cluster_columns = [col for col in cluster_counts.columns if col != "donor_id"]
    unmapped = sorted(set(cluster_columns) - set(CLUSTER_FAMILY_MAP))
    if unmapped:
        raise ValueError(f"Unmapped UC clusters found: {unmapped}")

    family_map = pd.DataFrame(
        [
            {"cluster": cluster, "coarse_family": CLUSTER_FAMILY_MAP[cluster]}
            for cluster in cluster_columns
        ]
    ).sort_values(["coarse_family", "cluster"])

    family_counts = (
        cluster_counts.set_index("donor_id")
        .T.assign(coarse_family=lambda frame: frame.index.map(CLUSTER_FAMILY_MAP))
        .groupby("coarse_family")
        .sum()
        .T.reset_index()
        .rename(columns={"index": "donor_id"})
    )
    family_value_columns = [col for col in family_counts.columns if col != "donor_id"]
    family_props = family_counts.copy()
    family_props[family_value_columns] = (
        family_props[family_value_columns]
        .div(family_props[family_value_columns].sum(axis=1), axis=0)
        .round(8)
    )

    family_long = family_props.merge(
        donor_meta[["donor_id", "donor_label"]], on="donor_id", how="left"
    )
    family_label_means = (
        family_long.groupby("donor_label")[family_value_columns].mean().T.rename(
            columns={"Healthy": "mean_prop_healthy", "UC": "mean_prop_uc"}
        )
    )
    family_label_means["delta_uc_minus_healthy"] = (
        family_label_means["mean_prop_uc"] - family_label_means["mean_prop_healthy"]
    )
    family_label_means["abs_delta"] = family_label_means["delta_uc_minus_healthy"].abs()
    family_label_means["log2_fc_uc_vs_healthy"] = np.log2(
        (family_label_means["mean_prop_uc"] + CLUSTER_LOG2_FC_PSEUDOCOUNT)
        / (family_label_means["mean_prop_healthy"] + CLUSTER_LOG2_FC_PSEUDOCOUNT)
    )
    family_label_means["abs_log2_fc_uc_vs_healthy"] = family_label_means[
        "log2_fc_uc_vs_healthy"
    ].abs()
    family_label_means = family_label_means.sort_values(
        ["abs_delta", "abs_log2_fc_uc_vs_healthy"], ascending=False
    )
    family_label_means.index.name = "coarse_family"

    return (
        family_map.reset_index(drop=True),
        family_counts,
        family_props,
        family_label_means.reset_index(),
    )


def write_summary_tables(raw_dir: Path, processed_dir: Path, output_dir: Path) -> None:
    check_required_files(raw_dir=raw_dir, processed_dir=processed_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    donor_meta = pd.read_csv(processed_dir / "donor_metadata.tsv", sep="\t")
    cluster_counts = pd.read_csv(processed_dir / "donor_cluster_counts.tsv", sep="\t")
    cluster_props = pd.read_csv(processed_dir / "donor_cluster_props.tsv", sep="\t")
    cell_metadata = load_cell_metadata(raw_dir / "all.meta2.txt")
    sample_df = load_sample_overview(cell_metadata)

    sample_counts_by_health_location = (
        sample_df.groupby(["sample_health", "location"])
        .size()
        .reset_index(name="n_samples")
        .sort_values(["sample_health", "location"])
    )

    donor_health_mix = (
        sample_df.groupby("donor_id")["sample_health"]
        .agg(lambda values: ",".join(sorted(set(values))))
        .reset_index(name="sample_health_values")
    )
    donor_sample_health_counts = pd.crosstab(
        sample_df["donor_id"], sample_df["sample_health"]
    )
    donor_sample_health_counts.index.name = "donor_id"

    donor_dispersion = build_donor_dispersion_summary(donor_meta)
    (
        donor_sample_location_counts,
        donor_cell_location_counts,
        donor_cell_location_props,
        donor_location_overview,
    ) = (
        build_donor_location_tables(
            donor_meta=donor_meta, cell_metadata=cell_metadata, sample_df=sample_df
        )
    )
    cluster_label_summary = build_cluster_label_summary(
        donor_meta=donor_meta, cluster_counts=cluster_counts, cluster_props=cluster_props
    )
    (
        cluster_family_map,
        donor_cluster_family_counts,
        donor_cluster_family_props,
        cluster_family_label_summary,
    ) = build_cluster_family_outputs(donor_meta=donor_meta, cluster_counts=cluster_counts)
    donor_n_cells_ranked = donor_meta.sort_values("n_cells", ascending=False)

    sample_df.to_csv(output_dir / "sample_overview.tsv", sep="\t", index=False)
    sample_counts_by_health_location.to_csv(
        output_dir / "sample_counts_by_health_location.tsv", sep="\t", index=False
    )
    donor_health_mix.to_csv(output_dir / "donor_sample_health_mix.tsv", sep="\t", index=False)
    donor_sample_health_counts.to_csv(
        output_dir / "donor_sample_health_counts.tsv", sep="\t"
    )
    donor_sample_location_counts.to_csv(
        output_dir / "donor_sample_location_counts.tsv", sep="\t"
    )
    donor_dispersion.to_csv(output_dir / "donor_dispersion_summary.tsv", sep="\t", index=False)
    donor_cell_location_counts.to_csv(
        output_dir / "donor_cell_location_counts.tsv", sep="\t"
    )
    donor_cell_location_props.to_csv(
        output_dir / "donor_cell_location_props.tsv", sep="\t", float_format="%.8f"
    )
    donor_location_overview.to_csv(
        output_dir / "donor_location_overview.tsv", sep="\t", index=False
    )
    cluster_family_map.to_csv(output_dir / "cluster_family_map.tsv", sep="\t", index=False)
    donor_cluster_family_counts.to_csv(
        output_dir / "donor_cluster_family_counts.tsv", sep="\t", index=False
    )
    donor_cluster_family_props.to_csv(
        output_dir / "donor_cluster_family_props.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    cluster_family_label_summary.to_csv(
        output_dir / "cluster_family_label_deltas.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    cluster_label_summary.to_csv(
        output_dir / "cluster_label_mean_deltas.tsv", sep="\t", index=False, float_format="%.8f"
    )
    donor_n_cells_ranked.to_csv(output_dir / "donor_ranked_by_n_cells.tsv", sep="\t", index=False)

    healthy_n_cells = donor_meta.loc[donor_meta["donor_label"] == "Healthy", "n_cells"]
    uc_n_cells = donor_meta.loc[donor_meta["donor_label"] == "UC", "n_cells"]
    healthy_n_samples = donor_meta.loc[donor_meta["donor_label"] == "Healthy", "n_samples"]
    uc_n_samples = donor_meta.loc[donor_meta["donor_label"] == "UC", "n_samples"]
    lp_only_donors = donor_location_overview.loc[
        donor_location_overview["location_profile"] == "LP_only", "donor_id"
    ].tolist()

    summary_lines = [
        "UC foundation summary",
        f"donors\t{donor_meta['donor_id'].nunique()}",
        f"healthy_donors\t{(donor_meta['donor_label'] == 'Healthy').sum()}",
        f"uc_donors\t{(donor_meta['donor_label'] == 'UC').sum()}",
        f"samples\t{sample_df['sample_id'].nunique()}",
        f"samples_healthy\t{(sample_df['sample_health'] == 'Healthy').sum()}",
        f"samples_non_inflamed\t{(sample_df['sample_health'] == 'Non-inflamed').sum()}",
        f"samples_inflamed\t{(sample_df['sample_health'] == 'Inflamed').sum()}",
        f"samples_epi\t{(sample_df['location'] == 'Epi').sum()}",
        f"samples_lp\t{(sample_df['location'] == 'LP').sum()}",
        f"clusters\t{cluster_props.shape[1] - 1}",
        f"coarse_families\t{len([col for col in donor_cluster_family_props.columns if col != 'donor_id'])}",
        f"largest_donor\t{donor_n_cells_ranked.iloc[0]['donor_id']}",
        f"largest_donor_cells\t{donor_n_cells_ranked.iloc[0]['n_cells']}",
        f"healthy_n_cells_mean\t{healthy_n_cells.mean():.2f}",
        f"healthy_n_cells_std\t{healthy_n_cells.std(ddof=1):.2f}",
        f"healthy_n_cells_median\t{healthy_n_cells.median():.2f}",
        f"healthy_n_cells_mad\t{median_abs_deviation(healthy_n_cells):.2f}",
        f"uc_n_cells_mean\t{uc_n_cells.mean():.2f}",
        f"uc_n_cells_std\t{uc_n_cells.std(ddof=1):.2f}",
        f"uc_n_cells_median\t{uc_n_cells.median():.2f}",
        f"uc_n_cells_mad\t{median_abs_deviation(uc_n_cells):.2f}",
        f"healthy_n_samples_mean\t{healthy_n_samples.mean():.2f}",
        f"healthy_n_samples_std\t{healthy_n_samples.std(ddof=1):.2f}",
        f"uc_n_samples_mean\t{uc_n_samples.mean():.2f}",
        f"uc_n_samples_std\t{uc_n_samples.std(ddof=1):.2f}",
        f"lp_only_donors\t{','.join(lp_only_donors) if lp_only_donors else 'None'}",
    ]
    (output_dir / "foundation_summary.txt").write_text("\n".join(summary_lines) + "\n")


def main() -> None:
    args = parse_args()
    write_summary_tables(
        raw_dir=args.raw_dir.resolve(),
        processed_dir=args.processed_dir.resolve(),
        output_dir=args.output_dir.resolve(),
    )


if __name__ == "__main__":
    main()
