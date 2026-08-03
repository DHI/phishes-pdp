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

## Installation

Installations are handled per sub-project — each has its own environment. See the module README
files for setup steps:

- [data-download-tool/README.md](data-download-tool/README.md)
- [model-trains/MSHE-Ecolab/README.md](model-trains/MSHE-Ecolab/README.md)

## Where can I get help?

- Module-specific documentation:
  - [data-download-tool/README.md](data-download-tool/README.md)
  - [model-trains/MSHE-Ecolab/README.md](model-trains/MSHE-Ecolab/README.md)
- Model train descriptions: [model-trains/README.md](model-trains/README.md)
- Repository design: [REPOSITORY_DESIGN.md](REPOSITORY_DESIGN.md)
- Contributing and CI: [CONTRIBUTING.md](CONTRIBUTING.md)

## 📦 What this repository contains

### Data Download Tool

Downloads dataset subsets clipped to a catchment: Zarr time series, Cloud Optimized GeoTIFF static
rasters, GeoParquet vector layers, and partner data zip bundles. Shared by every model train.

- Location: [data-download-tool/](data-download-tool/)
- Documentation: [data-download-tool/README.md](data-download-tool/README.md)

### Model trains

Each model train is an independent project under [model-trains/](model-trains/). The scientific
description of all four trains — inputs, coupling, data exchanged, outputs — is in
[model-trains/README.md](model-trains/README.md).

| Model train | Status | Documentation |
| --- | --- | --- |
| [MSHE-Ecolab](model-trains/MSHE-Ecolab/) — MIKE SHE + MIKE ECO Lab Plant Growth Module | Implemented | [README](model-trains/MSHE-Ecolab/README.md) |
| [MSHE-Daisy](model-trains/MSHE-Daisy/) — MIKE SHE + Daisy | Description only | [README](model-trains/MSHE-Daisy/README.md) |
| [HYDRUS-PHREEQC-MODFLOW2005-MT3D](model-trains/HYDRUS-PHREEQC-MODFLOW2005-MT3D/) | Description only | [README](model-trains/HYDRUS-PHREEQC-MODFLOW2005-MT3D/README.md) |

**MSHE-Ecolab** generates spatially distributed DFS2 maps for DHI's ECO Lab Plant Growth Module from
land use, soil profile and species parameter templates, plus forcing grids and MIKE SHE hotstart
initial conditions. It was previously `plant-growth-module/` at the repository root; the move was
path-only, so the `plant_growth_module` package and all imports are unchanged.

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
    ├── README.md                           # Scientific description of all four trains
    ├── MSHE-Ecolab/                        # MIKE SHE + ECO Lab Plant Growth Module (implemented)
    ├── MSHE-Daisy/
    └── HYDRUS-PHREEQC-MODFLOW2005-MT3D/
```

Adding a model train means creating `model-trains/<train-name>/` as a self-contained project with its
own `pyproject.toml`, environment, tests and notebooks — not a new top-level folder.

## 📚 Documentation

- Repository-level design: [REPOSITORY_DESIGN.md](REPOSITORY_DESIGN.md)
- Model train descriptions: [model-trains/README.md](model-trains/README.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)
- Module technical details:
  - [data-download-tool/README.md](data-download-tool/README.md)
  - [model-trains/MSHE-Ecolab/README.md](model-trains/MSHE-Ecolab/README.md)

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
