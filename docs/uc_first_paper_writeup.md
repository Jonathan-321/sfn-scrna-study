# Toward Structured Modeling of Ulcerative Colitis Single-Cell Transcriptomics
## A Donor-Level Benchmark Scaffold for Predictive Performance and Stable Biological Structure

Status: working paper-style draft  
Last updated: 2026-03-27

## Abstract

Single-cell RNA sequencing is attractive for structure-aware modeling because it
contains both high-dimensional molecular signal and biologically meaningful
cell-state organization. However, most first-pass analyses fail much earlier:
they either mix train and test cells from the same donor, overstate performance
through pseudoreplication, or jump to complex models before establishing a
stable benchmark. This document defines and executes a donor-aware benchmark
for the ulcerative colitis colon atlas `SCP259`. The primary task is donor-
level `Healthy` versus `UC` classification using donor-level aggregated
features. Two frozen donor-global representations are benchmarked first: donor
cluster-composition proportions and donor-level pseudobulk expression. The
benchmark is then extended to compartment-aware `Epi` / `LP` blocked features,
followed by a first StructuralCFN evaluation on composition-based tables. The
current evidence shows that the donor-level task is strongly learnable, with
pseudobulk near ceiling under repeated donor resampling and leave-one-donor-out
evaluation. StructuralCFN is predictive on both donor-global and compartment-
aware composition, and compartment blocking improves CFN performance
substantially. However, structural recurrence remains weak across folds: top-k
overlap is low, consensus support does not produce a stable backbone, and full
dependency-matrix similarity is only moderate. The current justified SCP259
claim is therefore an honest benchmark claim: CFN recovers biologically
suggestive but not yet stably recurring structure at `N=30`.

## 1. Introduction

The long-term aim of this project is to evaluate whether structured models such
as StructuralCFN can improve single-cell disease prediction and expose stable,
biologically interpretable relationships. The immediate problem is narrower:
before a structured model can be justified, the benchmark itself must be
biologically meaningful, leakage-safe, and reproducible.

Ulcerative colitis is a strong first disease setting for this question because
it combines donor-level disease labels, clear tissue context, rich cell-state
diversity, and a natural path from raw single-cell matrices to donor-level
tabular summaries. The current dataset, the Smillie et al. UC colon atlas
(`SCP259`), contains both healthy and diseased donors as well as inflamed and
non-inflamed sampling contexts. That makes it useful both for supervised
benchmarking and for later structure-oriented analysis.

This writeup documents what the project is trying to do, what has already been
built, what has already been tried, and what the next model-facing steps should
be.

## 2. Problem Statement

The first concrete problem is not yet “can CFN beat everything?” The first
problem is:

- can we define a donor-aware single-cell disease benchmark that avoids
  pseudoreplication,
- can simple models learn meaningful disease signal from donor-level
  representations,
- and can the benchmark be made stable enough that later CFN results are worth
  interpreting?

This leads to the following first research question:

Can donor-level summaries from the UC colon atlas distinguish `Healthy` from
`UC` under donor-aware evaluation, and which representation carries that
signal: cell composition, pseudobulk expression, or both?

## 3. Dataset and Cohort

The current anchor dataset is the ulcerative colitis colon atlas from Smillie
et al., available in processed form through Single Cell Portal `SCP259`.

The current local raw files are stored in:

- `data/raw/uc_scp259/all.meta2.txt`
- `data/raw/uc_scp259/Epi.barcodes2.tsv`
- `data/raw/uc_scp259/Fib.barcodes2.tsv`
- `data/raw/uc_scp259/Imm.barcodes2.tsv`
- `data/raw/uc_scp259/gene_sorted-Epi.matrix.mtx`
- `data/raw/uc_scp259/gene_sorted-Fib.matrix.mtx`
- `data/raw/uc_scp259/gene_sorted-Imm.matrix.mtx`

