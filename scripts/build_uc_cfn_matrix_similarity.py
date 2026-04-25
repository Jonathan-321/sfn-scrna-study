#!/usr/bin/env python3

"""Compute pairwise full-matrix similarity diagnostics for saved CFN structures."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute pairwise full dependency-matrix similarity across CFN folds."
    )
    parser.add_argument("--structure-dir", type=Path, required=True)
    parser.add_argument("--output-pairs", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    parser.add_argument(
        "--exclude-diagonal",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exclude diagonal/self-edge terms before flattening matrices.",
    )
    return parser.parse_args()


def load_fold_artifacts(structure_dir: Path) -> List[Dict]:
    files = sorted(structure_dir.glob("cfn_default_fold*.json"))
    if not files:
        raise FileNotFoundError(f"No cfn_default_fold*.json found in {structure_dir}")
    payloads = []
    for file_path in files:
        with file_path.open("r", encoding="utf-8") as handle:
            payloads.append(json.load(handle))
    return payloads


def flatten_matrix(matrix: np.ndarray, exclude_diagonal: bool) -> np.ndarray:
    if exclude_diagonal:
        mask = ~np.eye(matrix.shape[0], dtype=bool)
        return matrix[mask].astype(float).ravel()
    return matrix.astype(float).ravel()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0.0:
        return float("nan")
    return float(np.dot(a, b) / denom)


def pearson_r(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) == 0.0 or np.std(b) == 0.0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def spearman_r(a: np.ndarray, b: np.ndarray) -> float:
    a_rank = pd.Series(a).rank(method="average").to_numpy(dtype=float)
    b_rank = pd.Series(b).rank(method="average").to_numpy(dtype=float)
    return pearson_r(a_rank, b_rank)


def normalized_frobenius_distance(a: np.ndarray, b: np.ndarray) -> float:
    num = np.linalg.norm(a - b)
    denom = np.linalg.norm(a) + np.linalg.norm(b)
    if denom == 0.0:
        return float("nan")
    return float(num / denom)


def summarize_pairs(pair_df: pd.DataFrame, n_folds: int, n_edges: int, exclude_diagonal: bool) -> pd.DataFrame:
    metric_cols = [
        "cosine_similarity",
        "pearson_r",
        "spearman_r",
        "frobenius_distance_norm",
    ]
    row = {
        "n_folds": int(n_folds),
        "n_pairs": int(len(pair_df)),
        "n_edges_compared": int(n_edges),
        "exclude_diagonal": bool(exclude_diagonal),
    }
    for col in metric_cols:
        values = pair_df[col].to_numpy(dtype=float)
        row[f"{col}_mean"] = float(np.nanmean(values))
        row[f"{col}_std"] = float(np.nanstd(values, ddof=1)) if len(values) > 1 else 0.0
        row[f"{col}_min"] = float(np.nanmin(values))
        row[f"{col}_max"] = float(np.nanmax(values))
    return pd.DataFrame([row])


def main() -> None:
    args = parse_args()
    payloads = load_fold_artifacts(args.structure_dir)

    fold_ids = []
    flat_mats = []
    feature_names_ref = None

    for payload in payloads:
        fold_ids.append(int(payload["fold"]))
        feature_names = payload["artifacts"]["feature_names"]
        dep = np.array(payload["artifacts"]["dependency_matrix"], dtype=float)
        if feature_names_ref is None:
            feature_names_ref = feature_names
        elif feature_names_ref != feature_names:
            raise ValueError("Feature name mismatch across folds; cannot compare matrices cleanly.")
        flat_mats.append(flatten_matrix(dep, exclude_diagonal=args.exclude_diagonal))

    pair_rows = []
    for idx_a, idx_b in itertools.combinations(range(len(flat_mats)), 2):
        a = flat_mats[idx_a]
        b = flat_mats[idx_b]
        pair_rows.append(
            {
                "fold_a": int(fold_ids[idx_a]),
                "fold_b": int(fold_ids[idx_b]),
                "cosine_similarity": cosine_similarity(a, b),
                "pearson_r": pearson_r(a, b),
                "spearman_r": spearman_r(a, b),
                "frobenius_distance_norm": normalized_frobenius_distance(a, b),
                "norm_a": float(np.linalg.norm(a)),
                "norm_b": float(np.linalg.norm(b)),
            }
        )

    pair_df = pd.DataFrame(pair_rows).sort_values(["fold_a", "fold_b"]).reset_index(drop=True)
    summary_df = summarize_pairs(
        pair_df=pair_df,
        n_folds=len(flat_mats),
        n_edges=len(flat_mats[0]),
        exclude_diagonal=args.exclude_diagonal,
    )

    args.output_pairs.parent.mkdir(parents=True, exist_ok=True)
    pair_df.to_csv(args.output_pairs, index=False)
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(args.output_summary, index=False)

    print(f"[ok] Wrote matrix-similarity pairs: {args.output_pairs}")
    print(f"[ok] Wrote matrix-similarity summary: {args.output_summary}")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
