#!/usr/bin/env python3

"""Compute donor-level bootstrap confidence intervals for all baseline models.

This script takes existing per-fold prediction tables (from run_uc_baselines.py
or run_clr_baselines.py) and computes **donor-level bootstrap 95% CIs** for
AUROC, PR-AUC, balanced accuracy, and macro-F1.

Why donor-level bootstrap
--------------------------
CV fold CIs measure variance in *fold assignment*, not in the donor population.
Donor-level bootstrap resamples donors (with replacement) from the full test
pool, providing a more principled CI that matches the actual sampling unit of
the study (donors, not folds).

We pool all test-set predictions across folds to get one predicted probability
per donor (each donor appears in exactly one test fold), then bootstrap the
resulting N=30 donor prediction list.

Usage (from repo root):
    # Bootstrap CIs for composition predictions
    python scripts/run_bootstrap_ci.py \\
        --predictions results/uc_scp259/benchmarks/donor_cluster_props_baselines_predictions.tsv \\
        --output-dir  results/uc_scp259/benchmarks \\
        --run-name    donor_cluster_props_baselines

    # Bootstrap CIs for CLR predictions (once you've run run_clr_baselines.py)
    python scripts/run_bootstrap_ci.py \\
        --predictions results/uc_scp259/benchmarks/donor_cluster_props_clr_baselines_predictions.tsv \\
        --output-dir  results/uc_scp259/benchmarks \\
        --run-name    donor_cluster_props_clr_baselines

    # Process multiple prediction files in one call
    python scripts/run_bootstrap_ci.py \\
        --predictions \\
            results/uc_scp259/benchmarks/donor_cluster_props_baselines_predictions.tsv \\
            results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_baselines_predictions.tsv \\
        --output-dir results/uc_scp259/benchmarks \\
        --run-name combined_bootstrap_ci

Outputs:
    {run_name}_bootstrap_ci.tsv   -- per-model bootstrap CI table (main table)
    {run_name}_bootstrap_draws.tsv -- per-model per-draw metrics (for distribution plots)
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)


# ---------------------------------------------------------------------------
# Bootstrap core
# ---------------------------------------------------------------------------

def bootstrap_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bootstrap: int,
    seed: int,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Bootstrap point estimates and CI for AUROC, PR-AUC, bal-acc, macro-F1.

    Uses the percentile method (not BCa) — appropriate for the sample sizes
    here and simpler to audit.

    Args:
        y_true:      Binary labels (0/1), shape (N,).
        y_prob:      Predicted probabilities for the positive class, shape (N,).
        n_bootstrap: Number of bootstrap draws.
        seed:        Random seed for reproducibility.
        alpha:       Significance level (default 0.05 → 95% CI).

    Returns:
        dict with keys: {metric}_mean, {metric}_ci_low, {metric}_ci_high,
                        {metric}_std, n_donors, n_bootstrap.
    """
    rng = np.random.default_rng(seed)
    n   = len(y_true)

    draw_metrics: dict[str, list[float]] = {
        "roc_auc":           [],
        "pr_auc":            [],
        "balanced_accuracy": [],
        "macro_f1":          [],
    }

    for _ in range(n_bootstrap):
        idx     = rng.integers(0, n, size=n)
        yt_boot = y_true[idx]
        yp_boot = y_prob[idx]

        # Skip draws where only one class is present (degenerate)
        if len(np.unique(yt_boot)) < 2:
            continue

        y_pred = (yp_boot >= 0.5).astype(int)
        draw_metrics["roc_auc"].append(float(roc_auc_score(yt_boot, yp_boot)))
        draw_metrics["pr_auc"].append(float(average_precision_score(yt_boot, yp_boot)))
        draw_metrics["balanced_accuracy"].append(
            float(balanced_accuracy_score(yt_boot, y_pred))
        )
        draw_metrics["macro_f1"].append(
            float(f1_score(yt_boot, y_pred, average="macro", zero_division=0))
        )

    result: dict[str, Any] = {
        "n_donors":    n,
        "n_bootstrap": n_bootstrap,
    }

    for metric, draws in draw_metrics.items():
        arr = np.array(draws)
        if len(arr) == 0:
            result[f"{metric}_mean"]     = float("nan")
            result[f"{metric}_std"]      = float("nan")
            result[f"{metric}_ci_low"]   = float("nan")
            result[f"{metric}_ci_high"]  = float("nan")
        else:
            result[f"{metric}_mean"]     = float(np.mean(arr))
            result[f"{metric}_std"]      = float(np.std(arr, ddof=1))
            result[f"{metric}_ci_low"]   = float(np.quantile(arr, alpha / 2))
            result[f"{metric}_ci_high"]  = float(np.quantile(arr, 1 - alpha / 2))

    return result, draw_metrics


# ---------------------------------------------------------------------------
# Load and aggregate predictions
# ---------------------------------------------------------------------------