The current cohort summary, derived directly from the metadata audit and
exploration outputs, is:

- `30` donors
- `12` healthy donors
- `18` UC donors
- `133` samples
- `48` healthy samples
- `45` non-inflamed samples
- `40` inflamed samples
- `51` annotated clusters

The current summary file is:

- `data/processed/uc_scp259/exploration/foundation_summary.txt`

## 4. Benchmark Definition

### 4.1 Primary task

The first supervised benchmark is frozen as:

- task: donor-level `Healthy` versus `UC`
- row unit: donor
- split unit: donor

Label rule:

- `Healthy` donor if all associated samples are labeled `Healthy`
- `UC` donor if the donor has any `Non-inflamed` or `Inflamed` sample

This label contract is represented in:

- `data/processed/uc_scp259/donor_metadata.tsv`
- `data/processed/uc_scp259/donor_sample_health_counts.tsv`

### 4.2 Why donor-level

This choice is deliberate. In scRNA studies, random cell-level splits can make
results look excellent simply because cells from the same donor appear in both
training and test sets. That is not real generalization. The donor is the true
independent biological unit, so the benchmark is designed at the donor level.

## 5. Representations Built So Far

### 5.1 Donor metadata

The donor metadata table is:

- `data/processed/uc_scp259/donor_metadata.tsv`

It contains:

- donor label
- health values across samples
- sampled locations
- number of cells
- number of samples
- number of clusters
- basic donor-level observed UMI and gene summaries

### 5.2 Donor composition features

The first representation is donor-level cluster composition:

- `data/processed/uc_scp259/donor_cluster_counts.tsv`
- `data/processed/uc_scp259/donor_cluster_props.tsv`

This representation asks:

Can disease be predicted from shifts in relative cell-state abundance alone?

There are `51` cluster-proportion features, one per annotated cluster.

### 5.3 Donor pseudobulk expression

The second representation is donor-level all-cell pseudobulk:

- `data/processed/uc_scp259/donor_all_cells_gene_counts.tsv.gz`
- `data/processed/uc_scp259/donor_all_cells_gene_log1p_cpm.tsv.gz`
- `data/processed/uc_scp259/gene_union_info.tsv`

This representation asks:

Can disease be predicted from aggregated donor-level transcriptomic signal?

The current all-cell donor table contains `21,784` genes across `30` donors.

### 5.4 Donor-by-location extensions

Location-aware donor tables were also built:

- `data/processed/uc_scp259/donor_location_metadata.tsv`
- `data/processed/uc_scp259/donor_location_cluster_props.tsv`
- `data/processed/uc_scp259/donor_location_gene_log1p_cpm.tsv.gz`

These are not yet the primary benchmark, but they are the natural next stage
once the donor-only baseline is stable.

## 6. Evaluation Design

### 6.1 Locked donor folds

The current split file is:

- `data/processed/uc_scp259/donor_healthy_vs_uc_folds.json`

It was generated by:

- `scripts/build_uc_donor_splits.py`

Current split design:

- `5` folds
- stratified by donor label
- `24` donors in train and `6` donors in test per fold

Why `5` folds rather than `10`:

- the cohort has only `30` donors
- `10` folds would leave only about `3` donors per test fold
- that would make fold-level metrics very unstable
- `5` folds is a better tradeoff between repeated evaluation and minimally
  usable test size

### 6.2 Baselines currently implemented

The first conventional benchmark runner is:

- `scripts/run_uc_baselines.py`

It currently supports:

- logistic regression
- linear SVM
- XGBoost

Outputs are written to:

- `results/uc_scp259/benchmarks/`

### 6.3 Preprocessing currently applied inside the benchmark

For composition features:

- all `51` cluster proportions are used
- linear models are scaled within the training fold
- XGBoost uses raw proportions

For pseudobulk expression:

- the current executable runner applies train-only variance ranking
- top `1,000` genes are retained per fold
- scaling is applied for the linear models
- XGBoost uses the filtered numeric features directly after median imputation

