"""
extract_kong_obs.py
===================
Extract ONLY the obs (cell metadata) from a Kong 2023 H5AD file and save it
as a lightweight parquet (~a few MB). Does NOT load gene expression matrix X.

This allows disk-constrained sequential processing: download each H5AD, run
this script to extract obs, delete the H5AD, then move to the next file.

After all 6 files are processed, run build_kong2023_donor_tables.py with
--from-obs-cache to build final composition tables from the parquet cache.

Usage
-----
python scripts/extract_kong_obs.py \
    --h5ad data/raw/kong2023_cd/TI_immune.h5ad \
    --compartment TI_immune \
    --obs-cache-dir data/processed/kong2023_cd/obs_cache
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

WANTED_COLS = ["donor_id", "disease", "Celltype", "Type", "Layer", "biosample_id"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--h5ad", type=Path, required=True, help="Path to H5AD file.")
    p.add_argument("--compartment", required=True,
                   help="Compartment label (e.g. TI_immune, colon_epithelial).")
    p.add_argument("--obs-cache-dir", type=Path,
                   default=Path("data/processed/kong2023_cd/obs_cache"),
                   help="Directory to save obs parquet files.")
    args = p.parse_args()

    args.obs_cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading obs from {args.h5ad} ...", flush=True)
    try:
        import anndata as ad
    except ImportError:
        raise ImportError("anndata required: pip install anndata")

    # backed=True reads only metadata, not the full gene matrix
    adata = ad.read_h5ad(args.h5ad, backed="r")
    obs = adata.obs.copy()
    adata.file.close()

    obs["compartment"] = args.compartment
    obs["donor_id"] = obs["donor_id"].astype(str)

    # Keep only wanted columns (plus compartment)
    keep = [c for c in WANTED_COLS + ["compartment"] if c in obs.columns]
    obs = obs[keep].reset_index(drop=True)

    out_path = args.obs_cache_dir / f"{args.compartment}_obs.parquet"
    obs.to_parquet(out_path, index=False)

    n_cells = len(obs)
    n_donors = obs["donor_id"].nunique()
    diseases = obs.groupby("disease")["donor_id"].nunique().to_dict() if "disease" in obs.columns else {}
    print(f"  Saved {n_cells:,} cells, {n_donors} donors → {out_path}")
    print(f"  Disease breakdown: {diseases}")
    print("Done.")


if __name__ == "__main__":
    main()
