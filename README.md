# PHISHES

![logo](<images/2line _ LOGO PHISHES _ 2024.png>)

PHISHES seeks to bridge the gap between soil health data and actions, providing much-needed predictive capability in terms of the consequences of actions on the provision of soil functions and associated ecosystem services, taking into account soil use, soil contamination and various drivers such as climate change.

## Overview

This repository hosts Python tooling and notebooks that support the PHISHES simulation platform. It is
organised around two layers:

- **`data-download-tool/`** — shared infrastructure that pulls clipped datasets (climate time series,
  static rasters, vector layers, partner data bundles) from the PDP datastore for a catchment you define
- **`model-trains/`** — one self-contained project per coupled model train, each consuming the
  downloaded data and producing that train's simulation inputs

Most user-facing workflows are provided as Jupyter notebooks in the module folders.

## Requirements

- Windows, Linux, or macOS
- Python x64 3.10 - 3.13 (each module pins `3.11` to match CI)
- Per model train: the third-party simulation software that train drives (MIKE SHE + MIKE ECO Lab,
  Daisy, HYDRUS-1D, MODFLOW). None of it is redistributed here — each train's README lists what it
  needs and where to download it.

## Installation

Installations are handled per sub-project — each has its own environment. See that project's README
for setup steps:

- [data-download-tool/README.md](data-download-tool/README.md)
- Model trains: pick yours from the index in [model-trains/README.md](model-trains/README.md), then
  follow that train's own README

## Where can I get help?

- Shared download tooling: [data-download-tool/README.md](data-download-tool/README.md)
- Model trains — index, status and scientific descriptions: [model-trains/README.md](model-trains/README.md)
- Repository design: [REPOSITORY_DESIGN.md](REPOSITORY_DESIGN.md)
- Contributing and CI: [CONTRIBUTING.md](CONTRIBUTING.md)

## 📦 What this repository contains

### Data Download Tool

Downloads dataset subsets clipped to a catchment: Zarr time series, Cloud Optimized GeoTIFF static
rasters, GeoParquet vector layers, and partner data zip bundles. Shared by every model train.

- Location: [data-download-tool/](data-download-tool/)
- Documentation: [data-download-tool/README.md](data-download-tool/README.md)

### Model trains

Each model train is an independent project under [model-trains/](model-trains/), built by one of the
project partners, that produces the simulation inputs for its own chain of coupled models. Some take
their data from the download tool, others ship with their own.

[model-trains/README.md](model-trains/README.md) is the single index: which trains exist, which one
fits your problem, who delivered each, and the scientific description of each — inputs, the coupling,
the data exchanged between components, and outputs. Start there and follow the link to the train you
need.

Available to use today:

- **MIKE SHE–MIKE ECO Lab Plant Growth Module** (DHI) — [model-trains/MSHE-Ecolab-PGM/](model-trains/MSHE-Ecolab-PGM/)
- **MODFLOW6-reservoir-model** (Deltares) — [model-trains/MODFLOW6-reservoir-model/](model-trains/MODFLOW6-reservoir-model/)
- **1D HYDRUS–PHREEQC–MODFLOW-2005–MT3D** (BRGM) — [model-trains/1D-HYDRUS-PHREEQC-MODFLOW2005-MT3D/](model-trains/1D-HYDRUS-PHREEQC-MODFLOW2005-MT3D/)

## 📁 Repository structure (high level)

```
phishes-pdp/
├── README.md
├── REPOSITORY_DESIGN.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── .github/                                # CI workflows, agents, governance
├── images/
├── data-download-tool/                     # Shared: datastore downloads + catchment analysis
└── model-trains/                           # One self-contained project per model train
    ├── README.md                           # Index + scientific description of every train
    └── <train-name>/                       # e.g. MSHE-Ecolab-PGM/, MSHE-Daisy/
```

Adding a model train means creating `model-trains/<train-name>/` as a self-contained project with its
own `pyproject.toml`, environment, tests and notebooks — not a new top-level folder.

## 📚 Documentation

- Repository-level design: [REPOSITORY_DESIGN.md](REPOSITORY_DESIGN.md)
- Model trains — index, status and scientific descriptions: [model-trains/README.md](model-trains/README.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)
- Download tool technical details: [data-download-tool/README.md](data-download-tool/README.md)

---

**Version**: 1.0
**Contact**: PHISHES Research Team

## Security and Contribution Guidelines

This repository has branch protection rules enabled to ensure code quality and security.

### 🔒 Branch Protection

- **Direct pushes to `main` are not allowed**
- All changes must go through pull requests
- Pull requests require approval from code owners
- All **blocking** CI checks must pass before merging

Checks are split by what a failure means. Blocking checks (lint, tests, file size, secret scan,
dependency audit) mean the change is wrong. Advisory checks (formatting, markdown lint, notebook
lint) mean it is merely untidy and never block — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
full table.

### 📝 Contributing

1. Install the pre-commit hooks (`pip install pre-commit && pre-commit install`)
2. Create a new branch from `main`
3. Make your changes and run `uv run ruff check .` plus `uv run pytest -q` in the affected module
4. Open a pull request
5. Wait for code owner approval and blocking CI checks to pass
6. Merge after approval

Full details, including the fork workflow: [CONTRIBUTING.md](CONTRIBUTING.md).

### 👥 Code Owners

Code reviews are required from designated code owners (defined in `.github/CODEOWNERS`).

**Note for administrators**: Before enabling branch protection with code owner requirements, ensure the team or users referenced in the CODEOWNERS file exist and have appropriate permissions.

### 📋 Documentation

- [Security Policy](SECURITY.md) - Security guidelines and vulnerability reporting
- [Branch Protection Guide](.github/BRANCH_PROTECTION.md) - Configuration instructions for administrators

For more information, see our [Security Policy](SECURITY.md).
