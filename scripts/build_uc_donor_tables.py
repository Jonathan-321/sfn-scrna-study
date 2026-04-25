#!/usr/bin/env python3

"""Build first-pass donor-level tables for the UC SCP259 benchmark."""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


FAMILIES = ("Epi", "Fib", "Imm")


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build donor metadata, composition tables, and donor-level "
            "all-cell pseudobulk tables for the UC SCP259 dataset."
        )
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/uc_scp259"),
        help="Directory containing all.meta2.txt and the split matrix files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/uc_scp259"),
        help="Directory where processed donor tables should be written.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5_000_000,
        help="Matrix-market rows to parse per pandas chunk.",
    )
    parser.add_argument(
        "--families",
        default="Epi,Fib,Imm",
        help="Comma-separated matrix families to process. Default: Epi,Fib,Imm",
    )
    parser.add_argument(
        "--skip-pseudobulk",
        action="store_true",
        help="Only build metadata and composition tables.",
    )
    return parser.parse_args()


def load_metadata(path: Path) -> pd.DataFrame:
    metadata = pd.read_csv(path, sep="\t", dtype=str)
    metadata = metadata.loc[metadata["NAME"] != "TYPE"].copy()
    metadata["nGene"] = metadata["nGene"].astype(np.int32)
    metadata["nUMI"] = metadata["nUMI"].astype(np.int32)
    return metadata


def build_donor_metadata(metadata: pd.DataFrame) -> pd.DataFrame:
    donor_health_values = metadata.groupby("Subject")["Health"].agg(
        lambda values: ",".join(sorted(set(values)))
    )
    donor_locations = metadata.groupby("Subject")["Location"].agg(
        lambda values: ",".join(sorted(set(values)))
    )
    donor_labels = donor_health_values.map(
        lambda value: "Healthy" if value == "Healthy" else "UC"
    )

    donor_table = pd.DataFrame(
        {
            "donor_id": sorted(metadata["Subject"].unique()),
        }
    ).set_index("donor_id")

    donor_table["donor_label"] = donor_labels.reindex(donor_table.index)
    donor_table["health_values"] = donor_health_values.reindex(donor_table.index)
    donor_table["locations"] = donor_locations.reindex(donor_table.index)
    donor_table["n_cells"] = metadata.groupby("Subject").size().reindex(donor_table.index)
    donor_table["n_samples"] = (
        metadata.groupby("Subject")["Sample"].nunique().reindex(donor_table.index)
    )
    donor_table["n_clusters"] = (
        metadata.groupby("Subject")["Cluster"].nunique().reindex(donor_table.index)
    )
    donor_table["total_nUMI_obs"] = (
        metadata.groupby("Subject")["nUMI"].sum().reindex(donor_table.index)
    )
    donor_table["mean_nUMI_obs"] = (
        metadata.groupby("Subject")["nUMI"].mean().round(2).reindex(donor_table.index)
    )
    donor_table["mean_nGene_obs"] = (
        metadata.groupby("Subject")["nGene"].mean().round(2).reindex(donor_table.index)
    )

    sample_meta = metadata[["Subject", "Sample", "Health", "Location"]].drop_duplicates()
    sample_health_counts = pd.crosstab(sample_meta["Subject"], sample_meta["Health"])
    sample_location_counts = pd.crosstab(sample_meta["Subject"], sample_meta["Location"])
    for frame in (sample_health_counts, sample_location_counts):
        for column in frame.columns:
            donor_table[f"n_samples_{column.lower().replace('-', '_')}"] = frame[
                column
            ].reindex(donor_table.index, fill_value=0)

    return donor_table.reset_index()


def write_composition_tables(metadata: pd.DataFrame, output_dir: Path) -> None:
    donor_cluster_counts = pd.crosstab(metadata["Subject"], metadata["Cluster"]).sort_index()
    donor_location_counts = pd.crosstab(metadata["Subject"], metadata["Location"]).sort_index()
    sample_meta = metadata[["Subject", "Sample", "Health"]].drop_duplicates()
    donor_sample_health_counts = pd.crosstab(
        sample_meta["Subject"], sample_meta["Health"]
    ).sort_index()

    donor_cluster_props = donor_cluster_counts.div(
        donor_cluster_counts.sum(axis=1), axis=0
    ).round(8)
    donor_location_props = donor_location_counts.div(
        donor_location_counts.sum(axis=1), axis=0
    ).round(8)

    for frame in (
        donor_cluster_counts,
        donor_cluster_props,
        donor_location_counts,
        donor_location_props,
        donor_sample_health_counts,
    ):
        frame.index.name = "donor_id"

    donor_cluster_counts.to_csv(output_dir / "donor_cluster_counts.tsv", sep="\t")
    donor_cluster_props.to_csv(output_dir / "donor_cluster_props.tsv", sep="\t")
    donor_location_counts.to_csv(output_dir / "donor_location_counts.tsv", sep="\t")
    donor_location_props.to_csv(output_dir / "donor_location_props.tsv", sep="\t")
    donor_sample_health_counts.to_csv(
        output_dir / "donor_sample_health_counts.tsv", sep="\t"
    )


