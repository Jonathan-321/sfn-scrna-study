# Peer Reviewer Simulation Critique

**Paper:** "Donor-Level Classification of Inflammatory Bowel Disease from Single-Cell RNA-seq: A Benchmark of Composition, Causal Factor Networks, and Variational Autoencoders"  
**Author:** Jonathan Muhire, Oklahoma Christian University  
**Critique prepared for:** Pre-submission internal review  

---

## 1. Sample Size and Statistical Power

### 1.1 Is n=30 for SCP259 defensible for the claims made?

**Problem:** The SCP259 cohort contains 30 donors (UC vs. Healthy). The best reported AUC is 0.978±0.050 (compartment CFN). With a standard deviation of ±0.050 across 5 folds, each fold is evaluated on approximately 6 donors. A binary classifier assessed on 6 test donors has an inherently coarse resolution: each individual donor contributes roughly 1/6 (~17 percentage points) of the fold-level AUC. The reported confidence is therefore as much a product of lucky fold composition as of genuine model performance.

**Why it matters to a reviewer:** Bioinformatics and PLOS CB both expect authors to confront statistical power explicitly. At n=30 with a 5-fold split, each test fold is evaluating on ~6 samples — far below what is needed to obtain AUC estimates with standard errors smaller than ~0.10. The ±0.050 SD reported here is suspiciously small and may reflect low fold-to-fold variance rather than genuine precision. A power analysis (even a retrospective bootstrapped one) is entirely absent. A reviewer will ask: what is the minimum detectable effect at this sample size, and are the observed inter-method differences (e.g., 0.956 vs. 0.978) meaningful?

**Addressability:** Can be partially addressed with existing data by running a bootstrap confidence interval analysis (1,000 bootstrap resamples of donors) or computing DeLong's test for AUC comparison between CLR-SVM and CFN on SCP259. Requires a caveat/limitation statement at minimum.

---

### 1.2 Is n=34 colon donors (Kong) sufficient to claim CFN is "best single-region result"?

**Problem:** The Kong colon subset involves approximately 34 donors (derived from n=71 total, split across three regions). Claiming CFN achieves the "best single-region result across all methods in this study" (0.960±0.055) based on 34 donors, where each test fold contains ~7 donors, is statistically fragile. The claim is a superlative ("best") asserted without any significance testing.

**Why it matters to a reviewer:** Superlative claims require statistical support. The confidence intervals for CFN colon (±0.055) and CLR unfiltered colon (±0.084) overlap substantially. Without a paired permutation test or Wilcoxon signed-rank test on the fold-level AUCs, there is no basis for asserting one method is definitively superior. This is a straightforward flag that any experienced computational reviewer will raise on page 1 of their review.

**Addressability:** Fully addressable with existing data. The 5 fold-level AUC values for each method are already computed; a Wilcoxon signed-rank test (or paired t-test with appropriate normality caveat) takes 3 lines of code. If the test is non-significant, the claim must be softened to "numerically higher."

---

### 1.3 Are the large standard deviations (±0.295 for colon CLR, ±0.399 for global scVI) addressed properly?

**Problem:** The global scVI XGBoost result for SCP259 is 0.725±0.399. A standard deviation of ±0.399 on an AUC that ranges [0, 1] means the confidence interval spans nearly the entire range of possible AUC values — the model is effectively performing at chance in some folds and near-perfectly in others. Similarly, CLR CatBoost for Kong colon filtered achieves 0.820±0.295. These extreme variances indicate either (a) severe sensitivity to fold composition, (b) a degenerate model in certain folds, or (c) possible fold-level label imbalance. The paper does not investigate which.

**Why it matters to a reviewer:** A result with ±0.399 SD cannot form the basis of any scientific conclusion. Reporting it without explicit investigation of what went wrong in the high-variance folds is a red flag. Are some folds severely class-imbalanced? Does XGBoost collapse to majority-class prediction on certain folds? The paper appears to present this result as a data point in a table without interrogating it. Reviewers at any serious journal will ask for fold-level AUC breakdowns, confusion matrices, and an explanation.

**Addressability:** Requires new analysis of fold-level outputs (fold-by-fold AUC tables, class balance per fold). This analysis requires no new experiments — the outputs should already exist from the CV runs. Requires a limitation statement if the variance cannot be explained.

---

### 1.4 Is 5-fold CV on n=30 enough? Are folds of ~6 donors each reliable?

