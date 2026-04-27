"""Publication-quality figure generation.

All figures are written as SVG (vectorized, editable) with text preserved as
text rather than converted to paths. Each figure function takes the relevant
data plus an output path.

To regenerate as PNG, edit the file extension or wrap with `_save_png_too`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Patch
from scipy import stats
from sklearn.tree import plot_tree

from rdp_analytics.step1_stats import jonckheere_terpstra, fmt_p, wilson_ci, pairwise_fisher_vs_reference


# ===== Global publication settings =====
mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = ["DejaVu Serif", "Liberation Serif", "Times New Roman"]
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["svg.fonttype"] = "none"  # keep text as text in SVG
mpl.rcParams["axes.spines.top"] = False
mpl.rcParams["axes.spines.right"] = False
mpl.rcParams["axes.linewidth"] = 0.8


# Short labels used across figures
DOMAIN_SHORT = [
    "Housing", "Employment", "Education", "Treatment\nconnection",
    "Community\nconnection", "Recovery\nsupport", "Probation",
    "Overdose hx", "Co-occurring\nMH", "Multiple\ntx episodes",
]
PATHWAY_SHORT = [
    "Abstinence", "12-Step", "Support\ngroups", "Natural\nrecovery",
    "Peer\nrecovery", "MAT", "Harm\nreduction", "Alt./\nholistic",
]


def _save(fig, out_path: str | Path) -> None:
    """Save a figure as both SVG and PNG (PNG path derived from SVG path)."""
    out_path = Path(out_path)
    fig.savefig(out_path, bbox_inches="tight")
    png_path = out_path.with_suffix(".png")
    fig.savefig(png_path, bbox_inches="tight", dpi=200)
    plt.close(fig)


# =====================================================================
# Figure 1: Distributions
# =====================================================================

def figure_1_distributions(person: pd.DataFrame, out_path: str | Path) -> None:
    """Need complexity and pathway diversity histograms."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)

    nc = person["need_complexity"].dropna().astype(int)
    ax = axes[0]
    counts = nc.value_counts().sort_index()
    bars = ax.bar(counts.index, counts.values, color="#2a4d6e", edgecolor="white", linewidth=0.6)
    ax.axvline(nc.median(), color="#c44e52", linestyle="--", linewidth=1.3, label=f"Median = {nc.median():.0f}")
    ax.set_xlabel("Number of need domains endorsed at intake", fontsize=11)
    ax.set_ylabel("Number of participants", fontsize=11)
    ax.set_xticks(range(0, 12))
    ax.set_xlim(-0.5, 11.5)
    ax.set_title(f"A. Need complexity (n = {len(nc):,})", fontsize=12, loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 5, f"{v}", ha="center", fontsize=8, color="#444")

    pd_s = person["pathway_diversity"].dropna().astype(int)
    ax = axes[1]
    counts = pd_s.value_counts().sort_index()
    bars = ax.bar(counts.index, counts.values, color="#3a7d44", edgecolor="white", linewidth=0.6)
    ax.axvline(pd_s.median(), color="#c44e52", linestyle="--", linewidth=1.3, label=f"Median = {pd_s.median():.0f}")
    ax.set_xlabel("Number of recovery pathway components endorsed", fontsize=11)
    ax.set_ylabel("Number of participants", fontsize=11)
    ax.set_xticks(range(0, 9))
    ax.set_xlim(-0.5, 8.5)
    ax.set_title(f"B. Pathway diversity (n = {len(pd_s):,})", fontsize=12, loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 5, f"{v}", ha="center", fontsize=8, color="#444")

    fig.suptitle("Figure 1. Multidomain need and pathway diversity at intake",
                 fontsize=13, fontweight="bold", x=0.02, y=1.04, ha="left")
    _save(fig, out_path)


# =====================================================================
# Figure 2: Need-pathway heatmap
# =====================================================================

