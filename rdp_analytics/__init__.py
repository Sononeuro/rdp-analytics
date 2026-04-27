"""rdp-analytics: open-source pipeline for Recovery Data Platform exports.

Reproduces the analyses in Walton et al. 2026 (manuscript in preparation).
"""

from rdp_analytics.data import build_person_dataset, load_rdp_extract
from rdp_analytics.features import (
    NEED_DOMAINS,
    PATHWAY_COMPONENTS,
    SEVERITY_COMPONENTS,
    add_need_indicators,
    add_pathway_indicators,
    add_severity_composite,
)
from rdp_analytics.step1_stats import (
    cochran_armitage,
    jonckheere_terpstra,
    fisher_with_fdr,
    need_pathway_matrix,
    wilson_ci,
)
from rdp_analytics.step2_ml import (
    BernoulliLCA,
    fit_cart_for_pathway,
    fit_random_forest_engagement,
    permutation_importance_pooled,
    umap_projection,
)
from rdp_analytics.pipeline import run_full_analysis

__version__ = "0.1.0"

__all__ = [
    "build_person_dataset",
    "load_rdp_extract",
    "NEED_DOMAINS",
    "PATHWAY_COMPONENTS",
    "SEVERITY_COMPONENTS",
    "add_need_indicators",
    "add_pathway_indicators",
    "add_severity_composite",
    "cochran_armitage",
    "jonckheere_terpstra",
    "fisher_with_fdr",
    "need_pathway_matrix",
    "wilson_ci",
    "BernoulliLCA",
    "fit_cart_for_pathway",
    "fit_random_forest_engagement",
    "permutation_importance_pooled",
    "umap_projection",
    "run_full_analysis",
]