Important note:

The current runner does not yet apply the donor-prevalence filter described in
`docs/uc_preprocessing_decisions.md`. That remains a planned sensitivity check.

## 7. What Has Been Tried

The following steps are now complete:

1. Metadata audit from `all.meta2.txt`
2. Donor metadata table generation
3. Donor cluster composition table generation
4. Donor all-cell pseudobulk generation
5. Donor-by-location table generation
6. Exploration summaries for donor, sample, location, and cluster structure
7. Locked donor split generation
8. First donor-level conventional baselines on composition and pseudobulk
9. Repeated stratified donor CV on composition and pseudobulk
10. Leave-one-donor-out evaluation on composition and pseudobulk
11. First donor-by-compartment baselines on `Epi` and `LP`
12. First StructuralCFN pass on the frozen donor-level composition benchmark

This is the project’s first real execution milestone: the benchmark is no
longer hypothetical.

## 8. Preliminary Results

### 8.1 Composition-only benchmark

Source:

- `results/uc_scp259/benchmarks/donor_cluster_props_baselines_summary.tsv`

Current mean 5-fold results:

- linear SVM: AUROC `0.9278`, AUPRC `0.9667`, balanced accuracy `0.8333`,
  macro-F1 `0.7962`
- logistic regression: AUROC `0.8778`, AUPRC `0.9467`, balanced accuracy
  `0.8333`, macro-F1 `0.8000`
- XGBoost: AUROC `0.8500`, AUPRC `0.9408`, balanced accuracy `0.8500`,
  macro-F1 `0.8527`

Interpretation:

- donor-level disease signal is already strong in cluster composition alone
- a simple linear separator on composition is highly competitive
- this means UC status in this atlas is at least partly reflected in cell-state
  abundance shifts

### 8.1.1 Composition repeated-CV robustness check

Source:

- `results/uc_scp259/benchmarks/donor_cluster_props_repeated_summary.tsv`

Current mean repeated 5-fold results across `10` repeats:

- logistic regression: AUROC `0.9364 +/- 0.0289`, AUPRC `0.9588 +/- 0.0190`
- linear SVM: AUROC `0.9272 +/- 0.0342`, AUPRC `0.9536 +/- 0.0236`
- XGBoost: AUROC `0.8786 +/- 0.0342`, AUPRC `0.9338 +/- 0.0209`

Interpretation:

- the composition result survives donor resampling; it is not a single-split
  artifact
- after repeated CV, the safer composition winners are the linear models rather
  than XGBoost
- this is useful feedback for the later CFN comparison, because it means the
  composition benchmark behaves more like a smooth linear-separable signal than
  like a tree-dominated nonlinear task

### 8.1.2 Composition leave-one-donor-out sanity check

Source:

- `results/uc_scp259/benchmarks/donor_cluster_props_lodo_summary.tsv`

Aggregated leave-one-donor-out results across all `30` held-out donors:

- logistic regression: AUROC `0.9491`, AUPRC `0.9602`, accuracy `0.8667`
- linear SVM: AUROC `0.9259`, AUPRC `0.9307`, accuracy `0.8667`
- XGBoost: AUROC `0.8611`, AUPRC `0.9228`, accuracy `0.7333`

Interpretation:

- the donor-level composition signal survives the harsher LODO setting
- the model ranking from repeated CV is consistent with LODO: linear models are
  safer than XGBoost on composition
- this reduces the risk that the original 5-fold result was driven mainly by a
  favorable donor partition

### 8.2 Donor pseudobulk benchmark

Source:

- `results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_baselines_summary.tsv`

Current mean 5-fold results:

- XGBoost: AUROC `1.0000`, AUPRC `1.0000`, balanced accuracy `0.9667`,
  macro-F1 `0.9657`
