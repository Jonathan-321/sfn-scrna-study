# Results — v1 baseline

**Date:** May 2, 2026
**Suite version:** v1 (15 tasks)
**Models evaluated:** `claude-sonnet-4-5`, `claude-opus-4-5`
**Status:** v1 ceiling reached. v2 in development with harder, multi-step, and quantitative tasks.

---

## Headline numbers

| Model | Pass rate | Pass / Total | Mean latency |
|---|---|---|---|
| Claude Sonnet 4.5 | 100.0% | 15 / 15 | ~1.6 s |
| Claude Opus 4.5   | 93.3%  | 14 / 15 | ~1.2 s |

Both runs used identical task YAMLs, identical graders, and the same 15 tasks. The single Opus failure (`uc_vs_cd_biology`) is analyzed below — it is best read as a grader-design issue, not a model capability gap.

---

## Per-task comparison

| # | Task | Category | Difficulty | Expected fail | Sonnet | Opus |
|---|------|----------|------------|----------------|--------|------|
| 01 | donor_label_leakage          | protocol_critique | medium | no  | ✅ | ✅ |
| 02 | compartment_vs_global        | protocol_critique | easy   | no  | ✅ | ✅ |
| 03 | region_specific_method_choice| method_selection  | medium | no  | ✅ | ✅ |
| 04 | cross_dataset_direction      | failure_mode      | hard   | **yes** | ✅ | ✅ |
| 05 | clr_vs_pseudobulk_choice     | method_selection  | easy   | no  | ✅ | ✅ |
| 06 | cv_strategy_critique         | protocol_critique | medium | no  | ✅ | ✅ |
| 07 | cfn_vs_linear_when           | method_selection  | hard   | no  | ✅ | ✅ |
| 08 | lodo_interpretation          | metrics           | medium | **yes** | ✅ | ✅ |
| 09 | class_imbalance_metric       | metrics           | medium | no  | ✅ | ✅ |
| 10 | feature_selection_leakage    | protocol_critique | hard   | no  | ✅ | ✅ |
| 11 | uc_vs_cd_biology             | biology           | hard   | **yes** | ✅ | ❌ |
| 12 | scvi_latent_use              | method_selection  | hard   | **yes** | ✅ | ✅ |
| 13 | bootstrap_ci_reading         | metrics           | medium | no  | ✅ | ✅ |
| 14 | dependency_structure_interp  | biology           | hard   | **yes** | ✅ | ✅ |
| 15 | failure_mode_diagnosis       | failure_mode      | hard   | **yes** | ✅ | ✅ |

---

## Honest interpretation

**The most important reading of these numbers is that v1 is too easy for frontier
models, including the six tasks marked `expected_failure: true`.** A 100% pass
rate on tasks predicted to be hard is not evidence that the suite is well
calibrated — it is evidence that the suite has not yet reached a regime where
it discriminates between strong models, or surfaces the kind of confident-wrong
answers that an evaluation is supposed to catch.

This is a useful negative result. It tells us three things:

1. **Frontier models reason competently about donor-aware splits, cross-dataset
   transfer asymmetry, regime-dependent method choice, and bootstrap CI
   reading** — at least when these questions are posed as multiple-choice or
   short-answer items with the relevant context provided in the prompt.

2. **Single-step domain reasoning grounded in textbook canon and
   pre-computed AUROC numbers is not a discriminating eval target** for the
   current generation of Claude models. Tasks of this shape, even when authored
   carefully, sit below the model ceiling.

3. **The discriminating signal lives in tasks v1 does not contain**:
   multi-step computation, counterfactual reasoning over closed sets of
   pipeline choices, adversarial framings (sycophancy under a confident wrong
   premise), and rubric-graded protocol critique.

This motivates v2.

---

## The single divergent task — `uc_vs_cd_biology`

Sonnet passed; Opus failed. Both responses are scientifically correct. The
divergence is a grader-design artifact, not a capability difference.

**Question:** "From a biological standpoint, what feature of Crohn Disease
makes it inherently harder to classify from colonic single-cell data alone
compared to Ulcerative Colitis?"

**Grader:** `exact_match` on the keyword `transmural` (case-insensitive
substring).

**Sonnet response (passed):** Opens with "Crohn's Disease is inherently harder
to classify... because it is a *transmural* disease that can affect any segment
of the GI tract with *skip lesions* and patchy involvement..." Sonnet uses the
keyword the grader is looking for.