def read_gene_list(path: Path) -> list[str]:
    with path.open() as handle:
        return [line.rstrip("\n") for line in handle]


def read_barcodes(path: Path) -> list[str]:
    with path.open() as handle:
        return [line.rstrip("\n") for line in handle]


def build_gene_union(raw_dir: Path, families: tuple[str, ...]) -> tuple[list[str], pd.DataFrame]:
    gene_to_index: dict[str, int] = {}
    ordered_genes: list[str] = []
    presence: dict[str, dict[str, int]] = {}

    for family in families:
        genes = read_gene_list(raw_dir / f"{family}.genes.tsv")
        for gene in genes:
            if gene not in gene_to_index:
                gene_to_index[gene] = len(ordered_genes)
                ordered_genes.append(gene)
                presence[gene] = {name: 0 for name in FAMILIES}
            presence[gene][family] = 1

    gene_info = pd.DataFrame(
        {
            "gene": ordered_genes,
            "present_in_epi": [presence[gene]["Epi"] for gene in ordered_genes],
            "present_in_fib": [presence[gene]["Fib"] for gene in ordered_genes],
            "present_in_imm": [presence[gene]["Imm"] for gene in ordered_genes],
        }
    )
    return ordered_genes, gene_info


def parse_matrix_shape(path: Path) -> tuple[int, int, int]:
    with path.open() as handle:
        header = handle.readline().strip()
        if not header.startswith("%%MatrixMarket"):
            raise ValueError(f"{path} is not a MatrixMarket file")
        dims_line = handle.readline().strip()
        n_rows, n_cols, n_entries = [int(value) for value in dims_line.split()]
    return n_rows, n_cols, n_entries


def build_barcode_to_donor_index(
    barcodes: list[str],
    barcode_to_donor: dict[str, str],
    donor_to_index: dict[str, int],
    family: str,
) -> np.ndarray:
    donor_index_by_column = np.empty(len(barcodes), dtype=np.int16)
    missing: list[str] = []
    for idx, barcode in enumerate(barcodes):
        donor = barcode_to_donor.get(barcode)
        if donor is None:
            missing.append(barcode)
            donor_index_by_column[idx] = -1
            continue
        donor_index_by_column[idx] = donor_to_index[donor]
    if missing:
        preview = ", ".join(missing[:5])
        raise KeyError(
            f"{family} barcodes missing from metadata: {len(missing)} missing; "
            f"examples: {preview}"
        )
    return donor_index_by_column


def accumulate_chunk(
    donor_gene_counts: np.ndarray,
    donor_index_by_column: np.ndarray,
    gene_index_by_row: np.ndarray,
    chunk: pd.DataFrame,
) -> None:
    gene_idx = gene_index_by_row[chunk.iloc[:, 0].to_numpy(dtype=np.int64) - 1]
    donor_idx = donor_index_by_column[chunk.iloc[:, 1].to_numpy(dtype=np.int64) - 1]
    counts = chunk.iloc[:, 2].to_numpy(dtype=np.int64)

    for donor in np.unique(donor_idx):
        mask = donor_idx == donor
        donor_gene_counts[donor] += np.bincount(
            gene_idx[mask],
            weights=counts[mask],
            minlength=donor_gene_counts.shape[1],
        ).astype(np.int64, copy=False)