- linear SVM: AUROC `0.9250`, AUPRC `0.9608`, balanced accuracy `0.8500`,
  macro-F1 `0.8324`
- logistic regression: AUROC `0.9250`, AUPRC `0.9608`, balanced accuracy
  `0.8500`, macro-F1 `0.8324`

Interpretation:

- donor-level expression carries very strong disease signal
- the perfect mean AUROC for XGBoost is encouraging but must be treated with
  caution because the cohort is still small
- one fold for the linear models was substantially weaker than the others,
  which shows the benchmark is still sensitive to donor partitioning

### 8.2.1 Pseudobulk repeated-CV robustness check

Source:

- `results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_repeated_summary.tsv`

Current mean repeated 5-fold results across `10` repeats:

- XGBoost: AUROC `0.9975 +/- 0.0079`, AUPRC `0.9990 +/- 0.0032`
- linear SVM: AUROC `0.9925 +/- 0.0237`, AUPRC `0.9961 +/- 0.0124`
- logistic regression: AUROC `0.9925 +/- 0.0237`, AUPRC `0.9961 +/- 0.0124`

Interpretation:

- the pseudobulk result is extremely strong under repeated donor resampling
- unlike the first single 5-fold pass, the repeated analysis shows that the
  linear models are also near-ceiling on this representation
- the benchmark conclusion is now much stronger: donor-level pseudobulk
  contains highly stable UC-versus-Healthy signal under the current donor-level
  evaluation setup

### 8.2.2 Pseudobulk leave-one-donor-out sanity check

Source:

- `results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_lodo_summary.tsv`

Aggregated leave-one-donor-out results across all `30` held-out donors:

- linear SVM: AUROC `1.0000`, AUPRC `1.0000`, accuracy `0.9667`
- logistic regression: AUROC `1.0000`, AUPRC `1.0000`, accuracy `0.9333`
- XGBoost: AUROC `0.9907`, AUPRC `0.9944`, accuracy `0.9667`

Interpretation:

- the pseudobulk representation remains near-ceiling even under leave-one-donor-out
- this is now strong evidence that donor-level pseudobulk carries a very large
  UC-versus-Healthy signal in this atlas
- because the donor count is still small, these results are best treated as a
  high-confidence benchmark foundation rather than as a final biological claim

### 8.4 Donor-by-compartment benchmark

Compartment-wide donor tables were built by pivoting donor-location features
into donor rows with separate `Epi__*` and `LP__*` blocks.

Sources:

- `data/processed/uc_scp259/donor_compartment_cluster_props.tsv`
- `data/processed/uc_scp259/donor_compartment_gene_log1p_cpm.tsv.gz`
- `results/uc_scp259/benchmarks/donor_compartment_cluster_props_baselines_summary.tsv`
- `results/uc_scp259/benchmarks/donor_compartment_pseudobulk_baselines_summary.tsv`

Current 5-fold compartment-composition results:

- linear SVM: AUROC `0.9556`, AUPRC `0.9667`
- logistic regression: AUROC `0.9556`, AUPRC `0.9667`
- XGBoost: AUROC `0.7111`, AUPRC `0.8428`

Current 5-fold compartment-pseudobulk results:

- linear SVM: AUROC `1.0000`, AUPRC `1.0000`
- logistic regression: AUROC `1.0000`, AUPRC `1.0000`
- XGBoost: AUROC `0.9556`, AUPRC `0.9611`

Interpretation:

- separating epithelial and lamina propria information is useful
- the compartment-aware composition table improves the linear baselines over
  donor-global composition
- the compartment-aware pseudobulk table is also extremely strong, and again
  the linear models are fully competitive
- this is important feedback for CFN: the benchmark does not look like a
  tree-only regime

### 8.5 StructuralCFN results and diagnostics

The first CFN pass was deliberately restricted to composition-based tables
rather than the wide pseudobulk table.

Sources:

