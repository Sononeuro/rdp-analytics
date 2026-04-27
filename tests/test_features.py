"""Tests for the rdp-analytics package.

These cover the most consequential pitfalls we encountered during development.
The tests double as documentation for things to be careful about.
"""

import numpy as np
import pandas as pd
import pytest

from rdp_analytics.features import add_demographics, add_need_indicators
from rdp_analytics.step1_stats import (
    cochran_armitage, fisher_with_fdr, jonckheere_terpstra, wilson_ci,
)
from rdp_analytics.step2_ml import BernoulliLCA


# =====================================================================
# The Hispanic indicator bug
# =====================================================================

def test_hispanic_indicator_no_substring_bug():
    """Document and protect against the substring-matching bug.

    Initial implementation used `Ethnicity.str.contains("Hispanic")`, which
    matches BOTH "Yes, Hispanic or Latino" AND "No, Not Hispanic or Latino"
    because both strings contain the literal text "Hispanic". The fix is
    exact match on the affirmative value.

    This bug masked the actual top engagement predictor (intake completion).
    """
    person = pd.DataFrame({
        "Ethnicity": ["Yes, Hispanic or Latino", "No, Not Hispanic or Latino", None, "Refused"],
        "Gender": [None] * 4, "Veteran Status": [None] * 4, "Age": [None] * 4,
        "Race": [None] * 4,
    })
    person = add_demographics(person)
    # Only the first row should be Hispanic
    assert list(person["hispanic"]) == [1, 0, 0, 0]
    # Intake completion: any non-null answer (including "Refused") counts
    assert list(person["intake_complete"]) == [1, 1, 0, 1]


# =====================================================================
# Need decomposition
# =====================================================================

def test_need_indicators_aggregate_lifetime_profile():
    """Need decomposition uses substring matching against the controlled vocabulary."""
    person = pd.DataFrame({
        "All Referrals": [
            "Housing;Employment",
            "Connection to recovery community",
            "Recovery support;Probation;Overdose",
            None,
        ],
    })
    person = add_need_indicators(person)
    assert list(person["need_Housing"]) == [1, 0, 0, 0]
    assert list(person["need_Employment"]) == [1, 0, 0, 0]
    assert list(person["need_Probation"]) == [0, 0, 1, 0]
    # The Connection-to-treatment vs Connection-to-recovery-community case:
    # "Connection to recovery community" should NOT count as Connection to treatment,
    # because we use case-insensitive substring matching on the literal domain name.
    assert list(person["need_Connection to treatment"]) == [0, 0, 0, 0]
    assert list(person["need_Connection to recovery community"]) == [0, 1, 0, 0]
    # Missing referral data yields NaN complexity
    assert person["need_complexity"].iloc[3] != person["need_complexity"].iloc[3]


# =====================================================================
# Statistical tests
# =====================================================================

def test_wilson_ci_zero_n():
    assert wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_ci_extremes():
    lo, hi = wilson_ci(0, 100)
    assert lo < 1e-10
    assert 0 < hi < 5
    lo, hi = wilson_ci(100, 100)
    assert hi > 100 - 1e-10
    assert 95 < lo < 100


def test_jonckheere_terpstra_monotonic_signal():
    """When higher group has stochastically larger values, z should be positive."""
    rng = np.random.default_rng(0)
    g1 = rng.normal(0, 1, 50)
    g2 = rng.normal(1, 1, 50)
    g3 = rng.normal(2, 1, 50)
    z, p = jonckheere_terpstra([g1, g2, g3])
    assert z > 5
    assert p < 0.001


def test_jonckheere_terpstra_no_trend():
    rng = np.random.default_rng(0)
    g = [rng.normal(0, 1, 50) for _ in range(3)]
    z, p = jonckheere_terpstra(g)
    assert abs(z) < 2
    assert p > 0.05


def test_cochran_armitage_monotonic():
    z, p = cochran_armitage(
        x_levels=[0, 1, 2, 3],
        n_arr=[100, 100, 100, 100],
        k_arr=[10, 30, 50, 70],
    )
    assert z > 5
    assert p < 0.001


def test_fisher_with_fdr_corrects_p_values():
    """FDR-corrected q-values should be >= the raw p-values."""
    tables = [[[10, 5], [5, 10]], [[20, 1], [1, 20]], [[50, 50], [50, 50]]]
    ors, ps, qs = fisher_with_fdr(tables)
    assert (qs >= ps).all()
    # Significant tables should remain significant
    assert qs[1] < 0.01


# =====================================================================
# LCA
# =====================================================================

def test_bernoulli_lca_recovers_known_classes():
    """LCA should recover known structure when one exists."""
    rng = np.random.default_rng(0)

    # Two latent classes: one endorses items 0-2, the other endorses items 3-5
    n = 200
    z = rng.binomial(1, 0.5, n)
    rho_true = np.array([
        [0.95, 0.95, 0.95, 0.05, 0.05, 0.05],
        [0.05, 0.05, 0.05, 0.95, 0.95, 0.95],
    ])
    X = np.zeros((n, 6))
    for i in range(n):
        X[i] = rng.binomial(1, rho_true[z[i]])

    lca = BernoulliLCA(n_classes=2, n_init=20, random_state=42).fit(X)
    # Mean modal posterior should be high for well-separated classes
    assert lca.result_.resp.max(axis=1).mean() > 0.95
    # Recovered probabilities should match (up to label swap)
    rho_est = lca.result_.rho
    # Sort by sum to align with true ordering
    order = np.argsort(rho_est.sum(axis=1))
    rho_aligned = rho_est[order]
    rho_true_sorted = rho_true[np.argsort(rho_true.sum(axis=1))]
    assert np.allclose(rho_aligned, rho_true_sorted, atol=0.10)


def test_bernoulli_lca_clipping_prevents_divergence():
    """Saturated item probabilities should not blow up the EM."""
    # Construct a class where item 0 is always 1
    X = np.zeros((100, 5))
    X[:, 0] = 1
    X[50:, 1] = 1
    lca = BernoulliLCA(n_classes=2, n_init=5, random_state=0).fit(X)
    assert np.isfinite(lca.result_.log_lik)
    # rho should be clipped strictly inside (0, 1)
    assert (lca.result_.rho > 0).all()
    assert (lca.result_.rho < 1).all()
