# Methods

## 2.1 Datasets

### SCP259 (Smillie et al. 2019 — UC vs Healthy)

Single-cell RNA-seq data were obtained from the Broad Single Cell Portal study SCP259 (Smillie et al., *Cell* 2019). The dataset comprises colonic biopsy specimens from 18 ulcerative colitis (UC) patients and 12 healthy controls (n=30 donors total). Raw count matrices were provided as gene_sorted MTX files separated by tissue compartment: epithelial (Epi), fibroblast/stromal (Fib), and immune (Imm). Gene-sorted format retains only the most highly expressed genes per cell; coverage varies by compartment (Fib: 19,076 genes, complete; Epi and Imm: 20,028 and 20,529 genes declared but partially filled). Cell type annotations (51 types) and donor metadata were obtained from the accompanying `all.meta2.txt` file.

Donor-level cell type composition was computed by counting cells per cluster per donor, then normalizing to proportions (cell fractions summing to 1 per donor). Separate composition tables were constructed for the combined dataset (51 types) and for each tissue compartment independently (epithelial, fibroblast, immune; the union of within-compartment cell types was used for the compartment-stratified 102-dimensional representation). Five-fold cross-validation splits were stratified by disease status and fixed before any model training.

### Kong et al. 2023 (CD vs Healthy)

Single-cell RNA-seq data were obtained from Kong et al. (*Nature Genetics* 2023), accessed via NCBI GEO (GSE202021). The dataset comprises intestinal biopsy specimens from 17 Crohn's disease (CD) patients and 54 healthy controls (n=71 donors). Data were distributed as six H5AD files corresponding to distinct cell lineage and biopsy site combinations. Cell metadata (obs) were extracted from each H5AD file in backed/read-only mode to avoid loading full count matrices, and saved as parquet files. Donor-level composition tables were built from the obs cache, yielding three region-stratified tables: all regions combined (71 donors, 68 cell types), terminal ileum only (42 donors, 61 cell types), and colon only (34 donors, 55 cell types). Five-fold cross-validation splits were stratified by disease status per region.

---

## 2.2 Feature representations

### 2.2.1 Raw cell type composition

The primary feature for donor-level classification is the vector of cell type proportions. Let \(c_{d,k}\) denote the number of cells of type \(k\) in donor \(d\), and \(N_d = \sum_k c_{d,k}\) the total cell count. The composition feature is \(p_{d,k} = c_{d,k} / N_d\), producing a K-dimensional proportion vector for each donor.

### 2.2.2 Centered log-ratio (CLR) transformation

Cell type composition vectors lie in the simplex \(\Delta^{K-1}\) and are subject to the unit-sum constraint, which renders Euclidean-geometry classifiers (logistic regression, SVM, elastic net) statistically invalid without transformation. We applied the centered log-ratio (CLR) transform (Aitchison 1982):

\[ \text{CLR}(p)_k = \log\left(\frac{p_k}{\left(\prod_{j=1}^{K} p_j\right)^{1/K}}\right) = \log(p_k) - \frac{1}{K}\sum_{j=1}^{K} \log(p_j) \]

A pseudocount proportional to the inverse of the number of cell types was added before log transformation to handle zero entries: \(p_k \leftarrow p_k + 0.5/K\). CLR was applied within each training fold using training-set statistics only (fit on train, transform train and test separately) to prevent label leakage from test donors' composition into the CLR normalization step.

### 2.2.3 Compartment-stratified composition

For SCP259, we additionally constructed a 102-dimensional feature vector by computing the within-compartment cell type proportions separately for the epithelial, fibroblast, and immune compartments, then concatenating the three compartment proportion vectors. This representation preserves the relative cell type frequencies within each compartment independently, avoiding confounding from cross-compartment variation in total cell yield. For Kong 2023, CLR was applied to the full 68-/61-/55-dimensional composition vector without compartment stratification, as the dataset annotation does not separate compartment-level cell types comparably.

---

## 2.3 Baseline classifiers

All baseline classifiers were evaluated in a standard 5-fold stratified cross-validation framework. Folds were generated once per dataset using `sklearn.model_selection.StratifiedKFold` (shuffle=True, random_state=42) and fixed for all subsequent evaluations on that dataset to ensure direct comparability across methods. Performance was measured by AUROC (primary metric) and PR-AUC (secondary).

### Logistic Regression (LogReg)

`sklearn.linear_model.LogisticRegression`, L2 penalty, solver='lbfgs', max_iter=5000, random_state=42.

