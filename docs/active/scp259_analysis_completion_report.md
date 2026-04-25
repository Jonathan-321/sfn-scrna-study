# SCP259 Analysis Completion Report

Status: draft for advisor / expert feedback  
Last updated: 2026-03-27

## Purpose

This document freezes the current `SCP259` story before any larger-cohort
expansion. It does four things:

1. defines the exact terms used in the project,
2. states the frozen benchmark contract,
3. presents the final SCP259 benchmarking tables and figure plan,
4. separates completed evidence from future work.

## 1. What The Project Is Trying To Do

The immediate goal is:

> Build an honest donor-aware ulcerative colitis single-cell benchmark and test
> whether StructuralCFN is competitive and biologically informative under that
> benchmark.

The project is not currently trying to prove that:

- CFN beats all baselines on raw predictive performance,
- CFN has already recovered a stable causal biological network,
- SCP259 alone is sufficient to settle the sample-size question for structure
  stability.

## 2. Term Breakdown

### 2.1 Donor-aware benchmark

The unit of prediction is the donor, not the cell. This avoids
pseudoreplication from putting cells from the same donor into both training and
test.

### 2.2 Donor-global composition

One row per donor. Features are cluster proportions across all cells for that
donor. This asks whether disease can be predicted from cell-state abundance
alone.

### 2.3 Donor-global pseudobulk

One row per donor. Features are donor-level aggregated expression values across
genes. This asks whether disease can be predicted from donor-level molecular
signal.

### 2.4 Compartment-aware composition

One row per donor. Features are blocked by compartment, currently `Epi` and
`LP`. This keeps epithelial and lamina propria composition separate rather than
mixing them into one donor-global vector.

### 2.5 Compartment-aware pseudobulk

One row per donor. Gene-expression features are blocked by compartment. This is
the strongest expression-style extension currently built, but it is near
ceiling for standard models and has not yet been the first CFN target.

### 2.6 CFN variants

In this project, `CFN variants` means different ways of running or constraining
StructuralCFN. They are not all completed results.

Completed CFN evaluations:

- donor-global composition CFN
- compartment-aware composition CFN

Possible future CFN variants:

- reduced-pseudobulk CFN using a smaller gene set
- compartment-aware pseudobulk CFN
- consensus-constrained CFN using recurrent edges only
- prior-seeded CFN using pathway or niche priors
- hyperparameter variants of the same base CFN

Important distinction:

- donor-global versus compartment-aware composition are representation changes
- consensus-constrained or prior-seeded CFN are model variants

### 2.7 Structural diagnostics

These are the metrics used to judge CFN structure quality.

- `grouped top-k Jaccard`: whether the same top structural edges recur across
  folds after grouping similar features
- `sign consistency`: whether feature directions are stable when a feature is
  used
- `consensus support profile`: how many folds support each edge
- `full dependency-matrix similarity`: whether the overall dense learned graph
  is similar across folds

## 3. Frozen Benchmark Contract

The current SCP259 benchmark should be treated as frozen for paper comparison.

- task: donor-level `Healthy` versus `UC`
- primary row unit: donor
- split unit: donor
- primary donor-global representations:
  - composition
  - pseudobulk
- primary baseline models:
  - logistic regression
  - linear SVM
  - XGBoost
- primary baseline protocol:
  - repeated stratified 5-fold donor CV
- robustness protocol:
  - leave-one-donor-out
- CFN-facing representations:
  - donor-global composition
  - compartment-aware composition

## 4. Final Benchmark Tables

### Table 1. Donor-global benchmark, repeated 5-fold donor CV

| Representation | Model | AUROC mean | AUROC SD | PR-AUC mean | Balanced Accuracy mean | Macro-F1 mean | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Composition | LogReg | 0.9364 | 0.0289 | 0.9588 | 0.8550 | 0.8393 | Best donor-global composition baseline |
| Composition | LinearSVM | 0.9272 | 0.0342 | 0.9536 | 0.8508 | 0.8379 | Competitive with LogReg |
| Composition | XGBoost | 0.8786 | 0.0342 | 0.9338 | 0.7675 | 0.7448 | Weaker than linear models here |
| Pseudobulk | XGBoost | 0.9975 | 0.0079 | 0.9990 | 0.9550 | 0.9475 | Near ceiling |
| Pseudobulk | LinearSVM | 0.9925 | 0.0237 | 0.9961 | 0.9600 | 0.9552 | Near ceiling |
| Pseudobulk | LogReg | 0.9925 | 0.0237 | 0.9961 | 0.9400 | 0.9279 | Near ceiling |

