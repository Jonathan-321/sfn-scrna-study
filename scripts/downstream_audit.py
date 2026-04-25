"""
downstream_audit.py
Two analyses closing remaining reviewer gaps:
  1. Leave-one-cell-type-out (LOCO) ablation — 4-type CD->UC cross-dataset transfer
  2. Individual AUROC of the 18 TI cell types dropped by the variance/prevalence filter

Saves:
  results/robustness/loco_transfer_ablation.tsv
  results/robustness/ti_dropped_types_auroc.tsv
"""

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import json, os, warnings
warnings.filterwarnings("ignore")

np.random.seed(42)

ROOT    = "/home/user/workspace/sfn-scrna-study"
DATA    = os.path.join(ROOT, "data/processed")
RESULTS = os.path.join(ROOT, "results")
os.makedirs(os.path.join(RESULTS, "robustness"), exist_ok=True)


def clr(X):
    """Centred log-ratio transform with 1e-6 pseudo-count."""
    X = np.array(X, dtype=float) + 1e-6
    log_X = np.log(X)
    return log_X - log_X.mean(axis=1, keepdims=True)


def transfer_auroc(X_train, y_train, X_test, y_test, seed=42):
    """Scale, fit LogReg on train, return AUROC on test."""
    sc = StandardScaler()
    X_tr = sc.fit_transform(X_train)
    X_te = sc.transform(X_test)
    lr = LogisticRegression(max_iter=1000, random_state=seed, C=1.0)
    lr.fit(X_tr, y_train)
    proba = lr.predict_proba(X_te)[:, 1]
    return roc_auc_score(y_test, proba)


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS 1: LOCO ablation — 4-type CD→UC transfer
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("ANALYSIS 1: Leave-one-cell-type-out ablation (4-type CD→UC transfer)")
print("=" * 70)

SHARED_TYPES = ["DC1", "ILCs", "Macrophages", "Tregs"]

# Load donor proportions
kong_props = pd.read_csv(
    os.path.join(DATA, "kong2023_cd/donor_cluster_props.tsv"), sep="\t", index_col=0)
scp_props = pd.read_csv(
    os.path.join(DATA, "uc_scp259/donor_cluster_props.tsv"), sep="\t", index_col=0)

# Load metadata
kong_meta = pd.read_csv(
    os.path.join(DATA, "kong2023_cd/donor_metadata.tsv"), sep="\t", index_col=0)
scp_meta = pd.read_csv(
    os.path.join(DATA, "uc_scp259/donor_metadata.tsv"), sep="\t", index_col=0)

# Align donors
kong_donors = kong_props.index.intersection(kong_meta.index)
scp_donors  = scp_props.index.intersection(scp_meta.index)
kong_props  = kong_props.loc[kong_donors]
scp_props   = scp_props.loc[scp_donors]
kong_meta   = kong_meta.loc[kong_donors]
scp_meta    = scp_meta.loc[scp_donors]

# Binary labels: Disease=1, Healthy=0
y_kong = (kong_meta["donor_label"] != "Healthy").astype(int).values
y_scp  = (scp_meta["donor_label"]  != "Healthy").astype(int).values

print(f"Kong: {len(kong_donors)} donors, {y_kong.sum()} CD / {(y_kong==0).sum()} Healthy")
print(f"SCP:  {len(scp_donors)} donors, {y_scp.sum()} UC / {(y_scp==0).sum()} Healthy")

# Extract the 4 shared types from each dataset
# For Kong "Macrophages" is one of several subtypes — use the column "Macrophages"
kong_4 = kong_props[SHARED_TYPES].copy()
scp_4  = scp_props[SHARED_TYPES].copy()

# CLR transform
kong_4_clr = pd.DataFrame(clr(kong_4.values), index=kong_4.index, columns=SHARED_TYPES)
scp_4_clr  = pd.DataFrame(clr(scp_4.values),  index=scp_4.index,  columns=SHARED_TYPES)

# Full 4-type baseline (CD→UC direction: train on Kong, test on SCP)
auroc_full = transfer_auroc(
    kong_4_clr.values, y_kong,
    scp_4_clr.values,  y_scp)