### Linear SVM (LinearSVM)

`sklearn.svm.SVC`, kernel='linear', probability=True (Platt scaling for AUROC), random_state=42.

### XGBoost

`xgboost.XGBClassifier`, n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, eval_metric='auc', tree_method='hist', n_jobs=1, random_state=42.

### ElasticNet logistic regression

`sklearn.linear_model.LogisticRegression`, penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=10,000, random_state=42. This regularization profile (equal L1/L2 weighting) was selected for its ability to handle the correlated composition features that arise when multiple cell types within a lineage shift together in disease.

### CatBoost

`catboost.CatBoostClassifier`, iterations=300, depth=4, learning_rate=0.05, eval_metric='AUC', random_seed=42, verbose=0. CatBoost uses ordered boosting, which reduces overfitting on small training sets relative to standard gradient boosting.

---

## 2.4 scVI latent representation

We trained a variational autoencoder (VAI) using the scVI framework (Lopez et al., *Nature Methods* 2018) on the SCP259 dataset. Raw count matrices for all three tissue compartments (Epi, Fib, Imm) were loaded using a custom tolerant MTX parser that handles the gene_sorted partial-fill format (pandas-based, `on_bad_lines='skip'`). Cells were subsampled to 300 per donor per compartment family before model training to reduce memory requirements on CPU hardware; across 30 donors and 3 families this yielded 9,000 cells total.

Preprocessing followed the standard scVI pipeline. Highly variable gene (HVG) selection was attempted using the seurat_v3 flavor (scanpy ≥ 1.9); when seurat_v3 failed due to near-singular LOESS fitting on the sparse Imm gene_sorted matrices, the cell_ranger flavor was used. When cell_ranger failed due to duplicate bin edges in the mean-expression percentile binning (a known issue with very sparse data), HVG selection was retried without a batch key. In practice, cell_ranger without batch key succeeded and retained 3,000 HVGs. The raw count layer was normalized to 10,000 counts per cell and log1p-transformed for HVG scoring; raw counts were retained in a separate layer for scVI training.

The scVI model was configured with:

- Latent dimensionality: 20
- Encoder: 2 fully connected layers, 128 hidden units per layer
- Gene likelihood: negative binomial (standard for UMI count data)
- Batch key: donor identity (to correct for donor-level technical variation)
- Training: up to 150 epochs, Adam optimizer, learning rate 1 × 10⁻³, early stopping with patience 45 epochs on ELBO validation loss; training terminated at epoch 111
- Random seed: 42

After training, donor-level latent representations were extracted using `scvi.model.SCVI.get_latent_representation()`. Two representations were derived:

1. **Global latent (20-dim):** mean latent vector averaged across all cells per donor, regardless of compartment.
2. **Compartment-stratified latent (60-dim):** per-compartment mean latent vectors computed separately for each of the three families (Epi, Fib, Imm), then concatenated into a single 60-dimensional donor feature vector. This representation is structurally analogous to the compartment-stratified composition feature (Section 2.2.3).

Both representations were evaluated using the same 5-fold CV framework and classifier suite as the composition baselines.

---

## 2.5 GatedStructuralCFN

