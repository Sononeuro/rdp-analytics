# rdp-analytics

[![tests](https://github.com/sononeuro/rdp-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/sononeuro/rdp-analytics/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

Open-source analytic pipeline for Recovery Data Platform (RDP) exports. Reproduces all descriptive statistics, regression models, latent class fitting, decision trees, random forest training and permutation importance, and UMAP visualizations reported in:

> Walton CM, Oldham BB, Markie F, Fiala B, Bell MS. Real-world decision trees for peer recovery support specialists: findings and methods from 1,411 community peer recovery participants in Minnesota. *Manuscript in preparation, 2026.*

## Install

```bash
git clone https://github.com/sononeuro/rdp-analytics
cd rdp-analytics
pip install -e .
```

Requires Python 3.10 or newer.

## Quick start

```bash
python -m rdp_analytics.pipeline \
  --input data/RDP_export.xlsx \
  --output figures/
```

Or from Python:

```python
from rdp_analytics import build_person_dataset, run_full_analysis

person = build_person_dataset("data/RDP_export.xlsx")
results = run_full_analysis(person, output_dir="figures/")
```

## Documentation

- **[User guide](docs/USER_GUIDE.md).** Installation details, the public API, common workflows, and a glossary of variable constructions. Read this if you want to apply the pipeline to your own RDP export.
- **[Developer guide](docs/DEVELOPER_GUIDE.md).** Internal architecture, design decisions, statistical method choices, and the rationale for the two-step framing. Read this if you want to contribute or extend the package.
- **[Notebook walkthrough](notebooks/01_walkthrough.ipynb).** A step-by-step Jupyter notebook that reproduces the manuscript figures from a representative RDP export, with prose commentary at each step.
- **[Contributing](CONTRIBUTING.md).** Guidelines for bug reports, methodological pushback, and pull requests.

## License

MIT. See [LICENSE](LICENSE).

## Citation

If you use this package, please cite the manuscript above and link to this repository.

## Contact

Marcus S. Bell, marcus@bellwetherbiotech.com