Interpretation:

- donor-global pseudobulk is the strongest predictive representation
- donor-global composition is still strong and remains the better first arena
  for structured-model comparison

### Table 2. Donor-global robustness check, leave-one-donor-out

| Representation | Model | AUROC | PR-AUC | Balanced Accuracy | Accuracy | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Composition | LogReg | 0.9491 | 0.9602 | 0.8750 | 0.8667 | Strong under the harsher donor-level check |
| Composition | LinearSVM | 0.9259 | 0.9307 | 0.8611 | 0.8667 | Confirms robust composition signal |
| Composition | XGBoost | 0.8611 | 0.9228 | 0.7222 | 0.7333 | Again weaker than linear models |
| Pseudobulk | LinearSVM | 1.0000 | 1.0000 | 0.9722 | 0.9667 | Near-perfect donor separability |
| Pseudobulk | LogReg | 1.0000 | 1.0000 | 0.9444 | 0.9333 | Near-perfect donor separability |
| Pseudobulk | XGBoost | 0.9907 | 0.9944 | 0.9722 | 0.9667 | Near-perfect donor separability |

Interpretation:

- the donor-level signal is not a one-split artifact
- pseudobulk remains extremely strong under the strictest donor-level protocol

### Table 3. Compartment-aware extension, frozen 5-fold donor CV

| Representation | Model | AUROC mean | PR-AUC mean | Balanced Accuracy mean | Macro-F1 mean | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Compartment composition | LinearSVM | 0.9556 | 0.9667 | 0.8750 | 0.8648 | Best compartment-composition baseline |
| Compartment composition | LogReg | 0.9556 | 0.9667 | 0.8500 | 0.8305 | Tied on AUROC |
| Compartment composition | XGBoost | 0.7111 | 0.8428 | 0.5917 | 0.5606 | Poor fit in this regime |
| Compartment pseudobulk | LinearSVM | 1.0000 | 1.0000 | 0.9667 | 0.9657 | Near ceiling |
| Compartment pseudobulk | LogReg | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Near ceiling |
| Compartment pseudobulk | XGBoost | 0.9556 | 0.9611 | 0.9083 | 0.8990 | Strong but not best |

Interpretation:

- separating `Epi` and `LP` helps the composition benchmark
- compartment-aware composition is the most informative first CFN-facing
  representation

### Table 4. StructuralCFN results and structure diagnostics

| CFN representation | AUROC mean | PR-AUC mean | Brier mean | Grouped top-k Jaccard | Sign consistency | Matrix cosine mean | Main reading |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Donor-global composition | 0.9056 | 0.9444 | 0.1640 | 0.0316 | 0.8980 | 0.5366 | Predictive, but weak recurring structure |
| Compartment-aware composition | 0.9778 | 0.9833 | 0.1320 | 0.0322 | 0.8980 | 0.4507 | Better prediction, no stability gain |

Interpretation:

- CFN is predictive on composition-based tables
- compartment blocking improves CFN predictive performance
- structural recurrence remains weak
- the instability is not only a top-k artifact because full-matrix similarity
  is only moderate on donor-global composition and lower on compartment-aware
  composition

## 5. What Stronger Biological Claims Mean Here

`Stronger biological claims` does not mean overstating the evidence. It means
stating the strongest claim that the current data actually supports.

### Claims that are justified now

- the recurring CFN edge set is enriched for epithelial regeneration /
  differentiation and epithelial-immune or epithelial-stromal crosstalk
- the strongest recurring edges are biologically coherent with known UC themes
- CFN is not learning obviously random structure, even though the structure is
  not stable enough to claim a recurring backbone

The main text edge set should be taken from:

- `results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_final_v3.csv`

That main-text set is:

- `Stem -> Immature Enterocytes 2`
- `Enterocyte Progenitors -> ILCs`
- `Enterocyte Progenitors -> Myofibroblasts`
- `RSPO3+ -> CD8+ IELs`

### Claims that are not justified now

