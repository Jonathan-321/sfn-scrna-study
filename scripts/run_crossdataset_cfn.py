#!/usr/bin/env python3
"""Cross-dataset CFN evaluation on the 4 shared cell types.

Only 4 cell types overlap between SCP259 (51 types) and Kong 2023 (68 types):
    DC1, ILCs, Macrophages, Tregs

This script:
  1. Subsets both composition tables to these 4 shared types (+ CLR transform).
  2. Within-dataset 5-fold CV on SCP259 (4-type subset).
  3. Within-dataset 5-fold CV on Kong (4-type subset, using all-region folds).
  4. Cross-dataset: train SCP259, evaluate on all Kong donors.
  5. Cross-dataset: train Kong, evaluate on all SCP259 donors.

Uses GatedStructuralCFN from fanglioc/StructuralCFN-public (v1.1.0, MIT).

REQUIREMENTS:
    pip install git+https://github.com/fanglioc/StructuralCFN-public.git

Usage (from repo root):
    python scripts/run_crossdataset_cfn.py \\
        --scp-features  data/processed/uc_scp259/donor_cluster_props.tsv \\
        --scp-metadata  data/processed/uc_scp259/donor_metadata.tsv \\
        --scp-folds     data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \\
        --kong-features data/processed/kong2023_cd/donor_cluster_props.tsv \\
        --kong-metadata data/processed/kong2023_cd/donor_metadata.tsv \\
        --kong-folds    data/processed/kong2023_cd/donor_cd_vs_healthy_folds.json \\
        --output-dir    results/cross_dataset_cfn_4types \\
        --n-epochs 300 --apply-clr

Outputs:
    results/cross_dataset_cfn_4types/
        summary.tsv
        scp_cv_fold_metrics.tsv
        kong_cv_fold_metrics.tsv
        cross_dataset_metrics.tsv
        cfn_structures/
            scp259_cfn_fold{i}.json
            kong2023_cfn_fold{i}.json
            SCP259_UC_to_Kong2023_CD.json
            Kong2023_CD_to_SCP259_UC.json
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
# CFN import
# ---------------------------------------------------------------------------

def import_cfn():
    try:
        from scfn import GatedStructuralCFN
        return GatedStructuralCFN
    except ImportError:
        pass
    try:
        from scfn import GenericStructuralCFN
        log("  GatedStructuralCFN not available; using GenericStructuralCFN")
        return GenericStructuralCFN
    except ImportError:
        raise ImportError(
            "scfn package not installed. Run:\n"
            "  pip install git+https://github.com/fanglioc/StructuralCFN-public.git"
        )


# ---------------------------------------------------------------------------
# Shared cell types
# ---------------------------------------------------------------------------

SHARED_CELL_TYPES = ["DC1", "ILCs", "Macrophages", "Tregs"]


# ---------------------------------------------------------------------------
# CLR transform
# ---------------------------------------------------------------------------

def clr_transform(X: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    X_safe = X + eps
    log_X = np.log(X_safe)
    return log_X - log_X.mean(axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_dataset(
    features_path: Path,
    metadata_path: Path,
    folds_path: Path,
    label_col: str,
    positive_label: str,
    cell_types: list[str],
) -> dict:
    feat = pd.read_csv(features_path, sep="\t", index_col=0)
    meta = pd.read_csv(metadata_path, sep="\t")

    if "donor_id" in meta.columns:
        meta = meta.set_index("donor_id")
    else:
        meta = meta.set_index(meta.columns[0])

    feat.index = feat.index.astype(str)
    meta.index = meta.index.astype(str)

    shared_donors = feat.index.intersection(meta.index)
    feat = feat.loc[shared_donors]
    meta = meta.loc[shared_donors]

    missing = [c for c in cell_types if c not in feat.columns]
    if missing:
        raise ValueError(f"Cell types missing from {features_path.name}: {missing}")
    feat = feat[cell_types]

    y = (meta[label_col].astype(str) == positive_label).astype(int).values
    X = feat.values.astype(np.float64)
    donor_ids = list(feat.index)
    feature_names = list(feat.columns)

    with open(folds_path) as f:
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

    return {
        "X": X, "y": y,
        "donor_ids": donor_ids,
        "feature_names": feature_names,
        "folds": folds,
    }


# ---------------------------------------------------------------------------
# CFN train + eval (single fold or full dataset)
# ---------------------------------------------------------------------------

def train_eval_cfn(
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
    import torch

    if apply_clr:
        X_train = clr_transform(X_train.copy())
        X_test  = clr_transform(X_test.copy())

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_test  = scaler.transform(X_test).astype(np.float32)

    torch.manual_seed(seed)
    np.random.seed(seed)

    # classification=False → MSELoss, raw scalar output; AUROC is rank-invariant
    model = CFNClass(input_dim=X_train.shape[1], classification=False)
    model.fit(X_train, y_train.astype(np.float32), epochs=n_epochs, lr=lr,
              batch_size=batch_size, verbose=False)

    model.eval()
    with torch.no_grad():
        scores = model(torch.FloatTensor(X_test)).squeeze().cpu().numpy()

    dep_matrix = model.get_dependency_matrix()

    if len(np.unique(y_test)) < 2:
        metrics = {"auroc": float("nan"), "pr_auc": float("nan")}
    else:
        metrics = {
            "auroc":  float(roc_auc_score(y_test, scores)),
            "pr_auc": float(average_precision_score(y_test, scores)),
        }
    metrics.update({"n_train": int(len(y_train)), "n_test": int(len(y_test))})

    return metrics, dep_matrix


# ---------------------------------------------------------------------------
# Within-dataset 5-fold CV
# ---------------------------------------------------------------------------

def within_cv(
    CFNClass,
    data: dict,
    dataset_name: str,
    n_epochs: int,
    lr: float,
    batch_size: int,
    apply_clr: bool,
    seed: int,
    output_dir: Path,
) -> tuple[list[dict], dict]:
    log(f"\n  Within-dataset CV: {dataset_name}")
    id_to_idx = {did: i for i, did in enumerate(data["donor_ids"])}
    cfn_dir = output_dir / "cfn_structures"
    cfn_dir.mkdir(parents=True, exist_ok=True)
    fold_records = []

    for i, fold_spec in enumerate(data["folds"]):
        train_idx = [id_to_idx[d] for d in fold_spec["train_ids"] if d in id_to_idx]
        test_idx  = [id_to_idx[d] for d in fold_spec["test_ids"]  if d in id_to_idx]

        t0 = time.time()
        metrics, dep_matrix = train_eval_cfn(
            CFNClass,
            data["X"][train_idx], data["y"][train_idx],
            data["X"][test_idx],  data["y"][test_idx],
            data["feature_names"], n_epochs, lr, batch_size, apply_clr, seed + i,
        )
        log(f"    fold {i}: AUROC={metrics['auroc']:.3f}  PR-AUC={metrics['pr_auc']:.3f}  "
            f"({time.time()-t0:.1f}s)")

        json_path = cfn_dir / f"{dataset_name}_cfn_fold{i}.json"
        with open(json_path, "w") as f:
            json.dump({
                "run_name": f"{dataset_name}_4types_cv",
                "fold": i, "model": "GatedStructuralCFN", "seed": seed + i,
                "artifacts": {
                    "feature_names": data["feature_names"],
                    "dependency_matrix": dep_matrix.tolist(),
                },
                **metrics,
            }, f, indent=2)

        fold_records.append({"dataset": dataset_name, "fold": i, **metrics})

    aurocs = [r["auroc"] for r in fold_records if not np.isnan(r["auroc"])]
    summary = {
        "dataset": dataset_name, "setting": "within_cv_4types",
        "mean_auroc": float(np.mean(aurocs)),
        "std_auroc":  float(np.std(aurocs)),
        "mean_pr_auc": float(np.mean([r["pr_auc"] for r in fold_records
                                      if not np.isnan(r["pr_auc"])])),
        "n_folds": len(fold_records),
    }
    log(f"  {dataset_name} CV: AUROC={summary['mean_auroc']:.3f}±{summary['std_auroc']:.3f}")
    return fold_records, summary


# ---------------------------------------------------------------------------
# Cross-dataset (train on A, test on B — full datasets)
# ---------------------------------------------------------------------------

def cross_dataset_eval(
    CFNClass,
    train_data: dict,
    test_data: dict,
    train_name: str,
    test_name: str,
    n_epochs: int,
    lr: float,
    batch_size: int,
    apply_clr: bool,
    seed: int,
    output_dir: Path,
) -> dict:
    log(f"\n  Cross-dataset: {train_name} → {test_name}")
    t0 = time.time()
    metrics, dep_matrix = train_eval_cfn(
        CFNClass,
        train_data["X"], train_data["y"],
        test_data["X"],  test_data["y"],
        train_data["feature_names"], n_epochs, lr, batch_size, apply_clr, seed,
    )
    log(f"  AUROC={metrics['auroc']:.3f}  PR-AUC={metrics['pr_auc']:.3f}  ({time.time()-t0:.1f}s)")

    run_key = f"{train_name}_to_{test_name}"
    cfn_dir = output_dir / "cfn_structures"
    cfn_dir.mkdir(parents=True, exist_ok=True)
    with open(cfn_dir / f"{run_key}.json", "w") as f:
        json.dump({
            "run_name": run_key,
            "train_dataset": train_name, "test_dataset": test_name,
            "model": "GatedStructuralCFN",
            "artifacts": {
                "feature_names": train_data["feature_names"],
                "dependency_matrix": dep_matrix.tolist(),
            },
            **metrics,
        }, f, indent=2)

    return {"direction": run_key, "train_dataset": train_name, "test_dataset": test_name, **metrics}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scp-features",  default="data/processed/uc_scp259/donor_cluster_props.tsv")
    p.add_argument("--scp-metadata",  default="data/processed/uc_scp259/donor_metadata.tsv")
    p.add_argument("--scp-folds",     default="data/processed/uc_scp259/donor_healthy_vs_uc_folds.json")
    p.add_argument("--kong-features", default="data/processed/kong2023_cd/donor_cluster_props.tsv")
    p.add_argument("--kong-metadata", default="data/processed/kong2023_cd/donor_metadata.tsv")
    p.add_argument("--kong-folds",    default="data/processed/kong2023_cd/donor_cd_vs_healthy_folds.json")
    p.add_argument("--output-dir",    default="results/cross_dataset_cfn_4types")
    p.add_argument("--n-epochs",      type=int, default=300)
    p.add_argument("--lr",            type=float, default=0.01)
    p.add_argument("--batch-size",    type=int, default=8,
                   help="Very small batch for n~30 (default 8)")
    p.add_argument("--seed",          type=int, default=42)
    p.add_argument("--apply-clr",     action="store_true")
    p.add_argument("--cell-types",    default=",".join(SHARED_CELL_TYPES))
    return p.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cell_types = [c.strip() for c in args.cell_types.split(",")]
    log(f"Shared cell types ({len(cell_types)}): {cell_types}")

    log("Importing GatedStructuralCFN...")
    CFNClass = import_cfn()
    log(f"Using: {CFNClass.__name__}")

    log("\nLoading SCP259 (UC vs Healthy)...")
    scp = load_dataset(
        Path(args.scp_features), Path(args.scp_metadata), Path(args.scp_folds),
        label_col="donor_label", positive_label="UC", cell_types=cell_types,
    )
    log(f"  {len(scp['donor_ids'])} donors, {len(scp['feature_names'])} features")
    log(f"  UC={int(scp['y'].sum())}  Healthy={int((1-scp['y']).sum())}")

    log("\nLoading Kong 2023 (CD vs Healthy)...")
    kong = load_dataset(
        Path(args.kong_features), Path(args.kong_metadata), Path(args.kong_folds),
        label_col="donor_label", positive_label="CD", cell_types=cell_types,
    )
    log(f"  {len(kong['donor_ids'])} donors, {len(kong['feature_names'])} features")
    log(f"  CD={int(kong['y'].sum())}  Healthy={int((1-kong['y']).sum())}")

    all_summary = []

    # 1. Within-dataset CV: SCP259
    scp_folds, scp_summary = within_cv(
        CFNClass, scp, "scp259",
        args.n_epochs, args.lr, args.batch_size, args.apply_clr, args.seed, output_dir,
    )
    all_summary.append(scp_summary)
    pd.DataFrame(scp_folds).to_csv(output_dir / "scp_cv_fold_metrics.tsv", sep="\t", index=False)

    # 2. Within-dataset CV: Kong
    kong_folds, kong_summary = within_cv(
        CFNClass, kong, "kong2023",
        args.n_epochs, args.lr, args.batch_size, args.apply_clr, args.seed, output_dir,
    )
    all_summary.append(kong_summary)
    pd.DataFrame(kong_folds).to_csv(output_dir / "kong_cv_fold_metrics.tsv", sep="\t", index=False)

    # 3. Cross-dataset: SCP259 → Kong
    s2k = cross_dataset_eval(
        CFNClass, scp, kong, "SCP259_UC", "Kong2023_CD",
        args.n_epochs, args.lr, args.batch_size, args.apply_clr, args.seed, output_dir,
    )
    all_summary.append({
        "dataset": "SCP259_UC→Kong2023_CD", "setting": "cross_dataset",
        "mean_auroc": s2k["auroc"], "std_auroc": float("nan"),
        "mean_pr_auc": s2k["pr_auc"], "n_folds": 1,
    })

    # 4. Cross-dataset: Kong → SCP259
    k2s = cross_dataset_eval(
        CFNClass, kong, scp, "Kong2023_CD", "SCP259_UC",
        args.n_epochs, args.lr, args.batch_size, args.apply_clr, args.seed, output_dir,
    )
    all_summary.append({
        "dataset": "Kong2023_CD→SCP259_UC", "setting": "cross_dataset",
        "mean_auroc": k2s["auroc"], "std_auroc": float("nan"),
        "mean_pr_auc": k2s["pr_auc"], "n_folds": 1,
    })

    pd.DataFrame(all_summary).to_csv(output_dir / "summary.tsv", sep="\t", index=False)
    pd.DataFrame([s2k, k2s]).to_csv(output_dir / "cross_dataset_metrics.tsv", sep="\t", index=False)

    log("\n=== SUMMARY ===")
    log(pd.DataFrame(all_summary).to_string(index=False))
    log(f"\nAll outputs: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
