"""Step 1: Inferential statistics for RDP person-level data.

These are classical methods that any analyst with introductory biostatistics
training can perform. They produce the descriptive findings reported in the
manuscript and underpin Figures 1-5.

Functions:
- wilson_ci:           Wilson score 95% CI for a binomial proportion
- cochran_armitage:    trend test for ordinal exposure x binary outcome
- jonckheere_terpstra: trend test for ordinal exposure x continuous outcome
- fisher_with_fdr:     Fisher's exact across many 2x2 tables with BH-FDR
- need_pathway_matrix: full need-by-pathway adoption matrix with FDR correction
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score 95% confidence interval for a binomial proportion.

    Returns (lower, upper) on the percentage scale.
    """
    if n == 0:
        return (0.0, 0.0)
    z = stats.norm.ppf(1 - alpha / 2)
    p = k / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    err = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return ((centre - err) / denom * 100, (centre + err) / denom * 100)


def cochran_armitage(
    x_levels: Sequence[float], n_arr: Sequence[int], k_arr: Sequence[int]
) -> tuple[float, float]:
    """Cochran-Armitage trend test for proportions across an ordinal exposure.

    Parameters
    ----------
    x_levels : ordinal score values
    n_arr    : sample size at each level
    k_arr    : event count at each level

    Returns
    -------
    (z, p) : test statistic and two-sided p-value
    """
    n_arr = np.asarray(n_arr)
    k_arr = np.asarray(k_arr)
    x = np.asarray(x_levels, dtype=float)
    N = n_arr.sum()
    K = k_arr.sum()
    if N == 0:
        return (0.0, 1.0)
    p = K / N
    num = ((x - (x * n_arr).sum() / N) * k_arr).sum()
    den = (p * (1 - p) * ((x - (x * n_arr).sum() / N) ** 2 * n_arr).sum()) ** 0.5
    z = num / den if den > 0 else 0.0
    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    return (z, pval)


def jonckheere_terpstra(groups: Iterable[np.ndarray]) -> tuple[float, float]:
    """Jonckheere-Terpstra trend test across ordered groups.

    Tests for a monotonic trend in central tendency across groups in their
    given order. More appropriate than Kruskal-Wallis when the exposure is
    ordinal because it provides a directional z-statistic.

    Parameters
    ----------
    groups : iterable of arrays, in increasing order of the exposure

    Returns
    -------
    (z, p) : standardized test statistic and two-sided p-value

    Notes
    -----
    Implemented in pure Python; quadratic in total N. Adequate for the
    cohort sizes in our analyses (n ~ 1,400). Use a scipy/statsmodels
    implementation for larger datasets if available.
    """
    g = [np.asarray(x) for x in groups]
    k = len(g)
    n = [len(a) for a in g]
    N = sum(n)
    if N == 0 or k < 2:
        return (0.0, 1.0)

    U = 0.0
    for i in range(k):
        for j in range(i + 1, k):
            ai = g[i]
            aj = g[j]
            for v in ai:
                U += (aj > v).sum() + 0.5 * (aj == v).sum()

    mean_U = (N**2 - sum(ni**2 for ni in n)) / 4
    var_U = (N**2 * (2 * N + 3) - sum(ni**2 * (2 * ni + 3) for ni in n)) / 72
    z = (U - mean_U) / np.sqrt(var_U) if var_U > 0 else 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return (z, p)