def figure_2_heatmap(
    np_matrix: dict, need_domains: Sequence[str], pathway_components: Sequence[str],
    out_path: str | Path
) -> None:
    """Need-by-pathway adoption heatmap with FDR-corrected significance."""
    diff_pp = np_matrix["diff_pp"]
    qvals = np_matrix["qvals"]
    pct_with = np_matrix["pct_with"]
    n_with_need = np_matrix["n_with_need"]
    N = np_matrix["N"]

    fig, ax = plt.subplots(figsize=(10.5, 6.5), constrained_layout=True)
    norm = TwoSlopeNorm(vmin=-30, vcenter=0, vmax=30)
    im = ax.imshow(diff_pp, cmap="RdBu_r", norm=norm, aspect="auto")

    for i in range(len(need_domains)):
        for j in range(len(pathway_components)):
            sig = "***" if qvals[i, j] < 0.001 else ("**" if qvals[i, j] < 0.01 else ("*" if qvals[i, j] < 0.05 else ""))
            txt = f"{pct_with[i, j]:.0f}%"
            if sig:
                txt += f"\n{sig}"
            v = diff_pp[i, j]
            text_color = "white" if abs(v) > 18 else "black"
            ax.text(j, i, txt, ha="center", va="center", fontsize=9,
                    color=text_color, fontweight="bold" if sig else "normal")

    ax.set_xticks(range(len(pathway_components)))
    ax.set_xticklabels(PATHWAY_SHORT, fontsize=10)
    ax.set_yticks(range(len(need_domains)))
    ax.set_yticklabels([f"{s}\n(n={n})" for s, n in zip(DOMAIN_SHORT, n_with_need)], fontsize=9.5)
    ax.set_xlabel("Recovery pathway component", fontsize=11.5, labelpad=10)
    ax.set_ylabel("Need domain at intake", fontsize=11.5, labelpad=8)
    ax.tick_params(axis="both", length=0)

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("Pathway adoption: percentage-point difference\n"
                   "(participants with need minus those without)", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    ax.set_title(
        f"Figure 2. Pathway adoption by need domain (n = {N:,})\n"
        f"Cell value: % of participants with that need who endorse that pathway. "
        f"Color: percentage-point shift vs participants without that need.\n"
        f"* q<0.05, ** q<0.01, *** q<0.001 (Fisher's exact, Benjamini-Hochberg FDR-corrected, 80 tests)",
        fontsize=11, fontweight="bold", loc="left", pad=14,
    )
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.5)
        spine.set_color("#888")

    _save(fig, out_path)


# =====================================================================
# Figure 3: Retention by complexity and pathway diversity
# =====================================================================

def figure_3_retention(ml: pd.DataFrame, out_path: str | Path) -> None:
    """Engagement % and duration by need complexity and pathway diversity."""
    sub = ml[ml["need_complexity"].notna() & ml["pathway_diversity"].notna()].copy()
    sub["need_complexity"] = sub["need_complexity"].astype(int)
    sub["pathway_diversity"] = sub["pathway_diversity"].astype(int)
    N = len(sub)

    nc_groups = sub.groupby("need_complexity").agg(
        n=("SAFEID", "count"), eng=("engaged", "sum"), median_d=("Days Engaged", "median"))
    nc_groups["pct_eng"] = 100 * nc_groups["eng"] / nc_groups["n"]
    pd_groups = sub.groupby("pathway_diversity").agg(
        n=("SAFEID", "count"), eng=("engaged", "sum"), median_d=("Days Engaged", "median"))
    pd_groups["pct_eng"] = 100 * pd_groups["eng"] / pd_groups["n"]

    nc_levels = sorted(sub["need_complexity"].unique())
    nc_eng_groups = [sub[sub.need_complexity == k]["engaged"].values for k in nc_levels]
    nc_days_groups = [sub[sub.need_complexity == k]["Days Engaged"].dropna().values for k in nc_levels]
    z_nc_eng, p_nc_eng = jonckheere_terpstra(nc_eng_groups)
    z_nc_days, p_nc_days = jonckheere_terpstra(nc_days_groups)

    pd_levels = sorted(sub["pathway_diversity"].unique())
    pd_eng_groups = [sub[sub.pathway_diversity == k]["engaged"].values for k in pd_levels]
    pd_days_groups = [sub[sub.pathway_diversity == k]["Days Engaged"].dropna().values for k in pd_levels]
    z_pd_eng, p_pd_eng = jonckheere_terpstra(pd_eng_groups)
    z_pd_days, p_pd_days = jonckheere_terpstra(pd_days_groups)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), constrained_layout=True)

    def _engagement_panel(ax, groups, color, xlabel, title_text):
        x = groups.index.values
        y = groups["pct_eng"].values
        ns = groups["n"].values
        ci_lo, ci_hi = [], []
        for k_, n in zip(groups["eng"].values, ns):
            lo, hi = wilson_ci(int(k_), int(n))
            ci_lo.append(lo); ci_hi.append(hi)
        ci_lo = np.array(ci_lo); ci_hi = np.array(ci_hi)
        ax.errorbar(x, y, yerr=[y - ci_lo, ci_hi - y], fmt="o-", color=color,
                    markersize=8, linewidth=1.5, capsize=4, capthick=1, ecolor=color)
        for xi, yi, ni in zip(x, y, ns):
            ax.annotate(f"n={ni}", (xi, yi), xytext=(0, 12), textcoords="offset points",
                        ha="center", fontsize=8, color="#555")
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel("% engaged at last observation\n(with 95% CI)", fontsize=11)
        ax.set_xticks(range(0, max(x) + 1))
        ax.set_ylim(30, 100)
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.set_axisbelow(True)
        ax.set_title(title_text, fontsize=11.5, fontweight="bold", loc="left")

    _engagement_panel(
        axes[0, 0], nc_groups, "#2a4d6e",
        "Need complexity (number of need domains at intake)",
        f"A. Engagement by need complexity\nJonckheere-Terpstra: z = {z_nc_eng:+.2f}, {fmt_p(p_nc_eng)}",
    )
    _engagement_panel(
        axes[0, 1], pd_groups, "#3a7d44",
        "Pathway diversity (number of components endorsed)",
        f"B. Engagement by pathway diversity\nJonckheere-Terpstra: z = {z_pd_eng:+.2f}, {fmt_p(p_pd_eng)}",
    )

    def _box_panel(ax, groups, base_color, edge_color, xlabel, title_text):
        data, labels = [], []
        for k in groups.index:
            arr = sub[sub[groups.index.name] == k]["Days Engaged"].dropna().values
            if len(arr) > 0:
                data.append(arr); labels.append(int(k))
        bp = ax.boxplot(data, positions=labels, widths=0.6, patch_artist=True,
                        showfliers=False, medianprops=dict(color="#c44e52", linewidth=1.6))
        for patch in bp["boxes"]:
            patch.set_facecolor(base_color); patch.set_edgecolor(edge_color)
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel("Engagement duration (days)", fontsize=11)
        ax.set_xticks(range(0, max(labels) + 1))
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.set_axisbelow(True)
        ax.set_title(title_text, fontsize=11.5, fontweight="bold", loc="left")

    _box_panel(
        axes[1, 0], nc_groups, "#bcd0e3", "#2a4d6e", "Need complexity",
        f"C. Engagement duration by need complexity\nJonckheere-Terpstra: z = {z_nc_days:+.2f}, {fmt_p(p_nc_days)}",
    )
    _box_panel(
        axes[1, 1], pd_groups, "#c4ddc6", "#3a7d44", "Pathway diversity",
        f"D. Engagement duration by pathway diversity\nJonckheere-Terpstra: z = {z_pd_days:+.2f}, {fmt_p(p_pd_days)}",
    )

    fig.suptitle(f"Figure 3. Retention by need complexity and pathway diversity (n = {N:,})",
                 fontsize=13, fontweight="bold", x=0.02, y=1.02, ha="left")
    _save(fig, out_path)


