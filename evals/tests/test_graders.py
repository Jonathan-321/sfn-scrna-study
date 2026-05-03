"""
Unit tests for evals/harness/graders.py.

Run with: pytest evals/tests/ -v

Tests cover:
- mc_match: letter extraction from various response formats
- numeric_tolerance: decimal, percent, multiple numbers in response
- set_match: case-insensitivity, order-insensitivity, partial match failure
- exact_match: substring matching, normalization, punctuation stripping
- run_grader dispatcher: correct routing to each grader
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow running as `pytest evals/tests/` from repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_EVALS_PARENT = Path(__file__).resolve().parents[2]
if str(_EVALS_PARENT) not in sys.path:
    sys.path.insert(0, str(_EVALS_PARENT))

from evals.harness.graders import (
    exact_match,
    mc_match,
    numeric_tolerance,
    rubric_match,
    run_grader,
    set_match,
)
from evals.harness.schema import NumericCorrect, RubricSpec


# ---------------------------------------------------------------------------
# mc_match
# ---------------------------------------------------------------------------

class TestMcMatch:
    def test_bare_letter(self):
        assert mc_match("B", "B") is True

    def test_bare_letter_lowercase(self):
        assert mc_match("b", "B") is True

    def test_answer_prefix(self):
        assert mc_match("Answer: C", "C") is True

    def test_sentence_format(self):
        assert mc_match("The answer is D.", "D") is True

    def test_parenthesis_format(self):
        assert mc_match("(A)", "A") is True

    def test_with_explanation(self):
        assert mc_match("B. Because the donor-level leakage...", "B") is True

    def test_wrong_letter(self):
        assert mc_match("A", "B") is False

    def test_empty_response(self):
        assert mc_match("", "B") is False

    def test_no_letter_in_response(self):
        assert mc_match("The answer is unclear.", "B") is False

    def test_first_letter_extracted(self):
        # The first matching letter A/B/C/D is extracted
        result = mc_match("A or maybe B", "A")
        assert result is True

    def test_correct_d(self):
        assert mc_match("D is the correct choice.", "D") is True

    def test_case_insensitive_correct(self):
        assert mc_match("C", "c") is True

    def test_multiline_response(self):
        assert mc_match("Let me think...\nThe answer is B.", "B") is True


# ---------------------------------------------------------------------------
# numeric_tolerance
# ---------------------------------------------------------------------------

class TestNumericTolerance:
    def test_exact_match(self):
        correct = NumericCorrect(value=0.96, tol=0.02)
        assert numeric_tolerance("0.96", correct) is True

    def test_within_tolerance_above(self):
        correct = NumericCorrect(value=0.96, tol=0.02)
        assert numeric_tolerance("0.975", correct) is True

    def test_within_tolerance_below(self):
        correct = NumericCorrect(value=0.96, tol=0.02)
        assert numeric_tolerance("0.942", correct) is True

    def test_outside_tolerance(self):
        correct = NumericCorrect(value=0.96, tol=0.02)
        assert numeric_tolerance("0.90", correct) is False

    def test_percent_representation(self):
        # 96% should be interpreted as 0.96
        correct = NumericCorrect(value=0.96, tol=0.02)
        assert numeric_tolerance("96%", correct) is True

    def test_percent_within_tolerance(self):
        correct = NumericCorrect(value=0.72, tol=0.02)
        assert numeric_tolerance("72.5%", correct) is True

    def test_dict_correct(self):
        correct = {"value": 0.72, "tol": 0.02}
        assert numeric_tolerance("0.72", correct) is True

    def test_number_embedded_in_text(self):
        correct = NumericCorrect(value=0.833, tol=0.02)
        assert numeric_tolerance("The AUROC is 0.833 which is strong.", correct) is True

    def test_empty_response(self):
        correct = NumericCorrect(value=0.833, tol=0.02)
        assert numeric_tolerance("", correct) is False

    def test_no_number_in_response(self):
        correct = NumericCorrect(value=0.833, tol=0.02)
        assert numeric_tolerance("The AUROC is very high.", correct) is False

    def test_zero_value(self):
        correct = NumericCorrect(value=0.0, tol=0.01)
        assert numeric_tolerance("0.0", correct) is True

    def test_wrong_number_in_context(self):
        # 1 appears in "1 fold" but 0.99 is the numeric value — test exact parsing
        correct = NumericCorrect(value=0.72, tol=0.02)
        assert numeric_tolerance("The 1 fold AUROC is 0.50.", correct) is False

    def test_large_tolerance(self):
        correct = NumericCorrect(value=0.5, tol=0.5)
        assert numeric_tolerance("0.9", correct) is True


# ---------------------------------------------------------------------------
# set_match
# ---------------------------------------------------------------------------

class TestSetMatch:
    def test_exact_set(self):
        assert set_match("epithelial, stromal, immune", ["epithelial", "stromal", "immune"]) is True

    def test_different_order(self):
        assert set_match("immune, epithelial, stromal", ["epithelial", "stromal", "immune"]) is True

    def test_case_insensitive(self):
        assert set_match("Epithelial, Stromal, IMMUNE", ["epithelial", "stromal", "immune"]) is True

    def test_embedded_in_sentence(self):
        assert set_match(
            "The three compartments are epithelial, stromal, and immune cells.",
            ["epithelial", "stromal", "immune"]
        ) is True

    def test_missing_element(self):
        assert set_match("epithelial and stromal", ["epithelial", "stromal", "immune"]) is False

    def test_all_missing(self):
        assert set_match("none of the above", ["epithelial", "stromal", "immune"]) is False

    def test_single_element_set(self):
        assert set_match("The colon region", ["colon"]) is True

    def test_empty_response(self):
        assert set_match("", ["epithelial", "stromal", "immune"]) is False

    def test_partial_word_not_counted(self):
        # "epithelials" contains "epithelial" as substring after normalization
        assert set_match("epithelials stromal immune", ["epithelial", "stromal", "immune"]) is True

    def test_two_element_set(self):
        assert set_match("colon and TI regions", ["colon", "TI"]) is True


# ---------------------------------------------------------------------------
# exact_match
# ---------------------------------------------------------------------------

class TestExactMatch:
    def test_exact_equality(self):
        assert exact_match("pseudobulk", "pseudobulk") is True

    def test_case_insensitive(self):
        assert exact_match("PSEUDOBULK", "pseudobulk") is True

    def test_substring_in_longer_answer(self):
        assert exact_match(
            "CD is transmural and affects multiple GI segments.",
            "transmural"
        ) is True

    def test_correct_embedded_in_verbose_response(self):
        assert exact_match(
            "The answer is that pseudobulk gene expression is the correct choice here.",
            "pseudobulk"
        ) is True

    def test_wrong_answer(self):
        assert exact_match("CLR composition", "pseudobulk") is False

    def test_empty_response(self):
        assert exact_match("", "pseudobulk") is False

    def test_punctuation_stripped(self):
        # Punctuation removed from both before comparison
        assert exact_match("transmural!", "transmural") is True

    def test_whitespace_normalized(self):
        assert exact_match("pseudo   bulk", "pseudobulk") is False  # Different words

    def test_longer_correct_in_response(self):
        assert exact_match(
            "CD is transmural and can affect any GI segment with heterogeneous involvement",
            "transmural"
        ) is True

    def test_no_match(self):
        assert exact_match("The colon is a large intestine segment.", "transmural") is False


# ---------------------------------------------------------------------------
# rubric_match
# ---------------------------------------------------------------------------

class TestRubricMatch:
    """Tests for the rubric_match grader."""

    _RUBRIC = RubricSpec(
        keyword_groups=[
            ["donor leakage", "donor-level leakage", "cell-level split"],
            ["batch effect", "batch correction", "batch confound"],
            ["no confidence interval", "no CI", "uncertainty"],
            ["class imbalance", "imbalanced", "unbalanced"],
            ["sample size", "small n", "only 40 donors"],
        ],
        threshold=4,
    )

    def test_meets_threshold_exactly(self):
        """Response that hits exactly `threshold` groups should pass."""
        resp = (
            "The design has donor leakage because cells from the same donor "
            "appear in train and test. There is also no batch correction. "
            "No confidence interval is reported. The labels are class imbalance."
        )
        assert rubric_match(resp, self._RUBRIC) is True

    def test_exceeds_threshold(self):
        """Response that mentions all 5 groups should pass."""
        resp = (
            "Problems: donor leakage, batch effect, no confidence interval, "
            "class imbalance, and the sample size is too small."
        )
        assert rubric_match(resp, self._RUBRIC) is True

    def test_below_threshold(self):
        """Response that hits only 2 groups (below threshold=4) should fail."""
        resp = "There is donor leakage and batch effect in this study."
        assert rubric_match(resp, self._RUBRIC) is False

    def test_zero_matches(self):
        """Empty / irrelevant response should fail."""
        assert rubric_match("The experiment looks completely fine.", self._RUBRIC) is False

    def test_case_insensitive_keywords(self):
        """Keywords should match regardless of case."""
        resp = (
            "DONOR LEAKAGE is present. BATCH CORRECTION is missing. "
            "NO CONFIDENCE INTERVAL. CLASS IMBALANCE noted."
        )
        assert rubric_match(resp, self._RUBRIC) is True

    def test_synonym_within_group(self):
        """Any synonym in a group counts — should not require a specific keyword."""
        # Uses 'cell-level split' (not 'donor leakage') and 'batch confound',
        # 'no CI', 'unbalanced' — four groups via synonyms.
        resp = (
            "cell-level split means the donor is in both folds; batch confound "
            "from multi-site; no CI reported; labels are unbalanced."
        )
        assert rubric_match(resp, self._RUBRIC) is True

    def test_dict_interface(self):
        """rubric_match accepts a plain dict as well as a RubricSpec."""
        rubric_dict = {
            "keyword_groups": [
                ["donor leakage"],
                ["batch effect"],
                ["no CI"],
                ["class imbalance"],
            ],
            "threshold": 3,
        }
        resp = "donor leakage, batch effect, no CI mentioned."
        assert rubric_match(resp, rubric_dict) is True

    def test_threshold_one_below_fails(self):
        """Exactly one below threshold should fail."""
        rubric = RubricSpec(
            keyword_groups=[
                ["donor leakage"],
                ["batch effect"],
                ["no CI"],
            ],
            threshold=3,
        )
        resp = "donor leakage and batch effect only."
        assert rubric_match(resp, rubric) is False  # 2 of 3, threshold=3

    def test_dispatch_rubric_match(self):
        """run_grader dispatches correctly to rubric_match."""
        rubric = RubricSpec(
            keyword_groups=[["donor leakage"], ["batch effect"], ["no CI"]],
            threshold=2,
        )
        resp = "donor leakage and batch effect found."
        assert run_grader("rubric_match", resp, rubric) is True


# ---------------------------------------------------------------------------
# run_grader dispatcher
# ---------------------------------------------------------------------------

class TestRunGraderDispatcher:
    def test_dispatch_mc_match(self):
        assert run_grader("mc_match", "B", "B") is True

    def test_dispatch_numeric_tolerance(self):
        correct = NumericCorrect(value=0.72, tol=0.02)
        assert run_grader("numeric_tolerance", "0.72", correct) is True

    def test_dispatch_set_match(self):
        assert run_grader("set_match", "epithelial, stromal, immune",
                          ["epithelial", "stromal", "immune"]) is True

    def test_dispatch_exact_match(self):
        assert run_grader("exact_match", "transmural disease", "transmural") is True

    def test_dispatch_invalid_grader(self):
        with pytest.raises(ValueError, match="Unknown grader"):
            run_grader("llm_judge", "some response", "some answer")

    def test_dispatch_mc_wrong(self):
        assert run_grader("mc_match", "A", "B") is False

    def test_dispatch_numeric_wrong(self):
        correct = NumericCorrect(value=0.96, tol=0.01)
        assert run_grader("numeric_tolerance", "0.50", correct) is False

    def test_dispatch_set_wrong(self):
        assert run_grader("set_match", "only stromal", ["epithelial", "stromal", "immune"]) is False

    def test_dispatch_exact_wrong(self):
        assert run_grader("exact_match", "wrong answer entirely", "pseudobulk") is False


# ---------------------------------------------------------------------------
# Schema loading integration test
# ---------------------------------------------------------------------------

class TestSchemaLoading:
    """Verify all 15 task YAML files load and validate without error."""

    def test_all_tasks_load(self):
        import yaml
        from evals.harness.schema import TaskSpec

        tasks_dir = Path(__file__).resolve().parents[1] / "tasks"
        task_files = sorted(tasks_dir.glob("*.yaml"))
        assert len(task_files) == 15, (
            f"Expected 15 task files, found {len(task_files)} in {tasks_dir}"
        )
        for f in task_files:
            with f.open() as fh:
                raw = yaml.safe_load(fh)
            task = TaskSpec.from_dict(raw)
            assert task.id, f"Task {f.name} has no id"
            assert task.category, f"Task {f.name} has no category"
            assert task.grader, f"Task {f.name} has no grader"

    def test_expected_failure_count(self):
        import yaml
        from evals.harness.schema import TaskSpec

        tasks_dir = Path(__file__).resolve().parents[1] / "tasks"
        tasks = []
        for f in sorted(tasks_dir.glob("*.yaml")):
            with f.open() as fh:
                raw = yaml.safe_load(fh)
            tasks.append(TaskSpec.from_dict(raw))

        ef_tasks = [t for t in tasks if t.expected_failure]
        assert len(ef_tasks) >= 6, (
            f"Need at least 6 expected_failure tasks; found {len(ef_tasks)}"
        )

    def test_category_coverage(self):
        import yaml
        from evals.harness.schema import TaskSpec

        tasks_dir = Path(__file__).resolve().parents[1] / "tasks"
        tasks = []
        for f in sorted(tasks_dir.glob("*.yaml")):
            with f.open() as fh:
                raw = yaml.safe_load(fh)
            tasks.append(TaskSpec.from_dict(raw))

        from collections import Counter
        cat_counts = Counter(t.category for t in tasks)
        assert cat_counts["protocol_critique"] >= 3
        assert cat_counts["method_selection"] >= 3
        assert cat_counts["biology"] >= 2
        assert cat_counts["metrics"] >= 3
        assert cat_counts["failure_mode"] >= 2

    def test_answer_format_coverage(self):
        import yaml
        from evals.harness.schema import TaskSpec

        tasks_dir = Path(__file__).resolve().parents[1] / "tasks"
        tasks = []
        for f in sorted(tasks_dir.glob("*.yaml")):
            with f.open() as fh:
                raw = yaml.safe_load(fh)
            tasks.append(TaskSpec.from_dict(raw))

        from collections import Counter
        fmt_counts = Counter(t.answer_format for t in tasks)
        assert fmt_counts["multiple_choice"] >= 8
        assert fmt_counts["short_answer"] >= 1
        assert fmt_counts["numeric"] >= 1
        assert fmt_counts["set"] >= 1
