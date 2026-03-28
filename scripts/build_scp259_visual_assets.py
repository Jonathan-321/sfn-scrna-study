#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "results" / "uc_scp259" / "benchmarks"
CFN = ROOT / "results" / "uc_scp259" / "cfn_benchmarks"
FIG_DIR = ROOT / "results" / "uc_scp259" / "figures"
TEX_DIR = ROOT / "results" / "uc_scp259" / "reports" / "latex"


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TEX_DIR.mkdir(parents=True, exist_ok=True)


def setup_style() -> None:
    plt.style.use("ggplot")
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["axes.titlesize"] = 16
    plt.rcParams["axes.labelsize"] = 13
    plt.rcParams["legend.fontsize"] = 10


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{stem}.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def load_inputs() -> dict[str, pd.DataFrame]:
    import json

    with open(ROOT / "data" / "processed" / "uc_scp259" / "donor_healthy_vs_uc_folds.json") as f:
        folds = json.load(f)

    return {
        "meta": pd.read_csv(ROOT / "data" / "processed" / "uc_scp259" / "donor_metadata.tsv", sep="\t"),
        "folds": folds,
        "props_raw": pd.read_csv(ROOT / "data" / "processed" / "uc_scp259" / "donor_cluster_props.tsv", sep="\t"),
        "pbulk_raw": pd.read_csv(ROOT / "data" / "processed" / "uc_scp259" / "donor_all_cells_gene_log1p_cpm.tsv.gz", sep="\t"),
        "comp_repeated": pd.read_csv(BENCH / "donor_cluster_props_repeated_summary.tsv", sep="\t"),
        "pbulk_repeated": pd.read_csv(BENCH / "donor_all_cells_pseudobulk_repeated_summary.tsv", sep="\t"),
        "comp_lodo": pd.read_csv(BENCH / "donor_cluster_props_lodo_summary.tsv", sep="\t"),
        "pbulk_lodo": pd.read_csv(BENCH / "donor_all_cells_pseudobulk_lodo_summary.tsv", sep="\t"),
        "compartment_comp": pd.read_csv(BENCH / "donor_compartment_cluster_props_baselines_summary.tsv", sep="\t"),
        "compartment_pbulk": pd.read_csv(BENCH / "donor_compartment_pseudobulk_baselines_summary.tsv", sep="\t"),
        "cfn_global": pd.read_csv(CFN / "donor_cluster_props_cfn_full_summary.csv"),
        "cfn_comp": pd.read_csv(CFN / "donor_compartment_cluster_props_cfn_full_summary.csv"),
        "cfn_stab_global": pd.read_csv(CFN / "donor_cluster_props_cfn_full_stability_summary.csv"),
        "cfn_stab_comp": pd.read_csv(CFN / "donor_compartment_cluster_props_cfn_full_stability_summary.csv"),
        "edge_v3": pd.read_csv(CFN / "uc_recurring_edge_annotation_final_v3.csv"),
    }


