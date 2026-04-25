# Results

## 3.1 Within-dataset classification of UC from cell type composition (SCP259)

We evaluated donor-level UC classification on the Smillie et al. 2019 dataset (SCP259; n=30 donors, 51 cell types) using 5-fold cross-validation across four feature representations: raw cell type composition, compartment-stratified composition, pseudobulk gene expression, and CFN-derived graph features.

Using the 51-dimensional raw composition vector, LinearSVM achieved the strongest performance among standard classifiers (AUROC 0.928 ± 0.110, PR-AUC 0.967), followed by LogReg (AUROC 0.878 ± 0.217, PR-AUC 0.947) and XGBoost (AUROC 0.850 ± 0.224, PR-AUC 0.941). Stratifying composition by tissue compartment — epithelial, fibroblast, and immune separately — yielded a 102-dimensional feature vector. Both LinearSVM and LogReg improved to AUROC 0.956 ± 0.061 (PR-AUC 0.967) under this representation, while XGBoost declined substantially (AUROC 0.711 ± 0.227), suggesting that tree-based methods did not generalize reliably under the expanded feature space at this sample size. The consistent advantage of compartment-stratified features over pooled composition indicates that between-compartment confounding partially obscures disease-associated shifts when cell types across compartments are treated as a single vector.

Pseudobulk gene expression (top 1,000 highly variable genes) yielded a perfect cross-validated AUROC of 1.000 ± 0.000 with XGBoost. Given n=30 donors, this result almost certainly reflects overfitting rather than true generalization; the high-dimensional gene expression space provides ample capacity to memorize fold-specific variation, and this result should be interpreted with caution.

StructuralCFN applied to the global 51-dimensional composition yielded AUROC 0.906 ± 0.130 (PR-AUC 0.944), comparable to but slightly below the best linear baselines. Applied to the 102-dimensional compartment-stratified composition, StructuralCFN achieved AUROC 0.978 ± 0.050 (PR-AUC 0.983), the highest point estimate among all evaluated methods on SCP259. The reduction in variance relative to the global CFN result (SD 0.050 vs. 0.130) is consistent with the compartment features providing a more structured input to the causal graph inference step.

Bootstrap confidence intervals (N=2,000 resamples, pooled across representations) indicated high overall discriminability: LogReg AUROC 0.991 [95% CI: 0.959–1.000], LinearSVM AUROC 0.987 [95% CI: 0.944–1.000], and XGBoost AUROC 0.995 [95% CI: 0.973–1.000]. The width of these intervals, however, reflects the limited sample size (n=30), and these estimates should not be taken as proxies for out-of-sample performance in an independent cohort.

## 3.2 scVI latent space representation (SCP259, all compartments)

We trained scVI on the full SCP259 dataset spanning all three tissue compartments (epithelial, fibroblast, and immune; families Epi, Fib, and Imm). Cells were subsampled to 300 per donor per compartment family to control memory during CPU training, yielding 9,000 cells across 30 donors. HVG selection retained 3,000 genes (cell_ranger flavor; seurat_v3 was attempted first but failed due to near-singular LOESS fitting on the sparse Imm gene_sorted MTX). The model used a two-layer encoder with 128 hidden units, a 20-dimensional latent space, negative binomial gene likelihood, donor identity as batch key, and was trained for up to 150 epochs with early stopping (patience 45 epochs on ELBO validation loss); training terminated at epoch 111.

We evaluated two latent feature representations extracted from the trained model. The global representation averaged latent vectors across all cells per donor, yielding a 20-dimensional feature vector. The compartment-stratified representation computed the per-compartment donor mean latent and concatenated the three 20-dimensional vectors into a 60-dimensional feature, directly analogous to the compartment-stratified composition features evaluated in Section 3.1.

On the global 20-dimensional latent, all three classifiers performed modestly: XGBoost AUROC 0.725 ± 0.399, LogReg AUROC 0.706 ± 0.327, LinearSVM AUROC 0.706 ± 0.305. Variance was high, consistent with 20 dimensions being an underspecified summary of disease-relevant variation when compartment structure is collapsed.

