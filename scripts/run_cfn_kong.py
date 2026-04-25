#!/usr/bin/env python3
"""StructuralCFN on Kong 2023 CD vs Healthy donor composition features.

Runs 5-fold CV using GatedStructuralCFN (fanglioc/StructuralCFN-public, v1.1.0)
on all three Kong composition tables:
  - All regions  (n=71, 68 cell types)
  - TI only      (n=42, 61 cell types)
  - Colon only   (n=34, 55 cell types)

Saves CFN dependency matrices and AUROC/PR-AUC per fold — directly comparable
to the Kong CLR baselines in results/kong2023_cd/baselines/.

REQUIREMENTS:
    pip install git+https://github.com/fanglioc/StructuralCFN-public.git
    # or: pip install /path/to/StructuralCFN-public

Usage (from repo root):
    python scripts/run_cfn_kong.py \\
        --kong-dir      data/processed/kong2023_cd \\
        --output-dir    results/kong2023_cd/cfn \\
        --n-epochs      300

Outputs:
    results/kong2023_cd/cfn/
        summary.tsv
        kong_cfn_{region}_fold_metrics.tsv
        cfn_structures/
            kong_cfn_{region}_fold{i}.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# CLR transform
# ---------------------------------------------------------------------------

def clr_transform(X: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    X_safe = X + eps
    log_X = np.log(X_safe)
    return log_X - log_X.mean(axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# CFN import (pip-installed from fanglioc/StructuralCFN-public)
# ---------------------------------------------------------------------------

def import_cfn():
    """Import GatedStructuralCFN from the pip-installed scfn package."""
    try:
        from scfn import GatedStructuralCFN
        return GatedStructuralCFN
    except ImportError:
        pass
    try:
        from scfn import GenericStructuralCFN
        log("  GatedStructuralCFN not found; using GenericStructuralCFN")
        return GenericStructuralCFN
    except ImportError:
        raise ImportError(
            "scfn package not installed. Run:\n"
            "  pip install git+https://github.com/fanglioc/StructuralCFN-public.git"
        )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_kong_region(
    kong_dir: Path,
    region: str,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str], list[dict]]:
    """Load Kong composition + metadata + folds for one region.

    region: 'all' | 'TI' | 'colon'
    Returns (X, y, donor_ids, feature_names, folds)
    """
    if region == "all":
        feat_file  = kong_dir / "donor_cluster_props.tsv"
        folds_file = kong_dir / "donor_cd_vs_healthy_folds.json"
    elif region == "TI":
        feat_file  = kong_dir / "donor_TI_cluster_props.tsv"
        folds_file = kong_dir / "donor_cd_vs_healthy_TI_folds.json"
    elif region == "colon":
        feat_file  = kong_dir / "donor_colon_cluster_props.tsv"
        folds_file = kong_dir / "donor_cd_vs_healthy_colon_folds.json"
    else:
        raise ValueError(f"Unknown region: {region}")

    meta_file = kong_dir / "donor_metadata.tsv"

    feat = pd.read_csv(feat_file, sep="\t", index_col=0)
    meta = pd.read_csv(meta_file, sep="\t")

    if "donor_id" in meta.columns:
        meta = meta.set_index("donor_id")
    else:
        meta = meta.set_index(meta.columns[0])

    feat.index = feat.index.astype(str)
    meta.index = meta.index.astype(str)

    shared = feat.index.intersection(meta.index)
    feat = feat.loc[shared]
    meta = meta.loc[shared]

    y = (meta["donor_label"].astype(str) == "CD").astype(int).values
    X = feat.values.astype(np.float64)
    donor_ids = list(feat.index)
    feature_names = list(feat.columns)

    with open(folds_file) as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "folds" in raw:
        raw = raw["folds"]
    folds = [
        {
            "train_ids": [str(x) for x in fold.get("train_ids", fold.get("train", []))],
            "test_ids":  [str(x) for x in fold.get("test_ids",  fold.get("test",  []))],
        }
        for fold in raw
    ]

    return X, y, donor_ids, feature_names, folds


# ---------------------------------------------------------------------------
# CFN training + evaluation
# ---------------------------------------------------------------------------

def train_eval_cfn_fold(
    CFNClass,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
    n_epochs: int,
    lr: float,
    batch_size: int,
    apply_clr: bool,
    seed: int,
) -> tuple[dict, np.ndarray]:
    """Train CFN on one fold, return (metrics dict, dependency_matrix)."""
    import torch

    if apply_clr:
        X_train = clr_transform(X_train.copy())
        X_test  = clr_transform(X_test.copy())

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_test  = scaler.transform(X_test).astype(np.float32)

    torch.manual_seed(seed)
    np.random.seed(seed)

    # classification=False → MSELoss, raw scalar output (monotone with prob)
    # AUROC is rank-invariant so raw scores == sigmoid scores for ranking
    model = CFNClass(
        input_dim=X_train.shape[1],
        classification=False,
    )

    model.fit(
        X_train, y_train.astype(np.float32),
        epochs=n_epochs,
        lr=lr,
        batch_size=batch_size,
        verbose=False,
    )

    # Get continuous raw scores for AUROC (rank-invariant, no sigmoid needed)
    model.eval()
    with torch.no_grad():
        X_t = torch.FloatTensor(X_test)
        scores = model(X_t).squeeze().cpu().numpy()

    dep_matrix = model.get_dependency_matrix()  # N×N numpy array

    if len(np.unique(y_test)) < 2:
        metrics = {"auroc": float("nan"), "pr_auc": float("nan")}
    else:
        metrics = {
            "auroc":  float(roc_auc_score(y_test, scores)),
            "pr_auc": float(average_precision_score(y_test, scores)),
        }
    metrics["n_train"] = int(len(y_train))
    metrics["n_test"]  = int(len(y_test))

    artifacts = {
        "feature_names":     feature_names,
        "dependency_matrix": dep_matrix.tolist(),
        "x_linear_weights":  None,
        "z_linear_weights":  None,
    }

    return metrics, artifacts


# ---------------------------------------------------------------------------
# Run one region
# ---------------------------------------------------------------------------

def run_region(
    CFNClass,
    kong_dir: Path,
    region: str,
    n_epochs: int,
    lr: float,
    batch_size: int,
    apply_clr: bool,
    seed: int,
    output_dir: Path,
) -> pd.DataFrame:
    log(f"\n=== Kong CFN: region='{region}' ===")

    X, y, donor_ids, feature_names, folds = load_kong_region(kong_dir, region)
    log(f"  Donors: {len(donor_ids)}  Features: {len(feature_names)}")
    log(f"  CD={int(y.sum())}  Healthy={int((1-y).sum())}")

    id_to_idx = {did: i for i, did in enumerate(donor_ids)}
    fold_records = []
    cfn_dir = output_dir / "cfn_structures"
    cfn_dir.mkdir(parents=True, exist_ok=True)

    for i, fold_spec in enumerate(folds):
        train_idx = [id_to_idx[d] for d in fold_spec["train_ids"] if d in id_to_idx]
        test_idx  = [id_to_idx[d] for d in fold_spec["test_ids"]  if d in id_to_idx]

        X_train, y_train = X[train_idx], y[train_idx]
        X_test,  y_test  = X[test_idx],  y[test_idx]

        t0 = time.time()
        metrics, artifacts = train_eval_cfn_fold(
            CFNClass, X_train, y_train, X_test, y_test,
            feature_names, n_epochs, lr, batch_size, apply_clr, seed + i,
        )
        elapsed = time.time() - t0
        log(f"  fold {i}: AUROC={metrics['auroc']:.3f}  PR-AUC={metrics['pr_auc']:.3f}  "
            f"n_train={metrics['n_train']}  n_test={metrics['n_test']}  ({elapsed:.1f}s)")

        json_path = cfn_dir / f"kong_cfn_{region}_fold{i}.json"
        with open(json_path, "w") as f:
            json.dump({
                "run_name": f"kong_cfn_{region}",
                "fold": i,
                "model": "GatedStructuralCFN",
                "seed": seed + i,
                "n_epochs": n_epochs,
                "apply_clr": apply_clr,
                "artifacts": artifacts,
                **{k: v for k, v in metrics.items()},
            }, f, indent=2)

        fold_records.append({
            "region": region,
            "fold": i,
            "model": "GatedStructuralCFN",
            **metrics,
        })

    df = pd.DataFrame(fold_records)
    aurocs = df["auroc"].dropna()
    prauc  = df["pr_auc"].dropna()
    log(f"  {region} summary: AUROC={aurocs.mean():.3f}±{aurocs.std():.3f}  "
        f"PR-AUC={prauc.mean():.3f}±{prauc.std():.3f}")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kong-dir",    default="data/processed/kong2023_cd")
    p.add_argument("--output-dir",  default="results/kong2023_cd/cfn")
    p.add_argument("--regions",     default="all,TI,colon")
    p.add_argument("--n-epochs",    type=int, default=300)
    p.add_argument("--lr",          type=float, default=0.01)
    p.add_argument("--batch-size",  type=int, default=16,
                   help="Small batch recommended for small n (default 16)")
    p.add_argument("--seed",        type=int, default=42)
    p.add_argument("--apply-clr",   action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    kong_dir   = Path(args.kong_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log("Importing GatedStructuralCFN...")
    CFNClass = import_cfn()
    log(f"Using: {CFNClass.__name__}")

    regions = [r.strip() for r in args.regions.split(",")]
    summary_rows = []

    for region in regions:
        fold_df = run_region(
            CFNClass, kong_dir, region,
            args.n_epochs, args.lr, args.batch_size,
            args.apply_clr, args.seed, output_dir,
        )
        fold_df.to_csv(
            output_dir / f"kong_cfn_{region}_fold_metrics.tsv",
            sep="\t", index=False,
        )
        aurocs = fold_df["auroc"].dropna()
        prauc  = fold_df["pr_auc"].dropna()
        summary_rows.append({
            "region":      region,
            "model":       "GatedStructuralCFN",
            "apply_clr":   args.apply_clr,
            "n_epochs":    args.n_epochs,
            "n_folds":     len(fold_df),
            "mean_auroc":  float(aurocs.mean()),
            "std_auroc":   float(aurocs.std()),
            "mean_pr_auc": float(prauc.mean()),
            "std_pr_auc":  float(prauc.std()),
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_dir / "summary.tsv", sep="\t", index=False)

    log("\n=== FINAL SUMMARY ===")
    log(summary_df.to_string(index=False))
    log(f"\nOutputs: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
