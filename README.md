# sfn-scrna-study

Separate workspace for the single-cell RNA direction.

This directory exists to keep the scRNA project distinct from the current
clinical tabular NHANES and diabetes evaluation work in
`/Users/jonathanmuhire/CFN/cfn-biomed-eval`.

## Current goal

Pick one concrete scRNA-seq task, one dataset family, and one defensible
preprocessing plus evaluation setup before committing to model-heavy work.

## Initial layout

- `docs/research_plan.md`: working project plan for the scRNA direction.
- `docs/dataset_shortlist.md`: shortlist of candidate public datasets and the
  eventual anchor task.
- `docs/conventional_modeling_path.md`: methods-first note on the standard
  scRNA workflow, major design decisions, and frontier directions.
- `docs/first_benchmark_spec.md`: concrete first benchmark, test families, and
  diligence gates.
- `docs/uc_metadata_inventory.md`: current access and metadata audit for the UC
  anchor dataset.
- `docs/uc_preprocessing_decisions.md`: dataset-specific preprocessing rules
  for the first UC donor-level benchmark.
- `docs/uc_foundations_and_reference_workflows.md`: dataset-understanding note
  linking the UC structure to standard scRNA workflow branches and reference
  implementations.
- `docs/uc_cluster_glossary.md`: plain-language explanation of the UC atlas
  cluster labels and naming conventions.
- `docs/uc_first_paper_writeup.md`: working paper-style writeup for the UC
  benchmark, including current baseline results and the path to StructuralCFN.
- `docs/uc_intuition_map.tex`: LaTeX concept map for the UC dataset hierarchy,
  groupings, questions, and modeling ladder.
- `data/`: raw and processed dataset notes for this track.
- `scripts/`: one-off utilities for download, preprocessing, and dataset audit.

## Immediate next steps

1. Keep the UC metadata audit reproducible with `scripts/audit_uc_metadata.py`.
2. Build the first donor-level pseudobulk table for the frozen `Healthy` vs
   `UC` benchmark.
3. Build donor-level cluster-composition features before adding the more
   granular donor-by-cell-type table.