**Problem:** With n=30 donors in a binary classification task and donor-stratified 5-fold CV, each test fold contains exactly 6 donors. For a binary task, 6 donors yields a maximum of 7 distinguishable AUC values (0, 1/6, 2/6, ..., 6/6 for a rank-based metric). This severely quantizes the AUC distribution and makes fold-level standard deviation estimates unreliable.

**Why it matters to a reviewer:** The paper presents inter-method AUC differences on the order of 0.02–0.05 (e.g., 0.956 vs. 0.978 on SCP259). These differences are smaller than the resolution achievable in a single 6-donor test fold. The comparison is therefore at the edge of statistical resolution. Leave-one-out CV (LOOCV) would be more appropriate at this sample size, or at minimum, repeated k-fold (e.g., 10 × 5-fold) to obtain stable variance estimates. The absence of repeated CV is a meaningful methodological gap.

**Addressability:** Requires a new experiment (repeated 5-fold CV or LOOCV) or a limitation statement explaining why 5-fold was chosen and acknowledging the coarse AUC resolution.

---

## 2. The CFN classification=False Bug

### 2.1 Is the bug adequately disclosed?

**Problem:** The CFN model is run with `classification=False`, which routes it through MSELoss with a sigmoid output rather than CrossEntropyLoss. This occurs because `classification=True` triggers a runtime error in GatedStructuralCFN v1.1.0. The paper notes this is a "known bug," but the severity of the methodological deviation is not fully characterized. The model is nominally a regression model (predicting a continuous score in [0,1]) being evaluated as a classifier via AUROC.

**Why it matters to a reviewer:** This is not a minor implementation detail — it is a fundamental change in the loss function and therefore in what the model is trained to optimize. MSELoss minimizes squared error between the sigmoid output and {0, 1} labels, while CrossEntropyLoss maximizes the log-likelihood of the correct class. These are not equivalent objectives. The paper must demonstrate, not assert, that AUROC-based evaluation is equally valid under MSELoss. At minimum, the author should show that the sigmoid outputs are not saturated (i.e., that predictions cluster away from 0 and 1 extremes) and that the ranking of samples is meaningful.

**Addressability:** Partially addressable with existing data by reporting the distribution of sigmoid output scores (histograms of predicted probabilities) to show they are not degenerate. The author should also add a clear limitation statement and, ideally, patch the v1.1.0 bug and rerun with `classification=True` for at least one cohort as a sanity check. If the bug cannot be patched, the method should be described explicitly as "CFN with regression objective" throughout the paper, not simply as "CFN."

---

### 2.2 Does the MSELoss objective introduce bias?

**Problem:** MSELoss treats misclassifications symmetrically in squared error space. For imbalanced classes (unequal numbers of UC/healthy or CD/healthy donors), this introduces implicit bias toward the majority class — exactly the same problem that motivates the use of weighted CrossEntropyLoss or balanced sampling in imbalanced classification settings. The class balance across folds is not reported.

**Why it matters to a reviewer:** If the Kong colon dataset has imbalanced classes across certain folds, MSELoss could produce a degenerate model that is nonetheless rank-ordered usefully (explaining the high AUROC), while a properly specified CrossEntropyLoss would perform better still. This means CFN's reported AUROC may be a lower bound on its true capability under the correct loss. Alternatively, if the imbalance is severe and MSELoss causes the sigmoid to saturate toward one class, AUROC could be inflated if a minority of extreme predictions dominate the rank ordering.

**Addressability:** Requires a caveat/limitation statement. Can partially be addressed with existing data by reporting class balance per fold and the distribution of sigmoid outputs.

---

### 2.3 Is AUROC truly rank-invariant under MSELoss/sigmoid saturation?

**Problem:** AUROC is rank-invariant under monotone transformations of the score, but sigmoid saturation can collapse a range of scores to near 0 or near 1, effectively destroying rank information for samples in the saturated region. If a subset of donors receive near-identical sigmoid scores (e.g., all healthy controls collapse to ~0.02), the inter-donor ranking within that group is essentially random, which degrades AUROC.

**Why it matters to a reviewer:** The paper implicitly assumes that MSELoss+sigmoid produces a useful ranking. This assumption needs empirical validation via a score distribution plot. If the sigmoid outputs are well-spread across [0,1], the concern is mitigated. If they are bimodal with near-degenerate tails, the AUROC is artificially inflated by the separation of the two modes rather than by fine-grained within-group discrimination.

**Addressability:** Fully addressable with existing data by plotting the sigmoid output distributions per class and per cohort. No new experiments required.

