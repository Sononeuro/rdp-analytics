# Contributing to rdp-analytics

Thanks for your interest in contributing. This package was built around a specific manuscript and a specific data system, but the analytic recipe is meant to generalize. Bug reports, methodological pushback, additional tests, and pull requests applying the pipeline to other RDP exports are all welcome.

## Quick start for contributors

```bash
git clone https://github.com/sononeuro/rdp-analytics
cd rdp-analytics
pip install -e ".[test]"
pytest tests/ -v
```

If the test suite passes you're set up correctly.

## What kinds of contributions are useful

**Bug reports.** If a function returns the wrong answer, an indicator is constructed incorrectly, or the pipeline fails on a real RDP export, please open an issue with a minimal reproduction.

**Methodological pushback.** The two-step framing of this paper has empirical and theoretical commitments. If you think a method choice is wrong (e.g., that we should be using a different LCA implementation, that our severity composite is poorly specified, or that our trend tests are inappropriate), please open a discussion. We will not always change the method, but we will engage with the argument.

**New analyses on other RDP exports.** If you've run the pipeline on a different recovery community organization's data, we'd like to know what worked, what broke, and what variables you had to map differently. A short writeup as an issue or a PR adding a notebook to `notebooks/` is the right format.

**Tests for new pitfalls.** The Hispanic-indicator test is documented in `tests/test_features.py` as a deliberate teaching example. If you discover another category of subtle bug that's easy to introduce when working with RDP fields, please add a test for it with a comment explaining the scenario.

**Documentation improvements.** Especially translation of the methods explanations into language a peer specialist or RCO director could read directly.

## What's out of scope

This package is not a general-purpose biostatistics toolkit. We won't add functionality that doesn't trace back to a specific RDP-export analysis need. If you want a feature that would, say, add a Bayesian re-estimation of the LCA, please open a discussion first to scope whether it belongs here or in a downstream package.

## Pull request expectations

- Pass the existing test suite (`pytest tests/`).
- Add tests for new functionality. The threshold for what needs a test is "would I want to be sure this didn't silently break six months from now."
- Match the existing code style. We don't enforce a formatter, but the package generally follows PEP 8 with line length around 100, docstrings on all public functions, and type hints where they help readability.
- Update `docs/USER_GUIDE.md` if you change the user-facing API.
- Update `docs/DEVELOPER_GUIDE.md` if you change internal architecture.
- Reference the manuscript in commit messages for analyses tied to specific paper findings.

## Variable construction conventions

When adding new derived features in `features.py`:

- Document the construction in the docstring with the source RDP field name.
- Note completeness of the source field (e.g., "100% complete in our cohort" or "49% complete; missing values treated as zero").
- If the construction is brittle (e.g., substring matching against a controlled vocabulary), add a regression test in `tests/test_features.py`.
- Use exact-match comparison rather than substring matching whenever the source values are categorical with known labels. This is what burned us with the Hispanic indicator.

## Statistical method conventions

When adding new statistical functions in `step1_stats.py` or `step2_ml.py`:

- Functions should take arrays or DataFrames in, return primitive types or named tuples out.
- Random methods take an explicit `random_state` argument.
- Multiple-comparison correction is the default for any function returning more than 5 p-values.
- Report effect sizes alongside p-values in figure captions.

## Reporting security issues

If you find a security issue (e.g., a way the package could be used to re-identify participants from a de-identified export), please email the corresponding author directly rather than opening a public issue.

## Code of conduct

Be kind. This work is personal for many of us. Engage with substance, not affect.

## Contact

Marcus S. Bell, marcus@bellwetherbiotech.com