On the compartment-stratified 60-dimensional latent, performance improved markedly: XGBoost AUROC 0.931 ± 0.101 (PR-AUC 0.951), LinearSVM AUROC 0.900 ± 0.224, LogReg AUROC 0.900 ± 0.224. The XGBoost result (0.931) is competitive with the best composition baseline on SCP259 (compartment LinearSVM 0.956) and substantially above the global scVI latent. This gap between global and compartment-stratified scVI embeddings mirrors the pattern observed for composition features: compartment-level signals are more discriminative than pooled signals, and this structure is captured by the latent representation as well as by raw cell type proportions. These results indicate that scVI latent embeddings can reach near-composition-level classification performance when compartment structure is preserved in the feature representation, even under CPU-bound training with subsampled cells.

## 3.3 CFN edge stability

We assessed the stability of learned CFN graphs across the five cross-validation folds as a measure of structural reliability. For the global CFN (51-dimensional composition input), the Jaccard similarity of the top-10 recurrent edges was 0.026, indicating poor consistency across folds — the inferred graph structure changed substantially depending on which donors were held out. This instability likely reflects both the small sample size and the relatively high dimensionality of the global composition vector relative to the number of training samples per fold.

In contrast, the compartment CFN (102-dimensional input, separate compartment blocks) showed complete structural stability: the top-20 edges exhibited a fold recurrence rate of 1.0 and a sign consistency of 1.0, meaning the same edges appeared in all five folds with identical directionality. This result indicates that compartment-stratified input substantially regularizes the CFN inference problem, producing a graph whose structure is robust to donor resampling. The stable compartment CFN edges therefore represent candidates for biologically interpretable cell-type co-abundance relationships, though functional validation is beyond the scope of this study.

## 3.4 CD classification in the Kong 2023 dataset

We evaluated Crohn's disease (CD) versus healthy classification on the Kong et al. 2023 dataset (n=71 donors, 68 cell types) using centered log-ratio (CLR) transformed composition features and 5-fold cross-validation. Across all biopsy regions combined (n=71), CatBoost achieved the highest performance (AUROC 0.840 ± 0.054, PR-AUC 0.711), followed closely by ElasticNet (AUROC 0.836 ± 0.120, PR-AUC 0.703), XGBoost (AUROC 0.824 ± 0.076), and LogReg (AUROC 0.819 ± 0.059).

Performance improved markedly when donors were stratified by biopsy site. Using terminal ileum (TI) biopsies only (n=42, 61 cell types), CatBoost achieved AUROC 0.967 ± 0.075 (PR-AUC 0.950), with LinearSVM reaching AUROC 0.917 ± 0.062 (PR-AUC 0.873), and both LogReg and XGBoost at AUROC 0.900. For colon-only donors (n=34, 55 cell types), the top result was LinearSVM at AUROC 0.900 ± 0.100, with LogReg, XGBoost, and ElasticNet each reaching AUROC 0.880. The substantially higher TI performance relative to pooled and colon analyses suggests that CD-associated cell type composition shifts are more consistently detectable in the terminal ileum, consistent with the known predilection of Crohn's disease for ileocecal involvement.

GatedStructuralCFN (300 epochs, CLR-transformed input) was also evaluated on Kong 2023 across all three biopsy-region strata. On all-region donors (n=71, 68 cell types), CFN achieved AUROC 0.812 ± 0.136 (PR-AUC 0.641), comparable to but below the CLR CatBoost baseline (AUROC 0.840 ± 0.054). On TI-only donors (n=42, 61 cell types), CFN yielded AUROC 0.811 ± 0.164, substantially below CLR CatBoost (0.967 ± 0.075) — the TI region appears to be a regime where linear CLR baselines strongly outperform CFN, likely because the composition shift is large and monotone enough to be linearly separable after CLR transformation. On colon-only donors (n=34, 55 cell types), CFN achieved AUROC 0.920 ± 0.084 (PR-AUC 0.883), modestly exceeding the top CLR baseline (LinearSVM 0.900 ± 0.100), suggesting a more complex colon composition structure where CFN's dependency modeling adds value.

## 3.5 Cross-dataset generalization

