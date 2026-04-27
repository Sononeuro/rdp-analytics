"""End-to-end pipeline: from RDP export to all figures and intermediate datasets.

Usage from CLI:
    python -m rdp_analytics.pipeline --input data/RDP.xlsx --output figures/

Usage from Python:
    from rdp_analytics import build_person_dataset, run_full_analysis
    person = build_person_dataset("data/RDP.xlsx")
    run_full_analysis(person, output_dir="figures/")
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from rdp_analytics.data import build_person_dataset, paired_pathway_change
from rdp_analytics.features import (
    NEED_DOMAINS, PATHWAY_COMPONENTS, build_full_feature_matrix, get_feature_lists,
)
from rdp_analytics.step1_stats import need_pathway_matrix
from rdp_analytics.step2_ml import (
    BernoulliLCA, fit_cart_for_pathway, fit_random_forest_engagement,
    lca_model_selection, permutation_importance_pooled,
    reorder_lca_classes_by_complexity, umap_projection,
)
from rdp_analytics.figures import (
    figure_1_distributions, figure_2_heatmap, figure_3_retention,
    figure_4_severity, figure_5_lives_in, figure_6_lca, figure_7_cart,
    figure_8_rf_importance, figure_9_umap,
)


def run_full_analysis(
    person: pd.DataFrame,
    output_dir: str | Path,
    paired_path: Optional[str | Path] = None,
    seed: int = 20260426,
) -> dict:
    """Run the full Step 1 + Step 2 analysis and write all figures + artifacts.

    Parameters
    ----------
    person : person-level DataFrame from `build_person_dataset`
    output_dir : where figures and intermediate artifacts will be written
    paired_path : optional earlier RDP export for pathway-change analysis
    seed : random seed for reproducibility

    Returns
    -------
    dict of all intermediate results (also pickled to disk)
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ----- Feature construction -----
    person = build_full_feature_matrix(person)
    feats = get_feature_lists()

    # Restrict to participants with both need and pathway data for ML
    ml = person[person["need_complexity"].notna() & person["pathway_diversity"].notna()].copy()
    ml.to_pickle(out / "ml_data.pkl")

    results = {"n_total": len(person), "n_ml": len(ml)}

    # ===== Step 1: descriptive and inferential statistics =====
    print(f"[Step 1] N total: {len(person)}, N for ML analyses: {len(ml)}")

    # Figure 1: distributions
    figure_1_distributions(person, out / "fig1_distributions.svg")

    # Figure 2: need-pathway heatmap with FDR correction
    np_matrix = need_pathway_matrix(person, NEED_DOMAINS, PATHWAY_COMPONENTS)
    np.save(out / "diff_pp.npy", np_matrix["diff_pp"])
    np.save(out / "qvals.npy", np_matrix["qvals"])
    figure_2_heatmap(np_matrix, NEED_DOMAINS, PATHWAY_COMPONENTS, out / "fig2_heatmap.svg")
    results["np_matrix"] = np_matrix
    print(f"[Fig 2] Cells significant at q<0.05: {(np_matrix['qvals'] < 0.05).sum()}/80")

    # Figure 3: retention by complexity and pathway diversity
    figure_3_retention(ml, out / "fig3_retention.svg")

    # Figure 4: severity composite x pathway adoption
    figure_4_severity(person, PATHWAY_COMPONENTS, out / "fig4_severity.svg")

    # Figure 5: living situation stratification
    figure_5_lives_in(person, out / "fig5_lives_in.svg")

    # Optional: pathway change diagnostic in paired subsample
    if paired_path is not None:
        change = paired_pathway_change(
            primary_path=Path(out).parent / "data" / "primary.xlsx",
            earlier_path=paired_path,
        )
        results["paired_change_pct"] = float(change["changed"].mean() * 100)
        print(f"[Paired] Pathway-string change rate: {results['paired_change_pct']:.1f}%")

    # ===== Step 2: machine learning =====
    print("[Step 2] Fitting LCA, CART, RF, UMAP")

    # ----- LCA on need indicators -----
    X_need = ml[feats["need_features"]].astype(int).values
    selection = lca_model_selection(X_need, k_range=range(2, 8), random_state=seed)
    selection.to_csv(out / "lca_model_selection.csv", index=False)
    best_k = int(selection.loc[selection["BIC"].idxmin(), "k"])
    print(f"[LCA] BIC-optimal k = {best_k}")

    lca = BernoulliLCA(n_classes=best_k, n_init=50, random_state=seed).fit(X_need)
    rho_o, pi_o, resp_o, perm = reorder_lca_classes_by_complexity(
        lca.result_.rho, lca.result_.pi, lca.result_.resp
    )
    np.save(out / "lca_rho.npy", rho_o)
    np.save(out / "lca_pi.npy", pi_o)
    ml["lca_class_ordered"] = resp_o.argmax(axis=1)
    ml["lca_post_max"] = resp_o.max(axis=1)
    print(f"[LCA] Mean modal posterior: {ml['lca_post_max'].mean():.3f}")
    figure_6_lca(selection, rho_o, pi_o, ml, NEED_DOMAINS, PATHWAY_COMPONENTS, out / "fig6_lca.svg")

    # ----- CART for MAT pathway -----
    cart, cart_info = fit_cart_for_pathway(
        ml, feats["features_for_pathway"],
        target_col="path_Medication_assisted_Recovery",
        random_state=seed,
    )
    print(f"[CART] depth=4 CV AUC: {cart_info['cv_auc_mean']:.3f} +/- {cart_info['cv_auc_std']:.3f}")
    figure_7_cart(cart, cart_info["features"], out / "fig7_cart.svg")

    # ----- Random forest for engagement -----
    rf, rf_info = fit_random_forest_engagement(
        ml, feats["features_for_engagement"], random_state=seed,
    )
    print(f"[RF] CV AUC: {rf_info['cv_aucs'].mean():.3f} +/- {rf_info['cv_aucs'].std():.3f}, OOB: {rf_info['oob']:.3f}")

    X = ml[feats["features_for_engagement"]].dropna()[feats["features_for_engagement"]].values
    y = ml.loc[ml[feats["features_for_engagement"]].dropna().index, "engaged"].values
    perm_means, perm_stds = permutation_importance_pooled(rf, X, y)
    np.save(out / "perm_means.npy", perm_means)
    np.save(out / "perm_stds.npy", perm_stds)
    np.save(out / "cv_aucs.npy", rf_info["cv_aucs"])

    figure_8_rf_importance(rf_info, perm_means, perm_stds, feats["features_for_engagement"], out / "fig8_rf_importance.svg")

    # ----- UMAP -----
    umap_features = [f for f in feats["features_for_engagement"] if not f.startswith("path_")]
    emb, umap_data = umap_projection(ml, umap_features, random_state=seed)
    np.save(out / "umap_embedding.npy", emb)
    figure_9_umap(emb, umap_data, ml, out / "fig9_umap.svg")

    # Save feature lists for posterity
    with open(out / "feature_lists.json", "w") as f:
        json.dump(feats, f, indent=2)

    return results


def main():
    p = argparse.ArgumentParser(description="Reproduce all figures and analyses from an RDP export")
    p.add_argument("--input", required=True, help="Path to primary RDP Excel export")
    p.add_argument("--paired", help="Optional path to earlier RDP export for pathway-change analysis")
    p.add_argument("--output", default="figures/", help="Output directory for figures and artifacts")
    p.add_argument("--seed", type=int, default=20260426, help="Random seed for reproducibility")
    args = p.parse_args()

    person = build_person_dataset(args.input, paired_path=args.paired)
    run_full_analysis(person, output_dir=args.output, paired_path=args.paired, seed=args.seed)


if __name__ == "__main__":
    main()