---

## 3. Comparison Fairness

### 3.1 Were CFN hyperparameters tuned, and if so, was tuning done on the full dataset?

**Problem:** CFN is configured with 300 epochs, lr=0.01, batch_size=16. It is not stated whether these hyperparameters were selected via a systematic search or chosen ad hoc. If they were tuned by observing CV performance on the datasets used in the benchmark, this constitutes a form of data leakage that advantages CFN over the linear baselines, whose hyperparameters appear to be fixed defaults.

**Why it matters to a reviewer:** This is a classical benchmarking fairness concern. Any reviewer with experience in ML-based bioinformatics benchmarks will ask whether all methods were given equal opportunity for hyperparameter optimization, and whether the optimization procedure was itself held out from the evaluation data. The paper must either (a) state explicitly that CFN hyperparameters were chosen without reference to benchmark performance (e.g., borrowed from a prior study), (b) report a nested cross-validation procedure where hyperparameter selection occurred inside each fold, or (c) acknowledge that CFN may have a hyperparameter advantage.

**Addressability:** Requires a caveat/limitation statement if tuning was informal, or requires nested CV as a new experiment if rigorous fairness is needed.

---

### 3.2 Linear baselines: were any hyperparameters tuned?

**Problem:** LinearSVM, CatBoost, and XGBoost are described without specifying whether they use default hyperparameters or tuned ones. For XGBoost and CatBoost in particular, defaults differ substantially across library versions and can have large effects on performance — especially for datasets with fewer than 50 samples.

**Why it matters to a reviewer:** If the linear/tree baselines use library defaults while CFN was hand-tuned, CFN has a structural advantage. Conversely, if the baselines were also tuned (even informally, by trying a few settings), this should be reported. The benchmark's validity rests on methodological parity.

**Addressability:** Requires a disclosure statement. If defaults were used throughout, state so. If any tuning was done, describe the procedure and where in the CV loop it occurred.

---

### 3.3 "Best model per region" reporting — is cherry-picking a concern?

**Problem:** The paper reports the best-performing method per region (e.g., "CatBoost CLR 0.967 for TI"). Selecting the best result from a set of methods and reporting it as the headline number without correction for multiple comparisons is a form of winner's curse. With three regions × multiple methods × three feature representations, the expected maximum AUC across all configurations will be inflated relative to any single pre-specified method.

**Why it matters to a reviewer:** This is a well-known problem in computational biology benchmarks. Without Bonferroni correction or a pre-registered analysis plan, the headline numbers are optimistically biased. A reviewer will note that if 15 method/feature/region combinations are evaluated and the best is reported, the expected inflation of the maximum depends on the correlation structure of methods — but it is rarely zero.

**Addressability:** Requires a caveat/limitation statement. A pre-specified primary analysis (e.g., "CLR with LinearSVM is our primary baseline; CFN and scVI are secondary") would have sidestepped this. At this stage, the author can add a Bonferroni-adjusted discussion or report all results in a table with the understanding that no single configuration is selected post hoc as the primary claim.

---

## 4. scVI Design Choices

### 4.1 scVI trained on the full dataset — data leakage in cross-validation?

**Problem:** This is the most serious methodological flaw in the scVI evaluation. The scVI model is trained on all 30 (or 71) donors simultaneously, using donor as the batch key, before the cross-validation loop is run. The latent embeddings for each donor are then used as features in the downstream CV. This means the scVI encoder has seen all donors — including test-fold donors — during its own training. The latent representation of a test-fold donor is therefore influenced by all other donors in the dataset, including training-fold donors it will be compared against in the CV evaluation. This is textbook data leakage.

**Why it matters to a reviewer:** Data leakage in representation learning is a well-documented problem in single-cell ML papers and is a near-automatic rejection trigger at journals like Nature Methods, Bioinformatics, or Cell Systems. The correct procedure is to train a separate scVI model for each of the 5 folds using only training-fold donors, then embed the held-out test-fold donors using the trained encoder. The current procedure means the reported AUC for scVI cannot be trusted as a measure of out-of-sample performance.

**Addressability:** Requires a new experiment — full re-implementation of the scVI evaluation within each CV fold. This is computationally feasible (5 scVI runs per cohort) but will require rewriting the evaluation pipeline. If the authors cannot rerun the experiments, the scVI results must be explicitly labelled as "approximate in-sample estimates" and excluded from direct comparison with the properly cross-validated CLR and CFN results.

