# Scripts

Use this directory for small utilities related to:

- dataset download manifests
- metadata audit
- donor-aware split generation
- pseudobulk construction
- feature filtering and summary generation

## Current helpers

- `build_uc_donor_tables.py`: builds the first donor-level UC benchmark tables,
  including donor metadata, cluster-composition features, and all-cell donor
  pseudobulk
- `build_uc_donor_splits.py`: builds locked donor-level cross-validation folds
  for the first `Healthy` vs `UC` benchmark
- `build_uc_compartment_tables.py`: pivots donor-by-location features into
  donor-wide `Epi` / `LP` compartment tables
- `build_uc_supervised_table.py`: merges donor labels into a numeric,
  model-ready table for external runners such as the CFN benchmark harness
- `build_uc_donor_location_tables.py`: builds donor-by-location metadata,
  composition features, and location-aware pseudobulk tables for the UC atlas
- `download_uc_scp259.sh`: downloads the first-pass UC benchmark files from a
  TSV of signed URLs into `data/raw/uc_scp259/`
- `explore_uc_foundations.py`: writes donor, sample, and cluster-shift summary
  tables for the dataset-understanding phase
- `run_uc_baselines.py`: runs donor-level conventional baselines on frozen UC
  donor tables
- `run_uc_repeated_cv.py`: runs repeated stratified donor-level CV baselines on
  frozen UC donor tables
- `run_uc_lodo.py`: runs leave-one-donor-out baseline evaluation on frozen UC
  donor tables
- `audit_uc_metadata.py`: summarizes `all.meta2.txt` and prints the subject,
  sample, label, and task-setup counts needed to freeze the first benchmark
- `uc_scp259_urls.example.tsv`: template for the filename-to-URL mapping

Example:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
cp scripts/uc_scp259_urls.example.tsv scripts/uc_scp259_urls.tsv
# paste the signed URLs from the actual SCP download buttons or the
# storage.googleapis.com file URLs into scripts/uc_scp259_urls.tsv
# do not use the generic Single Cell Portal study-page URLs
bash scripts/download_uc_scp259.sh scripts/uc_scp259_urls.tsv
```

Metadata audit:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
python3 scripts/audit_uc_metadata.py
```

Build first donor tables:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
python3 scripts/build_uc_donor_tables.py
```

Build donor splits:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python scripts/build_uc_donor_splits.py
```

Run first donor baselines:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python scripts/run_uc_baselines.py \
  --features data/processed/uc_scp259/donor_cluster_props.tsv \
  --folds data/processed/uc_scp259/donor_healthy_vs_uc_folds.json \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_cluster_props_baselines
```

Run repeated donor CV:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python scripts/run_uc_repeated_cv.py \
  --features data/processed/uc_scp259/donor_cluster_props.tsv \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_cluster_props
```

Run leave-one-donor-out:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
/Users/jonathanmuhire/CFN/cfn-biomed-eval/.venv/bin/python scripts/run_uc_lodo.py \
  --features data/processed/uc_scp259/donor_cluster_props.tsv \
  --output-dir results/uc_scp259/benchmarks \
  --run-name donor_cluster_props
```

Build donor-wide compartment tables:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
python3 scripts/build_uc_compartment_tables.py
```

Build donor-by-location tables:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
python3 scripts/build_uc_donor_location_tables.py
```

Write dataset-foundation summaries:

```bash
cd /Users/jonathanmuhire/CFN/sfn-scrna-study
python3 scripts/explore_uc_foundations.py
```
