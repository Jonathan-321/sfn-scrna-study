# Professor Review Brief

Status: advisor-facing summary  
Last updated: 2026-03-27

## Why this note exists

This is the fastest way to review the current state of the `SCP259` scRNA
benchmark without reading the full paper draft first.

## Project question

The current question is:

> Can a donor-aware scRNA benchmark on ulcerative colitis support a fair test
> of StructuralCFN, and if so, what is the honest result on prediction and
> structure?

## What is complete

- donor-aware `Healthy` vs `UC` benchmark on `SCP259`
- donor-global composition benchmark
- donor-global pseudobulk benchmark
- repeated 5-fold donor CV
- leave-one-donor-out robustness check
- compartment-aware `Epi` / `LP` benchmark extension
- first StructuralCFN runs on donor-global and compartment-aware composition
- structural diagnostics:
  - top-k overlap
  - sign consistency
  - consensus support
  - full dependency-matrix similarity
- recurring-edge interpretation table with conservative language

## Main results

### Baselines

- donor-global composition is strong
- donor-global pseudobulk is near ceiling
- compartment-aware composition improves the composition benchmark

Key numbers:

- donor-global composition, repeated CV:
  - LogReg AUROC `0.9364`
  - LinearSVM AUROC `0.9272`
- donor-global pseudobulk, repeated CV:
  - XGBoost AUROC `0.9975`
  - LinearSVM AUROC `0.9925`
  - LogReg AUROC `0.9925`

### StructuralCFN

- donor-global composition CFN:
  - AUROC `0.9056`
  - grouped Jaccard `0.0316`
  - sign consistency `0.8980`
  - matrix cosine `0.5366`
- compartment-aware composition CFN:
  - AUROC `0.9778`
  - grouped Jaccard `0.0322`
  - sign consistency `0.8980`
  - matrix cosine `0.4507`

## What the results mean

The benchmark is real and the donor-level task is strongly learnable.

The honest current reading is:

- pseudobulk is the strongest predictive representation
- composition remains the more informative first testbed for structured
  modeling because it is not already at ceiling
- StructuralCFN is predictive and benefits from compartment-aware input
- StructuralCFN does not yet recover a stable recurring structural backbone at
  `N=30`

## What is biologically interpretable right now

The strongest recurring CFN edges are biologically coherent with known UC
themes, especially:

- epithelial regeneration / differentiation
- epithelial-immune crosstalk
- epithelial-stromal remodeling

Main text edge set:

- `Stem -> Immature Enterocytes 2`
- `Enterocyte Progenitors -> ILCs`
- `Enterocyte Progenitors -> Myofibroblasts`
- `RSPO3+ -> CD8+ IELs`

These should be described as:

- supported or supported-with-caveat
- biologically coherent
- not directly validated causal edges

## What the paper should claim now

The paper should currently be framed as:

> an honest donor-aware benchmark paper with a structured-model evaluation

It should not currently be framed as:

- CFN beats all baselines
- CFN recovered the true UC structural program
- CFN produced a stable mechanistic dependency graph

## What feedback is needed

The main questions for feedback are:

1. Is the current SCP259 claim scoped correctly?
2. Is the benchmark sufficiently complete to write up before expanding?
3. Should the next scientific move be:
   - a larger cohort to test the sample-size hypothesis for CFN stability, or
   - a tighter SCP259 paper with a strong limitations section?
4. Are the current biological interpretations conservative enough?

## Recommended review order

1. [`README.md`](../README.md)
2. [`docs/active/scp259_analysis_completion_report.md`](scp259_analysis_completion_report.md)
3. [`docs/active/scp259_visual_asset_manifest.md`](scp259_visual_asset_manifest.md)
4. [`docs/active/uc_first_paper_writeup.md`](uc_first_paper_writeup.md)
5. [`results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_final_v3.csv`](../results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_final_v3.csv)

The image-based figures are the primary review assets. The LaTeX table files are
not part of the recommended advisor review path.
