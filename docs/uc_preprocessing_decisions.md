# UC Preprocessing Decisions

Last updated: 2026-03-12

## Purpose

This note freezes the useful preprocessing choices for the first UC benchmark
before baseline modeling starts.

The goal is not to apply every possible single-cell preprocessing method. The
goal is to apply only the preprocessing that helps the first donor-level
`Healthy` vs `UC` benchmark stay:

- leakage-safe
- biologically interpretable
- numerically stable for small-`n` modeling

## What has already been done

The current processed UC tables already include important upstream work:

- donor-level aggregation from the cell-by-gene matrices
- library-size normalization and `log1p` transform for the donor expression
  table
- donor-level cluster proportions for the composition table
- a donor metadata table with the frozen `Healthy` vs `UC` label

That means the first benchmark does not need cell-level QC, cell filtering,
doublet detection, or new normalization. Those are upstream dataset
construction questions, not first-pass donor-table questions.

## What we are actually evaluating

The first benchmark compares two distinct signal sources.

### Composition-only baseline

Input:

- `data/processed/uc_scp259/donor_cluster_props.tsv`

Question:

- can we distinguish `Healthy` vs `UC` using only changes in the relative
  abundance of the 51 annotated cell states?

### Expression baseline

Input:

- `data/processed/uc_scp259/donor_all_cells_gene_log1p_cpm.tsv.gz`

Question:

- can we distinguish `Healthy` vs `UC` using donor-level transcriptomic signal
  after aggregation across all cells?

### Label and grouping contract

Input:

- `data/processed/uc_scp259/donor_metadata.tsv`

Question:

- what is the donor label, and what is the independent unit for evaluation?

## What preprocessing is useful now

### 1. Keep the donor as the independent unit

This is not optional.

- row unit: donor
- split unit: donor
- all feature selection and scaling must be fit on the training fold only

This is the main protection against pseudoreplication and leakage.

### 2. Do not use technical metadata as first-pass features

Keep these columns for diagnostics, not prediction:

- `n_cells`
- `n_samples`
- `total_nUMI_obs`
- `mean_nUMI_obs`
- `mean_nGene_obs`

Why:

- they may reflect sampling or capture differences
- they can create shortcuts that look predictive without being biologically
  meaningful

We can test them later as a sensitivity analysis.

### 3. Keep all cluster proportions for the first composition baseline

Current dataset facts:

- there are `51` cluster-proportion features
- none has zero variance across donors
- every cluster appears in at least `14` of the `30` donors

Decision:

- keep all 51 cluster proportions for the first pass
- do not apply an aggressive rarity filter yet

Useful preprocessing:

- for logistic regression and linear SVM, standardize within each training fold
- for XGBoost, leave the raw proportions alone

Optional later:

- compare raw proportions to a compositional transform such as CLR, but do not
  make that the first benchmark default

### 4. Do not use all 21,784 genes directly

This is the main place where preprocessing matters.

Current dataset facts:

- expression table has `21,784` genes and `30` donors
- all genes have nonzero variance, so a naive zero-variance filter does almost
  nothing
- `19,157` genes are present in at least `5` donors
- `17,790` genes are present in at least `10` donors

Why variance filtering alone is not enough:

- with only `30` donors, the feature space is far wider than the sample space
- even after log-CPM normalization, many genes are too sparse or too unstable
  for a clean first baseline

Decision:

- use a two-step gene filter

Step 1: prevalence filter on counts

- keep genes with raw donor pseudobulk count `> 0` in at least `5` donors
- this removes the rarest donor-specific genes while keeping most of the union
  gene space

Step 2: variance ranking on the training fold only

- compute variance on the training donors only
- keep the top `500` genes for the first baseline
- run `1,000` genes as the first sensitivity check

Why `500` first:

- `30` donors is a very small sample
- a smaller feature set gives more stable linear baselines
- it keeps the first comparison interpretable and less likely to overfit