---

### 4.2 300 cells/donor subsampling variance and seed fixing

**Problem:** The paper uses 300 cells per donor as input to scVI. This subsampling introduces stochastic variance at two levels: (a) which 300 cells are drawn, affecting the input data distribution, and (b) the scVI training objective (ELBO) is stochastic via the reparameterization trick. It is not stated whether the subsampling step was performed with a fixed random seed across runs.

**Why it matters to a reviewer:** If the subsampling seed is not fixed, re-running the scVI analysis will produce different latent embeddings and potentially different AUCs. This makes the result non-reproducible at the most basic level. Furthermore, the stochastic variance from subsampling should be quantified — e.g., by running the subsampling 3–5 times with different seeds and reporting the resulting AUC variance. Without this, the ±0.101 SD reported for compartment scVI XGBoost may conflate fold-composition variance with subsampling variance.

**Addressability:** Requires a disclosure statement (were seeds fixed?) and a new experiment (multiple subsampling runs) to quantify subsampling-induced variance. The computational cost is modest.

---

### 4.3 Global vs. compartment scVI gap — fair comparison?

**Problem:** Global scVI uses a 20-dimensional latent space applied to all cell types simultaneously, yielding a 20-dimensional feature vector per donor. Compartment scVI presumably uses a 20-dimensional latent space per compartment, producing a 60-dimensional feature vector (3 compartments × 20 dimensions) for a three-compartment dataset. The gap between global (0.725±0.399) and compartment (0.931±0.101) scVI AUC is attributed to biological signal partitioning, but the confounding factor of latent dimensionality (20-dim vs. 60-dim) is not controlled.

**Why it matters to a reviewer:** A reviewer cannot determine whether the compartment advantage reflects biology or simply a more expressive feature space. A fair comparison would use global scVI with 60-dim latent (matching the compartment total) and compartment scVI with 6-7 dim per compartment (matching the global total). Alternatively, the paper should at minimum acknowledge this confound explicitly.

**Addressability:** Requires a new experiment (rerun global scVI at 60-dim and/or compartment scVI at 6-dim) or a caveat/limitation statement acknowledging the confound.

---

## 5. Feature Engineering Methodology

### 5.1 Variance threshold computed on the full dataset

**Problem:** The variance threshold filter (std < 0.005) removes cell-type composition features with low variance. If this threshold was computed on the full dataset (all donors combined) before splitting into CV folds, it constitutes a mild data leakage: the identity of which features are "low variance" is informed by the variance structure of the held-out test donors.

**Why it matters to a reviewer:** This is a subtle but real form of data leakage. In a properly implemented pipeline, all preprocessing decisions — including feature selection — must be made using only training-fold data and then applied (without re-estimation) to test-fold data. If the variance filter removes features that, in isolation, carry test-fold-specific signal, the resulting feature set is optimistic. The concern is compounded if the threshold of 0.005 was itself chosen by observing its effect on CV performance.

**Addressability:** Requires a clarification statement. If the filter was applied globally before CV, it should be moved inside the CV loop and results should be re-reported. If the effect is small (i.e., the same features would be removed in each fold regardless), the author can demonstrate this empirically by showing that the removed features are near-zero variance in every individual fold.

---

### 5.2 Rare-type filter (prevalence < 20%) applied globally before fold splitting

**Problem:** The rare-type filter removes cell types present in fewer than 20% of donors. Like the variance threshold, if this filter is computed on the full donor set before CV splitting, it leaks information from held-out test donors. A cell type that is rare in the test fold but common in training folds (or vice versa) would be treated differently under a within-fold vs. full-dataset filter.

**Why it matters to a reviewer:** At n=30, a 20% threshold means a cell type must be present in at least 6 donors to be retained. If one of those 6 donors falls in the test fold, the global filter would retain that cell type, but a within-fold filter (applied to 24 training donors) would require only 5/24 = ~21% prevalence — a similar threshold. In practice, the leakage from this filter is likely small, but it is non-zero and should be acknowledged. The author should state explicitly where in the pipeline the filter is applied.

**Addressability:** Requires a clarification/limitation statement. Rerunning with the filter inside the CV loop would be ideal but likely has minimal effect at this sample size.

---

### 5.3 TI CLR drop after filtering (0.967→0.917, -0.050) — "some signal resided in low-variance types"