- direct causal validation of any learned edge
- a stable recurring dependency graph
- the statement that CFN has recovered the true UC regulatory network in SCP259

## 6. New Representation Families

These are future work, not completed SCP259 results.

### 6.1 Reduced pseudobulk

Use a smaller expression feature set for CFN, such as top `100-300` genes or a
strictly filtered donor-prevalence subset. This is the most practical first
expression-side CFN extension.

### 6.2 Pathway or module scores

Replace raw genes with pathway scores, hallmark signatures, or curated module
summaries. This reduces dimensionality and increases interpretability.

### 6.3 Compartment-aware pseudobulk for CFN

Use the existing compartment-blocked expression table as a later CFN target,
after dimensionality reduction or pathway compression.

### 6.4 Prior-aware structured inputs

Inject pathway priors, niche priors, or curated epithelial-stromal / immune
interaction priors into CFN as a future model-variant study.

## 7. Figure List

### Figure 1. Benchmark design schematic

Content:

- raw single-cell donor data
- donor-level aggregation
- donor-global composition
- donor-global pseudobulk
- compartment-aware `Epi` / `LP` blocking
- donor-level cross-validation and LODO

Purpose:

- define the benchmark clearly for readers before any results

### Figure 2. Donor-global baseline performance

Content:

- Table 1 as the main benchmark panel
- optional repeat-level AUROC boxplots for composition and pseudobulk

Purpose:

- establish that the benchmark is real and that pseudobulk is strongest

### Figure 3. Donor-global robustness check

Content:

- Table 2 or a compact LODO comparison figure

Purpose:

- show that the donor-global conclusions survive the harsher donor-wise check

### Figure 4. Compartment-aware extension

Content:

- Table 3
- optional heatmap of AUROC by representation and model

Purpose:

- show that separating `Epi` and `LP` adds useful composition signal

### Figure 5. StructuralCFN performance versus stability

Content:

- Table 4
- grouped Jaccard, sign consistency, and matrix cosine shown side by side

Purpose:

- make the mixed CFN result explicit: prediction improves, structure does not
  stabilize

### Figure 6. Recurring edge interpretation

Content:

- the four main-text edges from `final_v3`
- grouped into:
  - epithelial regeneration / differentiation
  - epithelial-immune crosstalk
  - epithelial-stromal remodeling

Purpose:

- show that the recurring edge set is biologically coherent while still making
  the stability limitation explicit

## 8. Current Paper Claim

The strongest current SCP259 claim is:

> We established a donor-aware ulcerative colitis single-cell benchmark in
> `SCP259` in which both donor-level cell composition and donor-level
> pseudobulk expression robustly separate `Healthy` and `UC`, and this
> conclusion survives repeated donor resampling and leave-one-donor-out
> validation. Donor pseudobulk is the strongest predictive representation,
> while compartment-aware composition is the most informative first
> representation for structured modeling. StructuralCFN is predictive and
> recovers biologically coherent edge themes, but its unconstrained structure
> does not recur stably across folds at `N=30`, so the defensible claim is one
> of honest structured benchmarking rather than stable mechanistic recovery.

## 9. GitHub Readiness

This directory is currently **not a git repository**, so there is nothing to
push to GitHub from here yet.

What would make sense to track in version control:

- `docs/active/uc_first_paper_writeup.md`
- `docs/active/scp259_analysis_completion_report.md`
- scripts in `scripts/`
- small summary outputs such as:
  - `results/uc_scp259/benchmarks/donor_global_representation_comparison.csv`
  - `results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_final_v3.csv`

What probably should not be pushed directly without a plan:

- bulky prediction files
- raw matrices
- large intermediate artifacts

If this project is meant to live on GitHub, the next infrastructure step is:

1. put `sfn-scrna-study` inside a real git repository,
2. decide which result artifacts are tracked versus regenerated,
3. then commit the docs, scripts, and selected summary outputs.

## 10. Immediate Next Steps

1. use this report and `docs/active/uc_first_paper_writeup.md` as the SCP259 discussion
   package for your professor
2. convert Tables 1-4 and Figures 1-6 into slides or manuscript assets
3. get feedback on the current SCP259 claim before any larger-cohort expansion
4. only then decide whether the next scientific move is:
   - larger cohort for the sample-size hypothesis, or
   - a narrower SCP259 paper with a strong limitations section