print(f"\nFull 4-type (all types) CD→UC AUROC: {auroc_full:.4f}")

# LOCO: drop one type at a time
loco_rows = []
for drop_type in SHARED_TYPES:
    keep = [t for t in SHARED_TYPES if t != drop_type]
    X_tr = kong_4_clr[keep].values
    X_te = scp_4_clr[keep].values
    # re-CLR after dropping (recompute geometric mean on remaining types)
    X_tr = clr(kong_4[keep].values)
    X_te = clr(scp_4[keep].values)
    auroc = transfer_auroc(X_tr, y_kong, X_te, y_scp)
    delta = auroc - auroc_full
    print(f"  Drop {drop_type:<15} → AUROC {auroc:.4f}  (Δ {delta:+.4f})")
    loco_rows.append({
        "dropped_type": drop_type,
        "auroc_without": round(auroc, 4),
        "auroc_full_4type": round(auroc_full, 4),
        "delta": round(delta, 4),
        "direction": "CD→UC",
        "n_train": len(kong_donors),
        "n_test":  len(scp_donors),
    })

# Also run UC→CD direction for completeness
auroc_full_rev = transfer_auroc(
    scp_4_clr.values,  y_scp,
    kong_4_clr.values, y_kong)
print(f"\nFull 4-type (all types) UC→CD AUROC: {auroc_full_rev:.4f}")
for drop_type in SHARED_TYPES:
    keep = [t for t in SHARED_TYPES if t != drop_type]
    X_tr = clr(scp_4[keep].values)
    X_te = clr(kong_4[keep].values)
    auroc = transfer_auroc(X_tr, y_scp, X_te, y_kong)
    delta = auroc - auroc_full_rev
    print(f"  Drop {drop_type:<15} → AUROC {auroc:.4f}  (Δ {delta:+.4f})")
    loco_rows.append({
        "dropped_type": drop_type,
        "auroc_without": round(auroc, 4),
        "auroc_full_4type": round(auroc_full_rev, 4),
        "delta": round(delta, 4),
        "direction": "UC→CD",
        "n_train": len(scp_donors),
        "n_test":  len(kong_donors),
    })

loco_df = pd.DataFrame(loco_rows)
loco_out = os.path.join(RESULTS, "robustness/loco_transfer_ablation.tsv")
loco_df.to_csv(loco_out, sep="\t", index=False)
print(f"\nSaved: {loco_out}")

# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS 2: Individual AUROC of TI types dropped by filter
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 2: Individual AUROC of 18 dropped TI cell types")
print("=" * 70)

DROPPED_TYPES = [
    "DC1",
    "Endothelial cells CA4 CD36",
    "Endothelial cells LTC4S SEMA3G",
    "Enterochromaffin cells",
    "Enterocytes BEST4",
    "Enterocytes TMIGD1 MEP1A GSTA1",
    "Fibroblasts SMOC2 PTGIS",
    "ILCs",
    "L cells",
    "Macrophages CXCL9 CXCL10",
    "Mature DCs",
    "Monocytes CHI3L1 CYP27A1",
    "Monocytes HBB",
    "Monocytes S100A8 S100A9",
    "Myofibroblasts HHIP NPNT",
    "Neutrophils S100A8 S100A9",
    "Pericytes HIGD1B STEAP4",
    "Pericytes RERGL NTRK2",
]

# Load TI proportion table (unfiltered) and metadata
kong_ti = pd.read_csv(
    os.path.join(DATA, "kong2023_cd/donor_TI_cluster_props.tsv"), sep="\t", index_col=0)

# Load TI-specific fold splits
with open(os.path.join(DATA, "kong2023_cd/donor_cd_vs_healthy_TI_folds.json")) as f:
    ti_folds = json.load(f)

# Align to donors in folds
ti_all_donors = []
for fold in ti_folds["folds"]:
    ti_all_donors.extend(fold["train_ids"] + fold["test_ids"])
ti_all_donors = list(dict.fromkeys(ti_all_donors))   # dedup, preserve order

# Fold IDs are strings; props index is int — normalise both to string
kong_ti.index = kong_ti.index.astype(str)
kong_meta.index = kong_meta.index.astype(str)