**Problem:** The paper acknowledges a 5-percentage-point AUC drop in TI CLR after applying the variance/prevalence filter but attributes it to "some signal residing in low-variance types" without further investigation. Which specific cell types were removed? Were they biologically meaningful (e.g., rare innate immune subtypes in TI)? Is the drop consistent across folds or driven by one bad fold?

**Why it matters to a reviewer:** A 5-point AUROC drop is not trivial, especially on a dataset where the maximum achievable AUC may already be near ceiling. The fact that low-variance features carry discriminative information is itself a biologically interesting finding that deserves follow-up: it implies that rare or consistently low-abundance cell types shift in IBD. Dismissing this with a one-sentence observation is a missed opportunity and an intellectual gap that a careful reviewer will flag.

**Addressability:** Fully addressable with existing data by listing the removed cell types, computing their individual AUROCs (donor-level), and reporting which contributed most to the lost performance. No new experiments required.

---

## 6. Cross-Dataset Transfer Methodology

### 6.1 No held-out fold — single point estimate with no uncertainty

**Problem:** The cross-dataset transfer experiment trains on the full source dataset (e.g., all SCP259 donors for CD→UC direction) and tests on the full target dataset. There is no held-out fold, no bootstrapping, and no repeated sampling. The reported AUCs (0.833 for CD→UC; 0.503–0.558 for UC→CD) are therefore single point estimates with unknown variance.

**Why it matters to a reviewer:** A single AUC estimate has no associated uncertainty. We cannot determine whether 0.833 is significantly above chance without knowing its variance. With only 4 shared cell types (DC1, ILCs, Macrophages, Tregs), the feature vector is extremely sparse, and the result is highly sensitive to donor-level outliers in the test set. A bootstrap procedure (resample test donors with replacement, 1,000 iterations) would provide a 95% CI at minimal computational cost. Without it, the CD→UC=0.833 result is anecdotal.

**Addressability:** Fully addressable with existing data using bootstrapped confidence intervals. Takes ~10 lines of code and requires no new experiments.

---

### 6.2 Only 4 shared cell types — is transfer generalizable?

**Problem:** The cross-dataset transfer relies on only 4 cell types shared between the two datasets: DC1, ILCs, Macrophages, and Tregs. The feature vector for transfer is therefore 4-dimensional (or 4 CLR values). It is not established whether the 0.833 AUC is driven equally by all four types or dominated by a single type. If, for example, Macrophage composition alone drives the result, the "transfer" claim is misleading — it would be more accurately described as "a single cell-type proportion predicts disease across cohorts."

**Why it matters to a reviewer:** Cross-dataset generalizability is one of the most important claims a computational biology paper can make. If it rests on 4 features derived from a handful of donors, reviewers will require ablation analysis (leave-one-cell-type-out) to establish which types are necessary and which are redundant. The asymmetry (CD→UC=0.833 vs. UC→CD≈0.503) also demands explanation: is this a disease-direction effect (CD is more compositionally extreme than UC?), a donor-number effect (training on 71 vs. 30), or a technical batch effect?

**Addressability:** Requires new analysis (leave-one-out ablation of the 4 shared types) using existing data. Requires a caveat/limitation statement about the asymmetry if the ablation cannot fully explain it.

---

## 7. Claims About Biology

### 7.1 CFN colon advantage attributed to "co-dependent composition remodeling" — post-hoc?

**Problem:** The paper attributes CFN's superior performance in the colon (relative to CLR) to its ability to capture co-dependent composition remodeling via dependency matrices. However, it is not demonstrated that the CFN dependency matrices actually identify biologically coherent co-dependencies. The Jaccard similarity of CFN edges across CV folds is 0.026 (global) and described as having "top-20 recurrence 1.0" for compartment edges. This discrepancy — unstable global edges but stable compartment edges — is not fully reconciled with the biological claim.

**Why it matters to a reviewer:** A global Jaccard of 0.026 means that less than 3% of inferred edges are shared across CV folds. This is effectively zero reproducibility. If the CFN network structure is so unstable that only the top-20 edges recur, the biological attribution of performance to "co-dependent remodeling" cannot be validated from the network topology. The result could simply reflect CFN's architectural ability to fit a nonlinear decision boundary, not its sensitivity to co-dependencies. This is a significant overclaim.

**Addressability:** Requires a new analysis demonstrating that (a) the top-20 recurrent compartment edges correspond to known IBD biology and (b) performance drops meaningfully when those edges are masked. If this analysis cannot be done, the biological attribution must be removed or heavily qualified as speculative.

---

### 7.2 TI "monotone shifts" — cited or asserted?