# =====================================================================
# Figure 4: Severity composite x pathway adoption
# =====================================================================

def figure_4_severity(person: pd.DataFrame, pathway_components: Sequence[str], out_path: str | Path) -> None:
    """Recovery pathway adoption stratified by clinical severity composite."""
    sev = person.copy()
    sev["severity_score"] = sev["severity_score"].clip(upper=3)
    sev_levels = sorted(sev["severity_score"].unique())
    n_per_sev = [(sev.severity_score == s).sum() for s in sev_levels]

    pathways_to_show = list(pathway_components)
    path_cols = [f"path_{p.replace(' ', '_').replace('-', '_').replace('/', '_')}" for p in pathways_to_show]
    adoption = np.zeros((len(pathways_to_show), len(sev_levels)))
    for i, col in enumerate(path_cols):
        for j, s in enumerate(sev_levels):
            sub = sev[sev.severity_score == s]
            adoption[i, j] = sub[col].mean() * 100

    trends = {}
    for i, col in enumerate(path_cols):
        groups = [sev[sev.severity_score == s][col].values for s in sev_levels]
        z, p = jonckheere_terpstra(groups)
        trends[pathways_to_show[i]] = (z, p)

    fig, ax = plt.subplots(figsize=(11, 5.5), constrained_layout=True)
    x_pos = np.arange(len(pathways_to_show))
    width = 0.20
    colors = ["#3a7d44", "#7eb377", "#dca94a", "#c44e52"]

    for j, s in enumerate(sev_levels):
        ax.bar(x_pos + (j - 1.5) * width, adoption[:, j], width,
               color=colors[j], edgecolor="white", linewidth=0.6,
               label=f"{int(s)}{'+' if j == len(sev_levels) - 1 and j >= 3 else ''} (n={n_per_sev[j]})")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(PATHWAY_SHORT, fontsize=10)
    ax.set_ylabel("% endorsing pathway", fontsize=11.5)
    ax.set_ylim(-12, 90)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(title="Severity composite score", loc="upper right", fontsize=9, title_fontsize=10, frameon=False)

    for i, p in enumerate(pathways_to_show):
        z, pv = trends[p]
        arrow = "↑" if z > 0 else "↓"
        sig = "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < 0.05 else "ns"))
        txt = f"{arrow} {sig}" if sig != "ns" else "ns"
        color_txt = "#000" if sig != "ns" else "#888"
        ax.text(x_pos[i], -7, txt, ha="center", va="top", fontsize=9.5,
                color=color_txt, fontweight="bold" if sig != "ns" else "normal")

    ax.set_title(
        f"Figure 4. Recovery pathway adoption by clinical severity composite (n = {len(sev):,})\n"
        "Severity = sum of: history of seizures, ≥1 naloxone administration, ≥2 ER visits, "
        "active suicidal ideation, overdose as referral need (range 0-4+)",
        fontsize=11, fontweight="bold", loc="left", pad=14,
    )
    _save(fig, out_path)


