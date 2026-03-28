# Research Plan for Single-Cell RNA Learning

Corrected pivot: select a single-cell RNA task and dataset, not an NHANES extension

## Purpose

This document reorients the project toward single-cell RNA sequencing and away
from NHANES or generic clinical tabular benchmarking. The immediate goal is not
to lock in a model first. The immediate goal is to identify one concrete
scRNA-seq task, one dataset family, and one defensible preprocessing and
evaluation strategy that can later support StructuralCFN or related structured
models.

## 1. Project goal

The first goal is to choose a tractable and biologically meaningful single-cell
task. Only after the task, dataset, labels, and split strategy are clear should
the project move into serious modeling.

Working project statement:

Select a focused single-cell RNA-seq problem, build a reproducible
preprocessing and evaluation pipeline, and test whether structured models such
as StructuralCFN can help with prediction and relationship discovery once the
biological context, labels, and feature representation are stable.

## 2. Recommended scope

Keep the project narrow. Do not try to cover all of single-cell biology. Choose
one tissue or disease context, one dataset family, and one main task.

Recommended focus:

- Domain: single-cell transcriptomics
- Data type: scRNA-seq gene-expression matrix plus donor, batch, tissue, and
  condition metadata
- Main objective: identify one task that is both biologically meaningful and
  technically manageable
- Preferred split strategy: donor-aware or sample-aware, not random cells only
- Explicit non-goal for this phase: extending the project around NHANES

Current concrete dataset candidates and the current anchor recommendation are
tracked in `docs/dataset_shortlist.md`.

The current methods-first overview of standard scRNA workflows, decision
points, and frontier directions is tracked in
`docs/conventional_modeling_path.md`.

The first concrete execution plan and diligence gates are tracked in
`docs/first_benchmark_spec.md`.

Task shortlist:

- Cell-type classification within one curated atlas
  Why it works: clear labels, common baselines, easier startup, good for
  validating preprocessing choices.
  Main risk: can become too easy or too benchmark-like if the labels are
  already very clean.
  Recommendation: good fallback or technical warm-up task.

- Disease-state classification within one tissue or cohort
  Why it works: stronger biomedical motivation and more meaningful
  interpretation target.
  Main risk: confounding by donor, batch, site, and cell-composition effects.
  Recommendation: best main direction if donor IDs and case-control labels are
  available.

- Donor-level pseudobulk outcome prediction
  Why it works: more natural fit for structured tabular modeling and reduces
  cell-level sparsity.
  Main risk: fewer samples after aggregation and possible loss of fine-grained
  signals.
  Recommendation: best CFN-aligned option if enough donors exist.

- Hidden subgroup or state discovery
  Why it works: interesting for relationship discovery and biological
  heterogeneity.
  Main risk: harder to evaluate rigorously as the primary task.
  Recommendation: use as a secondary analysis, not the first anchor task.

Practical recommendation:

Start by screening datasets for a disease-state classification task within one
tissue. If the labels or donor structure are too messy, fall back to a
cell-type classification task on a curated dataset. If StructuralCFN needs a
more tabular representation, use donor-level pseudobulk or pathway-level
summaries rather than forcing raw cell-by-gene matrices into the model.

Current working recommendation:

Use a donor-aware ulcerative colitis colon dataset as the first anchor, with
donor-level or donor-by-cell-type pseudobulk as the initial representation.

## 3. Main research questions

1. Which single-cell task gives a clear biological question, manageable
   preprocessing, and a defensible evaluation setup?
2. How should raw counts be filtered, normalized, transformed, and reduced
   before applying structured models?
3. What information should come from the gene-expression matrix and what should
   come from metadata such as donor, tissue, batch, or condition?
4. Can StructuralCFN or a related structured approach reveal gene or pathway
   relationships beyond standard predictive models?
5. How should robustness be measured so the result is not driven by donor
   leakage, batch leakage, or label artifacts?

## 4. Research sequence to follow

Use this order to avoid jumping into modeling too early.

1. Define the biological niche
   Choose one tissue, disease or condition, and one target label.
2. Shortlist datasets
   Collect 2 to 4 public datasets and compare labels, donor counts, batches,
   and task feasibility.
3. Audit the data structure
   Determine what a row should represent: cell, sample, donor, or pseudobulk
   profile.
4. Design the split strategy
   Use donor-aware or sample-aware splits to avoid overestimating performance.
5. Design preprocessing
   Specify quality control, normalization, feature selection, and batch-handling
   decisions.
6. Run baselines
   Use simple baseline models before attempting StructuralCFN.
7. Apply structured modeling
   Use StructuralCFN only after the feature representation and task framing are
   stable.
8. Evaluate and interpret
   Assess predictive performance, robustness, and the biological meaning of
   discovered structure.

## 5. What to decide before touching models

- What exact biological question is being asked?
- What does each row represent: a cell, a donor, a sample, or a pseudobulk
  profile?
- What label is primary: cell type, disease state, treatment response, or
  another phenotype?
- Which metadata fields are biologically meaningful and which are nuisance or
  leakage risks?