**Problem:** The paper states that TI shows "monotone shifts" in cell-type composition in IBD. This is presented as an explanatory claim for why simpler methods (CLR LinearSVM) perform well in TI. It is unclear whether this is (a) a finding of the current study (in which case it needs statistical support, e.g., a correlation analysis of composition with disease label), (b) a citation from prior IBD literature, or (c) an intuition.

**Why it matters to a reviewer:** Biological assertions that explain computational results must be either rigorously demonstrated in the paper or appropriately cited. Presenting an unexplained mechanistic assertion to rationalize a result is circular reasoning if not supported independently. A reviewer will request either a citation (e.g., to Smillie et al. 2019, Kong et al. 2023, or similar IBD sc-RNA studies) or a within-paper quantitative demonstration.

**Addressability:** Addressable with existing data by computing rank correlations (Spearman) between individual cell-type CLR values and disease status across TI donors. If the correlation is strong and monotone, this supports the claim. Alternatively, cite the primary literature.

---

### 7.3 DC/Treg phenotype differences between UC and CD under identical annotation labels

**Problem:** The paper claims that DC and Treg phenotypes differ between UC and CD "even under identical annotation labels." This claim is used to explain the asymmetry in cross-dataset transfer. However, the paper does not present any gene-expression-level evidence for this (e.g., DE analysis of DCs between UC and CD under the same label). The claim is made based on transfer performance alone — circular reasoning.

**Why it matters to a reviewer:** Using classification failure as evidence for biological divergence, without independent gene-expression evidence, is logically circular: the model fails to transfer, therefore the biology must differ. This may be true, but alternative explanations (batch effects between cohorts, different cell isolation protocols, different healthy control selection criteria) are not excluded. At PLOS CB, this would require either a citation, a DE analysis, or explicit acknowledgment that the transfer failure has multiple possible explanations.

**Addressability:** Requires a caveat/limitation statement acknowledging alternative explanations (batch effects, protocol differences). Can partially be addressed with existing data if scVI latent spaces are compared across cohorts for shared cell types using UMAP plots or centroid distances.

---

## 8. Missing Baselines and Comparisons

### 8.1 No permuted-label random baseline

**Problem:** No permuted-label control is reported. A permuted-label baseline (shuffle donor labels, run the full pipeline, report AUC) serves two functions: (a) it confirms the pipeline is not trivially overfitting due to data leakage (a permuted-label model should achieve AUC≈0.5), and (b) it provides the empirical null distribution for significance testing. Its absence is notable.

**Why it matters to a reviewer:** Given the concerns about data leakage identified in sections 4.1 and 5.1–5.2, a permuted-label baseline is not just a courtesy — it is a necessary sanity check. If scVI is trained on all donors before CV (section 4.1), a permuted-label scVI may still achieve AUC > 0.5 because the encoder incorporates structure from all donors. A reviewer at Bioinformatics or Nature Methods will view the omission of this control as suspicious.

**Addressability:** Fully addressable with existing data. Five lines of code (shuffle labels, rerun CV). Should be added immediately.

---

### 8.2 No confidence intervals for cross-dataset transfer AUCs

**Problem:** As noted in section 6.1, the cross-dataset transfer AUCs are single point estimates. A baseline comparison (e.g., "is 0.833 significantly better than 0.5?") requires at minimum a bootstrap confidence interval. The UC→CD result of 0.503–0.558 is reported as a range across methods, but it is unclear whether this range reflects fold-level variance or method-level variance.

**Why it matters to a reviewer:** Without confidence intervals, neither result is actionable. 0.833 could be a statistical artifact of a favorable target cohort composition (e.g., if CD donors in the target set are more extreme than UC donors in the source set). 0.503–0.558 could indicate a method that genuinely transfers at slightly above chance, which is scientifically meaningful if it is reliably above chance — but this cannot be established without a CI.

**Addressability:** Fully addressable with existing data using bootstrapped CIs. No new experiments required.

---

### 8.3 No method evaluated consistently across both cohorts with the same hyperparameters

**Problem:** The "benchmark" framing implies that methods are evaluated under comparable conditions across cohorts. However, the best-performing method in SCP259 (CFN) is not the best in all Kong regions (CatBoost CLR wins TI), and the configurations vary between cohorts (e.g., different feature dimensionalities after filtering). There is no analysis that holds hyperparameters constant across cohorts and evaluates all methods.

