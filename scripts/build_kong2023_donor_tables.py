#!/usr/bin/env python3

"""Build donor-level feature tables from Kong et al. 2023 CD atlas H5AD files.

Kong et al. 2023: "The landscape of immune dysregulation in Crohn's disease
revealed through single-cell transcriptomics". Nat Commun.
CELLxGENE collection: https://cellxgene.cziscience.com/collections/5c868b6f-...

This script builds the same two donor-level feature families used for SCP259:
  1. donor_cluster_props  — proportion of each cell type per donor
  2. donor_pseudobulk     — mean log1p-normalised expression per donor

Schema discovered from H5AD inspection:
  obs['donor_id']   — numeric string donor ID (e.g. "105446")
  obs['disease']    — "Crohn disease" | "normal"
  obs['Celltype']   — fine-grained cell type label (e.g. "Fibroblasts ADAMDEC1")
  obs['Type']       — "Infl" | "NonI" | "Heal" (inflammation status per sample)
  obs['Layer']      — "N" (mucosa) | "L" (lamina propria) | "E" (epithelial)
  X                 — log1p-normalised expression (NOT raw counts); row sums ~12000
  var.index         — Ensembl gene IDs; var['feature_name'] — gene symbols

Files expected in --raw-dir:
  TI_epithelial.h5ad, TI_immune.h5ad, TI_stromal.h5ad
  colon_epithelial.h5ad, colon_immune.h5ad, colon_stromal.h5ad

Usage:
    python scripts/build_kong2023_donor_tables.py \\
        --raw-dir  data/raw/kong2023_cd \\
        --output-dir data/processed/kong2023_cd

Outputs (written to --output-dir):
    donor_metadata.tsv              — donor_id, donor_label, disease, n_cells, ...
    donor_cluster_props.tsv         — donor × cell_type proportions (all cells)
    donor_cluster_counts.tsv        — donor × cell_type raw counts
    donor_pseudobulk_log1p.tsv.gz   — donor × gene mean log1p expression
    donor_colon_cluster_props.tsv   — colon-only composition
    donor_TI_cluster_props.tsv      — TI-only composition
    gene_universe.tsv               — union of genes across all 6 files
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


FILES = {
    "TI_epithelial":   "TI_epithelial.h5ad",
    "TI_immune":       "TI_immune.h5ad",
    "TI_stromal":      "TI_stromal.h5ad",
    "colon_epithelial":"colon_epithelial.h5ad",
    "colon_immune":    "colon_immune.h5ad",
    "colon_stromal":   "colon_stromal.h5ad",
}

COLON_KEYS = {"colon_epithelial", "colon_immune", "colon_stromal"}
TI_KEYS    = {"TI_epithelial",    "TI_immune",    "TI_stromal"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Kong 2023 donor feature tables.")
    p.add_argument("--raw-dir",    type=Path, default=Path("data/raw/kong2023_cd"))
    p.add_argument("--output-dir", type=Path, default=Path("data/processed/kong2023_cd"))
    p.add_argument("--min-cells-per-donor", type=int, default=50,
                   help="Drop donors with fewer than this many cells (default 50).")
    p.add_argument("--max-genes",  type=int, default=2000,
                   help="Top-variance genes for pseudobulk (0 = keep all).")
    p.add_argument("--skip-pseudobulk", action="store_true")
    p.add_argument("--obs-cache-dir", type=Path, default=None,
                   help="Directory of obs parquets from extract_kong_obs.py.")
    p.add_argument("--from-obs-cache", action="store_true",
                   help="Build composition tables from pre-saved obs parquets instead of H5ADs.")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Load one H5AD file
# ---------------------------------------------------------------------------

def load_h5ad(path: Path, label: str) -> pd.DataFrame:
    """Load a Kong H5AD and return a tidy cell-level DataFrame.

    Returns columns: donor_id, disease, Celltype, compartment, gene_expr_*
    (gene expression columns are skipped here — handled separately for memory).
    """
    try:
        import anndata as ad
    except ImportError:
        raise ImportError("anndata is required: pip install anndata")

    log(f"  Loading {label} ({path.name}) ...")
    t0 = time.time()
    adata = ad.read_h5ad(path)          # full load (not backed) for aggregation
    log(f"  {label}: shape={adata.shape}  ({time.time()-t0:.1f}s)")
    return adata


# ---------------------------------------------------------------------------
# Build donor metadata
# ---------------------------------------------------------------------------

def build_donor_metadata(obs_all: pd.DataFrame, min_cells: int) -> pd.DataFrame:
    """Build one row per donor from the combined obs table."""
    required = ["donor_id", "disease", "Celltype"]
    for col in required:
        if col not in obs_all.columns:
            raise ValueError(f"Expected column '{col}' not found. obs columns: {list(obs_all.columns)}")

    # disease → binary label: CD vs non-IBD (normal)
    # Kong has CD donors and healthy controls. We frame as CD vs. Healthy.
    obs_all["donor_label"] = obs_all["disease"].map(
        lambda d: "CD" if "crohn" in d.lower() or "crohn's" in d.lower() else "Healthy"
    )

    donor_meta = (
        obs_all.groupby("donor_id", sort=True)
        .agg(
            donor_label        =("donor_label",  "first"),
            disease_raw        =("disease",       "first"),
            n_cells            =("donor_id",      "count"),
            n_celltypes        =("Celltype",      "nunique"),
        )
        .reset_index()
    )

    if "Type" in obs_all.columns:
        type_counts = (
            obs_all.groupby(["donor_id","Type"]).size().unstack(fill_value=0)
        )
        for col in type_counts.columns:
            donor_meta[f"n_cells_{col}"] = type_counts[col].reindex(
                donor_meta["donor_id"]
            ).values

    # Filter donors with too few cells
    n_before = len(donor_meta)
    donor_meta = donor_meta[donor_meta["n_cells"] >= min_cells].copy()
    n_after = len(donor_meta)
    if n_before > n_after:
        log(f"  Dropped {n_before - n_after} donors with < {min_cells} cells")

    return donor_meta.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Build composition tables
# ---------------------------------------------------------------------------

def build_composition(
    obs: pd.DataFrame,
    valid_donors: set[str],
    label: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build donor × cell_type count and proportion tables."""
    obs = obs[obs["donor_id"].isin(valid_donors)].copy()
    obs["donor_id"] = obs["donor_id"].astype(str)
    counts = pd.crosstab(obs["donor_id"], obs["Celltype"]).sort_index()
    props  = counts.div(counts.sum(axis=1), axis=0).round(8)
    counts.index.name = "donor_id"
    props.index.name  = "donor_id"
    log(f"  [{label}] composition: {counts.shape[0]} donors × {counts.shape[1]} cell types")
    return counts, props