- Will the evaluation split by donor, sample, batch, or study?
- How many genes should remain after filtering and high-variance gene
  selection?
- Should the model use raw genes, marker panels, pathway scores, or pseudobulk
  summaries?
- What success criteria matter: prediction only, stable structure, biological
  plausibility, or all three?

Important reminder:

The expression matrix is already numeric. One-hot encoding is mainly a metadata
question, not a gene-expression question. The bigger issue is whether the task
should be modeled at the cell level, donor level, or pseudobulk level, and how
to prevent donor or batch leakage.

## 6. Data preparation framework

Keep preprocessing explicit and separate from modeling.

Quality control and integrity:

- Filter low-quality cells based on gene count, UMI count, and mitochondrial
  fraction.
- Check whether doublets or ambient RNA need to be handled.
- Confirm donor IDs, batches, tissues, and label definitions.
- Inspect class imbalance across donors and conditions.
- Document any exclusions or sample-level quality concerns.

Feature representation and modeling setup:

- Normalize counts and apply a justified transformation such as `log1p` when
  appropriate.
- Select high-variance genes or derive pathway or marker summaries.
- Decide whether to model cells directly or aggregate to pseudobulk.
- Encode metadata only when it adds signal without creating shortcut leakage.
- Document every transformation so the pipeline is reproducible and
  interpretable.

## 7. Metrics to track

Use metrics that match both biological and modeling goals.

Predictive metrics:

- Macro-F1
- Balanced accuracy
- AUROC
- AUPRC for imbalanced outcomes
- Per-class recall when cell populations are uneven

Robustness and generalization metrics:

- Performance under donor-holdout or sample-holdout splits
- Performance across batches or cohorts
- Calibration if probabilities will be interpreted downstream

Structure and interpretation metrics:

- Stability of top genes, pathways, or interactions across splits
- Biological plausibility relative to known markers or pathways
- Consistency of discovered relationships across donors or cohorts
- Optional clustering agreement metrics such as ARI or NMI if subgroup
  discovery is used as a secondary analysis

## 8. Literature review plan

Read in a sequence that supports task selection, not random accumulation.

1. Read scRNA-seq workflow reviews covering QC, normalization, batch handling,
   and annotation.
2. Read task-specific papers for cell-type classification, disease-state
   classification, or perturbation prediction.
3. Read papers on donor-aware evaluation and data leakage in single-cell
   studies.
4. Read work on gene interaction modeling, pathway discovery, and structure
   learning relevant to CFN-style claims.
5. Read a smaller set of papers that use pseudobulk or gene-program summaries
   for more stable downstream modeling.

For every paper, extract the same fields:

- Biological task
- Tissue or disease context
- Dataset and sample size
- Split strategy
- Preprocessing choices
- Feature representation
- Models and baselines
- Metrics and major limitations

## 9. Suggested tools and workflow

- Python for the experimentation pipeline
- Scanpy and AnnData for scRNA-seq handling
- Pandas and NumPy for metadata and tabular summaries
- scikit-learn for preprocessing, baselines, and evaluation
- scvi-tools if a learned latent representation or stronger batch handling
  becomes necessary
- A reproducible experiment log for every preprocessing and modeling decision

## 10. Weekly execution plan

1. Define direction
   One biological context, one shortlist of 2 to 4 candidate scRNA tasks, and a
   clear non-NHANES pivot statement.
2. Compare datasets
   A dataset matrix covering labels, donor IDs, batch metadata, cell counts, and
   task feasibility.
3. Select the anchor task
   Chosen dataset, dataset card, and exact row and label definitions.
4. Design preprocessing
   Written QC, normalization, and feature-selection protocol.
5. Design evaluation
   Donor-aware split plan and baseline metric set.
6. Run baselines
   Initial results for simple models on the selected representation.
7. Run structured modeling
   First StructuralCFN or CFN-compatible experiment on filtered genes,
   pathways, or pseudobulk features.
8. Interpret and write
   Methods draft, result summary, and a decision on whether the chosen task
   supports a full project.

## 11. Final checklist before experimentation

- I can state the single-cell biological question in one sentence.
- I know whether the row unit is a cell, donor, sample, or pseudobulk profile.
- I have chosen a donor-aware or sample-aware split strategy.
- I know which metadata fields are signal, nuisance, or leakage risks.
- I have separated quality control from feature engineering.
- I have at least one simple baseline before StructuralCFN.
- I know whether CFN will use genes directly, a reduced gene set, pathway
  scores, or pseudobulk summaries.
- I am not using NHANES as the main project direction for this phase.

## 12. Bottom line

Core rule for this project:

Move the project toward a real single-cell task instead of stretching the
existing NHANES work further. First identify one dataset and one scRNA problem
that can be evaluated cleanly. Then lock the row definition, split strategy,
and preprocessing choices. Only after that should you decide how StructuralCFN
fits.

The strongest next step is to choose a disease-state classification task within
one tissue if donor-aware labels are available. If that is too noisy, use a
curated cell-type classification task as the first anchor and treat more
open-ended subgroup discovery as a later extension.