**Opus response (failed):** "Crohn's Disease preferentially involves the
terminal ileum rather than the colon, so colonic biopsies may sample uninvolved
or minimally involved tissue in many CD patients, diluting the
disease-associated cellular signature. In contrast, UC uniformly involves the
colonic mucosa..." Opus describes the same underlying biology — patchy and
heterogeneous CD involvement vs. uniform UC colonic involvement — but does not
use the word "transmural."

Both answers correctly identify why CD is harder to classify from colonic data.
The grader is checking word choice, not science. We document the failure here
rather than retroactively widen the keyword set, because (a) the failure mode
itself — narrow keyword graders punishing semantically equivalent answers — is
a real eval-design lesson worth preserving in the record, and (b) silently
adjusting graders after seeing model outputs is its own form of eval
malpractice.

The right fix is structural: in v2, biology questions of this shape are graded
by **rubric** (does the response identify *any* of {transmural, patchy
involvement, skip lesions, heterogeneous regional involvement, ileum-dominant
involvement}?), not by single-keyword substring match.

---

## Verification model — what each pass/fail actually means

A pass on a v1 task means: *the model's response, when fed through a
deterministic grader, matched the answer key derived from a results file in
this repository.* It does **not** mean: the model showed expert-level
biological reasoning, or that it would pass a domain reviewer.

We are explicit about which level of trust each task supports:

- **Tier 1 — computable ground truth:** The answer is a value from a TSV in
  `results/`. Re-running the pipeline reproduces it. (Tasks 03, 06, 08, 13.)
- **Tier 2 — textbook canon:** The answer is a fact any IBD pathologist or
  computational immunologist would agree on. (Tasks 02, 11.)
- **Tier 3 — mechanical reasoning over data:** Given the numbers and
  protocol details in the prompt, the answer is mechanically derivable.
  (Tasks 01, 04, 05, 07, 09, 10, 12, 14, 15.)
- **Tier 4 — open-ended scientific judgment:** Multiple valid answers
  exist; grader necessarily compresses. (None in v1 by design.)

v2 introduces tier-1 quantitative tasks (compute a value from a source TSV,
verified by `verify_groundtruth.py`), tier-3 closed-set counterfactuals, and a
small number of tier-4 rubric-graded items, clearly labeled as such.

---

## What changes for v2

Concrete plan for the next iteration of the suite:

1. **Quantitative computation tasks** (tier 1, 3 tasks). The model is given
   raw fold-level metrics from a source TSV and must compute a derived quantity
   (standard error of the mean, a delta between two methods, a confidence
   interval). Answers are numeric with explicit tolerance. A
   `verify_groundtruth.py` script reloads the TSV, recomputes the expected
   value with `pandas`, and asserts the YAML's `correct` matches — every task
   must pass this auto-verification before being added to the suite.

2. **Closed-set counterfactual tasks** (tier 3, 2 tasks). Format: "experiment A
   used preprocessing pipeline X and reached AUROC `α`; experiment B used
   pipeline Y and reached AUROC `β`. Which one preprocessing change explains
   the gap?" Choices are drawn from a closed set of pipeline diffs we actually
   ran. Mechanically grounded in `results/`.

3. **Adversarial / sycophancy tasks** (tier 2, 2 tasks). The prompt includes a
   confident wrong claim ("As established by the literature, terminal-ileum
   classification beats colonic classification in CD..."). The grader checks
   whether the model pushes back. Boolean: did the response disagree with the
   premise? Grounded in textbook canon.

4. **Rubric-graded design critique** (tier 4, 1 task, clearly labeled). The
   model is asked to critique an experimental design. The grader checks
   for *N of M* required concepts (donor leakage, batch confound, multiple
   testing, etc.) using deterministic per-criterion checks. Pass threshold and
   criterion list are specified in the YAML — no LLM-as-judge.

Both Sonnet and Opus will be run on v2. Cross-model agreement and disagreement
are themselves data points: if both models pass a "hard" task, the task is
likely below the frontier ceiling and gets cut. If they disagree, the
disagreement is investigated.

---

## Reproducibility

```bash
# Install
pip install -r evals/requirements.txt

# Verify harness end-to-end with no API key required
python evals/examples/run_mock.py

# Run against Claude (requires ANTHROPIC_API_KEY)
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

Raw run artifacts (full per-task model responses, latencies, grader outcomes)
are not committed to the repository — they are reproducible from the commands
above and would unnecessarily inflate diffs. A future commit may add an
optional `results/runs/<date>_<model>.json` archive for long-term tracking.
