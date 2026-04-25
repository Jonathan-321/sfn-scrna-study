# First Benchmark Spec

Last updated: 2026-03-11

## Purpose

This document turns the UC scRNA notes into a concrete first benchmark.
It answers four questions:

1. what the first supervised task is
2. what tables we build first
3. what we explicitly delay
4. what diligence rules keep the benchmark honest

## Primary objective

Build the first leakage-safe conventional benchmark for the project before any
CFN work.

The first benchmark is:

- donor-level `Healthy` vs `UC`
- on donor-level aggregated scRNA features

This is the reference benchmark that later structured models must beat or at
least match.

## Starting point

Start with the ulcerative colitis colon atlas in
`data/raw/uc_scp259/`.

Why:

- the real files are local now
- `all.meta2.txt` confirms `30` donors, `133` samples, and `51` clusters
- the main uncertainty is representation choice, not access

If the matrix joins fail or the tables turn out to be malformed, switch to the
lupus PBMC backup and reuse the same benchmark design.

## Frozen first-pass task contract

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

Why this is first:

- it respects replication directly
- it is the cleanest first disease benchmark
- it avoids mixing local inflammation labels with donor disease labels

### Secondary benchmark

- task: sample-level `Non-inflamed` vs `Inflamed` within UC only
- row unit: sample
- split unit: donor
- class counts:
  - `45` non-inflamed samples
  - `40` inflamed samples

Why this is second:

- it is biologically strong because it targets local inflammation
- it needs grouped donor-aware evaluation
- it should not block the simpler donor-level baseline

## What we test first

We test representations before fancy models.

### Test family A: metadata and label sanity

Goal:

- prove that the frozen first benchmark is internally coherent

Required checks:

- donor IDs are stable
- donor labels are derivable without ambiguity
- sample nesting is understandable
- cluster labels are usable for composition summaries

Deliverables:

- metadata inventory
- frozen task contract
- reproducible metadata audit script

### Test family B: first usable feature tables

Build the easiest clean tables first.

Table 1:

- donor-level pseudobulk across all cells

Table 2:

- donor-level cluster-composition features

Table 3:

- donor-by-compartment or donor-by-cell-type pseudobulk

Why this order:

- Table 1 is the cleanest conventional expression baseline
- Table 2 tells us whether composition alone carries most of the signal
- Table 3 matters, but it depends on a clean join between metadata and the
  split matrix families and should not block the first benchmark

### Test family C: first baseline models

For each usable table, test:

- logistic regression
- linear SVM
- XGBoost

Optional only if donor count supports it:

- small MLP

Why this order:

- linear models test whether the representation is already strong
- XGBoost tests whether moderate nonlinearity adds value
- a small MLP is only useful after the conventional baselines are stable

### Test family D: descriptive disease biology checks

Run in parallel:

- cluster-composition comparisons across donor labels
- first-pass pathway summaries
- limited pseudobulk differential-state checks once the tables exist

Why:

- the classifier needs biological context
- we want to know whether the signal is mostly composition, expression, or both

## What we do not test yet

Do not start with any of the following:

- raw cell-level disease classification
- random cell splits
- full 51-state fine-grained prediction
- treatment-response prediction
- anti-TNF resistance prediction
- aggressive hyperparameter sweeps
- StructuralCFN
- foundation models

Do not mix donor disease status and local inflammation labels into one target.
The first task is frozen; later tasks should be added one at a time.

## Diligence rules

### Rule 1: donor is the default independent unit

No result counts if train and validation share the same donor.

### Rule 2: freeze the split policy before model comparison

Before running baselines, write down:

- split unit
- number of folds
- class balance per split
- how repeated samples from the same donor stay grouped

### Rule 3: separate representation testing from model testing

Do not change the table and the model stack at the same time.

Test in this order:

1. is the table coherent
2. do simple models work
3. does a richer model help

### Rule 4: keep a descriptive branch alive

A classifier without composition or pathway context is hard to trust.

### Rule 5: do not let the granular table block the benchmark

If donor-by-cell-type pseudobulk is slow because of matrix joins, keep moving
with donor-level pseudobulk and composition first.

## Metrics for the first benchmark

Primary metrics:

- AUROC
- AUPRC
- balanced accuracy
- macro-F1

Secondary diagnostics:

- class prevalence by split
- donor count by split
- coefficient or feature-importance stability across folds

Interpretation rule:

- with only `30` donors, stability and plausibility matter almost as much as
  raw discrimination

## Concrete first execution order

1. Run the metadata audit script on `all.meta2.txt`.
2. Freeze donor-level `Healthy` vs `UC` as the primary task.
3. Build donor-level all-cell pseudobulk.
4. Build donor-level cluster-composition features.
5. Run logistic regression on both tables.
6. Add linear SVM and XGBoost on the same frozen tables.
7. Only after that, add donor-by-compartment or donor-by-cell-type pseudobulk.
8. Treat sample-level `Non-inflamed` vs `Inflamed` as the next benchmark.
9. Only then decide whether CFN is worth adding.