def load_predictions(path: Path) -> pd.DataFrame:
    """Load a predictions TSV, returning one row per donor per model."""
    suffix = "".join(path.suffixes[-2:]) if len(path.suffixes) >= 2 else path.suffix
    if suffix in {".tsv", ".tsv.gz"}:
        df = pd.read_csv(path, sep="\t")
    else:
        df = pd.read_csv(path)
    required = {"donor_id", "model", "y_true", "y_prob"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Prediction table {path} missing columns: {missing}.  "
            f"Found: {list(df.columns)}"
        )
    return df


def aggregate_donor_predictions(pred_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-fold predictions to one row per donor per model.

    Each donor appears in exactly one test fold, so this is mostly a
    deduplication / column reduction step.  If a donor somehow appears
    multiple times across folds (shouldn't happen with donor-aware CV),
    we take the mean probability.
    """
    agg = (
        pred_df.groupby(["model", "donor_id"], as_index=False)
        .agg(y_true=("y_true", "first"), y_prob=("y_prob", "mean"))
    )
    return agg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compute donor-level bootstrap CIs for existing prediction tables."
    )
    p.add_argument(
        "--predictions",
        type=Path,
        nargs="+",
        required=True,
        help="One or more prediction TSV files from run_uc_baselines.py or run_clr_baselines.py.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/uc_scp259/benchmarks"),
    )
    p.add_argument(
        "--run-name",
        default=None,
        help="Output file prefix. Defaults to the first prediction file stem.",
    )
    p.add_argument(
        "--n-bootstrap",
        type=int,
        default=2000,
        help="Number of bootstrap draws (default 2000 for stable 95%% CIs).",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level (default 0.05 → 95%% CI).",
    )
    return p.parse_args()


def main() -> None:
    args   = parse_args()
    run_name = args.run_name or args.predictions[0].stem

    # Load and combine all prediction files
    pred_frames = []
    for path in args.predictions:
        if not path.exists():
            print(f"  [skip] File not found: {path}")
            continue
        df = load_predictions(path)
        # Add source file as a column for traceability
        df["source_file"] = path.stem
        pred_frames.append(df)
        print(f"  [load] {path.name}  shape={df.shape}  models={sorted(df['model'].unique())}")

    if not pred_frames:
        print("[error] No valid prediction files found.")
        return

    all_preds = pd.concat(pred_frames, ignore_index=True)
    donor_preds = aggregate_donor_predictions(all_preds)

    print(f"\n  Combined: {len(all_preds)} rows → {len(donor_preds)} donor-model pairs")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    ci_rows  = []
    draw_rows = []

    # Group by run_name + model so each representation × model gets its own CI
    group_keys = ["run_name", "model"] if "run_name" in donor_preds.columns else ["model"]

    for group_vals, group in donor_preds.groupby(group_keys, sort=True):
        if isinstance(group_vals, str):
            group_vals = (group_vals,)
        label = "_".join(str(v) for v in group_vals)
        model_name = group_vals[-1]   # model is always the last key

        y_true = group["y_true"].to_numpy(dtype=int)
        y_prob  = group["y_prob"].to_numpy(dtype=float)

        print(f"  Bootstrapping {label} (n_donors={len(y_true)}, "
              f"n_bootstrap={args.n_bootstrap}) ...", end=" ", flush=True)

        ci_stats, draw_metrics = bootstrap_metrics(
            y_true, y_prob, args.n_bootstrap, args.seed, args.alpha
        )
        print("done")

        ci_rows.append({
            "label": label,
            "model": model_name,
            **ci_stats,
        })

        for draw_idx, (roc, pr, ba, f1) in enumerate(zip(
            draw_metrics["roc_auc"],
            draw_metrics["pr_auc"],
            draw_metrics["balanced_accuracy"],
            draw_metrics["macro_f1"],
        )):
            draw_rows.append({
                "label":            label,
                "model":            model_name,
                "draw":             draw_idx,
                "roc_auc":          roc,
                "pr_auc":           pr,
                "balanced_accuracy": ba,
                "macro_f1":         f1,
            })

    ci_df   = pd.DataFrame(ci_rows).sort_values(["label", "model"])
    draw_df = pd.DataFrame(draw_rows)

    ci_path   = args.output_dir / f"{run_name}_bootstrap_ci.tsv"
    draw_path = args.output_dir / f"{run_name}_bootstrap_draws.tsv"

    ci_df.to_csv(ci_path,   sep="\t", index=False)
    draw_df.to_csv(draw_path, sep="\t", index=False)

    print(f"\n[ok] Bootstrap CIs: {ci_path}")
    print(f"[ok] Bootstrap draws: {draw_path}")
    print("\n--- Bootstrap CI Summary (AUROC) ---")
    cols = ["model", "n_donors", "roc_auc_mean",
            "roc_auc_ci_low", "roc_auc_ci_high", "roc_auc_std"]
    with pd.option_context("display.max_columns", None, "display.width", 160):
        print(ci_df[[c for c in cols if c in ci_df.columns]].to_string(index=False))


if __name__ == "__main__":
    main()
