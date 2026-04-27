# User Guide

This guide is for analysts who want to apply the rdp-analytics pipeline to their own Recovery Data Platform export.

## Contents

1. [Installation](#installation)
2. [Input data requirements](#input-data-requirements)
3. [The pipeline at a glance](#the-pipeline-at-a-glance)
4. [Public API](#public-api)
5. [Common workflows](#common-workflows)
6. [Variable construction glossary](#variable-construction-glossary)
7. [Known pitfalls](#known-pitfalls)
8. [Output files](#output-files)
9. [FAQ](#faq)

## Installation

### From source (recommended)

```bash
git clone https://github.com/sononeuro/rdp-analytics
cd rdp-analytics
pip install -e .
```

### Dependencies

The package requires Python 3.10 or newer and the following libraries (installed automatically): pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, openpyxl, umap-learn, joblib.

For development and testing, install the test extras:

```bash
pip install -e ".[test]"
```

### Verifying installation

```bash
pytest tests/ -v
```

All 10 tests should pass.

## Input data requirements

The pipeline expects a Recovery Data Platform Excel export with one row per assessment record. The required columns are:

| Column | Type | Required | Notes |
|---|---|---|---|
| `SAFEID` | str | yes | unique participant identifier |
| `As of Date` | date | yes | assessment date |
| `Reason for Referral` | str | yes | semicolon-delimited multi-select |
| `Pathways` | str | yes | semicolon-delimited multi-select |
| `Status` | str | yes | "Engaged" or "No Longer Engaged" |
| `Days Engaged` | numeric | yes | days from intake to last contact |
| `Lives In` | str | recommended | living-situation category |
| `# of Supports` | numeric | recommended | service intensity |
| `Age`, `Gender`, `Race`, `Ethnicity`, `Veteran Status` | mixed | recommended | demographics |
| `History of Seizures`, `Times given Naloxone/Narcan`, `Emergency Room Visits`, `Ideations (Active)` | mixed | recommended | severity composite components |
| `Has Peer`, `# of No Shows`, `Insurance Type` | mixed | optional | service variables |

Missing columns will degrade specific analyses but won't crash the pipeline. The minimum viable input has SAFEID, As of Date, Reason for Referral, Pathways, Status, and Days Engaged.

## The pipeline at a glance

The package implements a two-step analytic approach:

**Step 1: Inferential statistics.** Fisher's exact tests with Benjamini-Hochberg FDR correction (need-pathway heatmap), Jonckheere-Terpstra trend tests on ordinal exposures (retention by complexity and pathway diversity), Wilson confidence intervals for proportions, and pairwise Fisher's exact comparisons against a reference (housing-stratified retention).

**Step 2: Basic machine learning.** Latent class analysis via Bernoulli mixture EM (need-profile clustering), classification and regression trees (decision aid for pathway endorsement), random forests with permutation importance (engagement prediction), and UMAP for two-dimensional visualization.

Each step produces specific figures that map to the manuscript:

| Figure | Step | Method | What it shows |
|---|---|---|---|
| 1 | 1 | Histograms | Need complexity and pathway diversity distributions |
| 2 | 1 | Fisher's + FDR | Need-by-pathway adoption matrix |
| 3 | 1 | Jonckheere-Terpstra | Retention by complexity and diversity |
| 4 | 1 | Jonckheere-Terpstra | Pathway adoption by clinical severity |
| 5 | 1 | Pairwise Fisher's + FDR | Living-situation stratified retention |
| 6 | 2 | LCA (Bernoulli mixture EM) | Five latent classes of need profiles |
| 7 | 2 | CART | Decision tree for MAT pathway endorsement |
| 8 | 2 | Random forest + permutation importance | Engagement predictors |
| 9 | 2 | UMAP | Participant feature-space visualization |

## Public API

### Top-level convenience functions

```python
from rdp_analytics import build_person_dataset, run_full_analysis

# Load and aggregate to person-level
person = build_person_dataset("data/RDP.xlsx")

# End-to-end analysis with all figures
results = run_full_analysis(person, output_dir="figures/")
```

### Step 1: Inferential statistics

```python
from rdp_analytics import (
    wilson_ci, cochran_armitage, jonckheere_terpstra,
    fisher_with_fdr, need_pathway_matrix,
)

# Wilson 95% CI for a proportion
lo, hi = wilson_ci(k=147, n=201)  # returns percentages

# Trend tests
z, p = cochran_armitage(x_levels=[0,1,2,3], n_arr=[100,100,100,100], k_arr=[10,30,50,70])
z, p = jonckheere_terpstra([group1_array, group2_array, group3_array])

# Many Fisher's exact tests with FDR correction
ors, ps, qs = fisher_with_fdr(list_of_2x2_tables)

# Full need-by-pathway adoption matrix
matrix = need_pathway_matrix(person, NEED_DOMAINS, PATHWAY_COMPONENTS)
```

### Step 2: Machine learning

```python
from rdp_analytics import (
    BernoulliLCA, fit_cart_for_pathway,
    fit_random_forest_engagement, permutation_importance_pooled,
    umap_projection,
)

# LCA with k=5
lca = BernoulliLCA(n_classes=5, n_init=20, random_state=42).fit(X)
print(lca.result_.bic, lca.result_.entropy_R2)

# CART for predicting MAT
cart, info = fit_cart_for_pathway(
    ml, features=mat_features,
    target_col="path_Medication_assisted_Recovery",
    max_depth=4,
)

# Random forest for engagement
rf, info = fit_random_forest_engagement(ml, features=engagement_features)
means, stds = permutation_importance_pooled(rf, X, y)

# UMAP
embedding, data = umap_projection(ml, features=umap_features)
```

### Feature construction

```python
from rdp_analytics.features import (
    build_full_feature_matrix, get_feature_lists,
    NEED_DOMAINS, PATHWAY_COMPONENTS, SEVERITY_COMPONENTS,
)

# Add all derived features in canonical order
person = build_full_feature_matrix(person)

# Get the canonical feature-name lists for ML
feats = get_feature_lists()
print(feats["features_for_engagement"])  # 42 features for the RF
```

## Common workflows

### Reproducing the published analysis

```bash
python -m rdp_analytics.pipeline \
  --input data/10_20_25_Amethyst_Report.xlsx \
  --paired data/2_18_25_Amethyst_Report.xlsx \
  --output figures_v2/ \
  --seed 20260426
```

### Running just Step 1 on a different RDP export

```python
from rdp_analytics import build_person_dataset
from rdp_analytics.features import build_full_feature_matrix, NEED_DOMAINS, PATHWAY_COMPONENTS
from rdp_analytics.step1_stats import need_pathway_matrix
from rdp_analytics.figures import figure_1_distributions, figure_2_heatmap

person = build_person_dataset("your_data.xlsx")
person = build_full_feature_matrix(person)

# Figure 1
figure_1_distributions(person, "fig1.svg")

# Figure 2 (the heatmap)
matrix = need_pathway_matrix(person, NEED_DOMAINS, PATHWAY_COMPONENTS)
figure_2_heatmap(matrix, NEED_DOMAINS, PATHWAY_COMPONENTS, "fig2.svg")
print(f"Significant cells: {(matrix['qvals'] < 0.05).sum()}/80")
```

### Custom decision tree on a different pathway

```python
from rdp_analytics import fit_cart_for_pathway
from rdp_analytics.features import get_feature_lists

feats = get_feature_lists()

# Predict harm-reduction endorsement instead of MAT
cart, info = fit_cart_for_pathway(
    person,
    features=feats["features_for_pathway"],
    target_col="path_Harm_Reduction",
    max_depth=4,
)
print(f"CV AUC: {info['cv_auc_mean']:.3f} ± {info['cv_auc_std']:.3f}")
```

### Just the LCA, custom k

```python
from rdp_analytics import BernoulliLCA
from rdp_analytics.step2_ml import lca_model_selection

# Compare k=2 through k=8
selection = lca_model_selection(X_need, k_range=range(2, 9))
print(selection)

# Fit at k=4 instead of the BIC-optimal
lca = BernoulliLCA(n_classes=4, n_init=50, random_state=42).fit(X_need)
```

## Variable construction glossary

The pipeline derives a large set of variables from the raw RDP fields. Each is documented here.

### Need indicators (10 binary variables)

The `Reason for Referral` field contains semicolon-delimited multi-select content drawn from a controlled vocabulary. We decompose into 10 binary indicators via case-insensitive substring matching:

| Indicator | Source vocabulary text |
|---|---|
| `need_Housing` | "Housing" |
| `need_Employment` | "Employment" |
| `need_Education` | "Education" |
| `need_Connection to treatment` | "Connection to treatment" |
| `need_Connection to recovery community` | "Connection to recovery community" |
| `need_Recovery support` | "Recovery support" |
| `need_Probation` | "Probation" |
| `need_Overdose` | "Overdose" |
| `need_Co-occurring` | "Co-occurring" |
| `need_Multiple treatment episodes` | "Multiple treatment episodes" |

We aggregate across all records per participant rather than using the most recent only, because referral reasons accumulate over time. Sum of indicators is `need_complexity` (range 0-10).

### Pathway indicators (8 binary variables)

| Indicator | Source vocabulary text |
|---|---|
| `path_Abstinence` | "Abstinence" |
| `path_12_Step_Recovery` | "12-Step Recovery" |
| `path_Support_groups` | "Support groups" |
| `path_Natural_Recovery` | "Natural Recovery" |
| `path_Peer_Recovery_support` | "Peer Recovery support" |
| `path_Medication_assisted_Recovery` | "Medication-assisted Recovery" |
| `path_Harm_Reduction` | "Harm Reduction" |
| `path_Alternative_Holistic_Recovery` | "Alternative/Holistic Recovery" |

We use only the most recent value per participant because pathway endorsement is approximately stable over time (~1% of paired participants showed any change between extracts in our cohort). Sum of indicators is `pathway_diversity` (range 0-8).

### Severity composite (5 components, range 0-5)

| Component | Construction |
|---|---|
| `sev_seizures` | `History of Seizures` == "Yes" |
| `sev_nlx` | `Times given Naloxone/Narcan` >= 1 |
| `sev_er` | `Emergency Room Visits` >= 2 |
| `sev_ideation` | `Ideations (Active)` contains "Suicidal" |
| `sev_overdose_need` | `need_Overdose` == 1 |

Component completeness varies (49-100% in our cohort). Missing values are treated as zero, biasing the composite downward. Use the `severity_complete` mask for complete-case sensitivity analyses.

### Demographics

| Indicator | Construction | Notes |
|---|---|---|
| `gender_male` | `Gender` == "Male" | |
| `gender_tgnb` | `Gender` in {Transgender Male, Transgender Female, Non-Binary, Genderqueer/Genderfluid} | |
| `hispanic` | `Ethnicity` == "Yes, Hispanic or Latino" | **Exact match required**; see Pitfalls |
| `intake_complete` | `Ethnicity` is not null | Data-completeness proxy; strongest engagement predictor |
| `veteran` | `Veteran Status` == "Veteran" | |
| `Age_num` | numeric coercion of `Age` | |
| `race_<Category>` | one-hot from `Race` | Top 5 categories plus "Other" |

### Living situation (one-hot)

| Indicator | Source |
|---|---|
| `lives_Recovery_Residence` | `Lives In` == "Recovery Residence" |
| `lives_Housed` | `Lives In` == "Housed" |
| `lives_Residential_Treatment` | `Lives In` == "Residential Treatment" |
| `lives_Unhoused` | `Lives In` == "Unhoused" |
| `lives_Halfway_House` | `Lives In` == "Halfway House" |

Living situation is preserved in its native 7-category form because pilot inspection revealed substantial inter-category variation in retention (the recovery capital inversion finding).

### Service intensity

| Indicator | Construction |
|---|---|
| `Supports_num` | numeric coercion of `# of Supports`, NA→0 |
| `NoShows_num` | numeric coercion of `# of No Shows`, NA→0 |
| `HasPeer_num` | numeric coercion of `Has Peer`, NA→0 |
| `ins_medicaid` | `Insurance Type` == "Medicaid" |

### Outcomes

| Variable | Construction |
|---|---|
| `engaged` | `Status` == "Engaged" (binary) |
| `Days Engaged` | numeric coercion (right-censored for engaged participants) |

## Known pitfalls

### The Hispanic indicator substring bug

Initial implementation used `Ethnicity.str.contains("Hispanic")`, which matches BOTH "Yes, Hispanic or Latino" AND "No, Not Hispanic or Latino" because both strings contain the literal text "Hispanic". The fix is exact match on the affirmative value.

This bug masked the actual top engagement predictor (intake completion). It is documented in `tests/test_features.py::test_hispanic_indicator_no_substring_bug`.

The general lesson: when categorical source values share substrings, use exact match rather than `str.contains`.

### Multi-select fields with hierarchical labels

The Reason for Referral controlled vocabulary contains both "Connection to treatment" and "Connection to recovery community". A naive substring search for "Connection to" would match both. We use the full domain text in our matchers to avoid this.

### Per-record vs per-participant fields

Some RDP fields are captured at intake only; others are updated at each assessment. Treating an intake-only field as longitudinal yields nonsense. The convention here is to take the most recent non-null value per participant for snapshot fields, but to aggregate across all records for fields that genuinely accumulate (only Reason for Referral in current implementation).

### Severity composite missingness

Components have variable completeness. Treating missing as zero biases the composite downward. For the published analysis we accepted this bias because the MAT-by-severity gradient was strong enough to remain significant in a complete-case sensitivity analysis. For other applications, run the sensitivity check explicitly.

### LCA item-probability saturation

When a class becomes deterministic on a particular item (e.g., 100% of class members endorse Recovery Support), item-response probabilities saturate at the boundary. We clip to [1e-6, 1-1e-6] each iteration to prevent log-likelihood divergence. If you see classes with many item probabilities at the boundary, consider whether you have a deterministic category masquerading as a latent class.

## Output files

The pipeline writes the following to your `--output` directory:

```
figures/
  fig1_distributions.{svg,png}
  fig2_heatmap.{svg,png}
  fig3_retention.{svg,png}
  fig4_severity.{svg,png}
  fig5_lives_in.{svg,png}
  fig6_lca.{svg,png}
  fig7_cart.{svg,png}
  fig8_rf_importance.{svg,png}
  fig9_umap.{svg,png}
  ml_data.pkl              # person-level analytic dataset (post-feature construction)
  diff_pp.npy              # need-pathway percentage-point difference matrix
  qvals.npy                # FDR-corrected q-values for the heatmap
  lca_model_selection.csv  # BIC/AIC/entropy across k=2-7
  lca_rho.npy              # item-response probabilities (K x J)
  lca_pi.npy               # class proportions (K,)
  cv_aucs.npy              # 5-fold cross-validated AUCs from the random forest
  perm_means.npy           # permutation importance means
  perm_stds.npy            # permutation importance standard deviations
  umap_embedding.npy       # 2D UMAP coordinates (N x 2)
  feature_lists.json       # canonical feature name lists used in the ML step
```

SVG files preserve text as text (not paths) and are editable in Illustrator or Inkscape without conversion.

## FAQ

**Why pure-Python LCA instead of stepmix?** Stepmix has a sklearn version incompatibility at the time of writing. Our Bernoulli mixture EM is the same algorithm and is documented in `step2_ml.py`.

**Why not use Cox regression for retention?** We did initially. The published paper documents that a binary Recovery Residence Cox term produces an HR of 2.7 and the conclusion "recovery residence worsens retention," which is wrong. Stratifying by housing category reveals that recovery residence has the LOWEST retention of any housed group because of expected graduation transitions. The Cox-binary framing distorts this. We use stratified Fisher's exact and Jonckheere-Terpstra instead.

**Why permutation importance instead of impurity importance?** Permutation importance is computed on held-out data and is robust to feature cardinality. Impurity importance is biased toward high-cardinality features and toward features used early in tree splits. For interpretability claims, permutation importance is the more honest method.

**Can I use this for non-RDP data?** Yes, but you'll need to implement the equivalent of `data.py` for your data source and the equivalent of the `add_*` functions in `features.py`. The Step 1 and Step 2 statistical functions are agnostic to data source.

**How do I cite this package?** Cite the manuscript and link to the GitHub repository. Once the manuscript has a DOI, we'll add a CITATION.cff file with formal citation metadata.