Causal factor network (CFN) analysis was performed using GatedStructuralCFN, the publicly available implementation from fanglioc/StructuralCFN-public (v1.1.0, MIT License; https://github.com/fanglioc/StructuralCFN-public), installed via pip. The model infers a directed dependency matrix over input features and produces a scalar prediction for each sample.

**Model instantiation.** The model was initialized with:

```python
from scfn import GatedStructuralCFN
model = GatedStructuralCFN(input_dim=K, classification=False)
```

The `classification=False` flag sets the output activation to sigmoid and the training loss to mean squared error (MSE). This setting was used in preference to `classification=True` because the public v1.1.0 implementation applies CrossEntropyLoss on a scalar sigmoid output when classification=True, producing a runtime error. With classification=False, the raw sigmoid output is monotonically related to class probability, so AUROC — which depends only on rank ordering — is identical to what a properly configured classification loss would produce.

**Training.** The model was trained using the built-in `.fit()` method:

```python
model.fit(
    X_train, y_train.astype(np.float32),
    epochs=300,
    lr=0.01,
    batch_size=16,      # Kong CFN; 8 for cross-dataset CFN (smaller training sets)
    verbose=False,
)
```

CLR transformation was applied to the input composition features before fitting (see Section 2.2.2); CLR was computed from training-set statistics and applied separately to train and test splits to prevent leakage.

**Inference.** Test-set scores for AUROC computation were extracted as:

```python
model.eval()
with torch.no_grad():
    scores = model(torch.FloatTensor(X_test)).squeeze().cpu().numpy()
```

The raw scalar output was used directly for AUROC computation.

**Dependency matrix extraction.** After training, the inferred cell-type co-dependency matrix was extracted via `model.get_dependency_matrix()`, returning a K × K numpy array. Dependency matrices were saved per fold and averaged across folds for visualization. Edge stability was quantified as the Jaccard similarity of the top-k edge sets across folds, and the fold recurrence rate and sign consistency of the top-ranked edges.

**Cross-validation setup.** For within-dataset evaluation, the same 5-fold stratified splits used for baseline classifiers were applied. For each fold, the model was trained on the training donors and evaluated on the held-out test donors; AUROC and PR-AUC were recorded per fold and summarized as mean ± SD.

**SCP259.** CFN was evaluated on two input representations: the 51-dimensional global composition and the 102-dimensional compartment-stratified composition. Batch size was set to 16. Hyperparameters (n_epochs, lr, batch_size) were not tuned; all values were fixed before any CFN training run.

**Kong 2023.** CFN was evaluated on each of the three region-stratified datasets (all regions 68-dim, TI 61-dim, colon 55-dim). Batch size was 16. CLR was applied with pseudocount ε = 10⁻⁶ at the numpy level for the Kong runs (differing from the pandas-level pseudocount used for SCP259 composition baselines; both approaches produce equivalent CLR outputs for non-zero entries).

---

## 2.6 Cross-dataset transfer evaluation

To assess generalizability of the learned disease signatures across datasets and disease contexts (UC and CD), we performed cross-dataset transfer experiments using the four cell types with compatible annotations across both atlases: DC1, ILCs, Macrophages, and Tregs. These were the only cell type names present in both the SCP259 (51-type) and Kong 2023 (68-type) composition tables after exact string matching.

**Composition baselines (CLR).** For cross-dataset composition transfer, the training dataset composition table was subsetted to the four shared cell types, CLR-transformed (pseudocount 0.5/K, K=4), and used to train a LogReg, LinearSVM, and XGBoost classifier. The test dataset composition table was subsetted to the same four types, CLR-transformed using test-set statistics, and passed to the trained classifier. Zero-filling was used for any shared cell type absent in a test donor. Two transfer directions were evaluated: UC→CD (train on SCP259 n=30, test on Kong n=71) and CD→UC (train on Kong n=71, test on SCP259 n=30).

**CFN transfer.** Cross-dataset CFN evaluation followed the same protocol: the GatedStructuralCFN model (input_dim=4, classification=False) was trained on the full training dataset (no held-out fold; the full dataset was used as training data for the cross-dataset direction) and evaluated on the full test dataset. Parameters: 300 epochs, lr=0.01, batch_size=8, CLR applied with ε = 10⁻⁶. For AUROC computation, raw sigmoid outputs from the test set were used.

**Within-dataset CV on the 4-type subset.** To establish a within-dataset reference using only the four shared cell types, we also ran 5-fold CV using GatedStructuralCFN on the 4-type subset of each dataset independently (using the same fixed fold splits as the full composition evaluations). This quantifies the discriminative content of the four shared types within each disease context, decoupled from the transfer direction.

---

## 2.7 Evaluation metrics

**AUROC** (area under the receiver operating characteristic curve) was the primary performance metric throughout. AUROC is threshold-independent and robust to class imbalance, making it appropriate for both the SCP259 (UC 18/12 imbalance, moderate) and Kong 2023 (CD 17/54 imbalance, severe) datasets.

**PR-AUC** (area under the precision-recall curve) was reported as a secondary metric. PR-AUC is sensitive to class imbalance in the positive-class direction and provides complementary information about classifier precision at different recall thresholds. It was not available for all cross-dataset experiments where single-point predictions (no fold replication) were produced.

**Bootstrap confidence intervals.** For SCP259 composition baselines, donor-level bootstrap confidence intervals (N=2,000 resamples with replacement; stratified by disease label) were computed on pooled predictions across the four feature representations. These CIs reflect uncertainty in AUROC estimation under resampling of the donor pool and are reported alongside cross-validated fold means.

All code implementing the above procedures is available in the accompanying GitHub repository (https://github.com/Jonathan-321/sfn-scrna-study).