def build_split_audit_figure(data: dict[str, pd.DataFrame]) -> None:
    meta = data["meta"].copy()
    label_counts = meta["donor_label"].value_counts().reindex(["Healthy", "UC"])

    folds = data["folds"]["folds"]
    fold_rows = []
    test_map = {}
    for fold in folds:
        fold_name = f"Fold {fold['fold'] + 1}"
        test_ids = set(fold["test_ids"])
        test_map[fold_name] = test_ids
        for label in ["Healthy", "UC"]:
            count = meta.loc[
                meta["donor_id"].isin(test_ids) & (meta["donor_label"] == label), "donor_id"
            ].nunique()
            fold_rows.append({"fold": fold_name, "label": label, "count": count})
    fold_df = pd.DataFrame(fold_rows)

    donor_order = (
        meta.sort_values(["donor_label", "donor_id"], ascending=[False, True])["donor_id"].tolist()
    )
    assignment = pd.DataFrame(
        0,
        index=donor_order,
        columns=[f"Fold {i + 1}" for i in range(len(folds))],
    )
    for fold_name, test_ids in test_map.items():
        for donor_id in test_ids:
            assignment.loc[donor_id, fold_name] = 1

    fig = plt.figure(figsize=(15, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.5], width_ratios=[1, 1.2])
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, :])

    ax1.bar(label_counts.index, label_counts.values, color=["#0f766e", "#b91c1c"])
    for i, v in enumerate(label_counts.values):
        ax1.text(i, v + 0.2, str(v), ha="center", va="bottom", fontsize=11)
    ax1.set_title("Donor Label Counts")
    ax1.set_ylabel("Donors")

    fold_pivot = fold_df.pivot(index="fold", columns="label", values="count").fillna(0)
    x = np.arange(len(fold_pivot.index))
    width = 0.35
    ax2.bar(x - width / 2, fold_pivot["Healthy"].values, width=width, color="#0f766e", label="Healthy")
    ax2.bar(x + width / 2, fold_pivot["UC"].values, width=width, color="#b91c1c", label="UC")
    ax2.set_xticks(x)
    ax2.set_xticklabels(fold_pivot.index)
    ax2.set_title("Held-Out Donors Per Fold")
    ax2.set_ylabel("Test donors")
    ax2.set_xlabel("")
    ax2.legend(frameon=True)

    label_lookup = meta.set_index("donor_id")["donor_label"].to_dict()
    yticklabels = [f"{d} ({'H' if label_lookup[d] == 'Healthy' else 'UC'})" for d in assignment.index]
    ax3.imshow(assignment.values, aspect="auto", cmap=plt.cm.Blues, vmin=0, vmax=1)
    ax3.set_title("Each donor appears in test exactly once")
    ax3.set_xlabel("")
    ax3.set_ylabel("Donor")
    ax3.set_xticks(np.arange(assignment.shape[1]))
    ax3.set_xticklabels(list(assignment.columns))
    ax3.set_yticks(np.arange(assignment.shape[0]))
    ax3.set_yticklabels(yticklabels, rotation=0, fontsize=8)
    for i in range(assignment.shape[0] + 1):
        ax3.axhline(i - 0.5, color="white", linewidth=0.4)
    for j in range(assignment.shape[1] + 1):
        ax3.axvline(j - 0.5, color="white", linewidth=0.8)

    fig.suptitle("SCP259 Cohort and Split Audit", y=1.02)
    save_figure(fig, "figure1_scp259_cohort_and_split_audit")


def build_overview_diagram() -> None:
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_axis_off()

    boxes = [
        ((0.03, 0.35), 0.18, 0.28, "Raw scRNA Atlas\nSCP259\n30 donors"),
        ((0.28, 0.35), 0.18, 0.28, "Donor Aggregation\nOne row per donor\nLeakage-safe unit"),
        ((0.53, 0.57), 0.18, 0.18, "Donor-global\nComposition"),
        ((0.53, 0.17), 0.18, 0.18, "Donor-global\nPseudobulk"),
        ((0.76, 0.57), 0.18, 0.18, "Repeated 5-fold\n+ LODO"),
        ((0.76, 0.17), 0.18, 0.18, "Compartment-aware\nEpi / LP"),
    ]

    for (x, y), w, h, label in boxes:
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.03",
            linewidth=1.8,
            edgecolor="#1f2937",
            facecolor="#f8fafc",
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=13)

    arrows = [
        ((0.21, 0.49), (0.28, 0.49)),
        ((0.46, 0.49), (0.53, 0.66)),
        ((0.46, 0.49), (0.53, 0.26)),
        ((0.71, 0.66), (0.76, 0.66)),
        ((0.71, 0.26), (0.76, 0.26)),
    ]

    for start, end in arrows:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=18,
                linewidth=1.8,
                color="#334155",
            )
        )

    ax.text(
        0.76,
        0.48,
        "StructuralCFN on\ncomposition-based tables\n+ stability diagnostics",
        ha="center",
        va="center",
        fontsize=13,
        color="#7c2d12",
        fontweight="bold",
    )
    ax.set_title("SCP259 Donor-Aware Benchmark Overview", pad=20)
    save_figure(fig, "figure2_scp259_benchmark_overview")


def _pca_coords(df: pd.DataFrame, feature_cols: list[str], top_var_k: int | None = None) -> np.ndarray:
    x = df[feature_cols].to_numpy(dtype=float)
    if top_var_k is not None and x.shape[1] > top_var_k:
        var = np.var(x, axis=0)
        keep = np.argsort(var)[::-1][:top_var_k]
        x = x[:, keep]
    x = x - x.mean(axis=0, keepdims=True)
    std = x.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    x = x / std
    u, s, _ = np.linalg.svd(x, full_matrices=False)
    return u[:, :2] * s[:2]