# Subset to donors present in the TI props table
ti_all_donors = [d for d in ti_all_donors if d in kong_ti.index]
kong_ti = kong_ti.loc[ti_all_donors]
kong_ti_meta = kong_meta.reindex(ti_all_donors)

print(f"TI donors: {len(ti_all_donors)}")

ti_rows = []
for cell_type in DROPPED_TYPES:
    if cell_type not in kong_ti.columns:
        print(f"  SKIP (not in table): {cell_type}")
        continue

    # Single-feature CLR-like: just log(prop + 1e-6), no centering (1D)
    x = np.log(kong_ti[cell_type].values + 1e-6)
    y = (kong_ti_meta["donor_label"] != "Healthy").astype(int).values

    # 5-fold CV AUROC using stored fold splits
    fold_aurocs = []
    for fold in ti_folds["folds"]:
        train_ids = [d for d in fold["train_ids"] if d in kong_ti.index]
        test_ids  = [d for d in fold["test_ids"]  if d in kong_ti.index]
        if len(test_ids) == 0:
            continue
        train_idx = [ti_all_donors.index(d) for d in train_ids]
        test_idx  = [ti_all_donors.index(d) for d in test_ids]
        y_tr = y[train_idx]
        y_te = y[test_idx]
        x_tr = x[train_idx].reshape(-1, 1)
        x_te = x[test_idx].reshape(-1, 1)
        if len(np.unique(y_te)) < 2:
            continue
        sc = StandardScaler()
        x_tr_sc = sc.fit_transform(x_tr)
        x_te_sc = sc.transform(x_te)
        lr = LogisticRegression(max_iter=500, random_state=42)
        lr.fit(x_tr_sc, y_tr)
        proba = lr.predict_proba(x_te_sc)[:, 1]
        fold_aurocs.append(roc_auc_score(y_te, proba))

    if not fold_aurocs:
        continue

    mean_auroc = np.mean(fold_aurocs)
    std_auroc  = np.std(fold_aurocs)
    # Also compute whole-cohort Spearman correlation with disease label
    y_all = y
    x_all = x
    rho, pval = 0.0, 1.0
    if len(np.unique(y_all)) > 1:
        rho, pval = __import__("scipy").stats.spearmanr(x_all, y_all)

    print(f"  {cell_type:<45} AUROC {mean_auroc:.3f} ± {std_auroc:.3f}  "
          f"ρ={rho:+.3f} p={pval:.3f}")
    ti_rows.append({
        "cell_type":       cell_type,
        "mean_auroc_5fold": round(mean_auroc, 4),
        "std_auroc_5fold":  round(std_auroc, 4),
        "n_folds_valid":    len(fold_aurocs),
        "spearman_rho":     round(rho, 4),
        "spearman_p":       round(pval, 4),
        "filter_reason":    "low_variance_or_prevalence",
    })

ti_df = pd.DataFrame(ti_rows).sort_values("mean_auroc_5fold", ascending=False)
ti_out = os.path.join(RESULTS, "robustness/ti_dropped_types_auroc.tsv")
ti_df.to_csv(ti_out, sep="\t", index=False)
print(f"\nSaved: {ti_out}")

# ─────────────────────────────────────────────────────────────────────────────
# Summary printout for paper
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SUMMARY — for prose update")
print("=" * 70)

print("\n--- LOCO Transfer (CD→UC) ---")
cd_uc = loco_df[loco_df.direction == "CD→UC"].sort_values("delta")
for _, r in cd_uc.iterrows():
    print(f"  Drop {r.dropped_type:<15}: {r.auroc_without:.3f} (Δ{r.delta:+.3f})")

print("\n--- TI Dropped Types (top 5 by AUROC) ---")
print(ti_df[["cell_type","mean_auroc_5fold","std_auroc_5fold","spearman_rho"]].head(5).to_string(index=False))
print("\n--- TI Dropped Types (bottom 5 by AUROC) ---")
print(ti_df[["cell_type","mean_auroc_5fold","std_auroc_5fold","spearman_rho"]].tail(5).to_string(index=False))
