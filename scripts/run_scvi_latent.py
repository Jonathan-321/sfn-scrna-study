#!/usr/bin/env python3

"""Train scVI on the UC SCP259 count matrix and extract per-donor mean latent.

This script implements the scVI latent baseline described in the publication
roadmap (§4.5 and §5.4).  It:

  1. Builds an AnnData object from the raw count matrices (same files used by
     build_uc_donor_tables.py).
  2. Trains scVI with donor as the batch key (batch correction).
  3. Extracts the per-cell latent (z) and aggregates to per-donor mean z.
  4. Writes the donor mean latent as a feature TSV compatible with
     run_uc_baselines.py and run_uc_repeated_cv.py.
  5. (Optional) also trains scANVI for semi-supervised integration.

The resulting latent feature table can then be fed directly into:
    python scripts/run_uc_repeated_cv.py \\
        --features data/processed/uc_scp259/donor_scvi_latent.tsv \\
        --run-name donor_scvi_latent \\
        --models logreg,linear_svm,xgb,elasticnet \\
        --max-features 0

Dependencies:
    pip install scvi-tools anndata scipy

Usage (from repo root):
    python scripts/run_scvi_latent.py \\
        --raw-dir   data/raw/uc_scp259 \\
        --metadata  data/processed/uc_scp259/donor_metadata.tsv \\
        --output-dir data/processed/uc_scp259 \\
        --n-latent  20 \\
        --n-epochs  150 \\
        --also-scanvi   # optional semi-supervised variant

Advanced options:
    --n-latent 10     # smaller latent for composition-scale experiments
    --n-latent 30     # richer latent
    --batch-key donor_id   # default
    --covariate-keys location   # include sample location as continuous covariate

Outputs:
    data/processed/uc_scp259/donor_scvi_latent.tsv
        Donor × latent_dim feature table; compatible with run_uc_baselines.py.
    data/processed/uc_scp259/donor_scvi_latent_per_cluster.tsv
        Donor × (cluster × latent_dim) feature table (flattened); optional,
        useful for compartment-aware experiments.
    data/processed/uc_scp259/donor_scanvi_latent.tsv  (if --also-scanvi)
        Same as above but from scANVI semi-supervised model.
    data/processed/uc_scp259/scvi_model/   (model checkpoint)
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers (copied locally to avoid importing from run_uc_baselines in a
# potentially different Python env)
# ---------------------------------------------------------------------------

def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def load_table(path: Path) -> pd.DataFrame:
    suffix = "".join(path.suffixes[-2:]) if len(path.suffixes) >= 2 else path.suffix
    if suffix in {".tsv", ".tsv.gz"}:
        return pd.read_csv(path, sep="\t")
    if suffix in {".csv", ".csv.gz"}:
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table format: {path}")


# ---------------------------------------------------------------------------
# Matrix loading (replicates build_uc_donor_tables.py at cell level)
# ---------------------------------------------------------------------------

def load_mtx_as_csr(raw_dir: Path, family: str):
    """Load a sparse MTX file for one compartment family as a scipy CSR matrix.

    Uses a tolerant custom parser instead of scipy.io.mmread so that
    'gene_sorted' MTX files (which may have fewer nnz entries than the header
    declares — the header reflects the full un-sorted matrix) can be loaded
    without crashing on the entry-count mismatch.

    Returns: (csr_matrix, genes, barcodes)
    """
    try:
        import scipy.sparse as sp
    except ImportError:
        raise ImportError("scipy is required: pip install scipy")

    mtx_path      = raw_dir / f"gene_sorted-{family}.matrix.mtx"
    genes_path    = raw_dir / f"{family}.genes.tsv"
    barcodes_path = raw_dir / f"{family}.barcodes2.tsv"

    genes    = [line.rstrip("\n") for line in genes_path.open()]
    barcodes = [line.rstrip("\n") for line in barcodes_path.open()]
    n_genes    = len(genes)
    n_barcodes = len(barcodes)

    log(f"  [{family}] reading {mtx_path.name} (tolerant parser) ...")
    t0 = time.time()

    # Count comment/header lines to skip
    skip_rows = 0
    with mtx_path.open() as fh:
        for line in fh:
            if line.startswith("%"):
                skip_rows += 1
            else:
                skip_rows += 1  # also skip the dimensions line
                break

    # Fast load with pandas — read as object first to handle malformed lines
    df = pd.read_csv(
        mtx_path, sep=" ", header=None,
        names=["gene", "cell", "value"],
        skiprows=skip_rows,
        on_bad_lines="skip",
        dtype=str,          # read all as string; cast after dropping NAs
    )
    # Drop rows with any NaN (from malformed / partial lines)
    df = df.dropna()
    df["gene"]  = pd.to_numeric(df["gene"],  errors="coerce").astype("Int32")
    df["cell"]  = pd.to_numeric(df["cell"],  errors="coerce").astype("Int32")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    # Drop any out-of-bounds entries
    df = df[(df["gene"] >= 1) & (df["gene"] <= n_genes) &
            (df["cell"] >= 1) & (df["cell"] <= n_barcodes)]

    row_arr  = (df["cell"].values.astype(np.int32) - 1)   # 0-indexed cells
    col_arr  = (df["gene"].values.astype(np.int32) - 1)   # 0-indexed genes
    data_arr = df["value"].values.astype(np.float32)

    mat = sp.csr_matrix(
        (data_arr, (row_arr, col_arr)),
        shape=(n_barcodes, n_genes),
    )
    log(f"  [{family}] shape={mat.shape}  nnz={mat.nnz}  ({time.time()-t0:.1f}s)")

    return mat, genes, barcodes


def build_anndata(raw_dir: Path, metadata: pd.DataFrame, families: tuple[str, ...]):
    """Concatenate all compartment matrices into a single AnnData object.

    AnnData obs (rows) = cells, var (columns) = genes (union).
    obs['donor_id'] and obs['batch'] are set to the Subject column.
    obs['compartment'] is set to the family name.
    Genes not present in a family get zero counts.
    """
    try:
        import anndata as ad
        from scipy.sparse import csr_matrix, hstack, vstack
    except ImportError:
        raise ImportError("anndata and scipy are required: pip install anndata scvi-tools")

    barcode_to_donor = metadata.set_index("NAME")["Subject"].to_dict()
    barcode_to_location = {}
    if "Location" in metadata.columns:
        barcode_to_location = metadata.set_index("NAME")["Location"].to_dict()

    # Collect per-family mats
    family_data = {}
    all_genes_ordered: list[str] = []
    gene_set: set[str] = set()
    for family in families:
        mat, genes, barcodes = load_mtx_as_csr(raw_dir, family)
        family_data[family] = (mat, genes, barcodes)
        for g in genes:
            if g not in gene_set:
                all_genes_ordered.append(g)
                gene_set.add(g)

    gene_to_idx = {g: i for i, g in enumerate(all_genes_ordered)}
    n_genes     = len(all_genes_ordered)

    mats_list      = []
    obs_rows: list[dict] = []

    for family in families:
        mat, genes, barcodes = family_data[family]
        n_cells = len(barcodes)

        # Map family gene indices to global gene indices
        import scipy.sparse as sp
        gene_idx_local  = np.arange(len(genes), dtype=np.int32)
        gene_idx_global = np.array([gene_to_idx[g] for g in genes], dtype=np.int32)

        # Build expanded matrix for this family (cells × n_genes)
        # Use COO directly to avoid the O(n_genes × n_cells) lil_matrix loop.
        mat_coo = mat.tocoo()
        # Remap local gene column indices to global gene indices
        col_global = gene_idx_global[mat_coo.col]
        expanded = sp.coo_matrix(
            (mat_coo.data, (mat_coo.row, col_global)),
            shape=(n_cells, n_genes),
            dtype=np.float32,
        ).tocsr()
        mats_list.append(expanded)

        for bc in barcodes:
            donor = barcode_to_donor.get(bc, "UNKNOWN")
            obs_rows.append({
                "barcode":     bc,
                "donor_id":    donor,
                "batch":       donor,    # use donor as batch key for scVI
                "compartment": family,
                "location":    barcode_to_location.get(bc, "UNKNOWN"),
            })

    # Stack all families
    X_full = vstack(mats_list, format="csr")
    obs_df = pd.DataFrame(obs_rows).set_index("barcode")
    var_df = pd.DataFrame({"gene_id": all_genes_ordered}, index=all_genes_ordered)

    log(f"  Building AnnData: {X_full.shape[0]} cells × {n_genes} genes")
    adata = ad.AnnData(X=X_full, obs=obs_df, var=var_df)
    return adata


# ---------------------------------------------------------------------------
# HVG filter + preprocessing
# ---------------------------------------------------------------------------

def preprocess_adata(adata, n_top_genes: int = 3000, batch_key: str = "batch"):
    """Standard scVI preprocessing: HVG selection on raw counts."""
    try:
        import scanpy as sc
    except ImportError:
        raise ImportError("scanpy is required: pip install scanpy")

    log(f"  Preprocessing AnnData ({adata.shape})...")
    adata.layers["counts"] = adata.X.copy()   # preserve raw counts for scVI

    sc.pp.normalize_total(adata, target_sum=1e4)
    sc.pp.log1p(adata)

    # Try seurat_v3 first; fall back to cell_ranger if LOESS hits near-singularity
    # (can happen with small/sparse subsampled datasets)
    try:
        sc.pp.highly_variable_genes(
            adata,
            n_top_genes=n_top_genes,
            subset=True,
            flavor="seurat_v3",
            layer="counts",
            batch_key=batch_key,
        )
    except (ValueError, Exception) as hvg_err:
        log(f"  seurat_v3 HVG failed ({hvg_err}); falling back to cell_ranger flavor")
        try:
            sc.pp.highly_variable_genes(
                adata,
                n_top_genes=min(n_top_genes, adata.shape[1]),
                subset=True,
                flavor="cell_ranger",
                batch_key=batch_key,
            )
        except (ValueError, Exception) as hvg_err2:
            # cell_ranger can also fail with duplicate bin edges on very sparse data;
            # fall back to no batch_key (pool all cells for HVG selection)
            log(f"  cell_ranger HVG failed ({hvg_err2}); retrying without batch_key")
            sc.pp.highly_variable_genes(
                adata,
                n_top_genes=min(n_top_genes, adata.shape[1]),
                subset=True,
                flavor="cell_ranger",
                batch_key=None,
            )
    log(f"  HVG selection: {adata.shape[1]} genes retained (target={n_top_genes})")
    return adata


# ---------------------------------------------------------------------------
# scVI training
# ---------------------------------------------------------------------------

def train_scvi(adata, n_latent: int, n_epochs: int, batch_key: str, seed: int, model_dir: Path):
    """Train scVI and save the model checkpoint."""
    try:
        import scvi
    except ImportError:
        raise ImportError("scvi-tools is required: pip install scvi-tools")

    scvi.settings.seed = seed
    scvi.model.SCVI.setup_anndata(
        adata,
        layer="counts",
        batch_key=batch_key,
    )
    model = scvi.model.SCVI(
        adata,
        n_latent=n_latent,
        n_layers=2,
        n_hidden=128,
        gene_likelihood="nb",   # negative binomial; standard for scRNA count data
    )
    log(f"  Training scVI (n_latent={n_latent}, n_epochs={n_epochs}) ...")
    model.train(
        max_epochs=n_epochs,
        early_stopping=True,
        plan_kwargs={"lr": 1e-3},
    )
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(model_dir), overwrite=True)
    log(f"  Model saved: {model_dir}")
    return model


def train_scanvi(adata, scvi_model, donor_meta: pd.DataFrame,
                 n_epochs: int, seed: int, model_dir: Path):
    """Fine-tune scANVI from a trained scVI model (semi-supervised).

    Labels are Healthy / UC from donor_meta.  Only donor-level labels are
    available, so we map them back to cells.
    """
    try:
        import scvi
    except ImportError:
        raise ImportError("scvi-tools is required: pip install scvi-tools")

    label_map = donor_meta.set_index("donor_id")["donor_label"].to_dict()
    adata.obs["cell_label"] = adata.obs["donor_id"].map(label_map).fillna("Unknown")

    scvi.model.SCANVI.setup_anndata(adata, labels_key="cell_label", unlabeled_category="Unknown")
    scanvi_model = scvi.model.SCANVI.from_scvi_model(
        scvi_model,
        labels_key="cell_label",
        unlabeled_category="Unknown",
    )
    log(f"  Fine-tuning scANVI (n_epochs={n_epochs}) ...")
    scanvi_model.train(max_epochs=n_epochs)
    model_dir.mkdir(parents=True, exist_ok=True)
    scanvi_model.save(str(model_dir), overwrite=True)
    return scanvi_model


# ---------------------------------------------------------------------------
# Latent extraction + donor aggregation
# ---------------------------------------------------------------------------

def extract_donor_mean_latent(
    adata, model, model_name: str, output_dir: Path
) -> pd.DataFrame:
    """Extract per-cell latent and aggregate to per-donor mean."""
    log(f"  Extracting {model_name} latent representations ...")
    latent = model.get_latent_representation()   # (n_cells, n_latent)
    adata.obsm[f"X_{model_name}"] = latent

    latent_df = pd.DataFrame(
        latent,
        index=adata.obs.index,
        columns=[f"{model_name}_z{i}" for i in range(latent.shape[1])],
    )
    latent_df["donor_id"] = adata.obs["donor_id"].values

    # Per-donor mean
    donor_mean = (
        latent_df.groupby("donor_id")
        .mean()
        .reset_index()
    )
    out_path = output_dir / f"donor_{model_name}_latent.tsv"
    donor_mean.to_csv(out_path, sep="\t", index=False)
    log(f"  [ok] Donor mean latent: {out_path}  shape={donor_mean.shape}")

    # Per-donor per-compartment mean (for compartment-aware experiments)
    latent_df["compartment"] = adata.obs["compartment"].values
    donor_compartment_mean = (
        latent_df.groupby(["donor_id", "compartment"])
        .mean()
        .reset_index()
    )
    # Pivot to wide: donor × (compartment_dim) features
    pivot = donor_compartment_mean.pivot_table(
        index="donor_id", columns="compartment",
        values=[c for c in donor_compartment_mean.columns
                if c.startswith(f"{model_name}_z")],
    )
    pivot.columns = [f"{comp}_{dim}" for dim, comp in pivot.columns]
    pivot = pivot.reset_index()
    comp_path = output_dir / f"donor_{model_name}_latent_per_compartment.tsv"
    pivot.to_csv(comp_path, sep="\t", index=False)
    log(f"  [ok] Donor compartment latent: {comp_path}  shape={pivot.shape}")

    return donor_mean


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train scVI and extract per-donor mean latent features."
    )
    p.add_argument("--raw-dir",    type=Path,
                   default=Path("data/raw/uc_scp259"),
                   help="Directory with raw MTX files.")
    p.add_argument("--metadata",   type=Path,
                   default=Path("data/processed/uc_scp259/donor_metadata.tsv"),
                   help="Donor metadata TSV (from build_uc_donor_tables.py).")
    p.add_argument("--output-dir", type=Path,
                   default=Path("data/processed/uc_scp259"))
    p.add_argument("--families",   default="Epi,Fib,Imm",
                   help="Comma-separated MTX families to load.")
    p.add_argument("--n-latent",   type=int, default=20,
                   help="scVI latent dimension (default 20).")
    p.add_argument("--n-top-genes", type=int, default=3000,
                   help="HVGs for preprocessing (default 3000).")
    p.add_argument("--n-epochs",   type=int, default=150,
                   help="scVI training epochs (default 150).")
    p.add_argument("--batch-key",  default="batch",
                   help="AnnData obs column to use as batch key (default: batch=donor_id).")
    p.add_argument("--also-scanvi", action="store_true",
                   help="Also fine-tune scANVI for semi-supervised latent.")
    p.add_argument("--scanvi-epochs", type=int, default=50)
    p.add_argument("--seed",       type=int, default=42)
    p.add_argument("--model-dir",  type=Path,
                   default=Path("data/processed/uc_scp259/scvi_model"),
                   help="Where to save the trained scVI model checkpoint.")
    p.add_argument("--max-cells-per-donor", type=int, default=0,
                   help="Subsample to at most this many cells per donor before training "
                        "(0 = no limit). Donor mean latent is still computed over all "
                        "cells in memory after subsampling. Recommended: 500-1000 for "
                        "CPU training on large datasets.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Validate raw files exist
    raw_dir = args.raw_dir.resolve()
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {raw_dir}\n"
            "Run bash scripts/download_uc_scp259.sh first."
        )

    donor_meta = load_table(args.metadata)
    # Normalise column names: build_uc_donor_tables.py outputs donor_id + donor_label
    if "donor_id" not in donor_meta.columns:
        raise ValueError("donor_metadata.tsv must contain 'donor_id' column.")

    metadata_full = pd.read_csv(raw_dir / "all.meta2.txt", sep="\t", dtype=str)
    metadata_full = metadata_full.loc[metadata_full["NAME"] != "TYPE"].copy()

    families = tuple(f.strip() for f in args.families.split(",") if f.strip())
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Build AnnData
    log("Building AnnData from raw count matrices ...")
    adata = build_anndata(raw_dir, metadata_full, families)

    # Filter to donors that have metadata labels
    valid_donors = set(donor_meta["donor_id"].astype(str))
    mask = adata.obs["donor_id"].isin(valid_donors)
    adata = adata[mask].copy()
    log(f"After donor filter: {adata.shape[0]} cells, {len(valid_donors)} donors")

    # Optional per-donor subsampling (speeds up CPU training significantly)
    if args.max_cells_per_donor > 0:
        rng = np.random.default_rng(args.seed)
        keep_indices = []
        for donor, grp in adata.obs.groupby("donor_id"):
            idxs = grp.index.tolist()
            if len(idxs) > args.max_cells_per_donor:
                idxs = rng.choice(idxs, size=args.max_cells_per_donor, replace=False).tolist()
            keep_indices.extend(idxs)
        adata = adata[keep_indices].copy()
        log(f"After subsampling ({args.max_cells_per_donor} cells/donor): {adata.shape[0]} cells")

    # Preprocess
    adata = preprocess_adata(adata, n_top_genes=args.n_top_genes, batch_key=args.batch_key)

    # Train scVI
    scvi_model = train_scvi(
        adata, args.n_latent, args.n_epochs,
        args.batch_key, args.seed, args.model_dir,
    )

    # Extract scVI latent
    extract_donor_mean_latent(adata, scvi_model, "scvi", args.output_dir)

    # scANVI (optional)
    if args.also_scanvi:
        scanvi_model_dir = args.model_dir.parent / "scanvi_model"
        scanvi_model = train_scanvi(
            adata, scvi_model, donor_meta,
            args.scanvi_epochs, args.seed, scanvi_model_dir,
        )
        extract_donor_mean_latent(adata, scanvi_model, "scanvi", args.output_dir)

    log("\n[done] scVI latent extraction complete.")
    log("Next: run run_uc_repeated_cv.py with --features data/processed/uc_scp259/donor_scvi_latent.tsv")


if __name__ == "__main__":
    main()
