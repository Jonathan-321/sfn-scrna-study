#!/usr/bin/env python3

"""Build a starter biological annotation table for recurring UC CFN edges."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


EPITHELIAL = {
    "Best4+ Enterocytes",
    "Enterocyte Progenitors",
    "Enterocytes",
    "Enteroendocrine",
    "Goblet",
    "Immature Enterocytes 1",
    "Immature Enterocytes 2",
    "Immature Goblet",
    "M cells",
    "Secretory TA",
    "Stem",
    "TA 1",
    "TA 2",
    "Cycling TA",
    "Tuft",
}

IMMUNE = {
    "CD4+ Activated Fos-hi",
    "CD4+ Activated Fos-lo",
    "CD4+ Memory",
    "CD4+ PD1+",
    "CD69+ Mast",
    "CD69- Mast",
    "CD8+ IELs",
    "CD8+ IL17+",
    "CD8+ LP",
    "Cycling B",
    "Cycling Monocytes",
    "Cycling T",
    "DC1",
    "DC2",
    "Follicular",
    "GC",
    "ILCs",
    "Inflammatory Monocytes",
    "Macrophages",
    "NKs",
    "Plasma",
    "Tregs",
}

STROMAL = {
    "Endothelial",
    "Glia",
    "Inflammatory Fibroblasts",
    "Microvascular",
    "Myofibroblasts",
    "Pericytes",
    "Post-capillary Venules",
    "RSPO3+",
    "WNT2B+ Fos-hi",
    "WNT2B+ Fos-lo 1",
    "WNT2B+ Fos-lo 2",
    "WNT5B+ 1",
    "WNT5B+ 2",
}

CAUTIONARY = {"MT-hi"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a starter biological annotation table for recurring CFN edges."
    )
    parser.add_argument(
        "--donor-global-support",
        type=Path,
        default=Path("results/uc_scp259/cfn_benchmarks/donor_cluster_props_cfn_full_consensus_edge_support.csv"),
    )
    parser.add_argument(
        "--compartment-support",
        type=Path,
        default=Path("results/uc_scp259/cfn_benchmarks/donor_compartment_cluster_props_cfn_full_consensus_edge_support.csv"),
    )
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--level", default="raw", choices=["raw", "grouped"])
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_starter.csv"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_starter.md"),
    )
    return parser.parse_args()


def split_edge_label(label: str) -> tuple[str, str]:
    source, target = label.split("->", maxsplit=1)
    return source, target


def split_compartment(feature_name: str) -> tuple[str, str]:
    if "__" in feature_name:
        compartment, feature = feature_name.split("__", maxsplit=1)
        return compartment, feature
    return "global", feature_name


def lineage_for(feature_name: str) -> str:
    if feature_name in EPITHELIAL:
        return "epithelial"
    if feature_name in IMMUNE:
        return "immune"
    if feature_name in STROMAL:
        return "stromal"
    if feature_name in CAUTIONARY:
        return "cautionary"
    return "unclear"


def theme_for(source_feature: str, target_feature: str, source_lineage: str, target_lineage: str) -> str:
    if "MT-hi" in {source_feature, target_feature}:
        return "stress-associated / caution"
    if source_lineage == target_lineage == "epithelial":
        return "epithelial regeneration / differentiation"
    if {source_lineage, target_lineage} == {"epithelial", "immune"}:
        return "epithelial-immune crosstalk"
    if {source_lineage, target_lineage} == {"epithelial", "stromal"}:
        return "epithelial-stromal remodeling"
    if {source_lineage, target_lineage} == {"immune", "stromal"}:
        return "immune-stromal interaction"
    if source_lineage == target_lineage == "immune":
        return "immune regulation"
    if source_lineage == target_lineage == "stromal":
        return "stromal niche / vascular remodeling"
    return "unclear"


def plausibility_for(source_feature: str, target_feature: str, theme: str) -> str:
    if "MT-hi" in {source_feature, target_feature}:
        return "caution"
    if source_feature == "Stem" and target_feature.startswith("Immature Enterocytes"):
        return "highly_plausible"
    if source_feature == "Enterocyte Progenitors" and target_feature in {"ILCs", "Myofibroblasts"}:
        return "highly_plausible"
    if source_feature == "RSPO3+" and target_feature == "CD8+ IELs":
        return "plausible"
    if source_feature == "Tuft" and target_feature == "TA 2":
        return "plausible"
    if theme in {
        "epithelial regeneration / differentiation",
        "epithelial-immune crosstalk",
        "epithelial-stromal remodeling",
    }:
        return "plausible"
    if theme == "unclear":
        return "unclear"
    return "plausible"


def rationale_for(source_feature: str, target_feature: str, theme: str) -> str:
    if source_feature == "Stem" and target_feature.startswith("Immature Enterocytes"):
        return "Direct epithelial stem-to-immature enterocyte axis; consistent with regeneration/remodeling."
    if source_feature == "Enterocyte Progenitors" and target_feature == "ILCs":
        return "Links epithelial progenitor stress with innate lymphoid response in mucosal inflammation."
    if source_feature == "Enterocyte Progenitors" and target_feature == "Myofibroblasts":
        return "Matches epithelial-stromal niche remodeling around crypt injury and repair."
    if source_feature == "RSPO3+" and target_feature == "CD8+ IELs":
        return "Stromal niche support paired with intraepithelial immune dysregulation is biologically suggestive in UC."
    if source_feature == "Tuft" and target_feature == "TA 2":
        return "Both are epithelial-state terms; may reflect remodeling of differentiation programs after injury."
    if "MT-hi" in {source_feature, target_feature}:
        return "Contains a stress-associated state; interpret cautiously."
    if theme == "epithelial-immune crosstalk":
        return "Cross-lineage epithelial and immune interaction is plausible in inflamed mucosa."
    if theme == "epithelial-stromal remodeling":
        return "Cross-lineage epithelial and stromal interaction is plausible in tissue remodeling."
    if theme == "epithelial regeneration / differentiation":
        return "Within-epithelial relation is plausible in regeneration and differentiation programs."
    if theme == "immune regulation":
        return "Within-immune relation is plausible but needs manual review."
    if theme == "stromal niche / vascular remodeling":
        return "Within-stromal/vascular relation is plausible but needs manual review."
    return "Needs manual biological review."


def markdown_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    widths = {}
    for col in cols:
        vals = [str(col)] + [str(v) for v in df[col].tolist()]
        widths[col] = max(len(v) for v in vals)

    def fmt(values: list[str]) -> str:
        parts = [f" {value.ljust(widths[col])} " for col, value in zip(cols, values, strict=True)]
        return "|" + "|".join(parts) + "|"

    header = fmt([str(c) for c in cols])
    sep = "|" + "|".join("-" * (widths[c] + 2) for c in cols) + "|"
    rows = [fmt([str(v) for v in row]) for row in df.itertuples(index=False, name=None)]
    return "\n".join([header, sep] + rows)


def load_and_annotate(path: Path, run_name: str, min_support: int, level: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[(df["support_count"] >= min_support) & (df["level"] == level)].copy()
    if df.empty:
        return pd.DataFrame()

    rows = []
    for row in df.to_dict(orient="records"):
        source_label, target_label = split_edge_label(row["edge_label"])
        source_compartment, source_feature = split_compartment(source_label)
        target_compartment, target_feature = split_compartment(target_label)
        source_lineage = lineage_for(source_feature)
        target_lineage = lineage_for(target_feature)
        theme = theme_for(source_feature, target_feature, source_lineage, target_lineage)
        plausibility = plausibility_for(source_feature, target_feature, theme)
        rationale = rationale_for(source_feature, target_feature, theme)
        rows.append(
            {
                "run": run_name,
                "level": row["level"],
                "edge_label": row["edge_label"],
                "support_count": int(row["support_count"]),
                "support_fraction": float(row["support_fraction"]),
                "source_compartment": source_compartment,
                "target_compartment": target_compartment,
                "source_feature": source_feature,
                "target_feature": target_feature,
                "source_lineage": source_lineage,
                "target_lineage": target_lineage,
                "biological_theme": theme,
                "plausibility_seed": plausibility,
                "rationale_seed": rationale,
                "manual_notes": "",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    donor_df = load_and_annotate(
        path=args.donor_global_support,
        run_name="donor_global_composition",
        min_support=args.min_support,
        level=args.level,
    )
    compartment_df = load_and_annotate(
        path=args.compartment_support,
        run_name="compartment_composition",
        min_support=args.min_support,
        level=args.level,
    )
    out = pd.concat([donor_df, compartment_df], ignore_index=True)
    if out.empty:
        raise ValueError("No edges matched the requested support threshold and level.")

    out = out.sort_values(["run", "support_count", "edge_label"], ascending=[True, False, True]).reset_index(drop=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_csv, index=False)

    md_cols = [
        "run",
        "edge_label",
        "support_count",
        "biological_theme",
        "plausibility_seed",
        "rationale_seed",
    ]
    lines = [
        "# UC Recurring CFN Edge Annotation Starter",
        "",
        f"- Minimum support: `{args.min_support}`",
        f"- Level: `{args.level}`",
        "",
        markdown_table(out[md_cols]),
        "",
    ]
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"[ok] Wrote annotation starter CSV: {args.output_csv}")
    print(f"[ok] Wrote annotation starter markdown: {args.output_md}")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(out.to_string(index=False))


if __name__ == "__main__":
    main()