- `data/processed/uc_scp259/donor_cluster_props_benchmark.csv`
- `data/processed/uc_scp259/donor_compartment_cluster_props_benchmark.csv`
- `results/uc_scp259/cfn_benchmarks/donor_cluster_props_cfn_full_summary.csv`
- `results/uc_scp259/cfn_benchmarks/donor_compartment_cluster_props_cfn_full_summary.csv`
- `results/uc_scp259/cfn_benchmarks/donor_cluster_props_cfn_full_stability_summary.csv`
- `results/uc_scp259/cfn_benchmarks/donor_compartment_cluster_props_cfn_full_stability_summary.csv`
- `results/uc_scp259/cfn_benchmarks/donor_cluster_props_cfn_full_consensus_support_summary.csv`
- `results/uc_scp259/cfn_benchmarks/donor_compartment_cluster_props_cfn_full_consensus_support_summary.csv`
- `results/uc_scp259/cfn_benchmarks/cfn_matrix_similarity_comparison.csv`
- `results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_final_v3.csv`

Current donor-global CFN composition result:

- StructuralCFN: AUROC `0.9056`, AUPRC `0.9444`, Brier `0.1640`
- grouped top-k Jaccard: `0.0316`
- sign consistency: `0.8980`
- full-matrix cosine similarity mean: `0.5366`

Current compartment-aware CFN composition result:

- StructuralCFN: AUROC `0.9778`, AUPRC `0.9833`, Brier `0.1320`
- grouped top-k Jaccard: `0.0322`
- sign consistency: `0.8980`
- full-matrix cosine similarity mean: `0.4507`

Top-k sensitivity on the compartment-aware run:

- `top_k = 10`: grouped Jaccard `0.0322`
- `top_k = 20`: grouped Jaccard `0.0532`
- `top_k = 30`: grouped Jaccard `0.0497`

Consensus support profile:

- donor-global and compartment-aware CFN both show only `1/5` and `2/5`
  support edges
- neither run produces any recurring `3/5+` consensus backbone

Biological interpretation of the recurring edge set:

- the small recurring set is enriched for epithelial regeneration /
  differentiation and epithelial-immune or epithelial-stromal crosstalk
- the strongest main-text edges are:
  - `Stem -> Immature Enterocytes 2`
  - `Enterocyte Progenitors -> ILCs`
  - `Enterocyte Progenitors -> Myofibroblasts`
  - `RSPO3+ -> CD8+ IELs`
- these edges are now framed in
  `results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_final_v3.csv`
  as supported or supported-with-caveat, not as directly verified causal edges

Interpretation:

- the benchmark can now carry StructuralCFN without changing the donor-aware
  evaluation harness
- compartment-aware composition clearly improves CFN predictive performance
- however, compartment blocking does not improve structural recurrence
- the instability is not just a top-k reporting artifact: full dependency-
  matrix similarity is only moderate on donor-global composition and lower on
  compartment-aware composition
- the strongest structural signal that survives across all diagnostics is
  directional consistency, not stable edge identity
- the honest SCP259 conclusion is therefore mixed: CFN is predictive and
  biologically suggestive, but its unconstrained structure is not stable enough
  at `N=30` for a strong recurring-backbone claim

### 8.6 Feature-level hints

Top composition-side signals currently include:

- Enteroendocrine
- Enterocyte Progenitors
- Tregs
- Pericytes
- Inflammatory Fibroblasts

Top expression-side signals currently include:

- `MMP3`
- `S100P`
- `PLA2G2A`
- `REG4`
- `CHI3L1`

These are not yet a finalized biological interpretation section, but they are
useful evidence that the baseline is picking up structured disease-related
signal rather than only obvious technical columns.

## 9. What These Results Mean

The benchmark is working. The donor-level `Healthy` versus `UC` task is not too
weak to study, and it is not blocked by preprocessing anymore.

The main scientific meaning of the current results is:

