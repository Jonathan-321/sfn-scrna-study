# Conventional Modeling Path for scRNA Tasks

Last updated: 2026-03-07

## Why this note exists

Before adding StructuralCFN or a custom baseline stack, we need a grounded view
of how strong single-cell projects are normally done. In this area, the biggest
mistake is often not "using the wrong model" but asking the wrong question,
splitting the data at the wrong level, or forcing a cell-level classifier onto a
problem whose real unit of inference is the donor.

This note summarizes:

- the conventional workflow for scRNA tasks like ours
- the main decisions people make and why they make them
- which ideas are actually frontier directions versus hype
- what this means for our own UC, lupus, and COVID candidate datasets

## The short version

For the kinds of disease-focused datasets we shortlisted, the conventional path
is usually:

1. Start from counts and metadata, not from a preselected model.
2. Perform strict QC, ambient RNA handling if needed, and doublet filtering.
3. Normalize and select informative genes in a task-aware way.
4. Use clustering and annotation to understand the cellular landscape.
5. Use integration carefully for alignment and annotation, but avoid treating
   "integrated values" as automatically valid for every downstream task.
6. For disease biology, analyze:
   - cell-type composition changes
   - cell-state or gene-expression changes within cell types
   - donor-level or sample-level prediction if the scientific question is
     patient-level
7. For supervised prediction, split by donor or sample, not random cells.
8. Only then compare linear models, tree models, neural baselines, and later
   CFN-like models on a representation that respects the unit of inference.

The most important practical rule is this:

- cell-level rows are often fine for atlas construction and annotation
- donor-level or donor-by-cell-type rows are often better for disease
  classification and any claim that is supposed to generalize across people

## 1. What the conventional pipeline looks like

### 1.1 Start from the scientific unit, not the matrix shape

scRNA datasets naturally arrive as cell-by-gene matrices, but that does not mean
the cell is the right supervised learning unit.

Common units:

- Cell-level:
  good for clustering, annotation, trajectory, and cell-state discovery.
- Donor-level:
  good for disease classification or patient-level outcome prediction.
- Donor-by-cell-type pseudobulk:
  often the most useful compromise for disease studies because it keeps some
  cellular resolution while respecting replication.

Why this matters:

- cells from the same donor are not independent observations
- random cell splits can leak donor identity and inflate performance
- many biomedical questions are actually about subjects, not isolated cells

This is exactly why pseudoreplication and replicate-aware design show up so
often in recent best-practices work.

### 1.2 Quality control is not optional cleanup

The standard preprocessing path is still dominated by:

- low-quality cell filtering
- mitochondrial fraction checks
- gene-count and UMI-count filtering
- doublet detection
- ambient RNA assessment when relevant

Why people do this:

- low-quality cells distort clustering and annotation
- doublets can look like fake intermediate cell states
- ambient RNA can create artifactual marker expression

The official scverse best-practices material treats QC, doublet detection, and
normalization as core preprocessing rather than minor housekeeping.

### 1.3 Normalization depends on the downstream task

There is no single "best" normalization for everything.

A strong conventional default is still:

- library-size normalization
- log1p transform
- highly variable gene selection
- PCA, neighborhood graph, UMAP for exploratory structure

But the literature has become more explicit that normalization should depend on
the downstream task:

- shifted log normalization is still a strong default for dimensionality
  reduction and exploratory structure
- scran-style size factors are often used when careful scaling across cells is
  important
- Pearson residual approaches can help when identifying biologically variable
  genes or rare populations

The key decision is not "which normalization is best in general" but "which
representation preserves the biological signal needed for the next step."

### 1.4 Clustering and annotation come before disease modeling

The normal path is not to jump directly into disease classification. It is to
first understand what cell populations are present.

Conventional annotation workflow:

1. cluster cells after basic preprocessing
2. inspect cluster markers
3. assign coarse labels manually or semi-automatically
4. refine labels with reference mapping or automated classifiers

Typical tools and ideas:

- manual marker review
- CellTypist-style logistic regression annotation
- scANVI or related semi-supervised reference mapping
- ontology-aware models such as OnClass when unseen or hierarchical labels are a
  concern

Why this matters:

- disease effects often differ by cell type
- pseudobulk aggregation usually needs at least a coarse cell-type map
- many later analyses, including compositional and differential-state analyses,
  depend on trustworthy labels

### 1.5 Integration is useful, but easy to misuse

This is one of the most important design choices.

What integration is usually for:

- combining batches or studies
- aligning datasets for atlas construction
- transferring labels from a reference to a query set
- improving visualization and neighborhood structure

What integration is not automatically for:

- replacing raw or count-like data for every downstream statistical test
- removing all donor or condition structure without damaging biology

Common conventional methods:

- Harmony
- BBKNN
- Scanorama
- scVI
- scANVI when labels are partially available

Current best-practices language is more careful here than older single-cell
work. Analysts now worry much more about overcorrection, especially when the
"batch" covariate may overlap with true disease biology.

### 1.6 Disease analysis usually branches into three different tasks

For our shortlisted datasets, conventional analysis usually separates the
following:

#### A. Cell-type composition or differential abundance

Question:

- Are some cell populations expanded or depleted across disease states?

Typical tools:

- simple donor-level proportion tests as a first pass
- scCODA for compositional modeling
- Milo for neighborhood-level differential abundance

Why these methods exist:

- cluster counts are compositional, so a rise in one population mechanically
  affects the others
- cluster-level summaries can miss subtler neighborhood shifts

#### B. Differential state within cell types

Question:

- Within a given cell type, which genes or pathways change across condition?

Conventional strong path:

- pseudobulk within cell type and donor
- then use bulk RNA-seq tools like edgeR, DESeq2, or limma-voom
- muscat is a common framework for multi-sample, multi-condition differential
  state analysis

Why this path dominates:

- it respects biological replicates
- it reduces the worst pseudoreplication problems
- recent benchmarking papers found that pseudobulk methods often recover
  ground truth better than naive single-cell DE

#### C. Subject-level or sample-level prediction

Question:

- Can we classify disease, severity, or response at the donor level?

Conventional feature representations:

- donor-level pseudobulk
- donor-by-cell-type pseudobulk
- cell-type composition features
- pathway scores
- latent sample summaries from models like scVI

Conventional baseline models:

- logistic regression
- linear SVM
- random forest or gradient boosting
- small MLP

This is the branch where our CFN work is most likely to fit naturally.

## 2. The decisions that matter most, and why

### Decision 1: What is the row unit?

Options:

- cell
- donor
- donor by cell type
- neighborhood

Why people choose differently:

- cell rows maximize sample count but risk leakage and pseudoreplication
- donor rows match patient-level questions but shrink sample size
- donor-by-cell-type rows preserve more biology without pretending cells are
  independent
- neighborhood rows help detect local abundance shifts

Our likely default:

- donor-level or donor-by-cell-type pseudobulk for supervised disease modeling

### Decision 2: When should integration happen?

Options:

- no integration
- light integration for visualization only
- strong latent integration for annotation or atlas building

Why this is hard:

- donor or batch effects can obscure biology
- but aggressive correction can erase real disease structure

Our likely default:

- use integration to aid annotation and exploratory alignment
- avoid treating corrected embeddings as unquestioned truth for every
  downstream analysis

### Decision 3: How much label granularity is useful?

Options:

- broad compartments only
- medium-resolution cell types
- fine-grained states and subtypes

Why people downshift granularity:

- fine labels are biologically attractive but often unstable across studies
- rare populations can break donor-level models
- pseudobulk needs enough cells per donor-cell-type combination

Our likely default:

- start coarse, then refine only where the signal is stable and biologically
  meaningful

### Decision 4: Should we predict at cell level or donor level?

Conventional answer for disease tasks:

- donor level, unless the scientific question is explicitly cell level

Why:

- generalization target is usually the next donor, not the next cell from the
  same donor
- donor-level evaluation is much harder to fool