# =====================================================================
# Figure 5: Living situation x retention
# =====================================================================

def figure_5_lives_in(person: pd.DataFrame, out_path: str | Path) -> None:
    """Stratified retention by living situation; the recovery capital inversion."""
    order = ["Unhoused", "Shelter", "Halfway House", "Residential Treatment",
             "Recovery Residence", "Housed", "Other"]
    lf = person[person["Lives In"].isin(order)].copy()

    stats_by = lf.groupby("Lives In").agg(
        n=("SAFEID", "count"), eng=("engaged", "sum"),
        median_d=("Days Engaged", "median"),
    )
    stats_by["pct_eng"] = 100 * stats_by["eng"] / stats_by["n"]
    stats_by = stats_by.reindex(order)

    pw = pairwise_fisher_vs_reference(lf, "Lives In", "engaged", "Recovery Residence")
    qmap = dict(zip(pw["group"], pw["q"])) if "q" in pw.columns else {}

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True,
                             gridspec_kw={"width_ratios": [1, 1.05]})

    ax = axes[0]
    y = stats_by["pct_eng"].values
    ci_lo, ci_hi = [], []
    for k_, n in zip(stats_by["eng"].values, stats_by["n"].values):
        lo, hi = wilson_ci(int(k_), int(n))
        ci_lo.append(lo); ci_hi.append(hi)
    ci_lo = np.array(ci_lo); ci_hi = np.array(ci_hi)
    err_lo = y - ci_lo; err_hi = ci_hi - y
    bar_colors = []
    for cat in order:
        if cat == "Unhoused":
            bar_colors.append("#c44e52")
        elif cat == "Recovery Residence":
            bar_colors.append("#2a4d6e")
        else:
            bar_colors.append("#7da7c7")
    y_pos = np.arange(len(order))
    ax.barh(y_pos, y, xerr=[err_lo, err_hi], color=bar_colors, edgecolor="white",
            linewidth=0.6, error_kw={"capsize": 3, "capthick": 0.8, "ecolor": "#444"})
    for i, (cat, val, n) in enumerate(zip(order, y, stats_by["n"].values)):
        sig = ""
        if cat in qmap:
            q = qmap[cat]
            sig = "***" if q < 0.001 else ("**" if q < 0.01 else ("*" if q < 0.05 else ""))
        ax.text(val + 1.5, i, f"{val:.0f}%  (n={n})  {sig}", va="center", fontsize=9.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(order, fontsize=10.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 110)
    ax.set_xlabel("% engaged at last observation (with 95% CI)", fontsize=11)
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_title(
        "A. Engagement by living situation\n* q<0.05, ** q<0.01, *** q<0.001 vs Recovery Residence",
        fontsize=11, fontweight="bold", loc="left",
    )

    ax = axes[1]
    data, labels = [], []
    for cat in order:
        arr = lf[lf["Lives In"] == cat]["Days Engaged"].dropna().values
        if len(arr) > 0:
            data.append(arr); labels.append(cat)
    bp = ax.boxplot(data, positions=range(len(data)), widths=0.6, patch_artist=True,
                    vert=False, showfliers=False, medianprops=dict(color="#c44e52", linewidth=1.6))
    for patch, cat in zip(bp["boxes"], labels):
        if cat == "Unhoused":
            patch.set_facecolor("#f4cccc"); patch.set_edgecolor("#c44e52")
        elif cat == "Recovery Residence":
            patch.set_facecolor("#bcd0e3"); patch.set_edgecolor("#2a4d6e")
        else:
            patch.set_facecolor("#dde9f1"); patch.set_edgecolor("#7da7c7")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10.5)
    ax.invert_yaxis()
    ax.set_xlabel("Engagement duration (days)", fontsize=11)
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_title("B. Engagement duration by living situation", fontsize=11, fontweight="bold", loc="left")

    groups_kw = [lf[lf["Lives In"] == cat]["Days Engaged"].dropna().values for cat in order]
    groups_kw = [g for g in groups_kw if len(g) > 1]
    H, p_kw = stats.kruskal(*groups_kw)
    ax.text(0.99, 0.02, f"Kruskal-Wallis: H = {H:.1f}, {fmt_p(p_kw)}",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5, color="#444",
            bbox=dict(facecolor="white", edgecolor="#ccc", boxstyle="round,pad=0.3"))

    fig.suptitle(
        f"Figure 5. Living situation, retention, and the recovery-capital inversion (n = {len(lf):,})",
        fontsize=13, fontweight="bold", x=0.02, y=1.04, ha="left",
    )
    _save(fig, out_path)


