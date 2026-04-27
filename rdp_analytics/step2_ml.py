"""Step 2: Basic machine learning for RDP person-level data.

Four methods:
- BernoulliLCA:               latent class analysis via EM on binary indicators
- fit_cart_for_pathway:       interpretable decision tree for pathway endorsement
- fit_random_forest_engagement: random forest classifier for engagement
- permutation_importance_pooled: pooled permutation importance across multiple seeds
- umap_projection:            UMAP 2D projection for visualization

All methods use a fixed random seed for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.special import logsumexp
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


# =====================================================================
# Latent class analysis: Bernoulli mixture model fit by EM
# =====================================================================

@dataclass
class LCAResult:
    """Container for a fitted Bernoulli mixture LCA model."""
    n_classes: int
    log_lik: float
    pi: np.ndarray            # (K,) class proportions
    rho: np.ndarray           # (K, J) item-response probabilities
    resp: np.ndarray          # (N, K) posterior class probabilities
    n_params: int
    bic: float
    aic: float
    entropy_R2: float


class BernoulliLCA:
    """Latent class analysis for binary indicators via Bernoulli mixture EM.

    We implement this from scratch rather than using stepmix because of a
    sklearn version incompatibility in stepmix at the time of writing. The
    algorithm is standard EM for a finite mixture of independent Bernoullis.

    Item-response probabilities are clipped to [1e-6, 1 - 1e-6] each iteration
    to prevent log-likelihood divergence when a class becomes deterministic
    on a particular item.

    Parameters
    ----------
    n_classes : int
    n_init :    int, number of random restarts (best by log-likelihood is kept)
    max_iter :  int, maximum EM iterations per restart
    tol :       float, log-likelihood convergence tolerance
    random_state : int or None
    """

    def __init__(
        self,
        n_classes: int,
        n_init: int = 20,
        max_iter: int = 500,
        tol: float = 1e-6,
        random_state: Optional[int] = None,
    ):
        self.K = n_classes
        self.n_init = n_init
        self.max_iter = max_iter
        self.tol = tol
        self.rng = np.random.default_rng(random_state)
        self.result_: Optional[LCAResult] = None

    def _fit_one(self, X: np.ndarray, init_state: int) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
        N, J = X.shape
        K = self.K
        rng = np.random.default_rng(init_state)

        # Init: random class probs and item probs jittered around mean
        pi = rng.dirichlet(np.ones(K))
        mean = X.mean(axis=0)
        rho = np.clip(mean[None, :] + rng.normal(0, 0.15, size=(K, J)), 0.05, 0.95)

        prev_ll = -np.inf
        for _ in range(self.max_iter):
            # E-step
            log_pi = np.log(pi + 1e-300)
            log_rho = np.log(rho + 1e-300)
            log_1mrho = np.log(1 - rho + 1e-300)
            log_lik = X @ log_rho.T + (1 - X) @ log_1mrho.T
            log_post = log_pi[None, :] + log_lik
            log_norm = logsumexp(log_post, axis=1, keepdims=True)
            log_resp = log_post - log_norm
            resp = np.exp(log_resp)
            ll = log_norm.sum()

            # M-step
            Nk = resp.sum(axis=0) + 1e-12
            pi = Nk / N
            rho = (resp.T @ X) / Nk[:, None]
            rho = np.clip(rho, 1e-6, 1 - 1e-6)

            if abs(ll - prev_ll) < self.tol:
                break
            prev_ll = ll
        return ll, pi, rho, resp

    def fit(self, X: np.ndarray) -> "BernoulliLCA":
        """Fit the model by EM with multiple random restarts.

        Returns
        -------
        self : the fitted estimator (with `.result_` populated)
        """
        X = np.asarray(X, dtype=float)
        best = None
        for _ in range(self.n_init):
            res = self._fit_one(X, init_state=int(self.rng.integers(0, 1 << 31)))
            if best is None or res[0] > best[0]:
                best = res
        ll, pi, rho, resp = best

        n_params = (self.K - 1) + self.K * X.shape[1]
        bic = -2 * ll + n_params * np.log(X.shape[0])
        aic = -2 * ll + 2 * n_params

        # Entropy R^2 (normalized class-membership entropy)
        entropy = -(resp * np.log(resp + 1e-300)).sum(axis=1).mean()
        max_entropy = np.log(self.K)
        entropy_R2 = 1 - entropy / max_entropy if max_entropy > 0 else 1.0

        self.result_ = LCAResult(
            n_classes=self.K, log_lik=ll, pi=pi, rho=rho, resp=resp,
            n_params=n_params, bic=bic, aic=aic, entropy_R2=entropy_R2,
        )
        return self


def lca_model_selection(
    X: np.ndarray, k_range: range = range(2, 8), n_init: int = 20,
    random_state: int = 20260426
) -> pd.DataFrame:
    """Fit BernoulliLCA across k values and return BIC/AIC/entropy comparison.

    Used to select the number of latent classes (Figure 6 panel A).
    """
    rows = []
    for k in k_range:
        m = BernoulliLCA(n_classes=k, n_init=n_init, random_state=random_state + k).fit(X)
        r = m.result_
        rows.append({"k": k, "LL": r.log_lik, "BIC": r.bic, "AIC": r.aic, "entropy_R2": r.entropy_R2})
    return pd.DataFrame(rows)


def reorder_lca_classes_by_complexity(
    rho: np.ndarray, pi: np.ndarray, resp: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Reorder LCA classes by ascending need complexity (sum of item probs).

    Returns reordered (rho, pi, resp, perm) where `perm` is the permutation
    used (so caller can map old class IDs to new ones).
    """
    complexity = rho.sum(axis=1)
    perm = np.argsort(complexity)
    return rho[perm], pi[perm], resp[:, perm], perm


