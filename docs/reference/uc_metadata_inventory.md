# UC Metadata Inventory

Last updated: 2026-03-11

This is the first local metadata audit for the ulcerative colitis anchor
dataset after the real study files were copied into the workspace.

## Audit summary

Current status: go for first-pass benchmark execution.

Why:

- the full first-pass raw dataset is now present locally
- `all.meta2.txt` is valid text metadata, not the earlier HTML placeholder
- donor, sample, location, and cluster fields are usable
- the remaining choice is the first label contract, not access

Operational decision:

- keep UC as the active anchor dataset
- freeze the primary first-pass supervised task as donor-level `Healthy` vs `UC`
- treat sample-level `Non-inflamed` vs `Inflamed` within UC as the next
  secondary benchmark, not the first one

## Local file validation

Validated local path:

- `/Users/jonathanmuhire/CFN/sfn-scrna-study/data/raw/uc_scp259`

Validated files:

- `all.meta2.txt`
- `Epi.genes.tsv`
- `Epi.barcodes2.tsv`
- `Fib.genes.tsv`
- `Fib.barcodes2.tsv`
- `Imm.genes.tsv`
- `Imm.barcodes2.tsv`
- `gene_sorted-Epi.matrix.mtx`
- `gene_sorted-Fib.matrix.mtx`
- `gene_sorted-Imm.matrix.mtx`

Notes:

- the three matrix files are present at realistic sizes for a full atlas
- the metadata file has a header row plus a `TYPE` descriptor row that should be
  skipped during parsing

## Local metadata audit

Parsed from the real `all.meta2.txt` file after skipping the `TYPE` row.

### Global counts

| Item | Value | Notes |
|---|---:|---|
| cell rows | 365492 | Matches the portal badge count. |
| subjects | 30 | Matches the paper cohort of 12 healthy + 18 UC. |
| samples | 133 | Sample-level repeated measures exist within donor. |
| locations | 2 | `Epi`, `LP` |
| clusters | 51 | Fine cell-state labels in `Cluster`. |

### Health labels

Cell-level counts:

| Health | Cells |
|---|---:|
| `Healthy` | 110110 |
| `Non-inflamed` | 130263 |
| `Inflamed` | 125119 |

Sample-level counts:

| Health | Samples |
|---|---:|
| `Healthy` | 48 |
| `Non-inflamed` | 45 |
| `Inflamed` | 40 |

Subject-level structure:

- `12` subjects are `Healthy` only
- `18` subjects have UC-associated samples and each of those subjects contains
  at least one `Non-inflamed` or `Inflamed` sample
- most UC subjects contain both `Non-inflamed` and `Inflamed` samples

Healthy-only subjects:

- `N10`, `N11`, `N13`, `N15`, `N16`, `N17`, `N18`, `N20`, `N21`, `N46`, `N51`,
  `N8`

UC subjects:

- `N106`, `N110`, `N111`, `N12`, `N14`, `N19`, `N23`, `N24`, `N26`, `N44`,
  `N49`, `N50`, `N52`, `N539`, `N58`, `N661`, `N7`, `N9`

### Sample and location structure

Sample-level `Health x Location` counts:

| Health | Epi | LP | Total |
|---|---:|---:|---:|
| `Healthy` | 24 | 24 | 48 |
| `Non-inflamed` | 21 | 24 | 45 |
| `Inflamed` | 16 | 24 | 40 |

Important note:

- most subjects have both `Epi` and `LP` samples
- one subject, `N661`, appears to have `LP` only
- some UC subjects have more than the usual four samples, so sample counts are
  not perfectly balanced across donors

### Core identifiers

| Field | Present? | Column name | Level | Notes |
|---|---|---|---|---|
| donor_id | Yes | `Subject` | donor | Usable donor grouping field. |
| sample_id | Yes | `Sample` | sample | Biopsy or sample-level repeated measure field. |
| cell_id | Yes | `NAME` | cell | Includes sample-prefixed cell names. |
| library_id | Not verified |  | library | No explicit library field seen in `all.meta2.txt`. |
| batch_id | Not verified |  | batch | No explicit batch field seen in `all.meta2.txt`. |

### Core labels

| Field | Present? | Column name | Notes |
|---|---|---|---|
| disease or condition label | Yes | derived from `Health` + `Subject` | Primary first-pass donor label can be frozen locally. |
| local inflammation label | Yes | `Health` | Values are `Healthy`, `Non-inflamed`, `Inflamed`. |
| coarse tissue compartment | Yes | `Location` | Values are `Epi`, `LP`. |
| fine cell-state label | Yes | `Cluster` | 51 cluster labels. |

## First-pass task freeze

### Primary benchmark

- task: donor-level `Healthy` vs `UC`
- row unit: donor
- split unit: donor
- label rule:
  - `Healthy` if the donor has only `Healthy` samples
  - `UC` if the donor has any `Non-inflamed` or `Inflamed` sample
- class counts:
  - `12` healthy donors
  - `18` UC donors

Why this first:

- it respects the donor as the independent unit
- it gives the cleanest first conventional benchmark
- it avoids pretending that hundreds of thousands of cells are independent
- it lets us build donor-level pseudobulk and composition tables immediately

### Secondary benchmark

- task: sample-level `Non-inflamed` vs `Inflamed` within UC only
- row unit: sample
- split unit: donor
- class counts:
  - `45` non-inflamed samples
  - `40` inflamed samples

Why this second:

- it is biologically interesting because it targets local inflammation
- it needs grouped subject-aware evaluation
- it is cleaner once the donor-level benchmark and tables already exist

## Readiness checks

| Check | Status | Notes |
|---|---|---|
| donor IDs are usable | Pass | `Subject` is clean and consistent. |
| disease labels are usable | Pass | The donor-level benchmark can now be frozen. |
| biopsy nesting is understandable | Pass | `Sample` is usable and shows repeated measures within donor. |
| coarse cell annotations exist or can be built | Pass | `Location` gives `Epi` vs `LP`; `Cluster` gives finer labels. |
| donor-level pseudobulk is feasible | Pass | Primary next feature table. |
| donor-by-cell-type pseudobulk is feasible | Partial | Likely feasible after matrix-family and barcode joins are verified. |

## Concrete next steps

1. Keep a reproducible metadata audit script in the repo and rerun it before
   feature generation.
2. Build the first donor-level pseudobulk table for the primary `Healthy` vs
   `UC` benchmark.
3. Build a donor-level composition table from `Cluster` counts and proportions.
4. Add donor-by-compartment or donor-by-cell-type pseudobulk only after the
   matrix-family join is verified cleanly.

## Sources

- Local file:
  `/Users/jonathanmuhire/CFN/sfn-scrna-study/data/raw/uc_scp259/all.meta2.txt`
- Single Cell Portal study page:
  https://singlecell.broadinstitute.org/single_cell/study/SCP259/intra-and-inter-cellular-rewiring-of-the-human-colon-during-ulcerative-colitis
- PubMed record:
  https://pubmed.ncbi.nlm.nih.gov/31348891/
