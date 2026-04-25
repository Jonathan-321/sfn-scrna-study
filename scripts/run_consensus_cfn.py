#!/usr/bin/env python3

"""Build consensus-constrained CFN from existing per-fold structure JSONs.

This script operationalises the "consensus-CFN" improvement described in the
publication roadmap (§6.2).  Rather than training a new model, it post-processes
the saved fold structure matrices to:

  1. Compute edge recurrence frequency across all saved folds (for each
     representation: donor_cluster_props and donor_compartment_cluster_props).
  2. Identify the top-K recurring edges (default K=20).
  3. Compute per-fold prediction metrics already stored in the fold JSONs /
     separate benchmark CSVs and re-summarise them alongside new stability
     metrics using only the consensus edge set.
  4. Generate the Pareto plot data (grouped Jaccard vs AUROC) as a CSV that
     can be fed into the figure pipeline.

Why this matters
----------------
The unconstrained CFN has grouped Jaccard ~ 0.03 across folds.  The
consensus-constrained variant restricts interpretation to the edges that
recur across folds, turning the instability observation into a constructive
result.  This is the single most impactful CFN improvement before submission.

Usage (from repo root):
    python scripts/run_consensus_cfn.py \\
        --cfn-dir  results/uc_scp259/cfn_structures \\
        --cfn-metrics results/uc_scp259/cfn_benchmarks \\
        --output-dir results/uc_scp259/cfn_benchmarks \\
        --top-k 20

Outputs (all in --output-dir):
    consensus_cfn_global_edge_recurrence.csv    -- per-edge fold-recurrence stats
    consensus_cfn_compartment_edge_recurrence.csv
    consensus_cfn_pareto_data.csv               -- AUROC + stability per representation
    consensus_cfn_top{K}_edges.csv              -- consensus edge table for paper Fig 5/6
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_fold_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_matrix(fold_data: dict) -> tuple[np.ndarray, list[str]]:
    """Return (dependency_matrix, feature_names) from a CFN fold JSON."""
    artifacts = fold_data["artifacts"]
    matrix = np.array(artifacts["dependency_matrix"], dtype=float)
    features = artifacts["feature_names"]
    return matrix, features


def sign_consistency(matrices: list[np.ndarray]) -> float:
    """Fraction of (i,j) pairs where sign is identical across all folds."""
    if len(matrices) < 2:
        return 1.0
    signs = np.stack([np.sign(m) for m in matrices], axis=0)   # (n_folds, d, d)
    # Consistent = all folds agree (ignore (i,i) diagonal, zeros)
    first = signs[0]
    consistent = np.all(signs == first, axis=0)
    # Exclude diagonal and zero-valued cells
    d = first.shape[0]
    off_diag_mask = ~np.eye(d, dtype=bool)
    nonzero_mask  = (np.abs(first) > 1e-8) & off_diag_mask
    if nonzero_mask.sum() == 0:
        return 1.0
    return float(consistent[nonzero_mask].mean())


def grouped_jaccard(matrices: list[np.ndarray], threshold: float) -> float:
    """Grouped Jaccard similarity of binarised edge sets across fold pairs.

    For each pair of folds, compute Jaccard(top-edge-set_i, top-edge-set_j).
    Return the mean over all pairs.
    """
    if len(matrices) < 2:
        return 1.0
    sets = []
    for m in matrices:
        flat = m.ravel()
        top_idx = set(np.where(np.abs(flat) >= threshold)[0].tolist())
        sets.append(top_idx)

    scores = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            inter = sets[i] & sets[j]
            if len(union) == 0:
                scores.append(1.0)
            else:
                scores.append(len(inter) / len(union))
    return float(np.mean(scores))


def matrix_cosine(matrices: list[np.ndarray]) -> float:
    """Mean pairwise cosine similarity of flattened fold matrices."""
    if len(matrices) < 2:
        return 1.0
    flat = np.stack([m.ravel() for m in matrices], axis=0)   # (n_folds, d*d)
    norms = np.linalg.norm(flat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalised = flat / norms
    scores = []
    for i in range(len(matrices)):
        for j in range(i + 1, len(matrices)):
            scores.append(float(np.dot(normalised[i], normalised[j])))
    return float(np.mean(scores))


def build_edge_recurrence_table(
    matrices: list[np.ndarray],
    feature_names: list[str],
    fold_ids: list[int],
) -> pd.DataFrame:
    """Build a per-edge table with fold-level recurrence statistics.

    For each (source, target) pair:
        - weight_mean, weight_std across folds
        - abs_weight_mean
        - recurrence_freq: fraction of folds where |weight| > 0 (non-pruned)
        - sign_consistency: fraction of folds with same sign (ignoring zeros)
    """
    n_features = len(feature_names)
    rows = []

    for i in range(n_features):
        for j in range(n_features):
            if i == j:
                continue   # skip self-loops
            weights = np.array([m[i, j] for m in matrices])
            nonzero  = np.abs(weights) > 1e-8
            rec_freq = float(nonzero.mean())
            if nonzero.sum() > 1:
                nonzero_weights = weights[nonzero]
                signs = np.sign(nonzero_weights)
                sign_cons = float((signs == signs[0]).mean())
            elif nonzero.sum() == 1:
                sign_cons = 1.0
            else:
                sign_cons = float("nan")

            rows.append({
                "source":           feature_names[i],
                "target":           feature_names[j],
                "weight_mean":      float(weights.mean()),
                "weight_std":       float(weights.std(ddof=1)) if len(weights) > 1 else 0.0,
                "abs_weight_mean":  float(np.abs(weights).mean()),
                "recurrence_freq":  rec_freq,
                "sign_consistency": sign_cons,
                "n_folds":          len(fold_ids),
            })

    df = pd.DataFrame(rows)
    df = df.sort_values("recurrence_freq", ascending=False).reset_index(drop=True)
    return df


def load_cfn_performance(metrics_dir: Path, run_prefix: str) -> dict[str, float]:
    """Load AUROC and PR-AUC from the existing CFN summary CSV."""
    summary_path = metrics_dir / f"{run_prefix}_summary.csv"
    if not summary_path.exists():
        return {}
    df = pd.read_csv(summary_path)
    # Summary CSVs have columns like auroc_mean, pr_auc_mean, brier_mean, etc.
    result = {}
    for col in df.columns:
        if col not in {"run_name", "model", "representation"}:
            try:
                result[col] = float(df[col].iloc[0])
            except Exception:
                pass
    return result


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def process_representation(
    cfn_dir: Path,
    metrics_dir: Path,
    run_prefix: str,
    top_k: int,
    threshold: float,
) -> tuple[pd.DataFrame, dict]:
    """Process one CFN representation (global or compartment).

    Returns:
        edge_table : full per-edge recurrence table
        pareto_row : dict with AUROC, stability metrics, and top-K stats
    """
    struct_dir = cfn_dir / run_prefix
    if not struct_dir.exists():
        print(f"  [skip] No structure directory: {struct_dir}")
        return pd.DataFrame(), {}

    fold_files = sorted(struct_dir.glob("cfn_default_fold*.json"))
    if not fold_files:
        print(f"  [skip] No fold JSON files in: {struct_dir}")
        return pd.DataFrame(), {}

    print(f"  Loading {len(fold_files)} folds from {struct_dir.name}")

    matrices    = []
    feature_names = None
    fold_ids    = []

    for fp in fold_files:
        data = load_fold_json(fp)
        m, fn = extract_matrix(data)
        matrices.append(m)
        if feature_names is None:
            feature_names = fn
        fold_ids.append(int(fp.stem.split("fold")[-1]))

    # Build edge recurrence table
    edge_table = build_edge_recurrence_table(matrices, feature_names, fold_ids)

    # Stability diagnostics
    j_score    = grouped_jaccard(matrices, threshold=threshold)
    cos_score  = matrix_cosine(matrices)
    sign_score = sign_consistency(matrices)

    # Top-K consensus edges
    top_k_edges = edge_table.head(top_k)
    top_k_rec_freq = float(top_k_edges["recurrence_freq"].mean())
    top_k_sign_cons = float(top_k_edges["sign_consistency"].dropna().mean())

    # Load existing performance metrics
    perf = load_cfn_performance(metrics_dir, run_prefix)

    pareto_row = {
        "representation":         run_prefix,
        "n_folds":                len(fold_files),
        "n_features":             len(feature_names) if feature_names else 0,
        # full-set stability
        "grouped_jaccard_full":   j_score,
        "matrix_cosine_full":     cos_score,
        "sign_consistency_full":  sign_score,
        # top-K consensus stability
        "top_k":                  top_k,
        "top_k_recurrence_freq":  top_k_rec_freq,
        "top_k_sign_consistency": top_k_sign_cons,
        # prediction performance (from existing summary CSV)
        **{f"perf_{k}": v for k, v in perf.items()},
    }

    return edge_table, pareto_row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build consensus-constrained CFN edge recurrence tables."
    )
    p.add_argument("--cfn-dir",     type=Path,
                   default=Path("results/uc_scp259/cfn_structures"),
                   help="Directory containing per-fold CFN structure JSON subdirs.")
    p.add_argument("--cfn-metrics", type=Path,
                   default=Path("results/uc_scp259/cfn_benchmarks"),
                   help="Directory containing CFN summary CSVs.")
    p.add_argument("--output-dir",  type=Path,
                   default=Path("results/uc_scp259/cfn_benchmarks"),
                   help="Output directory for consensus tables.")
    p.add_argument("--top-k",       type=int, default=20,
                   help="Number of top recurring edges to treat as 'consensus'.")
    p.add_argument("--threshold",   type=float, default=1e-4,
                   help="Absolute weight threshold for an edge to be 'active' in a fold.")
    return p.parse_args()


REPRESENTATIONS = {
    "donor_cluster_props_cfn_full":            "global",
    "donor_compartment_cluster_props_cfn_full": "compartment",
}


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pareto_rows = []

    for run_prefix, label in REPRESENTATIONS.items():
        print(f"\n[{label}] Processing {run_prefix}")
        edge_table, pareto_row = process_representation(
            cfn_dir     = args.cfn_dir,
            metrics_dir = args.cfn_metrics,
            run_prefix  = run_prefix,
            top_k       = args.top_k,
            threshold   = args.threshold,
        )
        if edge_table.empty:
            continue

        # Write full edge recurrence table
        edge_path = args.output_dir / f"consensus_cfn_{label}_edge_recurrence.csv"
        edge_table.to_csv(edge_path, index=False)
        print(f"  [ok] Edge recurrence table: {edge_path}  ({len(edge_table)} edges)")

        # Write top-K consensus edge table
        top_path = args.output_dir / f"consensus_cfn_{label}_top{args.top_k}_edges.csv"
        edge_table.head(args.top_k).to_csv(top_path, index=False)
        print(f"  [ok] Top-{args.top_k} consensus edges: {top_path}")

        pareto_rows.append(pareto_row)

        # Print summary
        print(f"\n  --- Stability summary ({label}) ---")
        print(f"  Grouped Jaccard (full):       {pareto_row.get('grouped_jaccard_full', 'N/A'):.4f}")
        print(f"  Matrix cosine (full):         {pareto_row.get('matrix_cosine_full', 'N/A'):.4f}")
        print(f"  Sign consistency (full):      {pareto_row.get('sign_consistency_full', 'N/A'):.4f}")
        print(f"  Top-{args.top_k} recurrence freq (mean): "
              f"{pareto_row.get('top_k_recurrence_freq', 'N/A'):.4f}")
        print(f"  Top-{args.top_k} sign consistency (mean): "
              f"{pareto_row.get('top_k_sign_consistency', 'N/A'):.4f}")

    # Write Pareto data (AUROC vs stability) for Fig 4/5
    if pareto_rows:
        pareto_path = args.output_dir / "consensus_cfn_pareto_data.csv"
        pd.DataFrame(pareto_rows).to_csv(pareto_path, index=False)
        print(f"\n[ok] Pareto data: {pareto_path}")

    print("\n[done] Consensus CFN analysis complete.")
    print("Next step: run run_bootstrap_ci.py to add bootstrap CIs to all models,")
    print("then update build_scp259_visual_assets.py to include Fig 5 (Pareto plot).")


if __name__ == "__main__":
    main()