**Why it matters to a reviewer:** If the best method changes between cohorts and the hyperparameters also change, it is impossible to attribute performance differences to the methods rather than to the tuning choices. A proper benchmark would specify a single fixed configuration per method and evaluate it identically on both cohorts. The current design is closer to "best possible configuration per dataset" than a controlled comparison.

**Addressability:** Requires either a new experiment (fixed hyperparameters, both cohorts) or a limitation statement clarifying that the current design reports upper-bound estimates per dataset rather than a controlled cross-cohort benchmark.

---

## 9. Reproducibility

### 9.1 Random seeds not universally reported

**Problem:** The paper states that `random_state=42` is used for CV fold splitting, but does not explicitly state that XGBoost, CatBoost, and scVI training runs are seeded. XGBoost and CatBoost both have stochastic components (bootstrap sampling, column subsampling) that are controlled by a `random_state` or `seed` parameter. scVI training uses stochastic gradient descent with random mini-batch sampling, and its latent space is stochastic (reparameterization trick).

**Why it matters to a reviewer:** Reproducibility requires that every stochastic element be seeded and reported. A reader attempting to replicate the paper cannot reproduce the exact AUC values if the model training seeds are not fixed and disclosed. At journals like Bioinformatics, a reproducibility statement is mandatory. The absence of universal seeding is a straightforward correction but signals incomplete experimental rigor.

**Addressability:** Requires a disclosure statement (list all random seeds used) and code release. If seeds were not uniformly applied, the author should quantify the variance due to random initialization by running each model 3–5 times and reporting mean ± SD across seeds.

---

### 9.2 scVI subsampling seed

**Problem:** The 300 cells/donor subsampling for scVI was almost certainly done with some random state, but the paper does not report whether this was fixed. As noted in section 4.2, this introduces stochastic variance at the data level, independent of model training variance.

**Why it matters to a reviewer:** If the subsampling seed is not fixed, the scVI results cannot be reproduced by an independent lab without obtaining the exact same cell subset. Given that scVI's architecture is sensitive to the distribution of input cells (e.g., rare cell types may or may not be represented in a 300-cell subsample), uncontrolled subsampling makes the reported AUCs partially a function of a lucky or unlucky draw.

**Addressability:** Requires a disclosure statement (was the seed fixed?) and a sensitivity analysis (run with 3 different seeds, report AUC variance). Fully addressable with existing computational infrastructure.

---

### 9.3 CFN training seed

**Problem:** CFN training involves stochastic gradient descent with mini-batch sampling (batch_size=16). The random seed for CFN training is not reported. Given the small batch size and the limited number of training donors (24 in a 5-fold split of 30), mini-batch composition variance can have a meaningful effect on the learned weights, especially in early epochs.

**Why it matters to a reviewer:** Reproducibility and stability of the CFN results cannot be assessed without knowing whether training was seeded and, if seeded, whether different seeds produce similar results. Given that CFN is the method being most strongly promoted in the paper, its training stability must be demonstrated. Running 5 seeds × 5 CV folds = 25 runs would provide both a training-seed sensitivity estimate and the actual AUC variance decomposition.

**Addressability:** Requires new experiments (multiple training seeds) or a disclosure statement plus a caveat that CFN results reflect a single training seed.

---

## 10. Framing and Overclaims

### 10.1 "Best single-region result" claim — statistically unsupported

**Problem:** The paper claims CFN achieves the "best single-region result across all methods in this study" with 0.960±0.055 on Kong colon filtered. As established in section 1.2, the 95% CI for this result overlaps substantially with CLR CatBoost colon unfiltered (0.920±0.084). No paired statistical test is presented.

**Why it matters to a reviewer:** Superlative claims ("best result") are strong and require strong evidence. The overlap of confidence intervals makes the claim statistically indefensible without a significance test. In a study with this sample size and fold count, a difference of 0.040 in mean AUROC is not statistically significant by any standard test given the reported SDs. The claim should be replaced with "CFN achieved numerically higher AUROC than CLR in the Kong colon region (0.960 vs. 0.920), though this difference was not formally tested."

**Addressability:** Immediately addressable with existing data (paired Wilcoxon on 5 fold-level AUCs). If non-significant, the claim must be softened.

---

### 10.2 "Measurable discriminative value" on n=34 donors — is this justified?

**Problem:** The abstract claims CFN "adds measurable discriminative value." In the context of a single-region result on approximately 34 donors with overlapping confidence intervals between methods, the word "measurable" is doing a lot of work. Without a significance test, the difference between CFN and the next-best method is numerically observed but not statistically established.

