#!/usr/bin/env python3

"""Build a single donor-global composition vs pseudobulk comparison table."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble donor-global comparison tables across representations and protocols."
    )
    parser.add_argument(
        "--composition-repeated",
        type=Path,
        default=Path("results/uc_scp259/benchmarks/donor_cluster_props_repeated_summary.tsv"),
    )
    parser.add_argument(
        "--composition-lodo",
        type=Path,
        default=Path("results/uc_scp259/benchmarks/donor_cluster_props_lodo_summary.tsv"),
    )
    parser.add_argument(
        "--pseudobulk-repeated",
        type=Path,
        default=Path("results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_repeated_summary.tsv"),
    )
    parser.add_argument(
        "--pseudobulk-lodo",
        type=Path,
        default=Path("results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_lodo_summary.tsv"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("results/uc_scp259/benchmarks/donor_global_representation_comparison.csv"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("results/uc_scp259/benchmarks/donor_global_representation_comparison.md"),
    )
    return parser.parse_args()


def markdown_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    widths = {}
    for col in cols:
        values = [str(col)] + [str(v) for v in df[col].tolist()]
        widths[col] = max(len(v) for v in values)

    def fmt_row(values: list[str]) -> str:
        parts = [f" {value.ljust(widths[col])} " for col, value in zip(cols, values, strict=True)]
        return "|" + "|".join(parts) + "|"

    header = fmt_row([str(col) for col in cols])
    sep = "|" + "|".join("-" * (widths[col] + 2) for col in cols) + "|"
    rows = [fmt_row([str(v) for v in row]) for row in df.itertuples(index=False, name=None)]
    return "\n".join([header, sep] + rows)


def main() -> None:
    args = parse_args()

    comp_rep = pd.read_csv(args.composition_repeated, sep="\t").assign(
        representation="composition",
        protocol="repeated_5fold",
    )
    pseudo_rep = pd.read_csv(args.pseudobulk_repeated, sep="\t").assign(
        representation="pseudobulk",
        protocol="repeated_5fold",
    )
    rep_df = pd.concat([comp_rep, pseudo_rep], ignore_index=True)
    rep_keep = [
        "representation",
        "protocol",
        "model",
        "roc_auc_mean",
        "roc_auc_ci95_low",
        "roc_auc_ci95_high",
        "pr_auc_mean",
        "pr_auc_ci95_low",
        "pr_auc_ci95_high",
        "balanced_accuracy_mean",
        "macro_f1_mean",
    ]
    rep_df = rep_df[rep_keep].sort_values(["representation", "roc_auc_mean"], ascending=[True, False])

    comp_lodo = pd.read_csv(args.composition_lodo, sep="\t").assign(
        representation="composition",
        protocol="lodo",
    )
    pseudo_lodo = pd.read_csv(args.pseudobulk_lodo, sep="\t").assign(
        representation="pseudobulk",
        protocol="lodo",
    )
    lodo_df = pd.concat([comp_lodo, pseudo_lodo], ignore_index=True)
    lodo_keep = [
        "representation",
        "protocol",
        "model",
        "roc_auc",
        "pr_auc",
        "balanced_accuracy",
        "macro_f1",
        "accuracy",
    ]
    lodo_df = lodo_df[lodo_keep].sort_values(["representation", "roc_auc"], ascending=[True, False])

    combined = pd.concat([rep_df, lodo_df], ignore_index=True, sort=False)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.output_csv, index=False)

    best_rep = (
        rep_df.sort_values(["representation", "roc_auc_mean"], ascending=[True, False])
        .groupby("representation", as_index=False)
        .head(1)
        .reset_index(drop=True)
    )

    lines = [
        "# Donor-Global Representation Comparison",
        "",
        "## Repeated 5-fold CV",
        "",
        markdown_table(rep_df),
        "",
        "## Leave-One-Donor-Out",
        "",
        markdown_table(lodo_df),
        "",
        "## Interpretation",
        "",
    ]
    for _, row in best_rep.iterrows():
        lines.append(
            f"- Best repeated-CV {row['representation']} model: `{row['model']}` "
            f"AUROC `{row['roc_auc_mean']:.4f}` "
            f"(95% CI `{row['roc_auc_ci95_low']:.4f}`-`{row['roc_auc_ci95_high']:.4f}`)."
        )
    lines.extend(
        [
            "- Pseudobulk is currently stronger than composition because every model family reaches near-ceiling AUROC under repeated donor resampling and remains strong under LODO.",
            "- Composition remains scientifically useful because it is not near ceiling, it is biologically interpretable, and it provides more room for StructuralCFN to add value.",
        ]
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[ok] Wrote donor-global comparison CSV: {args.output_csv}")
    print(f"[ok] Wrote donor-global comparison markdown: {args.output_md}")
    with pd.option_context("display.max_columns", None, "display.width", 160):
        print(rep_df.to_string(index=False))


if __name__ == "__main__":
    main()
