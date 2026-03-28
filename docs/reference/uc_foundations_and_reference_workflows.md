# UC Foundations And Reference Workflows

Last updated: 2026-03-13

## Why pause modeling here

This is the right place to spend time on foundations.

If we start modeling too early, we risk optimizing for the wrong supervised
unit, the wrong labels, or the wrong biological prior. In this dataset,
understanding the donor-sample-cell hierarchy matters more than squeezing out a few points of AUROC.

The first task is still donor-level `Healthy` vs `UC`, but that task should sit on top of a clear view of:

- how the study is structured
- what the labels actually mean
- which branches of single-cell analysis are standard for a dataset like this
- which workflow implementations are worth copying

## What this UC dataset actually is

Local files show the following structure.

### Study hierarchy

```text
30 donors
  -> 133 samples
     -> sample health: Healthy / Non-inflamed / Inflamed
     -> sample location: Epi / LP
        -> 365,492 cells
           -> 51 cluster labels
```

### Donor-level structure that matters

- `12` donors are healthy-only
- `18` donors are UC donors
- most UC donors contain both `Non-inflamed` and `Inflamed` samples
- most donors have both `Epi` and `LP` samples
- one large donor, `N661`, appears to have `LP` only
- UC donors are more uneven than healthy donors in both cell count and sample count

This means the dataset is not just a simple two-group case-control table.
It is a nested multi-sample design.

### What we have already learned from local summaries

Composition shifts are already visible at donor level.

Clusters with higher mean proportion in UC include:

- `Follicular`
- `CD4+ Memory`
- `Tregs`
- `Inflammatory Fibroblasts`
- `Macrophages`
- `Inflammatory Monocytes`

Clusters with lower mean proportion in UC include:

- `Immature Enterocytes 1`
- `Enterocyte Progenitors`
- `Immature Enterocytes 2`
- `Cycling TA`
- `TA 1`
- `Enterocytes`

This matters because the first classifier may get a lot of signal from
composition alone. That is not bad, but it means we should know it before we
over-interpret an expression model.

## Covariate audit gate before modeling

Before any disease-prediction result is taken seriously, we need an explicit
covariate audit.

### Covariates currently verified in local files

The current local foundation tables clearly expose:

- donor identifier
- sample identifier
- sample health state
- tissue location
- cluster label
- cell-level `nGene`
- cell-level `nUMI`

### Covariates not yet verified in local benchmark tables

We do not yet have explicit fields for:

- sequencing batch
- chemistry or library preparation batch
- age
- sex
- treatment history
- clinical site or collection date

This does not mean those covariates are absent from the study. It means they
are not yet present in the local benchmark tables we are using.

### Why this matters

If location, disease state, and an unmeasured technical factor are aligned, a
predictive model may learn the nuisance factor rather than the biology.

Examples:

- if `Epi` and `LP` were processed in different technical batches, batch could
  masquerade as compartment biology
- if some UC donors were sequenced in a different run than healthy donors, run
  effects could masquerade as disease signal
- if age, sex, or treatment history differ strongly across groups, some of the
  observed signal may not be disease-specific

### Operational rule

Before serious benchmark interpretation, create a covariate audit table with
three columns for each available field:

- availability
- likely biological signal vs nuisance role
- possible leakage or confounding risk

If the missing covariates can be recovered from the portal, paper supplement, or
metadata side files, add them to the audit before interpreting disease models.

### Consequence for pseudobulk granularity

Because location is already explicitly known and one donor, `N661`, is `LP`
only, donor-only pseudobulk is useful but not sufficient for later biological
claims.

That means:

- donor-level pseudobulk remains the first benchmark table
- donor-by-location pseudobulk should be treated as an early sensitivity
  analysis, not a late optional refinement

## The three analysis branches we should keep separate

A dataset like this usually supports three different analysis branches.

```text
counts + metadata
  -> atlas / annotation branch
  -> composition / differential-abundance branch
  -> donor-level prediction branch
```

And there is a fourth branch that usually comes after the first three:

```text
counts + metadata + coarse labels
  -> pseudobulk differential-state branch
```

These branches answer different questions and should not be collapsed into one
benchmark.

### 1. Atlas and annotation branch

Question:

- what cell populations are present, and are the labels trustworthy?

Why it matters:

- the quality of composition and pseudobulk analyses depends on trustworthy
  labels
- this is where single-cell-specific QC, clustering, marker review, and
  reference mapping belong

### 2. Composition branch

Question:

- which cell populations expand or contract across disease states?

Why it matters:

- the first donor-level classifier may largely reflect composition shifts
- we need to know whether that is the dominant signal

### 3. Donor-level prediction branch

Question:

- can we classify `Healthy` vs `UC` at donor level?

Why it matters:

- this is the branch that later CFN-style modeling is most likely to enter
- it must respect donor-level replication

### 4. Differential-state branch

Question:

- within a cell type, which genes or pathways change across condition?

Why it matters:

- this is the cleanest path to biological interpretation once composition is
  understood

## The diagrams we actually need first

We do not need a full architecture deck yet. We need a few simple foundation
diagrams and tables.

### Required diagram 1: study design diagram

```text
donor_id
  -> sample_id
     -> sample_health
     -> location
        -> cell_id
           -> cluster
           -> gene counts
```

Purpose:

- prevents confusion about row units
- makes the nested replication structure explicit

### Required diagram 2: analysis branch diagram

```text
raw matrices + metadata
  -> QC / annotation
  -> composition
  -> pseudobulk differential state
  -> donor prediction
```

Purpose:

- keeps us from forcing all questions into a single classifier

### Required tables first