# ---------------------------------------------------------------------------
# Build pseudobulk
# ---------------------------------------------------------------------------

def build_pseudobulk(
    adatas: dict[str, object],
    valid_donors: set[str],
    max_genes: int,
) -> pd.DataFrame:
    """Build donor × gene mean log1p expression across all compartments.

    X in Kong H5ADs is already log1p-normalised; we take the mean per donor
    across all cells, which preserves the normalisation scale.
    """
    import scipy.sparse as sp

    log("  Building gene union across all compartments...")
    # Collect gene union and per-file gene indices
    all_genes_ordered: list[str] = []
    gene_set: set[str] = set()
    file_genes: dict[str, list[str]] = {}

    for key, adata in adatas.items():
        # Prefer feature_name (gene symbols) over Ensembl IDs
        if "feature_name" in adata.var.columns:
            genes = adata.var["feature_name"].tolist()
        else:
            genes = adata.var.index.tolist()
        file_genes[key] = genes
        for g in genes:
            if g not in gene_set:
                all_genes_ordered.append(g)
                gene_set.add(g)

    n_genes = len(all_genes_ordered)
    gene_to_idx = {g: i for i, g in enumerate(all_genes_ordered)}
    all_donors = sorted(valid_donors)
    donor_to_idx = {d: i for i, d in enumerate(all_donors)}

    donor_gene_sum   = np.zeros((len(all_donors), n_genes), dtype=np.float32)
    donor_cell_count = np.zeros(len(all_donors), dtype=np.int64)

    for key, adata in adatas.items():
        obs_mask = adata.obs["donor_id"].isin(valid_donors)
        adata_sub = adata[obs_mask]
        genes = file_genes[key]
        gene_idx_map = np.array([gene_to_idx[g] for g in genes], dtype=np.int32)

        donor_ids = adata_sub.obs["donor_id"].values
        X = adata_sub.X
        if sp.issparse(X):
            X = X.toarray()
        X = np.array(X, dtype=np.float32)

        log(f"  Accumulating {key}: {X.shape[0]} cells × {X.shape[1]} genes")
        for d_str in np.unique(donor_ids):
            d_idx   = donor_to_idx[d_str]
            d_mask  = donor_ids == d_str
            d_expr  = X[d_mask, :]
            donor_gene_sum[d_idx, gene_idx_map] += d_expr.sum(axis=0)
            donor_cell_count[d_idx]             += d_mask.sum()

    # Mean expression per donor
    with np.errstate(invalid="ignore"):
        donor_gene_mean = donor_gene_sum / donor_cell_count[:, np.newaxis]
    donor_gene_mean = np.nan_to_num(donor_gene_mean, nan=0.0)

    pseudobulk_df = pd.DataFrame(
        donor_gene_mean,
        index=pd.Index(all_donors, name="donor_id"),
        columns=all_genes_ordered,
    )

    # Variance-filter to top-max_genes
    if max_genes > 0 and pseudobulk_df.shape[1] > max_genes:
        variances = pseudobulk_df.var(axis=0)
        top_genes = variances.nlargest(max_genes).index
        pseudobulk_df = pseudobulk_df[top_genes]
        log(f"  Variance filter: kept top {max_genes} genes out of {n_genes}")

    log(f"  Pseudobulk shape: {pseudobulk_df.shape}")
    return pseudobulk_df, pd.DataFrame({"gene": all_genes_ordered})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    raw_dir    = args.raw_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import anndata as ad
    except ImportError:
        raise ImportError("anndata is required: pip install anndata scvi-tools")

    # ------------------------------------------------------------------
    # Optionally load obs from pre-saved parquet cache (disk-constrained mode)
    # ------------------------------------------------------------------
    if args.from_obs_cache:
        cache_dir = (args.obs_cache_dir or args.output_dir / "obs_cache").resolve()
        obs_frames = []
        parquets = sorted(cache_dir.glob("*_obs.parquet"))
        if not parquets:
            raise RuntimeError(f"No *_obs.parquet files found in {cache_dir}")
        for pq in parquets:
            df = pd.read_parquet(pq)
            obs_frames.append(df)
            log(f"  Loaded obs cache: {pq.name}  ({len(df):,} cells)")
        obs_all = pd.concat(obs_frames, ignore_index=True)
        obs_all["donor_id"] = obs_all["donor_id"].astype(str)
        # Ensure string type propagates to all compartment subsets
        for col in ["donor_id"]:
            if col in obs_all.columns:
                obs_all[col] = obs_all[col].astype(str)
        log(f"\nCombined obs: {len(obs_all):,} cells, {obs_all['donor_id'].nunique()} donors")
        log(f"Disease breakdown: {obs_all.groupby('disease')['donor_id'].nunique().to_dict()}")
        # Skip to composition (no pseudobulk in cache mode since we don't have X)
        log("\nBuilding donor metadata...")
        donor_meta = build_donor_metadata(obs_all, min_cells=args.min_cells_per_donor)
        valid_donors = set(donor_meta["donor_id"].astype(str))
        log(f"  Final donor set: {len(valid_donors)} donors  "
            f"(CD={(donor_meta['donor_label']=='CD').sum()}, "
            f"Healthy={(donor_meta['donor_label']=='Healthy').sum()})")
        donor_meta_path = output_dir / "donor_metadata.tsv"
        donor_meta.to_csv(donor_meta_path, sep="\t", index=False)
        log(f"  [ok] {donor_meta_path}")

        log("\nBuilding composition tables...")
        counts_all, props_all = build_composition(obs_all, valid_donors, "all")
        counts_all.reset_index().to_csv(output_dir / "donor_cluster_counts.tsv", sep="\t", index=False)
        props_all.reset_index().to_csv(output_dir / "donor_cluster_props.tsv",   sep="\t", index=False)
        obs_colon = obs_all[obs_all["compartment"].isin(COLON_KEYS)]
        if len(obs_colon) > 0:
            _, props_colon = build_composition(obs_colon, valid_donors, "colon")
            props_colon.reset_index().to_csv(output_dir / "donor_colon_cluster_props.tsv", sep="\t", index=False)
        obs_ti = obs_all[obs_all["compartment"].isin(TI_KEYS)]
        if len(obs_ti) > 0:
            _, props_ti = build_composition(obs_ti, valid_donors, "TI")
            props_ti.reset_index().to_csv(output_dir / "donor_TI_cluster_props.tsv", sep="\t", index=False)
        log("  [ok] Composition tables written (from obs cache, pseudobulk skipped)")
        log(f"\n=== Kong 2023 donor tables complete ===")
        log(f"  Output: {output_dir}")
        log(f"  Donors: {len(valid_donors)}")
        log(f"  Cell types (all): {len(counts_all.columns)}")
        log(f"  Composition features: donor_cluster_props.tsv ({props_all.shape})")
        return

    # ------------------------------------------------------------------
    # Load all 6 H5AD files
    # ------------------------------------------------------------------
    adatas: dict[str, object] = {}
    obs_frames: list[pd.DataFrame] = []

    for key, fname in FILES.items():
        path = raw_dir / fname
        if not path.exists():
            log(f"  [skip] {path} not found — skipping this compartment")
            continue
        adata = load_h5ad(path, key)
        adata.obs["compartment"] = key
        adatas[key] = adata
        obs_frames.append(adata.obs[["donor_id","disease","Celltype","compartment"]
                                     + [c for c in ["Type","Layer","biosample_id"]
                                        if c in adata.obs.columns]])

    if not obs_frames:
        raise RuntimeError("No H5AD files found in --raw-dir. Run downloads first.")

    obs_all = pd.concat(obs_frames, ignore_index=True)
    obs_all["donor_id"] = obs_all["donor_id"].astype(str)

    log(f"\nCombined obs: {len(obs_all):,} cells, {obs_all['donor_id'].nunique()} donors")
    log(f"Disease breakdown: {obs_all.groupby('disease')['donor_id'].nunique().to_dict()}")

    # ------------------------------------------------------------------
    # Donor metadata
    # ------------------------------------------------------------------
    log("\nBuilding donor metadata...")
    donor_meta = build_donor_metadata(obs_all, min_cells=args.min_cells_per_donor)
    valid_donors = set(donor_meta["donor_id"].astype(str))
    log(f"  Final donor set: {len(valid_donors)} donors  "
        f"(CD={( donor_meta['donor_label']=='CD').sum()}, "
        f"Healthy={(donor_meta['donor_label']=='Healthy').sum()})")

    donor_meta_path = output_dir / "donor_metadata.tsv"
    donor_meta.to_csv(donor_meta_path, sep="\t", index=False)
    log(f"  [ok] {donor_meta_path}")

    # ------------------------------------------------------------------
    # Composition — all cells combined
    # ------------------------------------------------------------------
    log("\nBuilding composition tables...")
    counts_all, props_all = build_composition(obs_all, valid_donors, "all")
    counts_all.reset_index().to_csv(output_dir / "donor_cluster_counts.tsv",  sep="\t", index=False)
    props_all.reset_index().to_csv( output_dir / "donor_cluster_props.tsv",   sep="\t", index=False)

    # Colon-only composition
    obs_colon = obs_all[obs_all["compartment"].isin(COLON_KEYS)]
    if len(obs_colon) > 0:
        _, props_colon = build_composition(obs_colon, valid_donors, "colon")
        props_colon.reset_index().to_csv(output_dir / "donor_colon_cluster_props.tsv",
                                         sep="\t", index=False)

    # TI-only composition
    obs_ti = obs_all[obs_all["compartment"].isin(TI_KEYS)]
    if len(obs_ti) > 0:
        _, props_ti = build_composition(obs_ti, valid_donors, "TI")
        props_ti.index = props_ti.index.astype(str)
        props_ti.reset_index().to_csv(output_dir / "donor_TI_cluster_props.tsv",
                                      sep="\t", index=False)

    log("  [ok] Composition tables written")

    # ------------------------------------------------------------------
    # Pseudobulk
    # ------------------------------------------------------------------
    if not args.skip_pseudobulk:
        log("\nBuilding pseudobulk (this takes a few minutes)...")
        pseudobulk_df, gene_info = build_pseudobulk(adatas, valid_donors, args.max_genes)
        pb_path = output_dir / "donor_pseudobulk_log1p.tsv.gz"
        pseudobulk_df.reset_index().to_csv(pb_path, sep="\t", index=False, compression="gzip")
        gene_info.to_csv(output_dir / "gene_universe.tsv", sep="\t", index=False)
        log(f"  [ok] {pb_path}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log("\n=== Kong 2023 donor tables complete ===")
    log(f"  Output: {output_dir}")
    log(f"  Donors: {len(valid_donors)}")
    log(f"  Cell types (all): {len(counts_all.columns)}")
    log(f"  Composition features: donor_cluster_props.tsv ({props_all.shape})")
    log(f"\nNext step:")
    log(f"  python scripts/run_kong2023_baselines.py \\")
    log(f"    --smillie-results results/uc_scp259/benchmarks \\")
    log(f"    --kong-features   {output_dir}/donor_cluster_props.tsv \\")
    log(f"    --kong-metadata   {output_dir}/donor_metadata.tsv \\")
    log(f"    --output-dir      results/kong2023_cd/benchmarks")


if __name__ == "__main__":
    main()
