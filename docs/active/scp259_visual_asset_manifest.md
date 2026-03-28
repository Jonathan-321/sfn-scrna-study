# SCP259 Visual Asset Manifest

Status: generated asset guide  
Last updated: 2026-03-27

Use `.svg` for the paper when possible. Use `.png` for slides, chat, or quick
inspection.

## Figures

### Figure 1. Cohort and split audit

Files:

- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure1_scp259_cohort_and_split_audit.svg`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure1_scp259_cohort_and_split_audit.svg)
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure1_scp259_cohort_and_split_audit.png`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure1_scp259_cohort_and_split_audit.png)

Shows:

- donor label counts
- held-out donor counts per fold
- donor-to-fold test assignment matrix

Use for:

- proving the donor-aware split design is real and leakage-safe

### Figure 2. Benchmark overview

Files:

- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure2_scp259_benchmark_overview.svg`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure2_scp259_benchmark_overview.svg)
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure2_scp259_benchmark_overview.png`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure2_scp259_benchmark_overview.png)

Shows:

- raw atlas to donor-level aggregation
- donor-global representations
- compartment-aware representations
- evaluation and CFN diagnostic flow

Use for:

- methods / benchmark setup section

### Figure 3. Input representations

Files:

- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure3_scp259_input_representations.svg`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure3_scp259_input_representations.svg)
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure3_scp259_input_representations.png`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure3_scp259_input_representations.png)

Shows:

- PCA-style donor separation in donor-global composition
- PCA-style donor separation in donor-global pseudobulk

Use for:

- explaining what the model inputs look like before training

### Figure 4. Donor-global baseline performance

Files:

- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure4_donor_global_benchmarks.svg`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure4_donor_global_benchmarks.svg)
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure4_donor_global_benchmarks.png`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure4_donor_global_benchmarks.png)

Shows:

- repeated 5-fold donor CV AUROC
- LODO AUROC
- composition vs pseudobulk by model

Use for:

- the main baseline result

### Figure 5. Compartment-aware extension

Files:

- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure5_compartment_extension_heatmap.svg`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure5_compartment_extension_heatmap.svg)
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure5_compartment_extension_heatmap.png`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure5_compartment_extension_heatmap.png)

Shows:

- AUROC heatmap across models for compartment-aware composition and pseudobulk

Use for:

- the representation-extension section

### Figure 6. CFN performance vs stability

Files:

- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure6_cfn_performance_vs_stability.svg`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure6_cfn_performance_vs_stability.svg)
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure6_cfn_performance_vs_stability.png`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure6_cfn_performance_vs_stability.png)

Shows:

- CFN predictive metrics
- grouped Jaccard, sign consistency, and matrix cosine

Use for:

- the central mixed-result figure: prediction improves, stability does not

### Figure 7. Recurring edge themes

Files:

- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure7_recurring_edge_themes.svg`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure7_recurring_edge_themes.svg)
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure7_recurring_edge_themes.png`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/figures/figure7_recurring_edge_themes.png)

Shows:

- the main-text recurring edge set
- biological themes
- conservative status labels

Use for:

- interpretation section

## LaTeX Tables

### Donor-global repeated benchmark
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table1_donor_global_repeated.tex`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table1_donor_global_repeated.tex)

### Donor-global LODO benchmark
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table2_donor_global_lodo.tex`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table2_donor_global_lodo.tex)

### Compartment extension benchmark
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table3_compartment_extension.tex`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table3_compartment_extension.tex)

### CFN diagnostics
- [`/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table4_cfn_diagnostics.tex`](/Users/jonathanmuhire/CFN/sfn-scrna-study/results/uc_scp259/reports/latex/table4_cfn_diagnostics.tex)

## Recommended paper order

1. Figure 1
2. Figure 2
3. Figure 3
4. Figure 4
5. Figure 5
6. Figure 6
7. Figure 7
8. Tables 1-4 as manuscript tables or supplement tables