- donor overview table
- sample overview table
- sample `Health x Location` table
- donor ranked by cell count
- cluster mean-proportion delta table by label

These are enough to understand the foundation without plotting everything.

## Common scRNA implementations worth learning from

The point here is not to collect methods randomly. It is to identify the
reference workflows that match the questions above.

### A. Scanpy and scverse exploratory workflow

Reference pattern:

- QC
- normalization
- highly variable gene selection
- PCA
- neighbor graph
- UMAP
- clustering
- marker-based annotation

Why it matters for us:

- this is the standard atlas-building workflow
- it is the right reference for how the study likely built or refined cluster
  labels
- it is not by itself a donor-aware disease-prediction workflow

What we should copy:

- the discipline around separating QC, normalization, structure discovery, and
  annotation

What we should not copy blindly:

- using cell-level exploratory embeddings as if they were automatically the best
  disease-prediction representation

Sources:

- scverse best practices
- Scanpy PBMC3k tutorial

### B. Cell annotation implementations: CellTypist and scANVI

Reference pattern:

- learn or transfer cell labels from curated reference data
- refine manual labels with supervised or semi-supervised annotation

Why it matters for us:

- our current cluster labels come from the published study, but any future
  extension to new datasets will need annotation strategy
- the main point is not to trust cluster names blindly; it is to know where
  annotation enters the pipeline

What we should copy:

- treat coarse annotation as a first-class preprocessing step
- keep label transfer separate from downstream disease prediction

Sources:

- CellTypist documentation
- scvi-tools scANVI tutorial

### C. Composition workflows: scCODA and Milo

Reference pattern:

- model changes in population abundance across conditions
- account for the compositional nature of cell-type proportions
- neighborhood-level differential abundance when cluster boundaries are too
  coarse

Why it matters for us:

- our UC dataset already shows strong composition shifts
- a donor-level classifier may otherwise just rediscover those shifts without
  telling us that composition is the main signal

What we should copy:

- treat composition as its own branch of analysis
- use donor-level counts or proportions as first-class outputs, not just side
  features

Inference from these sources:

- for the first pass, our simple donor-level composition table is the right
  lightweight precursor to fuller compositional modeling

Sources:

- scCODA paper and documentation
- Milo paper and miloR documentation

### D. Differential-state workflows: pseudobulk and muscat

Reference pattern:

- aggregate counts within donor and cell type
- run replicate-aware differential expression or differential state analysis

Why it matters for us:

- the local study design is clearly multi-sample and donor-aware
- this is the conventional route for saying what changes inside a cell type

What we should copy:

- treat pseudobulk as a core analysis object, not a workaround
- keep donor as the replicate level

Inference from these sources:

- our donor-level gene table is only the first pseudobulk representation
- the more biologically specific extension is donor-by-cell-type pseudobulk,
  then muscat-style differential-state analysis

Sources:

- scverse differential expression guidance
- muscat paper

### E. Donor-level prediction workflows

There is no single universally canonical packaged workflow for our exact task.
The common pattern is inferred from the sources above:

- aggregate to donor or donor-by-cell-type
- keep the split at donor level
- compare composition and expression views separately
- run simple baselines before richer models

This is an inference from best-practice sources and multi-sample single-cell
analysis papers, not a single one-click official pipeline.

## What this means for our own UC foundations

The safest near-term path is:

1. understand the study design and label semantics
2. understand the dominant composition shifts
3. understand whether donor-level expression adds signal beyond composition
4. only then run the first prediction benchmark

That means the foundations phase should produce:

- reproducible donor and sample summaries
- a clear donor-sample-cell diagram
- a cluster shift table
- a covariate audit note
- a small note on which branch each later method belongs to

## Immediate next exploration tasks

### Task 1: lock the dataset summaries into files

Use the exploration script to write:

- donor overview
- sample overview
- `Health x Location` counts
- donor dispersion summaries
- donor-by-location summaries
- cluster mean-proportion deltas and log-ratio summaries

### Task 2: add a branch-specific note for the UC anchor

For each branch, write:

- the scientific question
- the row unit
- the natural metrics
- the likely failure modes

### Task 3: inspect whether location is dominating the disease signal

Because `Epi` and `LP` are biologically distinct compartments, we should check:

- whether donor-level prediction is mostly reflecting compartment mixture
- whether later donor-by-compartment pseudobulk should come before
  donor-by-cluster pseudobulk

### Task 4: only then run the first baseline

The first benchmark should be informed by the exploration phase, not the other
way around.

## Workspace artifacts

The local exploration script for this phase is:

- `scripts/explore_uc_foundations.py`

It writes foundation summaries into:

- `data/processed/uc_scp259/exploration/`

## Sources

- scverse best practices:
  https://www.sc-best-practices.org/
- scverse normalization:
  https://www.sc-best-practices.org/preprocessing_visualization/normalization.html
- scverse differential expression:
  https://www.sc-best-practices.org/conditions/differential_gene_expression.html
- Scanpy PBMC3k tutorial:
  https://scanpy.readthedocs.io/en/stable/tutorials/basics/clustering.html
- CellTypist documentation:
  https://celltypist.readthedocs.io/
- scvi-tools scANVI tutorial:
  https://docs.scvi-tools.org/en/stable/tutorials/notebooks/scrna/harmonization.html
- scCODA:
  https://sccoda.readthedocs.io/
- scCODA paper:
  https://www.nature.com/articles/s41467-021-27150-6
- Milo:
  https://marionilab.github.io/miloR/
- Milo paper:
  https://www.nature.com/articles/s41587-021-01033-z
- muscat paper:
  https://genomebiology.biomedcentral.com/articles/10.1186/s13059-020-02060-5