# =====================================================================
# Figure 6: LCA
# =====================================================================

def figure_6_lca(
    selection: pd.DataFrame, rho: np.ndarray, pi: np.ndarray, ml: pd.DataFrame,
    need_domains: Sequence[str], pathway_components: Sequence[str],
    out_path: str | Path
) -> None:
    """LCA model selection, profiles, engagement, pathways, and durations."""
    fig = plt.figure(figsize=(13.5, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.2], width_ratios=[1, 1.5, 1])

    # A: Model selection
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(selection["k"], selection["BIC"], "o-", color="#2a4d6e", label="BIC", linewidth=1.5, markersize=7)
    ax.plot(selection["k"], selection["AIC"], "s-", color="#7da7c7", label="AIC", linewidth=1.5, markersize=7)
    best_k = int(selection.loc[selection["BIC"].idxmin(), "k"])
    ax.axvline(best_k, color="#c44e52", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.text(best_k, ax.get_ylim()[1] * 0.98, f" k = {best_k}\n (BIC min)",
            color="#c44e52", fontsize=9, va="top", ha="left")
    ax.set_xlabel("Number of latent classes", fontsize=11)
    ax.set_ylabel("Information criterion", fontsize=11)
    ax.set_xticks(range(2, 8))
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    ax.set_title("A. Class selection\nBernoulli mixture EM", fontsize=11, fontweight="bold", loc="left")

    # B: Class profiles heatmap
    ax = fig.add_subplot(gs[0, 1:])
    im = ax.imshow(rho, aspect="auto", cmap="RdYlBu_r", vmin=0, vmax=1)
    K = rho.shape[0]
    for i in range(K):
        for j in range(rho.shape[1]):
            v = rho[i, j]
            tc = "white" if (v > 0.7 or v < 0.15) else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9,
                    color=tc, fontweight="bold" if v >= 0.5 else "normal")
    ax.set_xticks(range(rho.shape[1]))
    ax.set_xticklabels(DOMAIN_SHORT[:rho.shape[1]], fontsize=9)
    ax.set_yticks(range(K))
    ax.set_yticklabels([f"C{i+1} (n={int(p*len(ml))}, {p*100:.1f}%)" for i, p in enumerate(pi)], fontsize=9.5)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Item-response probability", fontsize=9)
    ax.set_title("B. Latent class need-domain profiles", fontsize=11, fontweight="bold", loc="left")
    for spine in ax.spines.values():
        spine.set_visible(True); spine.set_linewidth(0.5); spine.set_color("#888")

    # C: % engaged by class
    ax = fig.add_subplot(gs[1, 0])
    class_eng = ml.groupby("lca_class_ordered").agg(n=("SAFEID", "count"), eng=("engaged", "sum"))
    class_eng["pct"] = 100 * class_eng["eng"] / class_eng["n"]
    ci_lo, ci_hi = [], []
    for k_, n_ in zip(class_eng["eng"], class_eng["n"]):
        lo, hi = wilson_ci(int(k_), int(n_))
        ci_lo.append(lo); ci_hi.append(hi)
    ci_lo = np.array(ci_lo); ci_hi = np.array(ci_hi)
    y = class_eng["pct"].values
    colors = ["#7eb377", "#dca94a", "#7da7c7", "#2a4d6e", "#c44e52"][:K]
    ax.bar(range(K), y, yerr=[y - ci_lo, ci_hi - y], color=colors,
           edgecolor="white", linewidth=0.6,
           error_kw={"capsize": 3, "capthick": 0.8, "ecolor": "#444"})
    for i, (val, n_) in enumerate(zip(y, class_eng["n"])):
        ax.text(i, val + 2, f"{val:.0f}%\nn={n_}", ha="center", fontsize=8.5, color="#333")
    ax.set_xticks(range(K))
    ax.set_xticklabels([f"C{i+1}" for i in range(K)], fontsize=10)
    ax.set_ylabel("% engaged at last observation\n(95% CI)", fontsize=11)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    contingency = ml.groupby("lca_class_ordered")["engaged"].value_counts().unstack(fill_value=0).values
    chi2, p_chi, dof, _ = stats.chi2_contingency(contingency)
    ax.set_title(f"C. Engagement by latent class\n\u03c7\u00b2({dof}) = {chi2:.1f}, {fmt_p(p_chi)}",
                 fontsize=11, fontweight="bold", loc="left")

    # D: pathway adoption by class
    ax = fig.add_subplot(gs[1, 1])
    pcs_short = ["Abst.", "12-Step", "Support\ngroups", "Natural", "Peer", "MAT", "HR", "Alt."]
    path_cols = [f"path_{p.replace(' ', '_').replace('-', '_').replace('/', '_')}" for p in pathway_components]
    path_pct = np.zeros((K, len(path_cols)))
    for i in range(K):
        sub = ml[ml.lca_class_ordered == i]
        for j, c in enumerate(path_cols):
            path_pct[i, j] = sub[c].mean() * 100
    im = ax.imshow(path_pct, aspect="auto", cmap="Greens", vmin=0, vmax=100)
    for i in range(K):
        for j in range(len(path_cols)):
            v = path_pct[i, j]
            tc = "white" if v > 60 else "black"
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8.5, color=tc)
    ax.set_xticks(range(len(path_cols)))
    ax.set_xticklabels(pcs_short, fontsize=9)
    ax.set_yticks(range(K))
    ax.set_yticklabels([f"C{i+1}" for i in range(K)], fontsize=9.5)
    for spine in ax.spines.values():
        spine.set_visible(True); spine.set_linewidth(0.5); spine.set_color("#888")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("% endorsing", fontsize=9)
    ax.set_title("D. Pathway adoption by latent class", fontsize=11, fontweight="bold", loc="left")

    # E: Days Engaged by class
    ax = fig.add_subplot(gs[1, 2])
    data = []
    for c in range(K):
        arr = ml[ml.lca_class_ordered == c]["Days Engaged"].dropna().values
        data.append(arr)
    bp = ax.boxplot(data, positions=range(K), widths=0.6, patch_artist=True, showfliers=False,
                    medianprops=dict(color="#1a1a1a", linewidth=1.6))
    for patch, col in zip(bp["boxes"], colors):
        patch.set_facecolor(col); patch.set_alpha(0.5); patch.set_edgecolor(col)
    ax.set_xticks(range(K))
    ax.set_xticklabels([f"C{i+1}" for i in range(K)], fontsize=10)
    ax.set_ylabel("Engagement duration (days)", fontsize=11)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    H, p_kw = stats.kruskal(*[d for d in data if len(d) > 1])
    ax.set_title(f"E. Engagement duration by class\nKruskal-Wallis: H = {H:.1f}, {fmt_p(p_kw)}",
                 fontsize=11, fontweight="bold", loc="left")

    fig.suptitle(f"Figure 6. Latent class analysis of multidomain need profiles (n = {len(ml):,})",
                 fontsize=13, fontweight="bold", x=0.02, y=1.02, ha="left")
    _save(fig, out_path)


