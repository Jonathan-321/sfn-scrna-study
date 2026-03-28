# Ulcerative Colitis Anchor Dataset Card

Last updated: 2026-03-07

## Dataset identity

- Name: Smillie et al. ulcerative colitis colon atlas
- Publication: "Intra- and Inter-cellular Rewiring of the Human Colon during
  Ulcerative Colitis"
- Journal: Cell, 2019
- PubMed: https://pubmed.ncbi.nlm.nih.gov/31348891/
- Processed data portal: `SCP259`
- Single Cell Portal:
  https://singlecell.broadinstitute.org/single_cell/study/SCP259/intra-and-inter-cellular-rewiring-of-the-human-colon-during-ulcerative-colitis

## Why this is the current anchor

- It is the best match to the stated project direction: one disease, one tissue,
  one strong biological question.
- It has enough donor structure to support donor-aware evaluation.
- It has enough cellular diversity to make pathway or interaction analysis worth
  doing.
- It provides a natural path from single-cell profiles to compact tabular
  representations that CFN-style models can realistically consume.

## Source-backed cohort snapshot

- PubMed abstract reports an atlas of 366,650 cells from the colon mucosa of 18
  ulcerative colitis patients and 12 healthy individuals.
- The PubMed record also states that processed data were deposited in Single
  Cell Portal `SCP259` and raw data are available through Broad DUOS.
- The paper reports 51 epithelial, stromal, and immune cell subsets.
- Figure text in the PubMed record shows that samples include healthy,
  non-inflamed, and inflamed biopsies.
- The public portal page is accessible without login, but the documented SCP
  REST file endpoints returned `401 Unauthorized` in the first unauthenticated
  check, so actual file access needs to be verified before treating this as a
  ready-to-download benchmark.

## Working biological question

Can donor-level transcriptomic summaries from colon mucosa distinguish healthy
individuals from ulcerative colitis patients under donor-aware evaluation, and
can structured models later recover stable gene-program relationships that are
biologically plausible?

## Recommended first prediction task

Primary task:

- Healthy vs ulcerative colitis classification.

Why this first:

- It is simpler and cleaner than predicting anti-TNF resistance immediately.
- It avoids starting with a low-sample treatment-response problem.
- It still leaves room for later extensions once the preprocessing pipeline is
  stable.

Defer for later:

- Inflamed vs non-inflamed region classification.
- Anti-TNF resistance modeling.
- Cell-state discovery as a primary result.

## Recommended row unit

Do not start with individual cells as the main supervised benchmark.

Recommended row unit:

- One row per donor, or one row per donor-by-major-cell-type block.

Preferred first representation:

- Donor-level pseudobulk for major cell compartments.
- Optional donor-by-cell-type pseudobulk if donor counts remain adequate after
  stratification.
- Compact features built from high-variance genes, curated marker panels, or
  pathway scores.

Why this is the right starting point:

- It respects donor-aware evaluation.
- It reduces the risk of inflated cell-level performance caused by many cells
  from the same donor appearing highly similar.
- It produces a representation that is much closer to the tabular form CFN can
  plausibly use.

## Minimum metadata to confirm before modeling

- Donor ID
- Disease label
- Biopsy region or inflammation status
- Batch or library information
- Cell-type annotation or enough markers to derive a robust coarse annotation
- Any treatment or therapy metadata that could confound the primary task

## First-pass preprocessing plan

1. Download processed data and metadata from `SCP259`.
2. Inspect whether donor IDs and biopsy-level annotations are directly usable.
3. Build a coarse cell-type map first, not the most granular 51-subset map.
4. Aggregate counts to donor-level pseudobulk within each major cell class.
5. Filter low-information genes after aggregation.
6. Compare two compact feature representations:
   - high-variance gene pseudobulk
   - pathway or gene-program scores

## First baseline benchmark

Use the aggregated table before any CFN modeling.

Initial baseline set:

- logistic regression
- linear SVM
- XGBoost
- a small MLP only if donor count remains adequate after aggregation

Evaluation design:

- donor-level split only
- stratify by disease label if feasible
- avoid random cell splits entirely for the main result

## Main confounding and leakage risks

- Multiple biopsies from the same donor can leak donor identity if splits are
  not donor-aware.
- Inflamed versus non-inflamed sampling could dominate the disease label if not
  handled explicitly.
- Cell-composition shifts may drive much of the signal, so we should decide
  early whether that is part of the target or a nuisance to control for.
- Treatment and cohort effects may create shortcuts if included carelessly.

## Decision rules for moving forward

Proceed with this dataset if all of the following are true:

- donor IDs are recoverable from the public processed files
- disease labels are unambiguous
- there are enough donors to support at least a simple donor-level split regime
- we can build a compact donor-level table without collapsing the biology into
  noise
- the actual processed files are retrievable through an authenticated or
  documented public download path without excessive access friction

Fallback rule:

- If donor metadata or sample nesting are too messy to cleanly audit within the
  first pass, move to the lupus PBMC dataset as the backup anchor.

## Immediate next commands for the research track

1. Download or inspect `SCP259` processed metadata.
2. Build a metadata inventory: donor, biopsy, disease, inflammation, cell type.
3. Decide whether the first table will be donor-only or donor-by-cell-type.
4. Define the exact train-validation split policy before running any models.

## Sources

- PubMed abstract and data availability note:
  https://pubmed.ncbi.nlm.nih.gov/31348891/
- Single Cell Portal study page:
  https://singlecell.broadinstitute.org/single_cell/study/SCP259/intra-and-inter-cellular-rewiring-of-the-human-colon-during-ulcerative-colitis