### Decision 5: Which baseline family should come first?

Conventional answer:

- start with linear and tree baselines on aggregated features

Why:

- they are strong
- they are interpretable
- they test whether representation quality is already enough
- they expose whether a fancy model is actually needed

This is especially relevant for us because CFN should not be judged against weak
or mis-specified baselines.

## 3. What frontier work is actually pushing on

Not all "state-of-the-art" ideas are equally relevant to our problem. The most
important frontier directions for our project are below.

### 3.1 Foundation models for cell and gene representations

Examples:

- Geneformer
- scFoundation
- scGPT
- Nicheformer for single-cell plus spatial context

Why people are excited:

- large pretraining corpora
- reusable embeddings
- promising transfer across tasks like annotation, perturbation prediction, and gene module inference

Why caution is still warranted:

- recent evaluation work shows that zero-shot performance does not consistently beat simpler, task-specific baselines
- strong performance often depends on fine-tuning or task-specific adaptation
- interpretability claims are still ahead of validation in many cases

Takeaway for us:

- foundation models are worth understanding and maybe using as feature extractors later
- they are not a reason to skip rigorous donor-aware baselines now

### 3.2 Sample-aware generative models

Examples:

- scVI and scANVI for probabilistic representation and semi-supervised annotation
- MrVI for modeling sample-level heterogeneity directly
- CTMM for cell-type-specific interindividual variation

Why this matters more for us than generic cell embeddings:

- our shortlisted tasks are cohort-style disease problems
- sample-level heterogeneity is not a nuisance to ignore; it is part of the biology
- these methods are closer to the real replication structure of the datasets

Takeaway for us:

- this is one of the most relevant frontier directions to study before CFN
- especially if we want to compare sample-level latent models with
  donor-pseudobulk tabular baselines

### 3.3 Compositional and neighborhood-aware analysis

Examples:

- scCODA
- Milo
- muscat for differential state

Why this matters:

- disease effects in scRNA data are often not just "gene expression changed"
- they can also be "the neighborhood shifted" or "a population expanded"
- conventional cluster-count plots are usually too naive

Takeaway for us:

- any serious disease analysis should probably include at least one composition
  or abundance-aware method, even if the headline model is a classifier

### 3.4 Better annotation and ontology-aware transfer

Examples:

- CellTypist
- scANVI
- OnClass
- larger cross-tissue annotation models such as scTab

Why this matters:

- label quality is often the bottleneck
- weak labels contaminate every downstream model
- unseen or partially overlapping cell types remain a real problem in cross-dataset settings

Takeaway for us:

- our first pipeline should probably combine manual coarse review with one automated transfer method, not rely on either alone

## 4. What the conventional path looks like for our candidate datasets

### 4.1 Ulcerative colitis colon atlas

Conventional path:

1. QC and confirm donor and biopsy metadata.
2. Build broad epithelial, stromal, and immune annotations.
3. Analyze composition shifts between healthy and UC.
4. Run cell-type-specific differential-state analysis.
5. Build donor-level or donor-by-cell-type pseudobulk features.
6. Run donor-aware disease classification.

Why this is the normal choice:

- the disease biology is likely a mix of abundance shifts and within-cell-type
  transcriptional changes
- raw cell-level disease classification would be too easy to overstate
- pseudobulk lets us ask a donor-level question without discarding all cell-type
  structure

### 4.2 Lupus PBMC atlas

Conventional path:

1. QC and confirm donor and cohort partitioning.
2. Annotate major immune cell types.
3. Examine cell-type composition and interferon-related programs.
4. Build donor-level or donor-by-cell-type pseudobulk.
5. Run healthy versus SLE classification, possibly with pathway features.

Why people like this dataset:

- blood is logistically cleaner
- donor-level modeling is straightforward
- interferon and immune activation modules provide a strong biological prior

Main caution:

- a model may look strong simply because the global disease program is strong
- that is not necessarily bad, but it narrows the biological story

### 4.3 COVID nasal atlas

Conventional path:

1. QC and confirm participant, wave, and vaccination metadata.
2. Annotate major epithelial and immune populations.
3. Analyze abundance shifts and condition-specific programs.
4. Restrict the first supervised task to a simple donor-aware comparison.

Why it is harder:

- infection status, time, vaccination, and variant wave are entangled
- this makes causal interpretation and generalization much harder

Main conclusion:

- this is a good expansion dataset, not the right first benchmark

## 5. What this means for our project

If we want to be rigorous, our project should not start with "Can CFN beat
model X on a cell-by-gene matrix?"

It should start with:

1. What is the correct supervised unit for the scientific question?
2. Which parts of the problem are annotation, composition, differential state,
   and subject-level prediction?
3. Which representation preserves the biology while respecting replication?
4. Which strong conventional baselines are appropriate for that representation?

For our current direction, the most defensible first path is:

- choose one anchor disease dataset
- build coarse cell annotations
- aggregate to donor-level or donor-by-cell-type pseudobulk
- compare strong conventional tabular baselines first
- only then ask whether CFN adds anything on top

## 6. Recommended first study design for us

If the ulcerative colitis dataset remains the anchor:

1. Confirm data access and donor metadata.
2. Build a coarse annotation inventory.
3. Produce two feature tables:
   - donor-level pseudobulk
   - donor-by-major-cell-type pseudobulk
4. Train conventional baselines:
   - logistic regression
   - linear SVM
   - XGBoost
   - small MLP
5. Evaluate only with donor-aware splits.
6. Keep composition and differential-state analysis as parallel descriptive
   analyses.
7. Treat CFN as a later structured-model comparison, not the starting point.

If the UC dataset stays hard to access, repeat the same plan on the lupus PBMC
dataset.

## Sources

- scverse best practices, Quality Control:
  https://www.sc-best-practices.org/preprocessing_visualization/quality_control.html
- scverse best practices, Normalization:
  https://www.sc-best-practices.org/preprocessing_visualization/normalization.html
- scverse best practices, Annotation:
  https://www.sc-best-practices.org/cellular_structure/annotation.html
- scverse best practices, Data integration:
  https://www.sc-best-practices.org/cellular_structure/integration.html
- scverse best practices, Differential gene expression:
  https://www.sc-best-practices.org/conditions/differential_gene_expression.html
- CellTypist model documentation:
  https://www.celltypist.org/models
- scVI paper:
  https://www.nature.com/articles/s41592-018-0229-2
- scvi-tools scVI documentation:
  https://docs.scvi-tools.org/en/stable/user_guide/models/scvi.html
- scvi-tools scANVI tutorial:
  https://docs.scvi-tools.org/en/1.3.3/tutorials/notebooks/scrna/seed_labeling.html
- scANVI / probabilistic harmonization paper:
  https://www.embopress.org/doi/10.15252/msb.20209620
- Zimmerman et al., pseudoreplication bias:
  https://www.nature.com/articles/s41467-021-21038-1
- Squair et al., false discoveries and pseudobulk:
  https://www.nature.com/articles/s41467-021-25960-2
- muscat:
  https://www.nature.com/articles/s41467-020-19894-4
- scCODA:
  https://www.nature.com/articles/s41467-021-27150-6
- Milo:
  https://www.nature.com/articles/s41587-021-01033-z
- OnClass:
  https://www.nature.com/articles/s41467-021-25725-x
- scTab:
  https://www.nature.com/articles/s41467-024-51059-5
- CTMM:
  https://www.nature.com/articles/s41467-024-49242-9
- MrVI:
  https://www.nature.com/articles/s41592-025-02808-x
- Geneformer:
  https://www.nature.com/articles/s41586-023-06139-9
- scFoundation:
  https://www.nature.com/articles/s41592-024-02305-7
- Zero-shot evaluation of single-cell foundation models:
  https://genomebiology.biomedcentral.com/articles/10.1186/s13059-025-03574-x
- Nicheformer:
  https://www.nature.com/articles/s41592-025-02814-z
