#!/usr/bin/env python3

"""Build donor-by-location tables for the UC SCP259 benchmark."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from build_uc_donor_tables import (
    FAMILIES,
    build_gene_union,
    load_metadata,
    log,
    parse_matrix_shape,
    read_barcodes,
    read_gene_list,
)


ROW_ID_SEPARATOR = "__"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build donor-by-location metadata, composition tables, and "
            "location-aware pseudobulk tables for the UC SCP259 dataset."
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
        help="Directory where processed donor-location tables should be written.",
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
        help="Only build location metadata and composition tables.",
    )
    return parser.parse_args()


def add_location_ids(metadata: pd.DataFrame) -> pd.DataFrame:
    metadata = metadata.copy()
    metadata["donor_id"] = metadata["Subject"]
    metadata["location"] = metadata["Location"]
    metadata["sample_id"] = metadata["Sample"]
    metadata["cluster"] = metadata["Cluster"]
    metadata["cell_id"] = metadata["NAME"]
    metadata["sample_health"] = metadata["Health"]
    metadata["donor_location_id"] = (
        metadata["donor_id"] + ROW_ID_SEPARATOR + metadata["location"]
    )
    donor_labels = (
        metadata.groupby("donor_id")["sample_health"]
        .agg(lambda values: "Healthy" if set(values) == {"Healthy"} else "UC")
        .to_dict()
    )
    metadata["donor_label"] = metadata["donor_id"].map(donor_labels)
    return metadata


def build_donor_location_metadata(metadata: pd.DataFrame) -> pd.DataFrame:
    group = metadata.groupby("donor_location_id", sort=True)
    location_table = pd.DataFrame(index=sorted(metadata["donor_location_id"].unique()))
    location_table.index.name = "donor_location_id"

    location_table["donor_id"] = group["donor_id"].first().reindex(location_table.index)
    location_table["location"] = group["location"].first().reindex(location_table.index)
    location_table["donor_label"] = group["donor_label"].first().reindex(location_table.index)
    location_table["sample_health_values"] = group["sample_health"].agg(
        lambda values: ",".join(sorted(set(values)))
    ).reindex(location_table.index)
    location_table["n_cells"] = group.size().reindex(location_table.index)
    location_table["n_samples"] = group["sample_id"].nunique().reindex(location_table.index)
    location_table["n_clusters"] = group["cluster"].nunique().reindex(location_table.index)
    location_table["total_nUMI_obs"] = group["nUMI"].sum().reindex(location_table.index)
    location_table["mean_nUMI_obs"] = (
        group["nUMI"].mean().round(2).reindex(location_table.index)
    )
    location_table["mean_nGene_obs"] = (
        group["nGene"].mean().round(2).reindex(location_table.index)
    )

    sample_meta = metadata[
        ["donor_location_id", "sample_id", "sample_health", "location"]
    ].drop_duplicates()
    sample_health_counts = pd.crosstab(
        sample_meta["donor_location_id"], sample_meta["sample_health"]
    )
    for column in sorted(sample_health_counts.columns):
        location_table[f"n_samples_{column.lower().replace('-', '_')}"] = (
            sample_health_counts[column]
            .reindex(location_table.index, fill_value=0)
            .astype(np.int32)
        )

    location_table = location_table.reset_index()
    return location_table.sort_values(["donor_id", "location"]).reset_index(drop=True)


def write_location_composition_tables(metadata: pd.DataFrame, output_dir: Path) -> None:
    location_cluster_counts = pd.crosstab(
        metadata["donor_location_id"], metadata["cluster"]
    ).sort_index()
    location_cluster_props = location_cluster_counts.div(
        location_cluster_counts.sum(axis=1), axis=0
    ).round(8)
    location_sample_meta = metadata[
        ["donor_location_id", "sample_id", "sample_health"]
    ].drop_duplicates()
    location_sample_health_counts = pd.crosstab(
        location_sample_meta["donor_location_id"], location_sample_meta["sample_health"]
    ).sort_index()

    for frame in (
        location_cluster_counts,
        location_cluster_props,
        location_sample_health_counts,
    ):
        frame.index.name = "donor_location_id"

    location_cluster_counts.to_csv(
        output_dir / "donor_location_cluster_counts.tsv", sep="\t"
    )
    location_cluster_props.to_csv(
        output_dir / "donor_location_cluster_props.tsv", sep="\t"
    )
    location_sample_health_counts.to_csv(
        output_dir / "donor_location_sample_health_counts.tsv", sep="\t"
    )


def build_barcode_to_row_index(
    barcodes: list[str],
    barcode_to_row_id: dict[str, str],
    row_to_index: dict[str, int],
    family: str,
) -> np.ndarray:
    row_index_by_column = np.empty(len(barcodes), dtype=np.int16)
    missing: list[str] = []
    for idx, barcode in enumerate(barcodes):
        row_id = barcode_to_row_id.get(barcode)
        if row_id is None:
            missing.append(barcode)
            row_index_by_column[idx] = -1
            continue
        row_index_by_column[idx] = row_to_index[row_id]
    if missing:
        preview = ", ".join(missing[:5])
        raise KeyError(
            f"{family} barcodes missing from donor-location metadata: "
            f"{len(missing)} missing; examples: {preview}"
        )
    return row_index_by_column


def accumulate_chunk(
    row_gene_counts: np.ndarray,
    row_index_by_column: np.ndarray,
    gene_index_by_row: np.ndarray,
    chunk: pd.DataFrame,
) -> None:
    gene_idx = gene_index_by_row[chunk.iloc[:, 0].to_numpy(dtype=np.int64) - 1]
    row_idx = row_index_by_column[chunk.iloc[:, 1].to_numpy(dtype=np.int64) - 1]
    counts = chunk.iloc[:, 2].to_numpy(dtype=np.int64)

    for row in np.unique(row_idx):
        mask = row_idx == row
        row_gene_counts[row] += np.bincount(
            gene_idx[mask],
            weights=counts[mask],
            minlength=row_gene_counts.shape[1],
        ).astype(np.int64, copy=False)


def build_location_pseudobulk(
    raw_dir: Path,
    metadata: pd.DataFrame,
    output_dir: Path,
    families: tuple[str, ...],
    chunk_size: int,
) -> None:
    row_ids = sorted(metadata["donor_location_id"].unique())
    row_to_index = {row_id: idx for idx, row_id in enumerate(row_ids)}
    barcode_to_row_id = metadata.set_index("cell_id")["donor_location_id"].to_dict()

    ordered_genes, gene_info = build_gene_union(raw_dir, families)
    row_gene_counts = np.zeros((len(row_ids), len(ordered_genes)), dtype=np.int64)

    log(
        "Building donor-location pseudobulk across families "
        + ", ".join(families)
        + f" with {len(row_ids)} rows and {len(ordered_genes)} union genes."
    )

    gene_to_index = {gene: idx for idx, gene in enumerate(ordered_genes)}
    for family in families:
        family_start = pd.Timestamp.now()
        genes = read_gene_list(raw_dir / f"{family}.genes.tsv")
        barcodes = read_barcodes(raw_dir / f"{family}.barcodes2.tsv")
        n_rows, n_cols, n_entries = parse_matrix_shape(
            raw_dir / f"gene_sorted-{family}.matrix.mtx"
        )

        if n_rows != len(genes):
            raise ValueError(
                f"{family} gene count mismatch: matrix has {n_rows}, gene file has {len(genes)}"
            )
        if n_cols != len(barcodes):
            raise ValueError(
                f"{family} barcode count mismatch: matrix has {n_cols}, barcode file has {len(barcodes)}"
            )

        gene_index_by_row = np.array([gene_to_index[gene] for gene in genes], dtype=np.int32)
        row_index_by_column = build_barcode_to_row_index(
            barcodes, barcode_to_row_id, row_to_index, family
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
                row_gene_counts=row_gene_counts,
                row_index_by_column=row_index_by_column,
                gene_index_by_row=gene_index_by_row,
                chunk=chunk,
            )
            processed_entries += len(chunk)
            if chunk_number == 1 or chunk_number == total_chunks or chunk_number % 5 == 0:
                elapsed = (pd.Timestamp.now() - family_start).total_seconds()
                rate = processed_entries / elapsed if elapsed else 0.0
                log(
                    f"[{family}] chunk {chunk_number}/{total_chunks} "
                    f"processed={processed_entries}/{n_entries} "
                    f"rate={rate:,.0f} nnz/sec"
                )
        elapsed = (pd.Timestamp.now() - family_start).total_seconds()
        log(f"[{family}] complete in {elapsed:.1f}s")

    row_index = pd.Index(row_ids, name="donor_location_id")
    row_gene_counts_df = pd.DataFrame(
        row_gene_counts, index=row_index, columns=ordered_genes
    )
    library_sizes = row_gene_counts_df.sum(axis=1)
    row_gene_log1p_cpm = np.log1p(
        row_gene_counts_df.div(library_sizes.replace(0, np.nan), axis=0) * 1_000_000
    ).fillna(0.0)

    gene_info.to_csv(output_dir / "donor_location_gene_union_info.tsv", sep="\t", index=False)
    row_gene_counts_df.to_csv(
        output_dir / "donor_location_gene_counts.tsv.gz",
        sep="\t",
        compression="gzip",
    )
    row_gene_log1p_cpm.to_csv(
        output_dir / "donor_location_gene_log1p_cpm.tsv.gz",
        sep="\t",
        compression="gzip",
        float_format="%.6f",
    )
    library_sizes.rename("library_size").to_csv(
        output_dir / "donor_location_library_sizes.tsv", sep="\t"
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
    metadata = add_location_ids(load_metadata(metadata_path))
    donor_location_metadata = build_donor_location_metadata(metadata)
    donor_location_metadata.to_csv(
        output_dir / "donor_location_metadata.tsv", sep="\t", index=False
    )
    write_location_composition_tables(metadata, output_dir)

    if args.skip_pseudobulk:
        log("Skipped donor-location pseudobulk build as requested.")
        return

    build_location_pseudobulk(
        raw_dir=raw_dir,
        metadata=metadata,
        output_dir=output_dir,
        families=families,
        chunk_size=args.chunk_size,
    )
    log(f"Wrote donor-location tables to {output_dir}")


if __name__ == "__main__":
    main()
