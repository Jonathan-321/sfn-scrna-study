# Dataset Shortlist

Last updated: 2026-03-07

This is the first concrete research artifact for the scRNA direction. The goal
is to stop talking about single-cell work in the abstract and instead choose
from real public datasets that support donor-aware evaluation and a reasonable
first modeling path.

## Selection criteria

- Publicly accessible from an official portal or repository.
- Clear disease or control labels, or a clinically meaningful outcome.
- Enough donor or participant structure to support donor-aware splitting.
- A plausible path to a CFN-friendly representation such as donor-level
  pseudobulk, cell-type-specific pseudobulk, or pathway summaries.
- Biologically meaningful enough to support more than a toy benchmark claim.

## Shortlist summary

| Dataset | Tissue | Main task | Participant structure | Access path | Recommendation |
|---|---|---|---|---|---|
| Smillie et al. ulcerative colitis atlas | Colon mucosa | Healthy vs ulcerative colitis classification; later inflamed vs less-inflamed region or treatment-response analysis | 18 UC + 12 healthy donors | Single Cell Portal `SCP259` | Recommended anchor |
| Nehar-Belaid et al. lupus PBMC atlas | Peripheral blood | Healthy vs SLE classification; later disease-activity modeling | 33 childhood SLE + 11 matched controls, plus adult validation cohort in the same GEO series | GEO `GSE135779` | Best backup anchor |
| Long et al. COVID-19 nasal atlas | Nasopharyngeal swab | Control vs infected, or severity-aware outcome prediction | 112 adult participants: 26 controls + 86 cases across variant waves | Single Cell Portal `SCP2593` | Good expansion dataset, not the first anchor |

## 1. Recommended anchor: ulcerative colitis colon atlas

Dataset:

- Smillie et al., "Intra- and Inter-cellular Rewiring of the Human Colon during
  Ulcerative Colitis"
- Publication: Cell, 2019
- Public data page: `SCP259`

Cohort snapshot:

- 18 ulcerative colitis participants and 12 healthy individuals.
- Roughly 365k to 366k cells from colon mucosa, depending on whether the portal
  total or paper total is cited.
- Rich epithelial, stromal, and immune compartments rather than blood alone.

Why this is the best first anchor:

- It matches the current plan best: one disease, one tissue, one strong
  biomedical question.
- The donor count is not huge, but it is large enough to support donor-aware
  splits and donor-level pseudobulk experiments.
- It has strong biological structure and enough cell diversity to make pathway
  or interaction analysis meaningful.
- It is public, well known, and already widely reused, which lowers startup
  risk.
- It gives a natural bridge from single-cell data to tabular-style modeling:
  donor by cell-type pseudobulk, donor by pathway scores, or donor by selected
  marker programs.

Best first task:

- Binary disease-state classification: healthy vs ulcerative colitis.

Best first representation:

- Not raw cell-level prediction as the main result.
- Start with donor-level pseudobulk, ideally stratified by major cell classes or
  robust cell types.
- Build a compact feature table from high-variance genes, marker panels, or
  pathway scores.

Main risks:

- Multiple biopsies or regional sampling can create nested structure that must
  be handled carefully.
- Disease signal may be partly driven by cell-composition shifts rather than
  pure within-cell-state transcriptional changes.
- Treatment status and inflammation region may add confounding if metadata are
  not handled cleanly.
- The study summary is publicly visible, but SCP file endpoints returned `401`
  in the first unauthenticated API check, so download access needs to be
  verified early.

Verdict:

- This is the most defensible first dataset for the project.
- If the goal is to choose one anchor task this week, choose this one first.

## 2. Best backup anchor: systemic lupus erythematosus PBMC atlas

Dataset:

- Nehar-Belaid et al., "Mapping systemic lupus erythematosus heterogeneity at
  the single-cell level"
- Publication: Nature Immunology, 2020
- Public data page: GEO `GSE135779`

Cohort snapshot:

- Public GEO series summary reports about 276k PBMCs from 33 childhood SLE
  donors and 11 matched healthy donors.
- The same GEO series also includes an adult validation cohort with 8 adult SLE
  and 6 adult healthy donors.
- Total sample count in the GEO series is 56.

Why it is attractive:

- Clear disease and control labels with donor structure already present.
- Blood is easier to preprocess and compare across donors than solid tissue.
- Donor-level pseudobulk is straightforward.
- Disease activity framing is available as a later extension beyond simple case
  vs control prediction.

Why it is not the first anchor:

- PBMC data are practical, but they are less tissue-specific and may collapse
  into a strong interferon-dominant signal too quickly.
- If the project wants a sharper biological story around local tissue
  pathophysiology, colon tissue is stronger than blood.
- Pediatric and adult cohorts should not be mixed casually; they need to be
  handled as separate cohorts or explicit validation sets.

Best first task:

- Childhood healthy vs childhood SLE classification using donor-aware splits.

Best first representation:

- Donor-level pseudobulk across major immune cell classes.
- Pathway or module scores can be especially useful because interferon and
  immune activation programs are central here.

Main risks:

- Strong global disease programs may make the task easier but biologically
  narrower.
- Age and cohort structure require care.
- Public raw data access is partially limited by privacy, so the exact reuse
  workflow should be checked early.

Verdict:

- This is the cleanest backup if colon tissue complexity slows the project down.

## 3. Expansion candidate: COVID-19 nasal immunity atlas

Dataset:

- Long et al., "Impact of variants and vaccination on nasal immunity across
  three waves of SARS-CoV-2"
- Public data page: `SCP2593`

Cohort snapshot:

- 112 adult participants total.
- 26 control participants and 86 SARS-CoV-2 positive participants.
- About 55k cells from nasopharyngeal swab samples.

Why it is interesting:

- Participant count is larger than the other candidates.
- There are multiple clinically meaningful labels available beyond binary case
  status, including variant wave, vaccination status, and disease severity.
- It is a strong stress test for generalization because the cohort spans several
  biological and temporal conditions.

Why it should not be first:

- Variant, vaccination, and severity are all entangled, which makes the
  evaluation design much harder.
- A naive train-test split could produce misleading results.
- This is better as an expansion dataset after the project has a cleaner anchor
  workflow.

Best first task:

- Conservative binary classification: PCR-negative controls vs infected cases,
  with explicit donor holdout.

Best first representation:

- Donor-level pseudobulk or donor-by-cell-type summaries.
- Avoid starting with a severity model because the confounders are more severe.

Main risks:

- Variant wave confounding.
- Vaccination confounding.
- Heterogeneous timing and acute immune dynamics.
- Like the UC dataset, portal file access may require authenticated download
  flow even when the study page itself is public.

Verdict:

- Strong future dataset, weak first anchor.

## Recommended decision right now

Choose the ulcerative colitis colon atlas as the anchor dataset and define the
first project task as:

- donor-aware healthy vs ulcerative colitis classification
- using donor-level pseudobulk or pathway-level summaries as the first CFN
  compatible representation

Use the lupus PBMC dataset as the backup anchor if colon metadata or region
structure becomes too messy in the first audit.

Keep the COVID nasal dataset for later, after the preprocessing and evaluation
workflow are stable.

## Immediate next research tasks

1. Build a dataset card for the ulcerative colitis atlas.
2. Decide the row unit for the first benchmark: donor-level pseudobulk only, or
   donor by cell-type pseudobulk.
3. Check whether the public download includes donor IDs, biopsy region, and
   disease labels in a directly usable form.
4. Define the first baseline set: logistic regression, linear SVM, XGBoost, and
   one compact neural baseline on the aggregated table.
5. Only after that, decide how StructuralCFN should consume the representation.

## Sources

- Smillie et al. PubMed: https://pubmed.ncbi.nlm.nih.gov/31348891/
- Smillie et al. Single Cell Portal `SCP259`:
  https://singlecell.broadinstitute.org/single_cell/study/SCP259/intra-and-inter-cellular-rewiring-of-the-human-colon-during-ulcerative-colitis
- Nehar-Belaid et al. PubMed: https://pubmed.ncbi.nlm.nih.gov/32747814/
- Nehar-Belaid et al. GEO `GSE135779`:
  https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135779
- Long et al. Single Cell Portal `SCP2593`:
  https://singlecell.broadinstitute.org/single_cell/study/SCP2593/impact-of-variants-and-vaccination-on-nasal-immunity-across-three-waves-of-sars-cov-2