def fisher_with_fdr(
    contingency_tables: list[list[list[int]]], method: str = "fdr_bh"
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run Fisher's exact tests across many 2x2 tables with FDR correction.

    Parameters
    ----------
    contingency_tables : list of [[a, b], [c, d]] 2x2 tables
    method : multiple-comparison correction method (passed to statsmodels)

    Returns
    -------
    odds_ratios, p_values, q_values : np.ndarray, all length N
    """
    ors = []
    pvs = []
    for table in contingency_tables:
        OR, pv = stats.fisher_exact(table)
        ors.append(OR)
        pvs.append(pv)
    pvs = np.array(pvs)
    _, qvs, _, _ = multipletests(pvs, method=method)
    return np.array(ors), pvs, qvs


def need_pathway_matrix(
    person: pd.DataFrame,
    need_domains: Sequence[str],
    pathway_components: Sequence[str],
) -> dict:
    """Compute the full need-by-pathway adoption matrix with FDR correction.

    Reproduces Figure 2 of the manuscript: 80 Fisher's exact tests across the
    need-by-pathway grid, FDR-corrected with Benjamini-Hochberg.

    Returns
    -------
    dict with keys:
      - pct_with    : (n_need, n_path) matrix of % adoption among participants WITH the need
      - pct_without : same, among participants WITHOUT the need
      - diff_pp     : pct_with - pct_without (percentage-point shift)
      - or_matrix   : odds ratios
      - pvals       : raw p-values
      - qvals       : BH-FDR-corrected q-values
      - n_with_need : sample sizes for each need domain
    """
    sub = person[person["All Referrals"].notna() & person["Pathways"].notna()].copy()
    nD, nP = len(need_domains), len(pathway_components)

    pct_with = np.zeros((nD, nP))
    pct_without = np.zeros((nD, nP))
    diff_pp = np.zeros((nD, nP))
    or_matrix = np.zeros((nD, nP))
    pvals = np.zeros((nD, nP))
    n_with_need = np.zeros(nD, dtype=int)

    for i, d in enumerate(need_domains):
        has_need = sub[f"need_{d}"] == 1
        n_with_need[i] = int(has_need.sum())
        for j, p in enumerate(pathway_components):
            col = f"path_{p.replace(' ', '_').replace('-', '_').replace('/', '_')}"
            a = int(((sub[col] == 1) & has_need).sum())
            b = int(((sub[col] == 0) & has_need).sum())
            c = int(((sub[col] == 1) & ~has_need).sum())
            d2 = int(((sub[col] == 0) & ~has_need).sum())
            OR, pv = stats.fisher_exact([[a, b], [c, d2]])
            pct_with[i, j] = 100 * a / max(int(has_need.sum()), 1)
            pct_without[i, j] = 100 * c / max(int((~has_need).sum()), 1)
            diff_pp[i, j] = pct_with[i, j] - pct_without[i, j]
            or_matrix[i, j] = OR
            pvals[i, j] = pv

    flat_p = pvals.flatten()
    _, qvs_flat, _, _ = multipletests(flat_p, method="fdr_bh")
    qvals = qvs_flat.reshape(pvals.shape)

    return {
        "pct_with": pct_with,
        "pct_without": pct_without,
        "diff_pp": diff_pp,
        "or_matrix": or_matrix,
        "pvals": pvals,
        "qvals": qvals,
        "n_with_need": n_with_need,
        "N": len(sub),
    }


def pairwise_fisher_vs_reference(
    df: pd.DataFrame,
    group_col: str,
    outcome_col: str,
    reference_value,
    fdr_method: str = "fdr_bh",
) -> pd.DataFrame:
    """Pairwise Fisher's exact comparing each group level to a reference.

    Used for Figure 5 (Lives In vs Recovery Residence reference).

    Returns a DataFrame with columns:
        group, n, n_event, pct_event, OR_vs_reference, p, q
    """
    rows = []
    pvs = []
    keys = []

    ref = df[df[group_col] == reference_value]
    ref_n = len(ref)
    ref_e = int(ref[outcome_col].sum())

    for grp, sub in df.groupby(group_col, observed=True):
        if grp == reference_value:
            continue
        n = len(sub)
        e = int(sub[outcome_col].sum())
        if n < 5:
            continue
        OR, pv = stats.fisher_exact([[e, n - e], [ref_e, ref_n - ref_e]])
        rows.append({
            "group": grp,
            "n": n,
            "n_event": e,
            "pct_event": 100 * e / n,
            "OR_vs_reference": OR,
            "p": pv,
        })
        pvs.append(pv)
        keys.append(grp)

    if pvs:
        _, qvs, _, _ = multipletests(np.array(pvs), method=fdr_method)
        for row, q in zip(rows, qvs):
            row["q"] = q

    return pd.DataFrame(rows)


def fmt_p(p: float) -> str:
    """Format a p-value for figure captions and tables.

    Returns 'p < 0.001' for very small p, three-decimal precision otherwise.
    """
    if p < 0.001:
        return "p < 0.001"
    if p < 0.01:
        return f"p = {p:.3f}"
    return f"p = {p:.2f}"