def build_pseudobulk(
    raw_dir: Path,
    metadata: pd.DataFrame,
    output_dir: Path,
    families: tuple[str, ...],
    chunk_size: int,
) -> None:
    donors = sorted(metadata["Subject"].unique())
    donor_to_index = {donor: idx for idx, donor in enumerate(donors)}
    barcode_to_donor = metadata.set_index("NAME")["Subject"].to_dict()

    ordered_genes, gene_info = build_gene_union(raw_dir, families)
    donor_gene_counts = np.zeros((len(donors), len(ordered_genes)), dtype=np.int64)

    log(
        "Building donor pseudobulk across families "
        + ", ".join(families)
        + f" with {len(ordered_genes)} union genes."
    )

    gene_to_index = {gene: idx for idx, gene in enumerate(ordered_genes)}
    for family in families:
        family_start = time.time()
        genes = read_gene_list(raw_dir / f"{family}.genes.tsv")
        barcodes = read_barcodes(raw_dir / f"{family}.barcodes2.tsv")
        n_rows, n_cols, n_entries = parse_matrix_shape(raw_dir / f"gene_sorted-{family}.matrix.mtx")

        if n_rows != len(genes):
            raise ValueError(
                f"{family} gene count mismatch: matrix has {n_rows}, gene file has {len(genes)}"
            )
        if n_cols != len(barcodes):
            raise ValueError(
                f"{family} barcode count mismatch: matrix has {n_cols}, barcode file has {len(barcodes)}"
            )

        gene_index_by_row = np.array([gene_to_index[gene] for gene in genes], dtype=np.int32)
        donor_index_by_column = build_barcode_to_donor_index(
            barcodes, barcode_to_donor, donor_to_index, family
        )

        log(
            f"[{family}] rows={n_rows} cols={n_cols} nnz={n_entries} "
            f"chunk_size={chunk_size}"
        )

        reader = pd.read_csv(
            raw_dir / f"gene_sorted-{family}.matrix.mtx",
            sep=" ",
            header=None,
            skiprows=2,
            names=["gene_idx", "cell_idx", "count"],
            dtype={"gene_idx": np.int32, "cell_idx": np.int32, "count": np.int32},
            chunksize=chunk_size,
            engine="c",
        )

        processed_entries = 0
        total_chunks = max(1, math.ceil(n_entries / chunk_size))
        for chunk_number, chunk in enumerate(reader, start=1):
            accumulate_chunk(
                donor_gene_counts=donor_gene_counts,
                donor_index_by_column=donor_index_by_column,
                gene_index_by_row=gene_index_by_row,
                chunk=chunk,
            )
            processed_entries += len(chunk)
            if chunk_number == 1 or chunk_number == total_chunks or chunk_number % 5 == 0:
                elapsed = time.time() - family_start
                rate = processed_entries / elapsed if elapsed else 0.0
                log(
                    f"[{family}] chunk {chunk_number}/{total_chunks} "
                    f"processed={processed_entries}/{n_entries} "
                    f"rate={rate:,.0f} nnz/sec"
                )

        log(f"[{family}] complete in {time.time() - family_start:.1f}s")

    donor_index = pd.Index(donors, name="donor_id")
    donor_gene_counts_df = pd.DataFrame(
        donor_gene_counts, index=donor_index, columns=ordered_genes
    )
    library_sizes = donor_gene_counts_df.sum(axis=1)
    donor_gene_log1p_cpm = np.log1p(
        donor_gene_counts_df.div(library_sizes.replace(0, np.nan), axis=0) * 1_000_000
    ).fillna(0.0)

    gene_info.to_csv(output_dir / "gene_union_info.tsv", sep="\t", index=False)
    donor_gene_counts_df.to_csv(
        output_dir / "donor_all_cells_gene_counts.tsv.gz",
        sep="\t",
        compression="gzip",
    )
    donor_gene_log1p_cpm.to_csv(
        output_dir / "donor_all_cells_gene_log1p_cpm.tsv.gz",
        sep="\t",
        compression="gzip",
        float_format="%.6f",
    )
    library_sizes.rename("library_size").to_csv(
        output_dir / "donor_all_cells_library_sizes.tsv", sep="\t"
    )


def main() -> None:
    args = parse_args()
    raw_dir = args.raw_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    families = tuple(
        family.strip() for family in args.families.split(",") if family.strip()
    )
    unknown = set(families) - set(FAMILIES)
    if unknown:
        raise ValueError(f"Unsupported families requested: {sorted(unknown)}")

    metadata_path = raw_dir / "all.meta2.txt"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata file: {metadata_path}")

    log(f"Loading metadata from {metadata_path}")
    metadata = load_metadata(metadata_path)
    donor_metadata = build_donor_metadata(metadata)
    donor_metadata.to_csv(output_dir / "donor_metadata.tsv", sep="\t", index=False)
    write_composition_tables(metadata, output_dir)

    if args.skip_pseudobulk:
        log("Skipped pseudobulk build as requested.")
        return

    build_pseudobulk(
        raw_dir=raw_dir,
        metadata=metadata,
        output_dir=output_dir,
        families=families,
        chunk_size=args.chunk_size,
    )
    log(f"Wrote donor tables to {output_dir}")


if __name__ == "__main__":
    main()
