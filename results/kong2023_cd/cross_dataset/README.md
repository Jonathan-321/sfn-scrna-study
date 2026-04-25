# Cross-Dataset Validation: SCP259 (UC) ↔ Kong 2023 (CD)

## Overview

This directory contains results for cross-dataset generalization experiments
between two IBD cohorts with distinct disease subtypes and cell-type annotation schemes.

| Dataset | Disease | Donors | Cell types | Source |
|---------|---------|--------|------------|--------|
| Smillie SCP259 | Ulcerative Colitis vs Healthy | 30 (18 UC, 12 Healthy) | 51 | [SCP259](https://singlecell.broadinstitute.org/single_cell/study/SCP259) |
| Kong 2023 | Crohn Disease vs Healthy | 71 (17 CD, 54 Healthy) | 68 | [CELLxGENE](https://cellxgene.cziscience.com/collections/5c868b6f-62c5-4532-9d7f-a346ad4b50a7) |

**Feature overlap:** Only 4 cell types share names across both annotation schemes
(DC1, ILCs, Macrophages, Tregs). Non-overlapping features are zero-filled in the
test set (no leakage from test distribution).

---

## Results

### 1. Within-cohort baselines (5-fold StratifiedKFold)

| Dataset | Model | AUROC | PR-AUC |
|---------|-------|-------|--------|
| SCP259 (UC vs Healthy) | LogReg | 0.878 ± 0.217 | 0.947 ± 0.081 |
| SCP259 (UC vs Healthy) | LinearSVM | 0.928 ± 0.110 | 0.967 ± 0.046 |
| SCP259 (UC vs Healthy) | XGBoost | 0.850 ± 0.224 | 0.941 ± 0.085 |
| Kong (CD vs Healthy) | LogReg | 0.818 ± 0.059 | 0.694 ± 0.139 |
| Kong (CD vs Healthy) | LinearSVM | 0.712 ± 0.077 | 0.607 ± 0.134 |
| Kong (CD vs Healthy) | XGBoost | 0.780 ± 0.076 | 0.633 ± 0.108 |

### 2. Cross-dataset: Train SCP259 UC → Test Kong CD

Train on 30 UC/Healthy donors, test on 71 CD/Healthy donors.
Features: SCP259 51-dim composition; 4 shared → 47 zero-filled in test.

| Model | AUROC (CLR) | AUROC (raw) |
|-------|-------------|-------------|
| LogReg | 0.503 | 0.619 |
| LinearSVM | 0.547 | 0.614 |
| XGBoost | 0.465 | 0.576 |

### 3. Cross-dataset: Train Kong CD → Test SCP259 UC

Train on 71 CD/Healthy donors, test on 30 UC/Healthy donors.
Features: Kong 68-dim composition; 4 shared → 64 zero-filled in test.

| Model | AUROC |
|-------|-------|
| LogReg | 0.741 |
| LinearSVM | 0.764 |
| XGBoost | 0.833 |

---

## Interpretation

**Forward direction (UC → CD) collapses to near-chance (AUROC ~0.47–0.55).**
The 47 UC-specific cell-type proportions (Enterocytes, Goblet, Plasma, etc.)
provide no signal when zero-filled in the CD test set. Only 4 shared immune
cell types (DC1, ILCs, Macrophages, Tregs) carry information, which is insufficient.

**Reverse direction (CD → UC) shows partial transfer (AUROC 0.74–0.83).**
This asymmetry reflects the larger Kong training set (n=71 vs 30) and the fact
that 4 conserved immune cell types — which make up a larger fraction of the
Kong 68-dim feature space (4/68 = 5.9%) than SCP259 (4/51 = 7.8%) — retain
some IBD-discriminative signal across disease subtypes.

**Publication implication:**  Composition-based IBD classification is
annotation-scheme-specific, not disease-agnostic. This motivates graph-based
approaches (CFN) that exploit cell-type co-occurrence structure rather than
raw proportions — the graph topology is less dependent on annotation granularity.

---

## Files

| File | Description |
|------|-------------|
| `kong_cross_dataset_composition_metrics.tsv` | Forward metrics (CLR) |
| `kong_cross_dataset_composition_noclr_metrics.tsv` | Forward metrics (raw) |
| `kong_reverse_cross_dataset_metrics.tsv` | Reverse metrics |
| `*_predictions.tsv` | Per-donor predicted probabilities |
| `*_feature_importance.tsv` | Model coefficients/importances |
