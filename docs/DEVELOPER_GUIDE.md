# Developer Guide

This guide is for contributors and maintainers who want to extend the rdp-analytics package or understand its design.

## Contents

1. [Architecture](#architecture)
2. [Design decisions](#design-decisions)
3. [The two-step framing](#the-two-step-framing)
4. [Statistical method choices](#statistical-method-choices)
5. [Code style and conventions](#code-style-and-conventions)
6. [Adding a new feature decomposition](#adding-a-new-feature-decomposition)
7. [Adding a new statistical method](#adding-a-new-statistical-method)
8. [Adding a new figure](#adding-a-new-figure)
9. [Testing strategy](#testing-strategy)
10. [Release process](#release-process)

## Architecture

```
rdp_analytics/
  data.py        ← I/O layer: RDP Excel exports → person-level DataFrames
  features.py    ← Variable construction: needs, pathways, severity, demographics
  step1_stats.py ← Inferential statistics: Fisher's, FDR, Jonckheere-Terpstra
  step2_ml.py    ← Machine learning: LCA, CART, RF, UMAP
  figures.py     ← Publication-quality figure generation
  pipeline.py    ← Orchestration: end-to-end from input to outputs
```

The dependency graph is strict and downward-only:

```
pipeline → figures → step1_stats, step2_ml
        ↓                ↓
       features ← step1_stats, step2_ml
        ↓
       data
```

This means:
- `data.py` has zero internal dependencies
- `features.py` depends only on `data.py`
- `step1_stats.py` and `step2_ml.py` depend only on `features.py` (and standard libraries)
- `figures.py` depends on the step modules
- `pipeline.py` orchestrates everything

If you find yourself wanting to import `figures` into `step1_stats`, the design is wrong somewhere.

## Design decisions

### Why a package, not a notebook

The original analysis lived in Jupyter notebooks. We migrated to a package for three reasons. First, the manuscript's Code Availability section promises reproducibility, and notebooks are notoriously hard to reproduce because of execution-order dependencies. Second, when reviewers ask for a sensitivity analysis, we want to be able to run it as `pipeline.py --sensitivity` rather than re-execute cells in a particular order. Third, we wanted regression tests for the bugs we caught during development (especially the Hispanic indicator), and that requires a testable API.

### Why Bernoulli mixture from scratch instead of stepmix

We evaluated stepmix and lost a few hours to a sklearn version incompatibility. The Bernoulli mixture EM is approximately 60 lines of clear code, and writing it ourselves means we control the convergence criteria, the initialization strategy, and the clipping behavior at the boundary. For a fixed-scope research package, the stability tradeoff favored implementing it directly. If a maintained, well-tested LCA library becomes available, swapping `BernoulliLCA` for it would be a one-method refactor.

### Why pooled permutation importance across multiple seeds

A single `permutation_importance` call with `n_repeats=20` is cleaner code, but on our cohort size it took multiple minutes per run, which made interactive exploration painful. Pooling across four seeds with `n_repeats=5` gives an effectively-equivalent variance estimate at four-times-faster wall time per individual call (parallel execution where available). The pooling is documented in `permutation_importance_pooled` and is straightforward to revert if you'd rather have a single longer run.

### Why SVG with text-as-text

Reviewers often request edits to figures: changing a label, swapping a color, adjusting an annotation. SVG files with `svg.fonttype = 'none'` preserve text as text, which means the figures are directly editable in Illustrator or Inkscape without OCR or recreation. PNG copies are also written for inline preview in markdown and chat tools.

### Why constrained_layout instead of tight_layout

`constrained_layout` is more deterministic across matplotlib versions and handles colorbars and suptitles more gracefully. It does add some overhead for very complex figures (the LCA panel grid takes ~2-3 seconds to render), but the deterministic output is worth it for reproducibility.

## The two-step framing

The package is structured around a deliberate two-step analytic approach:

**Step 1 (`step1_stats.py`).** Methods that any analyst with introductory biostatistics training can perform. These produce the descriptive findings reported in Figures 1-5. The functions are deliberately minimalist; we use scipy or statsmodels under the hood rather than reimplementing standard tests.

**Step 2 (`step2_ml.py`).** Methods that require a second layer of methodological investment but produce decision-support output usable at intake. These produce Figures 6-9. The functions wrap scikit-learn classifiers with cross-validated evaluation and (where appropriate) permutation importance.

The split is not just organizational; it's pedagogical. The manuscript uses this framing to argue that meaningful operational insights are accessible at both methodological tiers. If you add functionality, place it in the tier that matches the methodological barrier to entry.

## Statistical method choices

Several method choices in this package are deliberate and worth documenting.

### Jonckheere-Terpstra over Kruskal-Wallis for ordinal exposures

Kruskal-Wallis is an omnibus test for differences across groups; it does not test for trend. When the exposure is ordinal (need complexity, pathway diversity, severity score), the question is "is there a monotonic trend across levels," not "are any levels different from any other levels." Jonckheere-Terpstra is the directional generalization and provides a signed z-statistic.

We had Kruskal-Wallis in the first analysis pass, and the trend interpretations were sloppy because we were back-translating from "p < 0.001 across 11 levels of need complexity" to "this is a trend." Jonckheere-Terpstra is the honest test.

### Fisher's exact over chi-square for sparse cells

Many of the need-pathway cells in our 80-test matrix have small expected frequencies. Chi-square's normal approximation is unreliable in that regime; Fisher's exact is exact. The cost is computational, but with N ~ 1,400 the runtime is irrelevant.

### Benjamini-Hochberg FDR over Bonferroni

The 80 need-pathway tests are not independent (a participant with overdose-need is more likely to also have multiple-tx-episodes). Bonferroni assumes independence and over-corrects. Benjamini-Hochberg controls the false discovery rate under positive dependence, which is the appropriate target for an exploratory adoption matrix.

### Wilson score CI over Wald CI for proportions

Wald CIs degenerate at the boundary (a proportion of 0 or 1 has a CI of width 0), and they can produce intervals that extend below 0 or above 1 for moderate sample sizes. Wilson score CIs are well-behaved everywhere and are the modern standard recommendation.

### Class-balanced weighting in scikit-learn classifiers

Engagement is ~66% positive in our cohort. Without class weighting, AUC-optimal tree splits and random forest votes tend toward the majority class. We use `class_weight="balanced"` throughout the ML step. If you change this, document the justification.

### Permutation importance over impurity importance for random forests

Impurity importance (the default `feature_importances_` attribute) is biased toward high-cardinality features and toward features used early in tree splits. Permutation importance is computed on held-out data and is robust to both. For any importance claim that goes into a paper, use permutation importance.

## Code style and conventions

We don't enforce a formatter. Match the existing style:

- Line length around 100 characters
- Type hints on public functions, especially numeric returns
- Docstrings on all public functions and classes (NumPy-style)
- Module-level docstrings explaining the role of each file
- Constants declared at module scope in UPPERCASE
- Helper functions prefixed with underscore

Imports are organized:
1. Standard library
2. Third-party scientific stack (numpy, pandas, scipy)
3. Third-party ML stack (scikit-learn, statsmodels, umap)
4. Internal (from rdp_analytics import ...)

## Adding a new feature decomposition

Suppose you want to add a derived "high engagement intensity" indicator.

1. **Add the construction to `features.py`.** Document the source field, the construction logic, and any completeness caveats. Use exact match rather than substring matching when possible.

2. **Add to `get_feature_lists()` if it should be in the canonical ML feature lists.** Place it in the appropriate category (need, severity, structural, service, demographic).

3. **Add a test in `tests/test_features.py`.** At minimum, test that:
   - The indicator is correctly constructed for known inputs
   - Edge cases (NaN, empty string, unexpected values) are handled
   - The indicator does not introduce a substring-matching bug

4. **Update the variable construction glossary in `docs/USER_GUIDE.md`.**

5. **If the new feature changes the canonical feature list,** verify that the integration test still passes (the package should reproduce the same paper numbers from the same input data).

## Adding a new statistical method

Suppose you want to add a new trend test.

1. **Add the function to `step1_stats.py`** with NumPy-style docstring. Take arrays in, return primitive types or named tuples out.

2. **Take an explicit `random_state` argument** if any sampling is involved.

3. **Document the assumptions in the docstring.** Independence, distributional assumptions, what happens with ties, etc.

4. **Add a test in `tests/test_features.py`** that:
   - Tests correctness against a known reference (a small worked example or comparison to scipy/statsmodels)
   - Tests that the function returns the expected sign for a designed signal
   - Tests behavior on edge cases (empty groups, single group, ties)

5. **If the function is intended to replace an existing test in the pipeline,** add a comparison note in the developer guide explaining why.

## Adding a new figure

1. **Add the function to `figures.py`** following the pattern of existing functions: take a data dict or DataFrame in, take an output path argument, write SVG and PNG, close the figure.

2. **Use the package-level matplotlib settings.** They are set at module import time and assume serif fonts, sans-serif-friendly colors, no top/right spines, and `svg.fonttype = 'none'`.

3. **Embed the relevant statistics in the figure title or caption** so the figure is self-contained and reviewers don't need to cross-reference text.

4. **Match the color palette of related figures.** The existing figures use a small consistent palette (defined inline in each function); adding a new figure should not introduce a new palette without justification.

5. **Add a call to the figure from `pipeline.py`** in the appropriate Step 1 or Step 2 section.

## Testing strategy

Tests live in `tests/` and are run with pytest. The current suite covers:

- **Regression tests for known bugs** (`test_hispanic_indicator_no_substring_bug`, `test_need_indicators_aggregate_lifetime_profile`). These exist specifically because we introduced these bugs once.

- **Correctness tests for statistical functions** (`test_jonckheere_terpstra_*`, `test_cochran_armitage_*`, `test_fisher_with_fdr_*`, `test_wilson_ci_*`). These verify the functions return expected values for known inputs.

- **Edge-case tests** (`test_wilson_ci_zero_n`, `test_wilson_ci_extremes`). These verify graceful behavior at boundaries.

- **Recovery tests for ML** (`test_bernoulli_lca_recovers_known_classes`, `test_bernoulli_lca_clipping_prevents_divergence`). These verify the EM recovers known structure and doesn't blow up at saturation.

When adding new functionality, the threshold for a test is "would I want to be sure this didn't silently break six months from now."

We do not test the figure functions directly because they're hard to test without visual regression infrastructure. We test the data and statistical functions thoroughly, and verify figures by inspection.

## Release process

This package follows semantic versioning.

To release a new version:

1. Update version in `pyproject.toml` and `rdp_analytics/__init__.py`
2. Update `CHANGELOG.md` (create if not present) with the changes since the last version
3. Tag the commit: `git tag v0.x.y && git push --tags`
4. Build and upload to PyPI if appropriate: `python -m build && twine upload dist/*`

For now, we're keeping the package source-installable from GitHub rather than publishing to PyPI. If we publish, the citation in the manuscript should be updated to include the PyPI version.

## Things that are deliberately not in this package

- Bayesian re-estimation of any model. We're using frequentist methods throughout and have argued why in the manuscript.
- Survival analysis (Cox, Kaplan-Meier). We document in the developer guide and manuscript why we moved away from Cox for retention.
- Causal inference methods (instrumental variables, propensity scores). The data is observational and the manuscript explicitly avoids causal claims.
- Visualization libraries beyond matplotlib. We use matplotlib because the figures need to be edited by hand by reviewers and editors.
- Configuration files (YAML, TOML beyond pyproject). The pipeline takes its small set of arguments via CLI flags. If the configuration surface grows substantially, revisit.

## Contact

For questions about the architecture or design decisions: marcus@bellwetherbiotech.com.

For specific PRs, please use the GitHub issue tracker.
