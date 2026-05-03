"""
Ground-truth verifier for the IBD scRNA eval suite.

Iterates all task YAML files under evals/tasks/ (including subdirectories).
For tasks that carry a `verification:` block, reloads the source TSV,
applies any column filters, computes the expected answer using the specified
formula, and asserts that the computed value matches the YAML's `correct.value`
within `correct.tol`.

Supported formulas
------------------
  mean           : arithmetic mean of the column values
  std            : sample standard deviation (ddof=1)
  sem            : sample SEM = std(ddof=1) / sqrt(n)
  delta          : |mean(column_A) - mean(column_B)|
                   requires delta_source_file and delta_column fields
  wald_ci_lower  : mean - 1.96 * sem

Usage::

    python evals/verify_groundtruth.py

Exits 0 if all verifiable tasks pass; exits 1 on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import yaml

# Allow running from the repository root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.harness.schema import NumericCorrect, TaskSpec, VerificationSpec


# ---------------------------------------------------------------------------
# Formula implementations
# ---------------------------------------------------------------------------

def _load_column(source_file: str, column: str, filter_spec: dict) -> np.ndarray:
    """Load a column from a TSV or CSV, applying optional column-equality filters."""
    path = _REPO_ROOT / source_file
    sep = "\t" if source_file.endswith(".tsv") else ","
    df = pd.read_csv(path, sep=sep)
    for col, val in filter_spec.items():
        df = df[df[col] == val]
    return df[column].values.astype(float)


def _compute(formula: str, vspec: VerificationSpec) -> float:
    """Compute the expected answer for a given verification spec."""
    values = _load_column(vspec.source_file, vspec.column, vspec.filter)

    if formula == "mean":
        return float(np.mean(values))
    elif formula == "std":
        return float(np.std(values, ddof=1))
    elif formula == "sem":
        return float(np.std(values, ddof=1) / np.sqrt(len(values)))
    elif formula == "delta":
        if not vspec.delta_source_file or not vspec.delta_column:
            raise ValueError(
                "formula='delta' requires delta_source_file and delta_column "
                f"in verification block of {vspec.source_file}"
            )
        values_b = _load_column(
            vspec.delta_source_file,
            vspec.delta_column,
            vspec.filter,
        )
        return float(abs(np.mean(values) - np.mean(values_b)))
    elif formula == "wald_ci_lower":
        mean = float(np.mean(values))
        sem = float(np.std(values, ddof=1) / np.sqrt(len(values)))
        return mean - 1.96 * sem
    else:
        raise ValueError(f"Unknown formula {formula!r}")


# ---------------------------------------------------------------------------
# Main verification loop
# ---------------------------------------------------------------------------

def verify_all(tasks_root: Path) -> Tuple[int, int]:
    """
    Walk all YAML task files under tasks_root (recursively).
    For tasks with a verification block, compute and compare.

    Returns (n_verified, n_failed).
    """
    task_files = sorted(tasks_root.rglob("*.yaml"))
    if not task_files:
        print(f"No task YAML files found under {tasks_root}")
        return 0, 0

    n_verified = 0
    n_failed = 0

    for f in task_files:
        with f.open() as fh:
            raw = yaml.safe_load(fh)

        task = TaskSpec.from_dict(raw)

        if task.verification is None:
            continue  # not a verifiable task

        vspec = task.verification
        correct = task.correct

        if not isinstance(correct, NumericCorrect):
            print(
                f"[SKIP ] {task.id}: has verification block but correct is not "
                f"NumericCorrect ({type(correct).__name__})"
            )
            continue

        n_verified += 1

        try:
            computed = _compute(vspec.formula, vspec)
        except Exception as exc:
            print(f"[FAIL ] {task.id}: error computing {vspec.formula!r}: {exc}")
            n_failed += 1
            continue

        diff = abs(computed - correct.value)
        if diff <= correct.tol:
            print(
                f"[PASS ] {task.id}: {vspec.formula}={computed:.6f}, "
                f"claimed={correct.value:.6f}, |diff|={diff:.6f} <= tol={correct.tol}"
            )
        else:
            print(
                f"[FAIL ] {task.id}: {vspec.formula}={computed:.6f}, "
                f"claimed={correct.value:.6f}, |diff|={diff:.6f} > tol={correct.tol}"
            )
            n_failed += 1

    return n_verified, n_failed


def main() -> int:
    tasks_root = Path(__file__).resolve().parent / "tasks"
    print(f"Verifying ground truth for tasks under: {tasks_root}")
    print()

    n_verified, n_failed = verify_all(tasks_root)

    print()
    if n_verified == 0:
        print("No tasks with verification blocks found.")
        return 0

    n_passed = n_verified - n_failed
    print(f"Verified {n_verified} task(s): {n_passed} passed, {n_failed} failed.")

    if n_failed > 0:
        print("VERIFICATION FAILED — fix the YAML correct values before running the suite.")
        return 1

    print("All verifiable tasks passed ground-truth check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