def build_input_representation_figure(data: dict[str, pd.DataFrame]) -> None:
    meta = data["meta"][["donor_id", "donor_label"]].copy()

    props = data["props_raw"].copy()
    props = props.merge(meta, on="donor_id", how="left")
    prop_coords = _pca_coords(props, [c for c in props.columns if c not in {"donor_id", "donor_label"}])

    pbulk = data["pbulk_raw"].copy()
    pbulk = pbulk.merge(meta, on="donor_id", how="left")
    pbulk_coords = _pca_coords(
        pbulk,
        [c for c in pbulk.columns if c not in {"donor_id", "donor_label"}],
        top_var_k=1000,
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    palette = {"Healthy": "#0f766e", "UC": "#b91c1c"}
    for ax, coords, frame, title in [
        (axes[0], prop_coords, props, "Donor-global composition input space"),
        (axes[1], pbulk_coords, pbulk, "Donor-global pseudobulk input space"),
    ]:
        for label, color in palette.items():
            mask = frame["donor_label"] == label
            ax.scatter(coords[mask, 0], coords[mask, 1], s=80, color=color, label=label, alpha=0.9)
        ax.set_xlabel("PC1")
        ax.set_ylabel("PC2")
        ax.set_title(title)
    axes[1].legend(frameon=True, loc="best")
    axes[0].legend(frameon=True, loc="best")
    fig.suptitle("Input Representations Separate Donors Differently", y=1.02)
    save_figure(fig, "figure3_scp259_input_representations")


def _grouped_bar(ax, labels, series, colors, ylabel, title, ylim=None):
    x = np.arange(len(labels))
    width = 0.24
    offsets = np.linspace(-width, width, num=len(series))
    for (name, values), color, offset in zip(series.items(), colors, offsets):
        bars = ax.bar(x + offset, values, width=width, label=name, color=color)
        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{bar.get_height():.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=90,
            )
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(frameon=True)


def build_global_baseline_plot(data: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    comp_rep = data["comp_repeated"].set_index("model")
    pbulk_rep = data["pbulk_repeated"].set_index("model")
    _grouped_bar(
        axes[0],
        ["LogReg", "LinearSVM", "XGBoost"],
        {
            "Composition": [
                comp_rep.loc["logreg", "roc_auc_mean"],
                comp_rep.loc["linear_svm", "roc_auc_mean"],
                comp_rep.loc["xgb", "roc_auc_mean"],
            ],
            "Pseudobulk": [
                pbulk_rep.loc["logreg", "roc_auc_mean"],
                pbulk_rep.loc["linear_svm", "roc_auc_mean"],
                pbulk_rep.loc["xgb", "roc_auc_mean"],
            ],
        },
        ["#0f766e", "#b45309"],
        "AUROC",
        "Repeated 5-fold Donor CV",
        ylim=(0.65, 1.05),
    )

    comp_lodo = data["comp_lodo"].set_index("model")
    pbulk_lodo = data["pbulk_lodo"].set_index("model")
    _grouped_bar(
        axes[1],
        ["LogReg", "LinearSVM", "XGBoost"],
        {
            "Composition": [
                comp_lodo.loc["logreg", "roc_auc"],
                comp_lodo.loc["linear_svm", "roc_auc"],
                comp_lodo.loc["xgb", "roc_auc"],
            ],
            "Pseudobulk": [
                pbulk_lodo.loc["logreg", "roc_auc"],
                pbulk_lodo.loc["linear_svm", "roc_auc"],
                pbulk_lodo.loc["xgb", "roc_auc"],
            ],
        },
        ["#0f766e", "#b45309"],
        "AUROC",
        "Leave-One-Donor-Out",
        ylim=(0.65, 1.05),
    )

    fig.suptitle("Donor-Global Benchmark Performance", y=1.05)
    save_figure(fig, "figure4_donor_global_benchmarks")


def build_compartment_heatmap(data: dict[str, pd.DataFrame]) -> None:
    comp = data["compartment_comp"].copy()
    comp["representation"] = "Compartment composition"
    pbulk = data["compartment_pbulk"].copy()
    pbulk["representation"] = "Compartment pseudobulk"
    df = pd.concat([comp, pbulk], ignore_index=True)
    heat = df.pivot(index="representation", columns="model", values="roc_auc_mean")
    heat = heat.rename(columns={"logreg": "LogReg", "linear_svm": "LinearSVM", "xgb": "XGBoost"})

    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(heat.values, aspect="auto", cmap="YlOrBr", vmin=0.65, vmax=1.0)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax.text(j, i, f"{heat.iloc[i, j]:.3f}", ha="center", va="center", fontsize=11)
    ax.set_title("Compartment-Aware Extension")
    ax.set_xlabel("Model")
    ax.set_ylabel("")
    ax.set_xticks(np.arange(heat.shape[1]))
    ax.set_xticklabels(list(heat.columns))
    ax.set_yticks(np.arange(heat.shape[0]))
    ax.set_yticklabels(list(heat.index))
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("AUROC")
    save_figure(fig, "figure5_compartment_extension_heatmap")


def build_cfn_diagnostics_plot(data: dict[str, pd.DataFrame]) -> None:
    labels = ["Donor-global\ncomposition", "Compartment-aware\ncomposition"]
    cfn_global = data["cfn_global"].iloc[0]
    cfn_comp = data["cfn_comp"].iloc[0]
    stab_global = data["cfn_stab_global"].iloc[0]
    stab_comp = data["cfn_stab_comp"].iloc[0]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    metrics = {
        "AUROC": [cfn_global["roc_auc_mean"], cfn_comp["roc_auc_mean"]],
        "PR-AUC": [cfn_global["pr_auc_mean"], cfn_comp["pr_auc_mean"]],
        "Brier": [cfn_global["brier_mean"], cfn_comp["brier_mean"]],
    }
    x = np.arange(len(labels))
    width = 0.22
    for idx, (name, vals) in enumerate(metrics.items()):
        bars = axes[0].bar(
            x + (idx - 1) * width,
            vals,
            width=width,
            label=name,
            color=["#1d4ed8", "#0f766e", "#b91c1c"][idx],
        )
        for bar in bars:
            axes[0].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{bar.get_height():.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=90,
            )
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels)
    axes[0].set_ylim(0, 1.1)
    axes[0].set_title("CFN Predictive Metrics")
    axes[0].legend(frameon=True)

    structure = {
        "Grouped Jaccard": [
            stab_global["group_topk_jaccard_mean"],
            stab_comp["group_topk_jaccard_mean"],
        ],
        "Sign consistency": [
            stab_global["sign_consistency_mean"],
            stab_comp["sign_consistency_mean"],
        ],
        "Matrix cosine": [0.536630, 0.450702],
    }
    for idx, (name, vals) in enumerate(structure.items()):
        bars = axes[1].bar(
            x + (idx - 1) * width,
            vals,
            width=width,
            label=name,
            color=["#7c3aed", "#15803d", "#ea580c"][idx],
        )
        for bar in bars:
            axes[1].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{bar.get_height():.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=90,
            )
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("CFN Structural Diagnostics")
    axes[1].legend(frameon=True)

    fig.suptitle("StructuralCFN: Prediction Improves, Stability Does Not", y=1.05)
    save_figure(fig, "figure6_cfn_performance_vs_stability")


def build_edge_theme_figure(data: dict[str, pd.DataFrame]) -> None:
    edges = data["edge_v3"].query("use_recommendation == 'main_text'").copy()
    edges = edges[["edge_label", "biological_theme", "verification_status"]]

    fig, ax = plt.subplots(figsize=(12, 3.6))
    ax.set_axis_off()
    tbl = ax.table(
        cellText=edges.values,
        colLabels=["Edge", "Theme", "Status"],
        loc="center",
        cellLoc="left",
        colLoc="left",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.6)
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor("#1f2937")
        else:
            cell.set_facecolor("#f8fafc" if row % 2 else "#eef2ff")
    ax.set_title("Biologically Coherent Recurring CFN Edge Themes", pad=18)
    save_figure(fig, "figure7_recurring_edge_themes")


def _fmt(x: float) -> str:
    return f"{x:.3f}"


def build_latex_tables(data: dict[str, pd.DataFrame]) -> None:
    comp_rep = data["comp_repeated"].copy()
    pbulk_rep = data["pbulk_repeated"].copy()
    rep = pd.concat([comp_rep.assign(representation="Composition"), pbulk_rep.assign(representation="Pseudobulk")])
    rep["Model"] = rep["model"].map({"logreg": "LogReg", "linear_svm": "LinearSVM", "xgb": "XGBoost"})
    rep = rep[["representation", "Model", "roc_auc_mean", "pr_auc_mean", "balanced_accuracy_mean", "macro_f1_mean"]]
    rep.columns = ["Representation", "Model", "AUROC", "PRAUC", "BalancedAcc", "MacroF1"]
    for c in ["AUROC", "PRAUC", "BalancedAcc", "MacroF1"]:
        rep[c] = rep[c].map(_fmt)
    (TEX_DIR / "table1_donor_global_repeated.tex").write_text(
        rep.to_latex(index=False, escape=False, caption="Donor-global benchmark under repeated 5-fold donor CV.")
    )

    lodo = pd.concat(
        [
            data["comp_lodo"].assign(representation="Composition"),
            data["pbulk_lodo"].assign(representation="Pseudobulk"),
        ]
    )
    lodo["Model"] = lodo["model"].map({"logreg": "LogReg", "linear_svm": "LinearSVM", "xgb": "XGBoost"})
    lodo = lodo[["representation", "Model", "roc_auc", "pr_auc", "balanced_accuracy", "accuracy"]]
    lodo.columns = ["Representation", "Model", "AUROC", "PRAUC", "BalancedAcc", "Accuracy"]
    for c in ["AUROC", "PRAUC", "BalancedAcc", "Accuracy"]:
        lodo[c] = lodo[c].map(_fmt)
    (TEX_DIR / "table2_donor_global_lodo.tex").write_text(
        lodo.to_latex(index=False, escape=False, caption="Leave-one-donor-out robustness check.")
    )

    comp = data["compartment_comp"].assign(representation="Compartment composition")
    pbulk = data["compartment_pbulk"].assign(representation="Compartment pseudobulk")
    ext = pd.concat([comp, pbulk])
    ext["Model"] = ext["model"].map({"logreg": "LogReg", "linear_svm": "LinearSVM", "xgb": "XGBoost"})
    ext = ext[["representation", "Model", "roc_auc_mean", "pr_auc_mean", "balanced_accuracy_mean", "macro_f1_mean"]]
    ext.columns = ["Representation", "Model", "AUROC", "PRAUC", "BalancedAcc", "MacroF1"]
    for c in ["AUROC", "PRAUC", "BalancedAcc", "MacroF1"]:
        ext[c] = ext[c].map(_fmt)
    (TEX_DIR / "table3_compartment_extension.tex").write_text(
        ext.to_latex(index=False, escape=False, caption="Compartment-aware benchmark extension.")
    )

    cfn_global = data["cfn_global"].iloc[0]
    cfn_comp = data["cfn_comp"].iloc[0]
    stab_global = data["cfn_stab_global"].iloc[0]
    stab_comp = data["cfn_stab_comp"].iloc[0]
    cfn_tbl = pd.DataFrame(
        [
            {
                "Representation": "Donor-global composition",
                "AUROC": _fmt(cfn_global["roc_auc_mean"]),
                "PRAUC": _fmt(cfn_global["pr_auc_mean"]),
                "Brier": _fmt(cfn_global["brier_mean"]),
                "GroupedJaccard": _fmt(stab_global["group_topk_jaccard_mean"]),
                "SignConsistency": _fmt(stab_global["sign_consistency_mean"]),
                "MatrixCosine": _fmt(0.536630),
            },
            {
                "Representation": "Compartment-aware composition",
                "AUROC": _fmt(cfn_comp["roc_auc_mean"]),
                "PRAUC": _fmt(cfn_comp["pr_auc_mean"]),
                "Brier": _fmt(cfn_comp["brier_mean"]),
                "GroupedJaccard": _fmt(stab_comp["group_topk_jaccard_mean"]),
                "SignConsistency": _fmt(stab_comp["sign_consistency_mean"]),
                "MatrixCosine": _fmt(0.450702),
            },
        ]
    )
    (TEX_DIR / "table4_cfn_diagnostics.tex").write_text(
        cfn_tbl.to_latex(index=False, escape=False, caption="StructuralCFN predictive and structural diagnostics.")
    )


def main() -> None:
    ensure_dirs()
    setup_style()
    data = load_inputs()
    build_split_audit_figure(data)
    build_overview_diagram()
    build_input_representation_figure(data)
    build_global_baseline_plot(data)
    build_compartment_heatmap(data)
    build_cfn_diagnostics_plot(data)
    build_edge_theme_figure(data)
    build_latex_tables(data)
    print(f"Wrote visual assets to {FIG_DIR}")
    print(f"Wrote LaTeX tables to {TEX_DIR}")


if __name__ == "__main__":
    main()