- composition already contains substantial signal
- donor pseudobulk expression may contain even stronger signal
- repeated CV shows that these conclusions survive donor resampling
- leave-one-donor-out confirms that the signal remains strong under a harsher
  donor-level validation setting
- compartment-aware donor tables add useful signal, especially for the linear
  baselines
- the project now has a strong enough baseline stage to justify structured
  modeling, and that stage is complete enough to support a paper claim on
  `SCP259`
- donor-global pseudobulk is the strongest predictive representation, but it is
  near ceiling and therefore not the best first arena for testing whether CFN
  adds structural value
- donor-global and compartment-aware composition are the right CFN-facing
  representations because they preserve biological meaning while still leaving
  room for structured-model comparison
- CFN does learn useful predictive signal, especially once compartment
  structure is preserved
- however, edge-identity recurrence remains weak, consensus support does not
  produce a stable backbone, and full-matrix similarity confirms that the
  instability is real rather than a top-k artifact
- the recurring edge set is biologically coherent enough to discuss, but not
  stable enough to justify strong mechanistic claims

These are no longer only setup-stage results. The SCP259 analysis is far enough
along to support a scoped paper framing and external feedback from advisors or
domain experts.

## 10. StructuralCFN Status in This Benchmark

The order of operations is now complete enough to interpret:

1. dataset understanding
2. donor-aware tables
3. locked folds
4. conventional baselines
5. repeated-resampling robustness checks
6. leave-one-donor-out sanity check
7. donor-compartment benchmark
8. first CFN runs
9. structural diagnostics
10. biological annotation of recurring edges

This matters because CFN is now being judged inside a benchmark that was
hardened first. That makes the current negative evidence on structure
stability scientifically meaningful rather than a setup artifact.

## 11. Analysis Completion and Paper Framing

### 11.1 What is complete

The following SCP259 analysis components are complete enough to support a
scoped paper claim:

- donor-aware benchmark construction
- donor-global baseline benchmarking
- repeated-CV and leave-one-donor-out robustness checks on donor-global tables
- donor-compartment baseline benchmarking
- donor-global CFN composition run
- compartment-aware CFN composition run
- top-k stability, sign consistency, consensus support, and full-matrix
  similarity diagnostics
- first-pass biological annotation of recurring CFN edges, now consolidated in
  `results/uc_scp259/cfn_benchmarks/uc_recurring_edge_annotation_final_v3.csv`

### 11.2 What the paper should claim now

The SCP259 paper should currently be framed as an honest donor-aware benchmark
paper with a structured-model evaluation, not as a victory lap for CFN.

The current claim should be:

- donor-level UC versus Healthy prediction is robustly learnable from SCP259
- donor pseudobulk is the strongest predictive representation
- compartment-aware composition improves CFN prediction
- CFN produces biologically suggestive but structurally unstable outputs at
  `N=30`

The paper should not currently claim:

- that CFN beats all baselines overall
- that CFN recovers a stable recurring dependency backbone
- that any learned directed edge is directly validated as a causal mechanism

### 11.3 What remains before seeking feedback

Before expanding to a larger cohort, the remaining SCP259-specific work should
be limited to paper framing and presentation:

- integrate the `final_v3` edge-annotation file into the writeup
- build the final benchmark tables and figure list for SCP259
- write one concise discussion paragraph on why structure instability may be
  expected at `N=30`
- prepare an advisor-facing summary of what is complete, what is mixed, and
  what would justify larger-cohort expansion

### 11.4 What should wait

The following should wait until after professor or expert feedback:

- larger-cohort expansion
- additional CFN architectural tweaks
- new representation families beyond the current donor-global and compartment-
  aware tables
- stronger biological claims than the current supported-with-caveat edge set

## 12. Reproducibility Map

Core scripts:

- `scripts/audit_uc_metadata.py`
- `scripts/build_uc_donor_tables.py`
- `scripts/build_uc_donor_location_tables.py`
- `scripts/build_uc_compartment_tables.py`
- `scripts/build_uc_supervised_table.py`
- `scripts/explore_uc_foundations.py`
- `scripts/build_uc_donor_splits.py`
- `scripts/run_uc_baselines.py`
- `scripts/run_uc_repeated_cv.py`
- `scripts/run_uc_lodo.py`
- `scripts/build_uc_cfn_consensus_support.py`
- `scripts/build_donor_global_comparison_table.py`
- `scripts/build_uc_cfn_matrix_similarity.py`
- `scripts/build_uc_edge_annotation_table.py`

Current benchmark commands:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/build_uc_donor_splits.py

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_baselines.py \
  --features data/processed/uc_scp259/donor_cluster_props.tsv \
  --folds data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_cluster_props_baselines

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_baselines.py \
  --features data/processed/uc_scp259/donor_all_cells_gene_log1p_cpm.tsv.gz \
  --folds data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_all_cells_pseudobulk_baselines \
  --max-features 1000

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_repeated_cv.py \
  --features data/processed/uc_scp259/donor_cluster_props.tsv \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_cluster_props

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_repeated_cv.py \
  --features data/processed/uc_scp259/donor_all_cells_gene_log1p_cpm.tsv.gz \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_all_cells_pseudobulk \
  --max-features 1000

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_lodo.py \
  --features data/processed/uc_scp259/donor_cluster_props.tsv \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_cluster_props

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_lodo.py \
  --features data/processed/uc_scp259/donor_all_cells_gene_log1p_cpm.tsv.gz \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_all_cells_pseudobulk \
  --max-features 1000

python3 scripts/build_uc_compartment_tables.py

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_baselines.py \
  --features data/processed/uc_scp259/donor_compartment_cluster_props.tsv \
  --folds data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_compartment_cluster_props_baselines

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  scripts/run_uc_baselines.py \
  --features data/processed/uc_scp259/donor_compartment_gene_log1p_cpm.tsv.gz \
  --folds data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_compartment_pseudobulk_baselines \
  --max-features 1000

python3 scripts/build_uc_supervised_table.py \
  --features data/processed/uc_scp259/donor_cluster_props.tsv \
  --output data/processed/uc_scp259/donor_cluster_props_benchmark.csv

/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python \
  /Users/jonathanmuhire/CFN/cfn-biomed-eval/research/scripts/run_locked_benchmarks.py \
  --data data/processed/uc_scp259/donor_cluster_props_benchmark.csv \
  --folds data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \
  --id-col donor_id \
  --target-col uc_binary \
  --models cfn_default \
  --output-dir results/uc_scp259/cfn_benchmarks \
  --run-name donor_cluster_props_cfn_full \
  --structure-dir results/uc_scp259/cfn_structures \
  --scfn-path /Users/jonathanmuhire/CFN/StructuralCFN-public
```

## 13. Current Paper Claim

The strongest claim that is justified right now is:

We have established a donor-aware ulcerative colitis single-cell benchmark in
`SCP259` in which both donor-level cell composition and donor-level pseudobulk
expression robustly separate `Healthy` and `UC`, and this conclusion survives
repeated donor resampling and leave-one-donor-out validation. Donor pseudobulk
is the strongest predictive representation, while compartment-aware composition
provides the most informative first arena for structured modeling. StructuralCFN
is predictive on both donor-global and compartment-aware composition and
recovers biologically coherent edge themes, but its unconstrained structure
does not recur stably across folds at `N=30`, so the defensible claim is one of
honest structured benchmarking rather than stable mechanistic recovery.

## 14. Current Decision Point

The immediate decision is no longer about what technical infrastructure to
build. It is about project framing.

The recommended order is:

1. finish the SCP259 paper framing
2. get feedback from the professor and any biological experts
3. only then decide whether larger-cohort expansion is needed to test the
   sample-size hypothesis for CFN structure stability