### 5. Standardize expression features inside the training fold

For logistic regression and linear SVM:

- fit `StandardScaler` on training donors only
- transform validation donors with that fitted scaler

For XGBoost:

- skip standardization unless a later experiment shows it helps

Why:

- linear models are sensitive to feature scale
- tree models are much less dependent on scaling

### 6. Do not apply integration or batch correction yet

Decision:

- no Harmony
- no BBKNN
- no scVI latent embedding as the first supervised representation

Why:

- we do not yet have a verified explicit batch column in the benchmark tables
- overcorrection is a real risk in disease-focused studies
- the first benchmark should use the most transparent donor-level
  representations

These methods can be added later if the simple donor tables fail for a clear
reason.

### 7. Do not run PCA as the first default compression step

Decision:

- first baseline should use filtered real features directly

Why:

- direct features are easier to interpret
- PCA would compress already small donor sample size into abstract components
- PCA can be a later sensitivity analysis if the linear baseline is unstable

## Recommended first-pass preprocessing contracts

### Composition model input

Use:

- `donor_cluster_props.tsv`

Steps:

1. join to `donor_metadata.tsv` by `donor_id`
2. keep all 51 cluster-proportion columns
3. standardize within fold for linear models only

### Expression model input

Use:

- `donor_all_cells_gene_counts.tsv.gz`
- `donor_all_cells_gene_log1p_cpm.tsv.gz`
- `donor_metadata.tsv`

Steps:

1. join by `donor_id`
2. apply prevalence filter using the count table
3. apply training-fold-only variance ranking using the log-CPM table
4. keep top `500` genes first
5. standardize within fold for linear models only

## What we should not do yet

Do not start with:

- global feature scaling before cross-validation
- global variance filtering before split-aware evaluation
- donor metadata as predictors
- integrated latent spaces
- pathway scores as the only first feature representation
- donor-by-cell-type pseudobulk as a prerequisite for the first baseline

## Immediate implementation sequence

1. build a baseline runner that consumes:
   - `donor_metadata.tsv`
   - `donor_cluster_props.tsv`
   - `donor_all_cells_gene_counts.tsv.gz`
   - `donor_all_cells_gene_log1p_cpm.tsv.gz`
2. implement fold-safe preprocessing inside the runner:
   - prevalence filter for genes
   - training-fold variance ranking
   - training-fold scaling for linear models
3. evaluate:
   - composition-only logistic regression
   - expression logistic regression with top `500` genes
   - then the same with linear SVM and XGBoost

## Source-backed rationale

- scverse best practices recommend library-size normalization and log transform
  as a strong default for exploratory and downstream structure-preserving work.
- scverse feature-selection guidance emphasizes selecting highly variable genes
  rather than carrying the full gene space into downstream analyses.
- pseudobulk and replicate-aware approaches are favored when the inferential unit
  is the subject rather than the cell.
- scikit-learn preprocessing should be fit inside the training pipeline to avoid
  leakage during evaluation.

## Sources

- scverse best practices, normalization:
  https://www.sc-best-practices.org/preprocessing_visualization/normalization.html
- scverse best practices, feature selection:
  https://www.sc-best-practices.org/preprocessing_visualization/feature_selection.html
- scverse best practices, integration:
  https://www.sc-best-practices.org/cellular_structure/integration.html
- Nature Communications, pseudoreplication in single-cell studies:
  https://www.nature.com/articles/s41467-021-21038-1
- Nature Communications, false discoveries and pseudobulk:
  https://www.nature.com/articles/s41467-021-25960-2
- Nature Communications, scCODA and compositional effects:
  https://www.nature.com/articles/s41467-021-27150-6
- scikit-learn `VarianceThreshold`:
  https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.VarianceThreshold.html
- scikit-learn `StandardScaler`:
  https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html
- scikit-learn `Pipeline`:
  https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html
