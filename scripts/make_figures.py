"""
make_figures.py — Generate all publication figures from existing results TSVs and JSONs.

Figures produced:
  Figure 1: ROC bar chart panels (SCP259 + Kong, per method/region)
  Figure 2: CFN dependency matrix heatmaps (SCP259 global + compartment,
             Kong all/TI/colon — averaged across folds)
  Figure 3: Cross-dataset transfer AUROC matrix (CLR + CFN, both directions)

All figures saved to results/figures/.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "results" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ── Style ──────────────────────────────────────────────────────────────────────
PALETTE = {
    "CLR / LinearSVM": "#2166AC",
    "CLR / LogReg":    "#4393C3",
    "CLR / XGBoost":   "#74ADD1",
    "CLR / CatBoost":  "#ABD9E9",
    "CLR / ElasticNet":"#D1E5F0",
    "CFN (GatedStructuralCFN)": "#D6604D",
    "scVI / LogReg":   "#878787",
}
DEFAULT_COLORS = [
    "#2166AC", "#4393C3", "#74ADD1", "#D6604D",
    "#ABD9E9", "#878787", "#BABABA", "#313695",
]
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 150,
})

# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — AUROC bar chart panels
# ══════════════════════════════════════════════════════════════════════════════

def _load_fold_auroc(path, model_col="model", auroc_col="roc_auc", sep="\t"):
    """Return DataFrame with [model, mean_auroc, std_auroc] from a fold_metrics file."""
    df = pd.read_csv(path, sep=sep)
    df.columns = df.columns.str.strip()
    # normalise column names
    if "auroc" in df.columns and auroc_col not in df.columns:
        auroc_col = "auroc"
    grp = df.groupby(model_col)[auroc_col].agg(["mean", "std"]).reset_index()
    grp.columns = ["model", "mean_auroc", "std_auroc"]
    grp["std_auroc"] = grp["std_auroc"].fillna(0)
    return grp


def build_figure1():
    panels = []

    # ── SCP259 panel ──────────────────────────────────────────────────────────
    scp_rows = []

    # Composition — LinearSVM (best)
    fm = pd.read_csv(ROOT / "results/uc_scp259/benchmarks/donor_cluster_props_baselines_fold_metrics.tsv", sep="\t")
    svm = fm[fm["model"] == "linear_svm"]["roc_auc"]
    scp_rows.append(("Composition\n(51-dim) SVM",   svm.mean(), svm.std(), "#2166AC"))

    # Compartment — LinearSVM
    fm2 = pd.read_csv(ROOT / "results/uc_scp259/benchmarks/donor_compartment_cluster_props_baselines_fold_metrics.tsv", sep="\t")
    sv2 = fm2[fm2["model"] == "linear_svm"]["roc_auc"]
    scp_rows.append(("Compartment\n(102-dim) SVM",  sv2.mean(), sv2.std(), "#4393C3"))

    # scVI compartment latent — XGBoost (60-dim Epi+Fib+Imm, 0.931)
    fm3 = pd.read_csv(ROOT / "results/uc_scp259/baselines/donor_scvi_compartment_latent_fold_metrics.tsv", sep="\t")
    lr3 = fm3[fm3["model"] == "xgb"]["roc_auc"]
    scp_rows.append(("scVI Compartment\n(60-dim) XGB",  lr3.mean(), lr3.std(), "#878787"))

    # CFN global
    fm4 = pd.read_csv(ROOT / "results/uc_scp259/cfn_benchmarks/donor_cluster_props_cfn_full_fold_metrics.csv")
    cfn_g = fm4["roc_auc"]
    scp_rows.append(("CFN global\n(51-dim)",         cfn_g.mean(), cfn_g.std(), "#D6604D"))

    # CFN compartment
    fm5 = pd.read_csv(ROOT / "results/uc_scp259/cfn_benchmarks/donor_compartment_cluster_props_cfn_full_fold_metrics.csv")
    cfn_c = fm5["roc_auc"]
    scp_rows.append(("CFN compartment\n(102-dim)",   cfn_c.mean(), cfn_c.std(), "#B2182B"))

    panels.append(("SCP259: UC vs Healthy (n=30, 5-fold CV)", scp_rows, "scp259"))

    # ── Kong 2023 panels ──────────────────────────────────────────────────────
    for region, label, n in [("all", "All regions (n=71)", 71),
                              ("TI",  "TI only (n=42)",    42),
                              ("colon", "Colon only (n=34)", 34)]:
        kong_rows = []

        # CLR baselines — best 3 models
        fmk = pd.read_csv(ROOT / f"results/kong2023_cd/baselines/kong_clr_{region}_fold_metrics.tsv", sep="\t")
        fmk.columns = fmk.columns.str.strip()
        auroc_col = "auroc" if "auroc" in fmk.columns else "roc_auc"
        for model, display, color in [
            ("catboost",   "CLR / CatBoost",   "#ABD9E9"),
            ("linear_svm", "CLR / LinearSVM",  "#2166AC"),
            ("logreg",     "CLR / LogReg",     "#4393C3"),
        ]:
            sub = fmk[fmk["model"] == model][auroc_col]
            if len(sub) == 0:
                continue
            kong_rows.append((display, sub.mean(), sub.std(), color))

        # CFN
        fmc = pd.read_csv(ROOT / f"results/kong2023_cd/cfn/kong_cfn_{region}_fold_metrics.tsv", sep="\t")
        fmc.columns = fmc.columns.str.strip()
        cfn_vals = fmc["auroc"]
        kong_rows.append(("CFN (GatedStructuralCFN)", cfn_vals.mean(), cfn_vals.std(), "#D6604D"))

        panels.append((f"Kong 2023: CD vs Healthy — {label}", kong_rows, f"kong_{region}"))

    # ── Draw ──────────────────────────────────────────────────────────────────
    n_panels = len(panels)
    fig, axes = plt.subplots(1, n_panels, figsize=(3.5 * n_panels, 4.2),
                             sharey=False)
    if n_panels == 1:
        axes = [axes]

    for ax, (title, rows, _) in zip(axes, panels):
        labels = [r[0] for r in rows]
        means  = [r[1] for r in rows]
        stds   = [r[2] for r in rows]
        colors = [r[3] for r in rows]
        x = np.arange(len(labels))
        bars = ax.bar(x, means, yerr=stds, color=colors, width=0.6,
                      capsize=4, error_kw={"linewidth": 1.2, "ecolor": "#555"},
                      edgecolor="white", linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7.5)
        ax.set_ylim(0.4, 1.08)
        ax.axhline(0.5, color="#aaa", linewidth=0.8, linestyle="--")
        ax.set_ylabel("AUROC (mean ± SD)" if ax == axes[0] else "")
        ax.set_title(title, fontsize=9, pad=6)
        # value labels on bars
        for bar, mean in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    min(bar.get_height() + 0.015, 1.04),
                    f"{mean:.3f}", ha="center", va="bottom", fontsize=7)

    fig.suptitle("Figure 1: AUROC across feature representations and models",
                 fontsize=10, fontweight="bold", y=1.01)
    fig.text(0.5, -0.04,
             "scVI Compartment: Epi+Fib+Imm per-compartment latent (20-dim each), XGBoost classifier, "
             "full-gene HVG set (2,000 genes per compartment).",
             ha="center", fontsize=7, color="#555")
    plt.tight_layout()
    out = FIG_DIR / "figure1_auroc_panels.pdf"
    fig.savefig(out, bbox_inches="tight")
    out_png = FIG_DIR / "figure1_auroc_panels.png"
    fig.savefig(out_png, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"Figure 1 saved: {out}")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — CFN dependency matrix heatmaps
# ══════════════════════════════════════════════════════════════════════════════

def _load_cfn_avg_matrix(json_paths):
    """Average dependency matrices across folds; return (mean_matrix, feature_names)."""
    matrices = []
    feature_names = None
    for p in json_paths:
        with open(p) as f:
            d = json.load(f)
        arts = d.get("artifacts", d)
        mat = np.array(arts["dependency_matrix"])
        matrices.append(mat)
        if feature_names is None:
            feature_names = arts.get("feature_names", [f"F{i}" for i in range(mat.shape[0])])
    return np.mean(matrices, axis=0), feature_names


def build_figure2():
    cfn_configs = []

    # SCP259 global CFN (51×51)
    json_dir = ROOT / "results/uc_scp259/cfn_structures/donor_cluster_props_cfn_full"
    paths = sorted(json_dir.glob("cfn_default_fold*.json"))
    if paths:
        mat, names = _load_cfn_avg_matrix(paths)
        cfn_configs.append(("SCP259: Global CFN\n(51-dim composition, mean across 5 folds)", mat, names))

    # SCP259 compartment CFN (102×102)
    json_dir2 = ROOT / "results/uc_scp259/cfn_structures/donor_compartment_cluster_props_cfn_full"
    paths2 = sorted(json_dir2.glob("cfn_default_fold*.json"))
    if paths2:
        mat2, names2 = _load_cfn_avg_matrix(paths2)
        cfn_configs.append(("SCP259: Compartment CFN\n(102-dim, mean across 5 folds)", mat2, names2))

    # Kong CFN per region
    for region in ["all", "TI", "colon"]:
        paths_k = sorted((ROOT / "results/kong2023_cd/cfn/cfn_structures").glob(f"kong_cfn_{region}_fold*.json"))
        if paths_k:
            matk, namesk = _load_cfn_avg_matrix(paths_k)
            auroc_str = {"all": "0.812", "TI": "0.811", "colon": "0.920"}[region]
            cfn_configs.append((f"Kong 2023: CFN — {region} region\n(AUROC {auroc_str}, mean across 5 folds)", matk, namesk))

    n = len(cfn_configs)
    if n == 0:
        print("No CFN JSON files found — skipping Figure 2.")
        return None

    fig, axes = plt.subplots(1, n, figsize=(4.5 * n, 4.5))
    if n == 1:
        axes = [axes]

    for ax, (title, mat, names) in zip(axes, cfn_configs):
        # Use absolute value for visibility; sign shown by diverging colormap
        vmax = np.percentile(np.abs(mat), 99)
        im = ax.imshow(mat, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_title(title, fontsize=8.5, pad=6)
        ax.set_xlabel("Target cell type", fontsize=8)
        ax.set_ylabel("Source cell type", fontsize=8)
        # Only label axes if <= 20 features (otherwise too crowded)
        if len(names) <= 20:
            ax.set_xticks(range(len(names)))
            ax.set_xticklabels(names, rotation=75, ha="right", fontsize=6)
            ax.set_yticks(range(len(names)))
            ax.set_yticklabels(names, fontsize=6)
        else:
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlabel(f"{len(names)} cell types — labels omitted for clarity",
                          fontsize=7, color="#555")
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Dependency weight")

    fig.suptitle("Figure 2: CFN dependency matrices (averaged across CV folds)",
                 fontsize=10, fontweight="bold", y=1.01)
    plt.tight_layout()
    out = FIG_DIR / "figure2_cfn_heatmaps.pdf"
    fig.savefig(out, bbox_inches="tight")
    out_png = FIG_DIR / "figure2_cfn_heatmaps.png"
    fig.savefig(out_png, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"Figure 2 saved: {out}")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Cross-dataset transfer AUROC
# ══════════════════════════════════════════════════════════════════════════════

def build_figure3():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # ── Left panel: bar chart — CLR and CFN per direction ─────────────────────
    ax = axes[0]

    clr_uc_cd = pd.read_csv(ROOT / "results/kong2023_cd/cross_dataset/kong_cross_dataset_composition_metrics.tsv", sep="\t")
    clr_cd_uc = pd.read_csv(ROOT / "results/kong2023_cd/cross_dataset/kong_reverse_cross_dataset_metrics.tsv", sep="\t")
    cfn_xd    = pd.read_csv(ROOT / "results/cross_dataset_cfn_4types/cross_dataset_metrics.tsv", sep="\t")
    scp_cv    = pd.read_csv(ROOT / "results/cross_dataset_cfn_4types/scp_cv_fold_metrics.tsv", sep="\t")
    kong_cv   = pd.read_csv(ROOT / "results/cross_dataset_cfn_4types/kong_cv_fold_metrics.tsv", sep="\t")

    # UC→CD direction
    uc_cd_clr_svm = float(clr_uc_cd[clr_uc_cd["model"] == "linear_svm"]["auroc"].iloc[0])
    uc_cd_clr_xgb = float(clr_uc_cd[clr_uc_cd["model"] == "xgb"]["auroc"].iloc[0])
    uc_cd_cfn     = float(cfn_xd[cfn_xd["direction"].str.contains("UC_to_Kong", na=False)]["auroc"].iloc[0])

    # CD→UC direction
    cd_uc_clr_svm = float(clr_cd_uc[clr_cd_uc["model"] == "linear_svm"]["auroc"].iloc[0])
    cd_uc_clr_xgb = float(clr_cd_uc[clr_cd_uc["model"] == "xgb"]["auroc"].iloc[0])
    cd_uc_cfn     = float(cfn_xd[cfn_xd["direction"].str.contains("Kong.*UC", na=False)]["auroc"].iloc[0])

    # Within-dataset CV (4 types only)
    scp_cfn_cv  = scp_cv["auroc"].mean()
    scp_cfn_std = scp_cv["auroc"].std()
    kong_cfn_cv  = kong_cv["auroc"].mean()
    kong_cfn_std = kong_cv["auroc"].std()

    categories = [
        "UC→CD\nCLR / SVM", "UC→CD\nCLR / XGB", "UC→CD\nCFN",
        "CD→UC\nCLR / SVM", "CD→UC\nCLR / XGB", "CD→UC\nCFN",
        "SCP259 CV\n(4 types)", "Kong CV\n(4 types)",
    ]
    values = [
        uc_cd_clr_svm, uc_cd_clr_xgb, uc_cd_cfn,
        cd_uc_clr_svm, cd_uc_clr_xgb, cd_uc_cfn,
        scp_cfn_cv, kong_cfn_cv,
    ]
    errs = [0, 0, 0,   0, 0, 0,   scp_cfn_std, kong_cfn_std]
    colors = [
        "#4393C3", "#74ADD1", "#D6604D",
        "#2166AC", "#313695", "#B2182B",
        "#F4A582", "#FDDBC7",
    ]

    x = np.arange(len(categories))
    bars = ax.bar(x, values, yerr=errs, color=colors, width=0.65,
                  capsize=4, error_kw={"linewidth": 1.2, "ecolor": "#555"},
                  edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30, ha="right", fontsize=8)
    ax.axhline(0.5, color="#aaa", linewidth=0.8, linestyle="--", label="Chance")
    ax.set_ylim(0.3, 1.05)
    ax.set_ylabel("AUROC")
    ax.set_title("Cross-dataset transfer (4 shared cell types:\nDC1, ILCs, Macrophages, Tregs)", fontsize=9, pad=6)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                min(bar.get_height() + 0.015, 1.01),
                f"{val:.3f}", ha="center", va="bottom", fontsize=7)

    # Separator line between directions
    ax.axvline(2.5, color="#ccc", linewidth=0.8, linestyle=":")
    ax.axvline(5.5, color="#ccc", linewidth=0.8, linestyle=":")
    ax.text(1,   0.33, "UC → CD", ha="center", fontsize=7.5, color="#555")
    ax.text(4,   0.33, "CD → UC", ha="center", fontsize=7.5, color="#555")
    ax.text(6.5, 0.33, "Within-CV",ha="center", fontsize=7.5, color="#555")

    # ── Right panel: 4×3 heatmap — model × direction × AUROC ─────────────────
    ax2 = axes[1]

    methods = ["CLR / SVM", "CLR / XGB", "CFN"]
    directions = ["UC→CD", "CD→UC"]
    matrix = np.array([
        [uc_cd_clr_svm, cd_uc_clr_svm],
        [uc_cd_clr_xgb, cd_uc_clr_xgb],
        [uc_cd_cfn,     cd_uc_cfn],
    ])

    im = ax2.imshow(matrix, cmap="YlOrRd", vmin=0.4, vmax=0.9, aspect="auto")
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(directions, fontsize=9)
    ax2.set_yticks(range(len(methods)))
    ax2.set_yticklabels(methods, fontsize=9)
    ax2.set_title("Transfer AUROC heatmap\n(4 shared cell types)", fontsize=9, pad=6)

    for i in range(len(methods)):
        for j in range(len(directions)):
            val = matrix[i, j]
            color = "white" if val > 0.72 else "#333"
            ax2.text(j, i, f"{val:.3f}", ha="center", va="center",
                     fontsize=10, fontweight="bold", color=color)

    plt.colorbar(im, ax=ax2, fraction=0.06, pad=0.04, label="AUROC")

    fig.suptitle("Figure 3: Cross-dataset generalization — UC vs CD (4 shared cell types)",
                 fontsize=10, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = FIG_DIR / "figure3_cross_dataset.pdf"
    fig.savefig(out, bbox_inches="tight")
    out_png = FIG_DIR / "figure3_cross_dataset.png"
    fig.savefig(out_png, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"Figure 3 saved: {out}")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating Figure 1 (AUROC panels)...")
    build_figure1()

    print("Generating Figure 2 (CFN heatmaps)...")
    build_figure2()

    print("Generating Figure 3 (Cross-dataset transfer)...")
    build_figure3()

    print(f"\nAll figures written to {FIG_DIR}")