# =====================================================================
# Figure 7: CART tree
# =====================================================================

DISPLAY_MAP = {
    "need_Housing": "Housing need",
    "need_Employment": "Employment need",
    "need_Education": "Education need",
    "need_Connection to treatment": "Treatment connection",
    "need_Connection to recovery community": "Community connection",
    "need_Recovery support": "Recovery support need",
    "need_Probation": "Probation need",
    "need_Overdose": "Overdose history",
    "need_Co-occurring": "Co-occurring MH",
    "need_Multiple treatment episodes": "Multiple tx episodes",
    "sev_seizures": "Hx seizures",
    "sev_nlx": "Naloxone given",
    "sev_er": "≥2 ER visits",
    "sev_ideation": "Active ideation",
    "Age_num": "Age",
    "gender_male": "Male",
    "gender_tgnb": "TGNB",
    "hispanic": "Hispanic ethnicity",
    "veteran": "Veteran",
    "race_White": "White",
    "race_Black_or_African_American": "Black",
    "race_Native_American": "Native American",
    "race_Multiracial": "Multiracial",
    "race_Other": "Other race",
    "lives_Recovery_Residence": "Recovery residence",
    "lives_Housed": "Housed (independent)",
    "lives_Residential_Treatment": "Residential treatment",
    "lives_Unhoused": "Unhoused",
    "lives_Halfway_House": "Halfway house",
    "ins_medicaid": "Medicaid",
    "HasPeer_num": "Has peer match",
    "Supports_num": "# of Supports",
    "NoShows_num": "# of No Shows",
    "path_Abstinence": "Abstinence pathway",
    "path_12_Step_Recovery": "12-Step pathway",
    "path_Support_groups": "Support groups path.",
    "path_Natural_Recovery": "Natural recovery",
    "path_Peer_Recovery_support": "Peer recovery path.",
    "path_Medication_assisted_Recovery": "MAT pathway",
    "path_Harm_Reduction": "Harm reduction",
    "path_Alternative_Holistic_Recovery": "Alt./holistic",
    "intake_complete": "Intake form completed",
}