To test whether disease-associated composition signals were transferable across datasets and disease contexts, we trained classifiers on one dataset and evaluated them on the other, restricting features to the four cell types with compatible annotations across both atlases: DC1, ILCs, Macrophages, and Tregs.

Training on SCP259 UC donors and testing on all 71 Kong donors (UC→CD direction) produced near-chance performance across all classifiers: LogReg AUROC 0.503, XGBoost AUROC 0.465, LinearSVM AUROC 0.547. This outcome was expected: the two atlases use incompatible annotation schemes (51 Smillie-defined types versus 68 Kong-defined types), and the four overlapping types provide insufficient signal to bridge datasets in this direction.

The reverse transfer (CD→UC; train Kong n=71, test SCP259 n=30) showed meaningfully above-chance performance: XGBoost AUROC 0.833, LinearSVM AUROC 0.764, LogReg AUROC 0.741. The asymmetry is interpretable: Kong's larger training set (n=71 vs. n=30) provides more stable parameter estimates, and UC and CD share substantial immunological features — particularly myeloid and regulatory T cell dysregulation — that may be partially captured by the four shared types. The result suggests partial transferability of CD-trained composition signals to UC classification, but the low-dimensional shared feature space limits the strength of this conclusion.

Cross-dataset CFN results using GatedStructuralCFN (fanglioc/StructuralCFN-public v1.1.0, 300 epochs, CLR-transformed 4-type input) are now available. Training SCP259 and testing on Kong (UC→CD direction) yielded AUROC 0.558 (PR-AUC 0.319), consistent with the near-chance composition baseline (LinearSVM CLR AUROC 0.547) and confirming that the 4-type shared feature space does not generalize UC signatures to CD. In the CD→UC direction (train Kong, test SCP259), CFN achieved AUROC 0.755 (PR-AUC 0.885), comparable to the composition baseline LogReg result (0.741) and below XGBoost (0.833). Notably, within-dataset CV on SCP259 using only the 4 shared types yielded CFN AUROC 0.883 ± 0.071, indicating that DC1, ILCs, Macrophages, and Tregs collectively carry substantial discriminative signal for UC vs. Healthy classification — despite constituting only 4 of 51 available cell types. Within-dataset CV on Kong (4 types) yielded AUROC 0.627 ± 0.133, reflecting both the smaller per-fold feature set and the more severe class imbalance in Kong (17 CD vs. 54 Healthy donors).

---

## Table 1. Summary of within-dataset classification results (completed experiments)