# =====================================================================
# Classification tree (CART) for pathway endorsement
# =====================================================================

def fit_cart_for_pathway(
    person: pd.DataFrame,
    features: list[str],
    target_col: str = "path_Medication_assisted_Recovery",
    max_depth: int = 4,
    min_samples_leaf: int = 20,
    random_state: int = 20260426,
) -> tuple[DecisionTreeClassifier, dict]:
    """Fit an interpretable CART tree predicting pathway endorsement.

    Reproduces Figure 7 of the manuscript with default parameters.

    Returns
    -------
    (model, info) where info contains 'cv_auc_mean', 'cv_auc_std', 'n', 'features'
    """
    data = person[features + [target_col]].dropna()
    X = data[features].values
    y = data[target_col].values

    clf = DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        class_weight="balanced",
        random_state=random_state,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    aucs = cross_val_score(clf, X, y, scoring="roc_auc", cv=cv)
    clf.fit(X, y)

    info = {
        "cv_auc_mean": float(aucs.mean()),
        "cv_auc_std": float(aucs.std()),
        "n": len(data),
        "features": list(features),
        "target": target_col,
    }
    return clf, info


# =====================================================================
# Random forest for engagement
# =====================================================================

def fit_random_forest_engagement(
    person: pd.DataFrame,
    features: list[str],
    target_col: str = "engaged",
    n_estimators: int = 200,
    min_samples_leaf: int = 5,
    random_state: int = 20260426,
) -> tuple[RandomForestClassifier, dict]:
    """Fit a random forest classifier predicting engagement.

    Reproduces Figure 8 panel A. Uses class-balanced training because the
    engagement rate (~66%) is imbalanced enough to matter for AUC.

    Returns
    -------
    (model, info) where info contains 'cv_aucs', 'oob', 'n', 'features',
    plus the fitted CV ROC arrays for plotting.
    """
    data = person[features + [target_col]].dropna()
    X = data[features].values
    y = data[target_col].values

    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        min_samples_leaf=min_samples_leaf,
        max_features="sqrt",
        class_weight="balanced",
        oob_score=True,
        n_jobs=1,
        random_state=random_state,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    cv_aucs = cross_val_score(rf, X, y, scoring="roc_auc", cv=cv)

    # Refit on full data for the importance analysis and OOB
    rf.fit(X, y)

    # CV ROC curves for plotting (one per fold)
    all_fpr = np.linspace(0, 1, 100)
    tprs = []
    for tr, te in cv.split(X, y):
        rf_cv = RandomForestClassifier(
            n_estimators=n_estimators,
            min_samples_leaf=min_samples_leaf,
            max_features="sqrt",
            class_weight="balanced",
            n_jobs=1,
            random_state=random_state,
        )
        rf_cv.fit(X[tr], y[tr])
        proba = rf_cv.predict_proba(X[te])[:, 1]
        fpr, tpr, _ = roc_curve(y[te], proba)
        tprs.append(np.interp(all_fpr, fpr, tpr))

    info = {
        "cv_aucs": cv_aucs,
        "oob": float(rf.oob_score_),
        "n": len(data),
        "features": list(features),
        "target": target_col,
        "roc_fpr": all_fpr,
        "roc_tpr_mean": np.mean(tprs, axis=0),
        "roc_tpr_std": np.std(tprs, axis=0),
    }
    return rf, info


def permutation_importance_pooled(
    estimator,
    X: np.ndarray,
    y: np.ndarray,
    n_repeats_per_seed: int = 5,
    seeds: tuple[int, ...] = (20260426, 42, 7, 1234),
) -> tuple[np.ndarray, np.ndarray]:
    """Compute permutation importance pooled across multiple random seeds.

    Returns (means, stds) on the accuracy scale. Pooling across 4 seeds with
    n_repeats=5 each gives effective n_repeats=20 with shorter wall time per
    invocation than a single n_repeats=20 call.
    """
    all_means = []
    all_stds = []
    for seed in seeds:
        perm = permutation_importance(
            estimator, X, y, n_repeats=n_repeats_per_seed, random_state=seed, n_jobs=1
        )
        all_means.append(perm.importances_mean)
        all_stds.append(perm.importances_std)
    means = np.mean(all_means, axis=0)
    stds = np.sqrt(np.mean(np.array(all_stds) ** 2, axis=0))
    return means, stds


# =====================================================================
# UMAP projection for visualization
# =====================================================================

def umap_projection(
    person: pd.DataFrame,
    features: list[str],
    n_neighbors: int = 25,
    min_dist: float = 0.15,
    metric: str = "euclidean",
    random_state: int = 20260426,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Project participants into 2D using UMAP on a standardized feature matrix.

    Reproduces Figure 9. Pathway components should be excluded from the
    feature list when projecting alongside LCA-derived classes to avoid
    trivial circularity (LCA classes were derived from need indicators only,
    but pathway adoption correlates with class structure).

    Returns
    -------
    (embedding, data) where embedding is (N, 2) and data is the DataFrame
    of participants used (subset of person with non-null features).
    """
    import umap  # imported lazily to avoid hard dep at import time

    data = person[features].dropna()
    Xs = StandardScaler().fit_transform(data.values)

    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
        n_jobs=1,
    )
    emb = reducer.fit_transform(Xs)
    return emb, data
