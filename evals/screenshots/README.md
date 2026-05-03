# Run screenshots

Rendered terminal output from live runs of the eval suite against Claude
on May 2-3, 2026 UTC.

| File | Model | Checkpoint | Pass rate |
|---|---|---|---|
| [`run_sonnet.png`](./run_sonnet.png) | Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | 21 / 23 (91.3%) |
| [`run_opus.png`](./run_opus.png)     | Claude Opus 4.5   | `claude-opus-4-5-20251101`   | 20 / 23 (87.0%) |

Both runs use the same 23 task YAMLs (15 v1 + 8 v2) under
`evals/tasks/`. The dated checkpoint shown in each screenshot is the
identifier returned by the Anthropic API in response to the alias
`claude-sonnet-4-5` / `claude-opus-4-5`, captured by `harness/runner.py`
and printed at the end of the run.

See [`../RESULTS.md`](../RESULTS.md) for the full per-task analysis,
failure-mode breakdown, and notes on run-to-run variance observed on
`v2_02_delta_method_pair`.

To reproduce:

```bash
pip install -r evals/requirements.txt

ANTHROPIC_MODEL=claude-sonnet-4-5 \
  python -m evals.harness.runner \
    --model claude \
    --tasks evals/tasks/ \
    --out results_sonnet.json

ANTHROPIC_MODEL=claude-opus-4-5 \
  python -m evals.harness.runner \
    --model claude \
    --tasks evals/tasks/ \
    --out results_opus.json
```

Pass rates may vary by ~1 task across runs; see RESULTS.md for the
documented run-to-run variance on numeric reasoning tasks.