| Dataset | Feature Representation | Classifier | AUROC (mean ± SD) | PR-AUC |
|---------|----------------------|------------|-------------------|--------|
| SCP259 (UC vs Healthy, n=30) | Composition 51-dim | LinearSVM | 0.928 ± 0.110 | 0.967 |
| SCP259 | Composition 51-dim | LogReg | 0.878 ± 0.217 | 0.947 |
| SCP259 | Composition 51-dim | XGBoost | 0.850 ± 0.224 | 0.941 |
| SCP259 | Compartment comp. 102-dim | LinearSVM | 0.956 ± 0.061 | 0.967 |
| SCP259 | Compartment comp. 102-dim | LogReg | 0.956 ± 0.061 | 0.967 |
| SCP259 | Compartment comp. 102-dim | XGBoost | 0.711 ± 0.227 | — |
| SCP259 | Pseudobulk HVG (top-1000) | XGBoost | 1.000 ± 0.000* | 1.000* |
| SCP259 | CFN global 51-dim | StructuralCFN | 0.906 ± 0.130 | 0.944 |
| SCP259 | CFN compartment 102-dim | StructuralCFN | 0.978 ± 0.050 | 0.983 |
| SCP259 | scVI global latent 20-dim† | LogReg | 0.706 ± 0.327 | — |
| SCP259 | scVI global latent 20-dim† | LinearSVM | 0.706 ± 0.305 | — |
| SCP259 | scVI global latent 20-dim† | XGBoost | 0.725 ± 0.399 | — |
| SCP259 | scVI compartment latent 60-dim† | LogReg | 0.900 ± 0.224 | 0.936 |
| SCP259 | scVI compartment latent 60-dim† | LinearSVM | 0.900 ± 0.224 | 0.936 |
| SCP259 | scVI compartment latent 60-dim† | XGBoost | 0.931 ± 0.101 | 0.951 |
| Kong 2023 (CD vs Healthy, n=71) | CLR comp. all regions | CatBoost | 0.840 ± 0.054 | 0.711 |
| Kong 2023 | CLR comp. all regions | ElasticNet | 0.836 ± 0.120 | 0.703 |
| Kong 2023 | CLR comp. all regions | XGBoost | 0.824 ± 0.076 | — |
| Kong 2023 | CLR comp. all regions | LogReg | 0.819 ± 0.059 | — |
| Kong 2023 | CLR comp. TI only (n=42) | CatBoost | 0.967 ± 0.075 | 0.950 |
| Kong 2023 | CLR comp. TI only (n=42) | LinearSVM | 0.917 ± 0.062 | 0.873 |
| Kong 2023 | CLR comp. TI only (n=42) | LogReg | 0.900 | — |
| Kong 2023 | CLR comp. TI only (n=42) | XGBoost | 0.900 | — |
| Kong 2023 | CLR comp. Colon only (n=34) | LinearSVM | 0.900 ± 0.100 | — |
| Kong 2023 | CLR comp. Colon only (n=34) | LogReg | 0.880 ± 0.110 | — |
| Kong 2023 | CLR comp. Colon only (n=34) | XGBoost | 0.880 | — |
| Kong 2023 | CLR comp. Colon only (n=34) | ElasticNet | 0.880 | — |
| Kong 2023 (CD vs Healthy, n=71) | CFN all regions 68-dim | GatedStructuralCFN | 0.812 ± 0.136 | 0.641 |
| Kong 2023 | CFN TI only (n=42) 61-dim | GatedStructuralCFN | 0.811 ± 0.164 | 0.733 |
| Kong 2023 | CFN Colon only (n=34) 55-dim | GatedStructuralCFN | **0.920 ± 0.084** | 0.883 |

*Likely overfit at n=30; not a reliable generalization estimate.
†Full three-compartment scVI (Epi+Fib+Imm), 300 cells/donor subsampled, 3,000 HVGs, negative binomial likelihood, 20-dim latent, 2-layer encoder. Global: donor mean latent across all cells (20-dim). Compartment: per-compartment donor mean latent concatenated (60-dim total, 20 per compartment). Trained on CPU with early stopping (terminated epoch 111/150).

## Table 2. Cross-dataset generalization (4 shared cell types: DC1, ILCs, Macrophages, Tregs)

| Direction | Train | Test | Classifier | AUROC |
|-----------|-------|------|------------|-------|
| UC → CD | SCP259 (n=30) | Kong (n=71) | LogReg | 0.503 |
| UC → CD | SCP259 (n=30) | Kong (n=71) | LinearSVM | 0.547 |
| UC → CD | SCP259 (n=30) | Kong (n=71) | XGBoost | 0.465 |
| CD → UC | Kong (n=71) | SCP259 (n=30) | XGBoost | 0.833 |
| CD → UC | Kong (n=71) | SCP259 (n=30) | LinearSVM | 0.764 |
| CD → UC | Kong (n=71) | SCP259 (n=30) | LogReg | 0.741 |
| SCP259 within-CV (4 types) | SCP259 (n=30) | — | GatedStructuralCFN | 0.883 ± 0.071 |
| Kong within-CV (4 types) | Kong (n=71) | — | GatedStructuralCFN | 0.627 ± 0.133 |
| UC → CD (CFN 4-types) | SCP259 (n=30) | Kong (n=71) | GatedStructuralCFN | 0.558 |
| CD → UC (CFN 4-types) | Kong (n=71) | SCP259 (n=30) | GatedStructuralCFN | 0.755 |

## Table 3. CFN edge stability (SCP259, 5-fold CV)

| CFN Configuration | Input Dim | Stability Metric | Value |
|-------------------|-----------|-----------------|-------|
| Global CFN | 51 | Top-10 edge Jaccard (across folds) | 0.026 |
| Compartment CFN | 102 | Top-20 edge fold recurrence | 1.000 |
| Compartment CFN | 102 | Top-20 edge sign consistency | 1.000 |