def figure_7_cart(model, features: list[str], out_path: str | Path) -> None:
    """CART decision tree for MAT pathway endorsement."""
    fig, ax = plt.subplots(figsize=(18, 10))
    display_features = [DISPLAY_MAP.get(f, f) for f in features]
    plot_tree(
        model, feature_names=display_features, class_names=["No MAT", "MAT endorsed"],
        filled=True, rounded=True, fontsize=9, impurity=False, proportion=False, ax=ax,
    )
    ax.set_title("Figure 7. Classification tree predicting MAT pathway endorsement at intake",
                 fontsize=11, fontweight="bold", loc="left", pad=14)
    plt.tight_layout()
    _save(fig, out_path)


# =====================================================================
# Figure 8: Random forest with permutation importance
# =====================================================================

def figure_8_rf_importance(
    rf_info: dict, perm_means: np.ndarray, perm_stds: np.ndarray,
    features: list[str], out_path: str | Path
) -> None:
    """RF cross-validated ROC and top-20 permutation-importance bars."""
    disp = [DISPLAY_MAP.get(f, f) for f in features]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7), constrained_layout=True,
                             gridspec_kw={"width_ratios": [1, 1.7]})

    # Panel A: ROC
    ax = axes[0]
    ax.plot([0, 1], [0, 1], "--", color="#999", linewidth=0.8)
    ax.plot(rf_info["roc_fpr"], rf_info["roc_tpr_mean"], color="#2a4d6e", linewidth=2,
            label=f"Random forest (AUC = {rf_info['cv_aucs'].mean():.2f} \u00b1 {rf_info['cv_aucs'].std():.2f})")
    ax.fill_between(rf_info["roc_fpr"],
                    rf_info["roc_tpr_mean"] - rf_info["roc_tpr_std"],
                    rf_info["roc_tpr_mean"] + rf_info["roc_tpr_std"],
                    color="#2a4d6e", alpha=0.2)
    ax.set_xlabel("False positive rate", fontsize=11)
    ax.set_ylabel("True positive rate", fontsize=11)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.01)
    ax.legend(loc="lower right", fontsize=10, frameon=False)
    ax.grid(linestyle=":", alpha=0.4); ax.set_axisbelow(True)
    ax.set_title("A. 5-fold cross-validated ROC", fontsize=11, fontweight="bold", loc="left")

    # Panel B: top-20 permutation importance
    ax = axes[1]
    order = perm_means.argsort()[::-1]
    top_n = 20
    top_idx = order[:top_n][::-1]
    y_pos = np.arange(top_n)
    labels = [disp[i] for i in top_idx]

    def get_color(name: str) -> str:
        n = name.lower()
        if "intake form" in n:
            return "#e0a040"
        if any(x in n for x in ["housing", "employment", "education", "recovery residence",
                                 "housed", "residential treatment", "unhoused", "halfway"]):
            return "#2a4d6e"
        if any(x in n for x in ["naloxone", "er ", "seizures", "ideation", "overdose",
                                 "co-occurring", "multiple tx", "probation"]):
            return "#c44e52"
        if any(x in n for x in ["supports", "peer match", "no shows", "recovery support need",
                                 "treatment connection", "community connection"]):
            return "#3a7d44"
        if "pathway" in n or any(x in n for x in ["abstinence", "12-step", "mat ", "harm reduction",
                                                    "natural", "alt.", "support groups path"]):
            return "#7a4ea0"
        return "#888888"

    colors = [get_color(l) for l in labels]
    ax.barh(y_pos, perm_means[top_idx], xerr=perm_stds[top_idx], color=colors,
            edgecolor="white", linewidth=0.5, error_kw={"capsize": 2, "capthick": 0.6, "ecolor": "#555"})
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlabel("Permutation importance (mean \u0394 accuracy when feature is shuffled)", fontsize=10.5)
    ax.axvline(0, color="#000", linewidth=0.6)
    ax.grid(axis="x", linestyle=":", alpha=0.4); ax.set_axisbelow(True)
    ax.set_title("B. Top 20 features by permutation importance", fontsize=11, fontweight="bold", loc="left")
    legend_handles = [
        Patch(facecolor="#e0a040", label="Data completeness"),
        Patch(facecolor="#2a4d6e", label="Structural / housing"),
        Patch(facecolor="#c44e52", label="Clinical severity"),
        Patch(facecolor="#3a7d44", label="Service / engagement"),
        Patch(facecolor="#7a4ea0", label="Pathway endorsement"),
        Patch(facecolor="#888888", label="Demographic"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=9, frameon=False)

    fig.suptitle("Figure 8. Random forest classifier with permutation importance for engagement",
                 fontsize=13, fontweight="bold", x=0.02, y=1.02, ha="left")
    _save(fig, out_path)


# =====================================================================
# Figure 9: UMAP
# =====================================================================

def figure_9_umap(emb: np.ndarray, umap_data: pd.DataFrame, ml: pd.DataFrame,
                  out_path: str | Path) -> None:
    """UMAP projection with six coloring panels."""
    data = umap_data.copy()
    data[["umap_x", "umap_y"]] = emb
    # Bring engagement and other annotation columns from ml on the index
    ann_cols = ["engaged", "lca_class_ordered", "severity_score",
                "path_Medication_assisted_Recovery", "need_complexity", "Days Engaged"]
    for c in ann_cols:
        if c in ml.columns:
            data[c] = ml.loc[data.index, c].values

    fig, axes = plt.subplots(2, 3, figsize=(15, 9.5), constrained_layout=True)
    x = data["umap_x"].values
    y = data["umap_y"].values

    # A: by LCA class
    ax = axes[0, 0]
    class_palette = {0: "#7eb377", 1: "#dca94a", 2: "#7da7c7", 3: "#2a4d6e", 4: "#c44e52"}
    class_names = {0: "C1 single-need", 1: "C2 tx-connection", 2: "C3 community",
                   3: "C4 multidomain", 4: "C5 high-complexity"}
    for lvl in sorted(class_palette):
        m = (data["lca_class_ordered"].values == lvl)
        ax.scatter(x[m], y[m], s=8, color=class_palette[lvl], alpha=0.55,
                   edgecolors="none", label=class_names[lvl])
    ax.legend(title="Latent class", fontsize=8, loc="best", frameon=False, markerscale=2.5)
    _umap_format(ax, "A. Colored by latent class")

    # B: engagement
    ax = axes[0, 1]
    for lvl, color, label in [(0, "#c44e52", "No longer engaged"), (1, "#3a7d44", "Engaged")]:
        m = (data["engaged"].values == lvl)
        ax.scatter(x[m], y[m], s=8, color=color, alpha=0.55, edgecolors="none", label=label)
    ax.legend(fontsize=9, loc="best", frameon=False, markerscale=2.5)
    _umap_format(ax, "B. Colored by engagement status")

    # C: severity
    ax = axes[0, 2]
    sc = ax.scatter(x, y, s=8, c=data["severity_score"].values, cmap="YlOrRd",
                    vmin=0, vmax=3, alpha=0.7, edgecolors="none")
    plt.colorbar(sc, ax=ax, fraction=0.04, pad=0.02, ticks=[0, 1, 2, 3]).set_label("Severity score", fontsize=9)
    _umap_format(ax, "C. Colored by clinical severity composite")

    # D: MAT
    ax = axes[1, 0]
    for lvl, color, label in [(0, "#cccccc", "Not endorsing"), (1, "#7a4ea0", "MAT endorsed")]:
        m = (data["path_Medication_assisted_Recovery"].values == lvl)
        ax.scatter(x[m], y[m], s=8, color=color, alpha=0.55, edgecolors="none", label=label)
    ax.legend(fontsize=9, loc="best", frameon=False, markerscale=2.5)
    _umap_format(ax, "D. Colored by MAT pathway endorsement")

    # E: need complexity
    ax = axes[1, 1]
    sc = ax.scatter(x, y, s=8, c=data["need_complexity"].values, cmap="viridis",
                    alpha=0.7, edgecolors="none")
    plt.colorbar(sc, ax=ax, fraction=0.04, pad=0.02).set_label("Need complexity", fontsize=9)
    _umap_format(ax, "E. Colored by need complexity")

    # F: log days engaged
    ax = axes[1, 2]
    days = data["Days Engaged"].values
    days_log = np.log10(days + 1)
    sc = ax.scatter(x, y, s=8, c=days_log, cmap="cividis", alpha=0.7, edgecolors="none")
    plt.colorbar(sc, ax=ax, fraction=0.04, pad=0.02).set_label("log\u2081\u2080(Days Engaged + 1)", fontsize=9)
    _umap_format(ax, "F. Colored by engagement duration")

    fig.suptitle("Figure 9. UMAP projection of participants in feature space",
                 fontsize=13, fontweight="bold", x=0.02, y=1.02, ha="left")
    _save(fig, out_path)


def _umap_format(ax, title: str) -> None:
    ax.set_xlabel("UMAP-1", fontsize=10)
    ax.set_ylabel("UMAP-2", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
