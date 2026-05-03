"""
End-to-end mock run of the IBD scRNA eval suite.

This script runs the full task suite (v1 + v2) with the deterministic mock
model, which requires no API keys. It verifies that:
  - All task YAML files (including v2 subdirectory) load and validate correctly
  - The grading machinery produces sensible pass/fail results for all graders
  - The summary statistics are computed correctly
  - A results JSON is written to disk

Usage::

    python evals/examples/run_mock.py

Expected output: ~50% overall pass rate (mock returns correct for even-indexed
tasks and wrong for odd-indexed tasks), with per-category breakdown.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running from repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Also allow running with evals/ as a relative path when invoked from repo root
_EVALS_PARENT = Path(__file__).resolve().parents[2]
if str(_EVALS_PARENT) not in sys.path:
    sys.path.insert(0, str(_EVALS_PARENT))

from evals.harness.runner import run

TASKS_DIR = Path(__file__).resolve().parents[1] / "tasks"
OUT_PATH = Path(__file__).resolve().parents[1] / "mock_results.json"


def main():
    print("=" * 60)
    print("IBD scRNA Eval Suite — Mock Run")
    print("=" * 60)
    print(f"Tasks directory : {TASKS_DIR}")
    print(f"Output path     : {OUT_PATH}")
    print()

    output = run(
        model_name="mock",
        tasks_dir=str(TASKS_DIR),
        out_path=str(OUT_PATH),
        verbose=True,
    )

    # Verify the output structure
    summary = output["summary"]
    results = output["results"]

    print()
    print("=" * 60)
    print("Verification checks")
    print("=" * 60)

    # Check 1: At least 15 tasks ran (v1 baseline; v2 adds more)
    n_tasks = len(results)
    assert n_tasks >= 15, f"Expected at least 15 tasks, got {n_tasks}"
    print(f"[PASS] All {n_tasks} tasks ran")

    # Check 2: task_ids are unique
    task_ids = [r["task_id"] for r in results]
    assert len(set(task_ids)) == n_tasks, f"Duplicate task IDs: {task_ids}"
    print(f"[PASS] All {n_tasks} task IDs are unique")

    # Check 3: pass rate is between 0 and 1
    pr = summary["overall_pass_rate"]
    assert 0.0 <= pr <= 1.0, f"Pass rate out of range: {pr}"
    print(f"[PASS] Overall pass rate in valid range: {pr:.1%}")

    # Check 4: mock model produces ~50% pass rate (even-index tasks pass)
    n_pass = summary["total_pass"]
    # Allow a wide band — ~50% ± 20 percentage points — to accommodate both
    # v1-only and v1+v2 task counts without brittle hard-coded bounds.
    lo = max(1, n_tasks // 4)
    hi = n_tasks - lo
    assert lo <= n_pass <= hi, (
        f"Mock model should pass ~50% of {n_tasks} tasks; got {n_pass}. "
        "This may indicate a grader bug."
    )
    print(f"[PASS] Mock pass rate plausible: {n_pass}/{n_tasks} tasks passed")

    # Check 5: per-category breakdown present
    categories_found = set(summary["per_category"].keys())
    expected_categories = {
        "protocol_critique", "method_selection", "biology", "metrics", "failure_mode"
    }
    assert categories_found == expected_categories, (
        f"Missing categories: {expected_categories - categories_found}"
    )
    print(f"[PASS] All 5 categories present in summary")

    # Check 6: expected_failure summary present
    ef = summary["expected_failure"]
    assert "n_tasks" in ef and "pass_rate" in ef
    assert ef["n_tasks"] >= 6, (
        f"Expected at least 6 expected_failure tasks; got {ef['n_tasks']}"
    )
    print(f"[PASS] Expected-failure tasks: {ef['n_tasks']} tasks, "
          f"{ef['pass_rate']:.1%} pass rate")

    # Check 7: results JSON written
    assert OUT_PATH.exists(), f"Output file not written: {OUT_PATH}"
    with OUT_PATH.open() as fh:
        loaded = json.load(fh)
    assert loaded["model"] == "mock"
    print(f"[PASS] results JSON written and readable: {OUT_PATH.name}")

    # Check 8: core grader types exercised (v2 adds rubric_match)
    graders_used = {r["grader"] for r in results}
    core_graders = {"mc_match", "numeric_tolerance", "set_match", "exact_match"}
    missing = core_graders - graders_used
    assert not missing, (
        f"Core grader types not exercised: {missing}. Found: {graders_used}"
    )
    print(f"[PASS] Core grader types exercised: {sorted(graders_used)}")

    # Check 9: latency recorded for all tasks
    latencies = [r["latency_ms"] for r in results]
    assert all(isinstance(lat, (int, float)) and lat >= 0 for lat in latencies)
    print(f"[PASS] Latency recorded for all tasks (mean: {sum(latencies)/len(latencies):.1f} ms)")

    print()
    print("All verification checks passed.")
    print(f"Full results saved to: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
