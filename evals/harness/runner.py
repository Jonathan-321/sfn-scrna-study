"""
CLI harness for the IBD scRNA eval suite.

Usage::

    python -m evals.harness.runner \\
        --model mock \\
        --tasks evals/tasks/ \\
        --out results.json

Or via the examples script::

    python evals/examples/run_mock.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Allow running as `python -m evals.harness.runner` from repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.harness.graders import run_grader
from evals.harness.models import MockModel, get_model
from evals.harness.schema import NumericCorrect, TaskSpec


# ---------------------------------------------------------------------------
# Task loading
# ---------------------------------------------------------------------------

def load_tasks(tasks_dir: str) -> List[TaskSpec]:
    """Load all YAML task files from a directory, sorted by filename."""
    p = Path(tasks_dir)
    if not p.exists():
        raise FileNotFoundError(f"Tasks directory not found: {tasks_dir}")
    task_files = sorted(p.glob("*.yaml"))
    if not task_files:
        raise ValueError(f"No .yaml files found in {tasks_dir}")
    tasks = []
    for f in task_files:
        with f.open() as fh:
            raw = yaml.safe_load(fh)
        task = TaskSpec.from_dict(raw)
        tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_prompt(task: TaskSpec) -> str:
    """Construct the prompt to send to the model."""
    lines = [
        "You are a single-cell RNA sequencing expert. Answer the following question "
        "based on your knowledge of IBD (inflammatory bowel disease) classification using "
        "scRNA-seq data.",
        "",
        "=== CONTEXT ===",
        task.context.strip(),
        "",
        "=== QUESTION ===",
        task.question.strip(),
    ]
    if task.answer_format == "multiple_choice" and task.choices:
        lines.append("")
        lines.append("=== CHOICES ===")
        for choice_dict in task.choices:
            for letter, text in choice_dict.items():
                lines.append(f"  {letter}: {text}")
        lines.append("")
        lines.append(
            "Respond with ONLY the letter of the correct answer (A, B, C, or D). "
            "Do not include any explanation."
        )
    elif task.answer_format == "numeric":
        lines.append("")
        lines.append(
            "Respond with a single numeric value (e.g. 0.96). "
            "Do not include units or explanation."
        )
    elif task.answer_format == "set":
        lines.append("")
        lines.append(
            "Respond with a comma-separated list of all correct items. "
            "Do not include explanation."
        )
    else:  # short_answer
        lines.append("")
        lines.append("Provide a concise answer (1-3 sentences).")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Single-task runner
# ---------------------------------------------------------------------------

def run_task(
    task: TaskSpec,
    model,
    task_index: int,
) -> Dict[str, Any]:
    """Run a single task and return a result dict."""
    prompt = build_prompt(task)

    t0 = time.perf_counter()
    if isinstance(model, MockModel):
        response = model.complete_for_task(task)
    else:
        response = model.complete(prompt)
    latency_ms = (time.perf_counter() - t0) * 1000

    # Grade
    correct = task.correct
    if isinstance(correct, NumericCorrect):
        correct_for_grader = correct
    else:
        correct_for_grader = correct

    grader_pass = run_grader(task.grader, response, correct_for_grader)

    return {
        "task_id": task.id,
        "task_index": task_index,
        "category": task.category,
        "difficulty": task.difficulty,
        "expected_failure": task.expected_failure,
        "grader": task.grader,
        "answer_format": task.answer_format,
        "model_response": response,
        "grader_pass": grader_pass,
        "latency_ms": round(latency_ms, 2),
    }


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def compute_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute overall and per-category pass rates."""
    total = len(results)
    total_pass = sum(1 for r in results if r["grader_pass"])
    overall_pass_rate = total_pass / total if total > 0 else 0.0

    # Per-category
    categories: Dict[str, List[bool]] = {}
    for r in results:
        cat = r["category"]
        categories.setdefault(cat, []).append(r["grader_pass"])
    per_category = {
        cat: {
            "pass": sum(v),
            "total": len(v),
            "pass_rate": sum(v) / len(v) if v else 0.0,
        }
        for cat, v in categories.items()
    }

    # Expected-failure breakdown
    ef_results = [r for r in results if r["expected_failure"]]
    ef_pass = sum(1 for r in ef_results if r["grader_pass"])
    expected_failure_summary = {
        "n_tasks": len(ef_results),
        "n_pass": ef_pass,
        "pass_rate": ef_pass / len(ef_results) if ef_results else 0.0,
        "interpretation": (
            "Low pass rate on expected_failure tasks is EXPECTED — these are "
            "the discriminating signal. Frontier models should fail most of them."
        ),
    }

    return {
        "total_tasks": total,
        "total_pass": total_pass,
        "overall_pass_rate": round(overall_pass_rate, 4),
        "per_category": per_category,
        "expected_failure": expected_failure_summary,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(
    model_name: str,
    tasks_dir: str,
    out_path: str,
    model_checkpoint: Optional[str] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Full eval run.

    Args:
        model_name: 'mock', 'claude', or 'openai'
        tasks_dir: path to directory containing *.yaml task files
        out_path: path for JSON output
        model_checkpoint: optional model version override
        verbose: print progress to stdout

    Returns:
        The full results dict (also written to out_path).
    """
    if verbose:
        print(f"Loading tasks from {tasks_dir} ...")
    tasks = load_tasks(tasks_dir)
    if verbose:
        print(f"  Loaded {len(tasks)} tasks")

    if verbose:
        print(f"Initializing model: {model_name!r} ...")
    model = get_model(model_name, model_name=model_checkpoint)

    results = []
    for i, task in enumerate(tasks):
        if verbose:
            print(f"  [{i+1:2d}/{len(tasks)}] {task.id} ...", end=" ", flush=True)
        result = run_task(task, model, task_index=i)
        results.append(result)
        if verbose:
            status = "PASS" if result["grader_pass"] else "FAIL"
            print(f"{status}  ({result['latency_ms']:.0f} ms)")

    summary = compute_summary(results)

    output = {
        "model": model_name,
        "model_checkpoint": model_checkpoint,
        "tasks_dir": str(tasks_dir),
        "summary": summary,
        "results": results,
    }

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w") as fh:
        json.dump(output, fh, indent=2)

    if verbose:
        print("\n=== SUMMARY ===")
        print(f"Overall pass rate : {summary['overall_pass_rate']:.1%}  "
              f"({summary['total_pass']}/{summary['total_tasks']})")
        print("\nPer-category:")
        for cat, stats in summary["per_category"].items():
            print(
                f"  {cat:<30s} {stats['pass_rate']:.1%}  "
                f"({stats['pass']}/{stats['total']})"
            )
        ef = summary["expected_failure"]
        print(
            f"\nExpected-failure tasks: {ef['pass_rate']:.1%}  "
            f"({ef['n_pass']}/{ef['n_tasks']})"
        )
        print(f"\nResults written to: {out_path}")

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the IBD scRNA eval suite against a language model."
    )
    parser.add_argument(
        "--model",
        default="mock",
        help="Model backend: mock | claude | openai (default: mock)",
    )
    parser.add_argument(
        "--model-checkpoint",
        default=None,
        help="Optional model checkpoint override (e.g. claude-opus-4-5)",
    )
    parser.add_argument(
        "--tasks",
        default="evals/tasks/",
        help="Path to tasks directory (default: evals/tasks/)",
    )
    parser.add_argument(
        "--out",
        default="results.json",
        help="Output JSON path (default: results.json)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    run(
        model_name=args.model,
        tasks_dir=args.tasks,
        out_path=args.out,
        model_checkpoint=args.model_checkpoint,
        verbose=not args.quiet,
    )
