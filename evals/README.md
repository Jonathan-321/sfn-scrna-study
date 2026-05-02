# IBD scRNA-seq Eval Suite

**A scBench/Inspect-compatible evaluation suite for frontier LLM reasoning on
single-cell RNA-seq classification of inflammatory bowel disease (IBD).**

Author: Jonathan Muhire · jonathan.muhire@eagles.oc.edu

---

## Motivation

Large language models are increasingly used to assist with bioinformatics analysis,
yet their reliability on nuanced, quantitative reasoning tasks in single-cell biology
remains poorly characterized. This eval suite fills a specific gap: it tests whether
frontier models can correctly reason about experimental design, method selection,
and result interpretation in the context of **donor-level IBD classification from
scRNA-seq data** — a task with real clinical implications.

The suite is grounded in completed experiments from this repository (SCP259 UC atlas
and Kong 2023 CD atlas), meaning every correct answer is traceable to a specific
results file. This is distinct from knowledge-retrieval benchmarks: the model must
reason about *numbers and protocols*, not just recall facts.

This eval suite is designed in the spirit of [Anthropic's evaluation research
philosophy](https://www.anthropic.com/research), which emphasizes measuring
model capabilities on hard, real-world scientific tasks where failure modes are
non-obvious and performance cannot be estimated from general benchmarks alone.

---

## Quickstart

```bash
# Install dependencies
pip install -r evals/requirements.txt

# Run end-to-end with mock model (no API keys required)
python evals/examples/run_mock.py
```

To run against a real model:

```bash
# Claude
export ANTHROPIC_API_KEY=sk-ant-...
python -m evals.harness.runner --model claude --tasks evals/tasks/ --out results_claude.json

# OpenAI
export OPENAI_API_KEY=sk-...
python -m evals.harness.runner --model openai --tasks evals/tasks/ --out results_gpt4o.json

# Mock (deterministic, no API keys)
python -m evals.harness.runner --model mock --tasks evals/tasks/ --out results_mock.json
```

---

## Baseline to Beat

[BixBench](https://arxiv.org/abs/2503.00096) reports approximately **17% pass rate**
for frontier models on open-ended biochemistry reasoning tasks. We expect frontier
LLMs to land in a similar range on this suite, particularly on the **6 expected-failure
tasks** (`expected_failure: true`) which require knowledge of:

- Exact cross-dataset transfer AUROC values and their mechanistic explanation
- Region-specific method selection nuance (colon vs. terminal ileum)
- The distinction between unsupervised feature selection and data leakage
- scVI within-fold retraining requirements

Passing ≥ 4 of 6 expected-failure tasks would be a strong positive result.

---

## What This Suite Tests That BixBench / scBench Don't

Standard benchmarks test general biochemistry knowledge or generic scRNA-seq
familiarity. This suite specifically targets:

| Capability | This Suite | BixBench/scBench |
|---|---|---|
| **Donor-aware leakage detection** | ✓ Tasks 01, 10 | Not tested |
| **Compartment-stratification reasoning** | ✓ Tasks 02, 14 | Not tested |
| **Cross-dataset transfer asymmetry** | ✓ Task 04 (AUROC 0.465 vs. 0.833) | Not tested |
| **Region-specific method ranking** | ✓ Tasks 03, 07 | Not tested |
| **Bootstrap CI reading on small cohorts** | ✓ Task 13 | Not tested |
| **scVI within-fold leakage** | ✓ Task 12 | Not tested |

All correct answers are grounded in **real AUROC numbers from `../results/`** —
not hypothetical scenarios.

---

## Suite Structure

```
evals/
├── README.md                       (this file)
├── tasks/                          (15 YAML task files)
│   ├── 01_donor_label_leakage.yaml
│   ├── 02_compartment_vs_global.yaml
│   ├── 03_region_specific_method_choice.yaml
│   ├── 04_cross_dataset_direction.yaml
│   ├── 05_clr_vs_pseudobulk_choice.yaml
│   ├── 06_cv_strategy_critique.yaml
│   ├── 07_cfn_vs_linear_when.yaml
│   ├── 08_lodo_interpretation.yaml
│   ├── 09_class_imbalance_metric.yaml
│   ├── 10_feature_selection_leakage.yaml
│   ├── 11_uc_vs_cd_biology.yaml
│   ├── 12_scvi_latent_use.yaml
│   ├── 13_bootstrap_ci_reading.yaml
│   ├── 14_dependency_structure_interp.yaml
│   └── 15_failure_mode_diagnosis.yaml
├── harness/
│   ├── __init__.py
│   ├── runner.py                   (CLI + run() function)
│   ├── graders.py                  (deterministic graders)
│   ├── models.py                   (Claude, OpenAI, mock wrappers)
│   └── schema.py                   (Pydantic task validation)
├── scoring/
│   └── rubric.md                   (per-category scoring criteria)
├── examples/
│   └── run_mock.py                 (end-to-end mock verification)
├── requirements.txt
└── tests/
    └── test_graders.py             (pytest unit tests)
```

---

## Task Coverage

### Coverage by Category

| Category | Tasks | Count |
|---|---|---|
| `protocol_critique` | 01, 06, 10 | 3 |
| `method_selection` | 03, 05, 07 | 3 |
| `biology` | 11, 14 | 2 |
| `metrics` | 08, 09, 13 | 3 |
| `failure_mode` | 04, 15 | 2 |
| **Total** | | **15** |

### Coverage by Answer Format

| Format | Count | Tasks |
|---|---|---|
| `multiple_choice` | 10 | 01, 03, 04, 05, 06, 07, 08, 09, 12, 14, 15 |
| `short_answer` | 1 | 11 |
| `numeric` | 1 | 13 |
| `set` | 1 | 02 |

*(Note: 15 tasks total; multiple_choice count includes task 15.)*

### Expected-Failure Tasks (6)

| Task ID | Topic |
|---|---|
| `cross_dataset_direction` | Near-chance UC→CD transfer + mechanism |
| `cfn_vs_linear_when` | Region-specific CFN advantage (TI vs. colon) |
| `feature_selection_leakage` | Unsupervised feature selection still leaks |
| `scvi_latent_use` | scVI within-fold retraining requirement |
| `dependency_structure_interp` | Stability ≠ overfitting |
| `failure_mode_diagnosis` | Regional co-occurrence heterogeneity mechanism |

---

## Reproducibility

Every task traces back to a specific results file in `../results/`:

| Task | Primary source file |
|---|---|
| 01 | `results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_baselines_summary.tsv` |
| 02 | `results/uc_scp259/benchmarks/donor_compartment_cluster_props_baselines_summary.tsv` |
| 03 | `results/kong2023_cd/cfn_clean/summary.tsv` |
| 04 | `results/kong2023_cd/cross_dataset/kong_cross_dataset_composition_metrics.tsv` |
| 05 | `results/uc_scp259/benchmarks/donor_global_representation_comparison.md` |
| 06 | `results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_repeated_summary.tsv` |
| 07 | `results/kong2023_cd/cfn_clean/summary.tsv` |
| 08 | `results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_lodo_summary.tsv` |
| 09 | `results/kong2023_cd/baselines_clean/kong_clr_all_clean_summary.tsv` |
| 10 | `results/uc_scp259/benchmarks/donor_all_cells_pseudobulk_baselines_summary.tsv` |
| 11 | `results/kong2023_cd/cfn_clean/summary.tsv` |
| 12 | `results/uc_scp259/scvi_within_fold/README_leakage_caveat.txt` |
| 13 | `results/robustness/cross_dataset_bootstrap_ci.tsv` |
| 14 | `results/uc_scp259/cfn_benchmarks/donor_compartment_cluster_props_cfn_full_stability_summary.csv` |
| 15 | `results/kong2023_cd/cfn_clean/summary.tsv` |

---

## Output Format

Results are written as JSON with the following structure:

```json
{
  "model": "mock",
  "summary": {
    "total_tasks": 15,
    "total_pass": 8,
    "overall_pass_rate": 0.5333,
    "per_category": {
      "protocol_critique": {"pass": 2, "total": 3, "pass_rate": 0.6667},
      ...
    },
    "expected_failure": {
      "n_tasks": 6,
      "n_pass": 3,
      "pass_rate": 0.5,
      "interpretation": "Low pass rate on expected_failure tasks is EXPECTED ..."
    }
  },
  "results": [
    {
      "task_id": "donor_label_leakage",
      "category": "protocol_critique",
      "difficulty": "medium",
      "expected_failure": false,
      "grader": "mc_match",
      "model_response": "The answer is B.",
      "grader_pass": true,
      "latency_ms": 0.12
    },
    ...
  ]
}
```

---

## Running Tests

```bash
pytest evals/tests/ -v
```

The test suite covers all four grader types with edge cases (empty responses,
percent vs. ratio numerics, case-insensitivity, partial MC extraction).
