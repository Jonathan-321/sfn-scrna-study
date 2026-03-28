# UC Metadata Inventory Template

Last updated: 2026-03-09

Use this file to audit whether the ulcerative colitis anchor dataset can support
the first donor-aware benchmark.

## Access status

- Study accession:
- Download path tested:
- Access method:
- Access result:
- Notes:

## Core identifiers

| Field | Present? | Column name | Level | Notes |
|---|---|---|---|---|
| donor_id |  |  | donor |  |
| sample_id |  |  | sample or biopsy |  |
| cell_id |  |  | cell |  |
| library_id |  |  | library |  |
| batch_id |  |  | batch |  |

## Core labels

| Field | Present? | Column name | Expected values | Notes |
|---|---|---|---|---|
| disease_label |  |  | healthy, UC |  |
| inflammation_status |  |  | healthy, non-inflamed, inflamed |  |
| treatment_status |  |  |  |  |
| response_label |  |  |  |  |

## Cell annotation fields

| Field | Present? | Column name | Resolution | Notes |
|---|---|---|---|---|
| coarse_cell_type |  |  | broad |  |
| fine_cell_type |  |  | fine |  |
| cluster_id |  |  | cluster |  |

## Data modalities and matrices

| Item | Present? | Path or file name | Notes |
|---|---|---|---|
| count matrix |  |  |  |
| normalized matrix |  |  |  |
| metadata table |  |  |  |
| marker or annotation file |  |  |  |

## Benchmark readiness checks

| Check | Status | Notes |
|---|---|---|
| donor IDs are usable |  |  |
| disease labels are usable |  |  |
| biopsy nesting is understandable |  |  |
| coarse cell annotations exist or can be built |  |  |
| donor-level pseudobulk is feasible |  |  |
| donor-by-cell-type pseudobulk is feasible |  |  |

## Decision

- Go with UC:
- Hold UC:
- Switch to lupus:
- Reason:
