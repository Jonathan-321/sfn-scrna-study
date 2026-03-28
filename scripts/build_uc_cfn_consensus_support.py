#!/usr/bin/env python3

"""Build consensus support profiles from UC CFN structure artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize fold support for top-k CFN edges on the UC benchmark."
    )
    parser.add_argument("--structure-dir", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--feature-table", type=Path, default=None)
    parser.add_argument("--id-col", default="donor_id")
    parser.add_argument("--target-col", default="uc_binary")
    parser.add_argument("--corr-threshold", type=float, default=0.85)
    parser.add_argument("--output-edge-support", type=Path, required=True)
    parser.add_argument("--output-summary", type=Path, required=True)
    return parser.parse_args()


def load_fold_artifacts(structure_dir: Path) -> List[Dict]:
    files = sorted(structure_dir.glob("cfn_default_fold*.json"))
    if not files:
        raise FileNotFoundError(f"No cfn_default_fold*.json found in {structure_dir}")
    payloads = []
    for f in files:
        with f.open("r", encoding="utf-8") as fh:
            payloads.append(json.load(fh))
    return payloads


def load_table(path: Path) -> pd.DataFrame:
    suffix = "".join(path.suffixes[-2:]) if len(path.suffixes) >= 2 else path.suffix
    if suffix in {".tsv", ".tsv.gz"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".csv", ".csv.gz"}:
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table type for {path}")


def _union_find_groups(corr_abs: np.ndarray, feature_names: List[str], threshold: float) -> Dict[str, str]:
    n = len(feature_names)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra = find(a)
        rb = find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(i + 1, n):
            if corr_abs[i, j] >= threshold:
                union(i, j)

    groups: Dict[int, List[str]] = {}
    for idx, fname in enumerate(feature_names):
        root = find(idx)
        groups.setdefault(root, []).append(fname)

    sorted_groups = sorted([sorted(v) for v in groups.values()], key=lambda vals: (len(vals), vals), reverse=True)
    f2g: Dict[str, str] = {}
    for gi, members in enumerate(sorted_groups):
        if len(members) <= 4:
            label_members = "|".join(members)
        else:
            label_members = "|".join(members[:4]) + "|..."
        label = f"grp{gi:02d}[{label_members}]"
        for m in members:
            f2g[m] = label
    return f2g


def build_feature_groups(
    feature_table: Path,
    id_col: str,
    target_col: str,
    feature_names: List[str],
    corr_threshold: float,
) -> Dict[str, str]:
    df = load_table(feature_table)
    available = [c for c in feature_names if c in df.columns and c not in {id_col, target_col}]
    if not available:
        raise ValueError("No benchmark feature columns found in provided feature table.")
    x = df[available].apply(pd.to_numeric, errors="coerce")
    corr_abs = x.corr(method="pearson").abs().fillna(0.0).to_numpy()
    f2g = _union_find_groups(corr_abs, available, corr_threshold)
    for fname in feature_names:
        f2g.setdefault(fname, f"grp_missing[{fname}]")
    return f2g


def get_topk_edge_labels(
    dep_matrix: np.ndarray,
    feature_names: List[str],
    k: int,
    feature_to_group: Optional[Dict[str, str]] = None,
) -> List[str]:
    d = dep_matrix.shape[0]
    edges: List[Tuple[str, float]] = []
    for target_idx in range(d):
        for source_idx in range(d):
            if source_idx == target_idx:
                continue
            source = feature_names[source_idx]
            target = feature_names[target_idx]
            if feature_to_group is None:
                label = f"{source}->{target}"
            else:
                label = f"{feature_to_group[source]}->{feature_to_group[target]}"
            edges.append((label, float(dep_matrix[target_idx, source_idx])))
    edges_sorted = sorted(edges, key=lambda x: x[1], reverse=True)
    return [label for label, _ in edges_sorted[:k]]


def support_rows(level: str, labels_per_fold: List[List[str]], n_folds: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = Counter()
    for labels in labels_per_fold:
        counts.update(set(labels))

    edge_rows = [
        {
            "level": level,
            "edge_label": edge,
            "support_count": int(count),
            "support_fraction": float(count / n_folds),
        }
        for edge, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    edge_df = pd.DataFrame(edge_rows)

    support_counter = Counter(counts.values())
    summary_rows = [
        {
            "level": level,
            "support_count": int(support),
            "n_edges": int(support_counter.get(support, 0)),
            "n_edges_at_least_support": int(sum(v for k, v in support_counter.items() if k >= support)),
            "n_folds": int(n_folds),
        }
        for support in range(1, n_folds + 1)
    ]
    summary_df = pd.DataFrame(summary_rows)
    return edge_df, summary_df


def main() -> None:
    args = parse_args()
    payloads = load_fold_artifacts(args.structure_dir)
    feature_names = payloads[0]["artifacts"]["feature_names"]
    n_folds = len(payloads)
    feature_to_group = None
    if args.feature_table is not None:
        feature_to_group = build_feature_groups(
            feature_table=args.feature_table,
            id_col=args.id_col,
            target_col=args.target_col,
            feature_names=feature_names,
            corr_threshold=args.corr_threshold,
        )

    raw_labels = []
    grouped_labels = []
    for payload in payloads:
        dep = np.array(payload["artifacts"]["dependency_matrix"], dtype=float)
        raw_labels.append(get_topk_edge_labels(dep, feature_names, args.top_k))
        if feature_to_group is not None:
            grouped_labels.append(get_topk_edge_labels(dep, feature_names, args.top_k, feature_to_group))

    raw_edge_df, raw_summary_df = support_rows("raw", raw_labels, n_folds)
    if grouped_labels:
        grouped_edge_df, grouped_summary_df = support_rows("grouped", grouped_labels, n_folds)
        edge_df = pd.concat([raw_edge_df, grouped_edge_df], ignore_index=True)
        summary_df = pd.concat([raw_summary_df, grouped_summary_df], ignore_index=True)
    else:
        edge_df = raw_edge_df
        summary_df = raw_summary_df

    args.output_edge_support.parent.mkdir(parents=True, exist_ok=True)
    edge_df.to_csv(args.output_edge_support, index=False)
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(args.output_summary, index=False)

    print(f"[ok] Wrote edge support table: {args.output_edge_support}")
    print(f"[ok] Wrote support summary: {args.output_summary}")
    with pd.option_context("display.max_columns", None, "display.width", 160):
        print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