**Why it matters to a reviewer:** Abstracts are the most widely read part of any paper, and overclaims in abstracts are specifically flagged by editors at Bioinformatics and PLOS CB. "Measurable" implies the difference has been quantified with appropriate uncertainty — which it has not. The abstract should accurately reflect the level of evidence, e.g., "shows a trend toward added discriminative value, though formal significance was not established given sample size."

**Addressability:** Requires a revision of the abstract. No new experiments needed if the claim is appropriately softened or a significance test is added.

---

### 10.3 Is "benchmark" in the title justified?

**Problem:** The paper uses the word "benchmark" in its title. In computational biology, a benchmark typically implies: (a) multiple independent datasets evaluated under identical protocols, (b) fixed, publicly documented configurations for all methods, (c) results that are reproducible by independent researchers, and (d) ideally, a community evaluation framework. The current study uses two cohorts, tested with partially varying hyperparameters, one of which (scVI) has a data leakage concern, produced by a single lab's implementation without publicly released code.

**Why it matters to a reviewer:** Using "benchmark" in a title sets a high bar that the paper may not meet. A reviewer who is familiar with true benchmarks (e.g., the scRNA-tools benchmarks, DREAM challenges, or the OpenProblems benchmarks) will note the discrepancy immediately. The risk is that the title attracts readers expecting a definitive community resource and then disappoints them. Alternative framings — "comparative evaluation," "feasibility study," or "systematic comparison" — would be more accurate and defensible.

**Addressability:** Requires a title revision. The paper's contributions are real and meaningful; they do not need to be inflated by a term that sets unrealistic expectations. A caveat in the discussion acknowledging the limited scope relative to a full benchmark would also be appropriate.

---

## Summary: Issues Most Likely to Trigger Rejection or Major Revision at Bioinformatics or PLOS CB

The following issues, ranked by severity, are most likely to be flagged by a real reviewer at a top computational biology journal:

**Critical (near-certain major revision or rejection if unaddressed):**

1. **scVI data leakage (Section 4.1):** Training scVI on all donors before CV is a fundamental methodological error. All scVI AUCs must be re-computed with within-fold scVI training, or the results must be removed from the benchmark comparison and clearly labelled as in-sample estimates. This is a non-negotiable fix.

2. **CFN classification=False bug (Section 2.1):** Using a regression objective due to a library bug without rigorous validation that the resulting scores are rank-meaningful is a serious concern. The paper must include sigmoid output distribution plots and, if possible, a patched run with `classification=True`.

3. **No permuted-label baseline (Section 8.1):** Given the data leakage concerns, the absence of a permuted-label sanity check will be interpreted as an oversight at best and as concealment of overfitting at worst.

**Serious (likely major revision):**

4. **Large unexplained SDs (Section 1.3):** The ±0.399 SD for global scVI XGBoost is indefensible without fold-level analysis. This single number undermines the credibility of the entire results table.

5. **Statistical tests absent for all inter-method comparisons (Sections 1.2, 10.1):** No paired tests are reported anywhere in the paper. In a comparative evaluation, this is expected as a minimum standard.

6. **Cross-dataset transfer: no uncertainty quantification (Sections 6.1, 8.2):** A single AUC point estimate for the transfer experiment cannot support any conclusion. Bootstrap CIs are trivially computable.

7. **Global Jaccard of 0.026 for CFN edges vs. biological attribution (Section 7.1):** Claiming "co-dependent remodeling" drives CFN's advantage while the edge Jaccard is 0.026 is internally contradictory and will not survive expert review.

**Moderate (likely minor revision or strong suggestion):**

8. **Variance/rare-type filter applied globally before CV (Sections 5.1, 5.2):** Mild data leakage; reviewers will flag it but it likely has small effect. Must be disclosed.

9. **Reproducibility: incomplete seeding disclosure (Sections 9.1–9.3):** All stochastic elements must be seeded and reported. Straightforward to fix.

10. **"Benchmark" framing and abstract overclaims (Section 10.3):** Title and abstract should be revised to match the actual scope and evidence level of the study.

**Observation:** The paper's core contribution — a donor-aware comparative evaluation of cell-type composition representations for IBD classification — is scientifically sound and timely. The problems above are largely methodological and presentational, not conceptual. Addressing the scVI leakage, adding significance tests, and including a permuted-label baseline would substantially strengthen the paper's credibility and address the majority of anticipated reviewer concerns.
