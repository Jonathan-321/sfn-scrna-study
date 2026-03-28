# Donor-Global Representation Comparison

## Repeated 5-fold CV

| representation | protocol       | model      | roc_auc_mean       | roc_auc_ci95_low   | roc_auc_ci95_high  | pr_auc_mean        | pr_auc_ci95_low    | pr_auc_ci95_high   | balanced_accuracy_mean | macro_f1_mean      |
|----------------|----------------|------------|--------------------|--------------------|--------------------|--------------------|--------------------|--------------------|------------------------|--------------------|
| composition    | repeated_5fold | logreg     | 0.9363888888888888 | 0.8827777777777779 | 0.970625           | 0.9587777777777776 | 0.9295902777777778 | 0.9871875          | 0.8549999999999999     | 0.8392936507936508 |
| composition    | repeated_5fold | linear_svm | 0.9272222222222222 | 0.8648611111111111 | 0.970625           | 0.9535555555555556 | 0.9203541666666668 | 0.9871875          | 0.8508333333333333     | 0.8378888888888888 |
| composition    | repeated_5fold | xgb        | 0.8786111111111111 | 0.8247222222222222 | 0.9270833333333334 | 0.9338333333333336 | 0.90025            | 0.9534791666666668 | 0.7674999999999998     | 0.7447857142857143 |
| pseudobulk     | repeated_5fold | xgb        | 0.9975             | 0.980625           | 1.0                | 0.999              | 0.99225            | 1.0                | 0.9549999999999998     | 0.9474761904761906 |
| pseudobulk     | repeated_5fold | linear_svm | 0.9925             | 0.941875           | 1.0                | 0.9960833333333332 | 0.9696458333333334 | 1.0                | 0.96                   | 0.9551666666666666 |
| pseudobulk     | repeated_5fold | logreg     | 0.9925             | 0.941875           | 1.0                | 0.9960833333333332 | 0.9696458333333334 | 1.0                | 0.94                   | 0.9279285714285714 |

## Leave-One-Donor-Out

| representation | protocol | model      | roc_auc            | pr_auc             | balanced_accuracy  | macro_f1           | accuracy           |
|----------------|----------|------------|--------------------|--------------------|--------------------|--------------------|--------------------|
| composition    | lodo     | logreg     | 0.949074074074074  | 0.9602306985240424 | 0.875              | 0.8642533936651584 | 0.8666666666666667 |
| composition    | lodo     | linear_svm | 0.925925925925926  | 0.9307164854313978 | 0.8611111111111112 | 0.8611111111111112 | 0.8666666666666667 |
| composition    | lodo     | xgb        | 0.8611111111111112 | 0.9227621211316864 | 0.7222222222222222 | 0.7222222222222222 | 0.7333333333333333 |
| pseudobulk     | lodo     | linear_svm | 1.0                | 1.0000000000000002 | 0.9722222222222222 | 0.9657142857142856 | 0.9666666666666668 |
| pseudobulk     | lodo     | logreg     | 1.0                | 1.0000000000000002 | 0.9444444444444444 | 0.9321266968325792 | 0.9333333333333332 |
| pseudobulk     | lodo     | xgb        | 0.9907407407407408 | 0.9944444444444448 | 0.9722222222222222 | 0.9657142857142856 | 0.9666666666666668 |

## Interpretation

- Best repeated-CV composition model: `logreg` AUROC `0.9364` (95% CI `0.8828`-`0.9706`).
- Best repeated-CV pseudobulk model: `xgb` AUROC `0.9975` (95% CI `0.9806`-`1.0000`).
- Pseudobulk is currently stronger than composition because every model family reaches near-ceiling AUROC under repeated donor resampling and remains strong under LODO.
- Composition remains scientifically useful because it is not near ceiling, it is biologically interpretable, and it provides more room for StructuralCFN to add value.
