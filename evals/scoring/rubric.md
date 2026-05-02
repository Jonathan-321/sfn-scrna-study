# Scoring Rubric

This document defines the per-category scoring criteria for the IBD scRNA eval suite.
Graders are fully deterministic; no LLM-as-judge is used anywhere.

---

## Grader Types

### `mc_match`
Extracts a single letter (A/B/C/D) from the model response and compares it to the
correct letter. The extractor uses a regex that tolerates common response formats:
- "B"
- "Answer: B"
- "The answer is B."
- "(B)"

**Pass condition:** extracted letter == correct letter (case-insensitive).

### `numeric_tolerance`
Extracts the first numeric value from the model response and checks:

```
|parsed_value - target_value| <= tolerance
```

Also accepts percentage representation (e.g., "96%" is treated as 0.96 if that
is within tolerance of the target).

**Pass condition:** at least one numeric token in the response is within tolerance.

### `set_match`
Normalizes both the response and the correct set elements (lowercase, strip
punctuation, collapse whitespace), then checks that every element of the correct
set appears as a substring in the normalized response.

**Pass condition:** all correct set elements found in the response (case-insensitive,
order-insensitive).

### `exact_match`
Normalizes both strings and checks either:
1. Full normalized equality, OR
2. The normalized correct string is a substring of the normalized response.

This is lenient: a model that gives the correct answer embedded in a longer
explanation will still pass.

**Pass condition:** correct string found (as substring) in response after normalization.

---

## Per-Category Scoring

### `protocol_critique` (Tasks 01, 06, 10)

These tasks test whether the model recognizes experimental design flaws in
scRNA-seq classification pipelines.

| Task | Topic | Expected Difficulty |
|------|-------|---------------------|
| 01 | Donor-level label leakage in cell-level CV | medium |
| 06 | Single vs. repeated CV variance | medium |
| 10 | Feature selection leakage across CV folds | hard |

**What counts as correct:**
- Must identify the *specific mechanism* of leakage/bias (not just "there is a problem").
- Must identify the correct fix (donor-level CV for task 01; within-fold feature selection
  for task 10; repeated CV for task 06).
- Task 10 is `expected_failure: true` because frontier models often accept the
  "unsupervised ≠ leakage" argument without recognizing the distributional information
  leakage from including test-fold donors in variance computation.

---

### `method_selection` (Tasks 03, 05, 07)

These tasks test whether the model can select the appropriate method given
empirical AUROC evidence from this repo.

| Task | Topic | Expected Difficulty |
|------|-------|---------------------|
| 03 | CFN vs. CLR for colonic CD | medium |
| 05 | CLR composition vs. pseudobulk for UC | easy |
| 07 | When CFN outperforms CLR (region-specific) | hard |

**What counts as correct:**
- Must cite the correct directional difference in AUROC (not just "one is better").
- Task 07 is `expected_failure: true` because it requires knowing that CFN's advantage
  is *region-specific* — frontier models tend to over-generalize CFN's superiority
  or fail to recall TI vs. colon distinctions.

---

### `biology` (Tasks 11, 14)

These tasks test biological reasoning about IBD disease biology in the context
of single-cell classification.

| Task | Topic | Expected Difficulty |
|------|-------|---------------------|
| 11 | UC vs. CD biological classification difficulty | medium |
| 14 | CFN dependency structure stability interpretation | hard |

**What counts as correct:**
- Task 11 (exact_match): model must mention transmural/heterogeneous CD involvement
  or that CD is not colon-limited. Partial biological reasoning (e.g., "CD is more
  complex") without the specificity about GI segment heterogeneity counts as partial
  but the grader uses substring matching — any response containing "transmural" or
  "heterogeneous" combined with "segment" or "GI" or "ileum" will pass.
- Task 14 is `expected_failure: true` because models often conflate structural
  stability with overfitting rather than recognizing it as evidence of reproducible
  biological signal.

---

### `metrics` (Tasks 08, 09, 13)

These tasks test correct interpretation of evaluation metrics in the context of
scRNA IBD classification.

| Task | Topic | Expected Difficulty |
|------|-------|---------------------|
| 08 | LODO vs. k-fold CV interpretation | medium |
| 09 | PR-AUC necessity for imbalanced cohorts | medium |
| 13 | Bootstrap CI lower bound reading | medium |

**What counts as correct:**
- Task 13 (numeric): any value within ±0.02 of 0.72 is correct (lower CI bound
  from cross_dataset_bootstrap_ci.tsv, XGBoost CD→UC row, ci_lo_95 = 0.72).
- Task 08: must recognize LODO is not universally higher than k-fold — models
  that state "LODO always gives more data therefore higher AUROC" fail.
- Task 09: must identify the specific mechanism (precision on minority class).

---

### `failure_mode` (Tasks 04, 15)

These tasks test diagnosis of the specific mechanisms that cause classification
to fail or underperform.

| Task | Topic | Expected Difficulty |
|------|-------|---------------------|
| 04 | Cross-dataset transfer asymmetry | hard |
| 15 | Multi-region pooling performance collapse | hard |

**What counts as correct:**
- Task 04 is `expected_failure: true`: requires knowing the exact cross-dataset
  XGBoost AUROC values (0.465 UC→CD, 0.833 CD→UC) *and* the mechanistic explanation
  (zero-filling of 47 UC-specific features in the Kong test set). Models that give
  generic "distribution shift" answers without the feature-overlap mechanism fail.
- Task 15 is `expected_failure: true`: requires understanding that regional
  heterogeneity in cell-type co-occurrence structures — not overfitting or normalization
  artifacts — is the cause.

---

## Expected Failure Tasks

Six tasks are marked `expected_failure: true`:

| Task ID | Category | Reason frontier models fail |
|---------|----------|------------------------------|
| `donor_label_leakage` | — (expected pass) | — |
| `cross_dataset_direction` | failure_mode | Requires exact AUROC values and feature-overlap mechanism |
| `cfn_vs_linear_when` | method_selection | Requires region-specific nuance (TI vs. colon) |
| `feature_selection_leakage` | protocol_critique | "Unsupervised ≠ leakage" misconception |
| `scvi_latent_use` | method_selection | Requires repo-specific leakage caveat knowledge |
| `dependency_structure_interp` | biology | Confuses stability with overfitting |
| `failure_mode_diagnosis` | failure_mode | Generic "distribution shift" vs. specific mechanism |

A frontier model that passes fewer than 2 of these 6 tasks is performing at or
below the BixBench baseline (~17% on biochemistry tasks). Passing ≥4 of 6
expected-failure tasks would be a strong positive signal.

---

## Baseline to Beat

- BixBench (biochemistry, frontier models): ~17% overall pass rate
  (source: https://arxiv.org/abs/2503.00096)
- This suite targets ~30–40% overall pass rate for frontier models on non-failure-mode
  tasks, with <40% on the 6 expected-failure tasks.

---

## Reproducibility

Every task `sources` field lists the specific results file(s) from `../results/`
used to derive the correct answer. All numeric values are taken directly from
TSV/CSV outputs without rounding beyond what is shown.
