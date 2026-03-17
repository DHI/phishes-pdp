# PHISHES

![logo](<images/2line _ LOGO PHISHES _ 2024.png>)

PHISHES seeks to bridge the gap between soil health data and actions, providing much-needed predictive capability in terms of the consequences of actions on the provision of soil functions and associated ecosystem services, taking into account soil use, soil contamination and various drivers such as climate change.

## Overview

This repository hosts Python tooling and notebooks that support the PHISHES simulation platform. It includes:

- Data download and preprocessing utilities for model forcing data
- A Plant Growth Module (PGM) workflow for generating DFS2 maps
- Reproducible project structures, logging, and analysis helpers

Most user-facing workflows are provided as Jupyter notebooks in the module folders.

## Requirements

- Windows, Linux, or macOS
- Python x64 3.10 - 3.13

## Installation

Installations are handled per sub-project. See the module README files for setup steps:

- [data-download-tool/README.md](data-download-tool/README.md)
- [plant-growth-module/README.md](plant-growth-module/README.md)

## Where can I get help?

- Module-specific documentation:
  - [data-download-tool/README.md](data-download-tool/README.md)
  - [plant-growth-module/README.md](plant-growth-module/README.md)
- Repository design: [REPOSITORY_DESIGN.md](REPOSITORY_DESIGN.md)

## 📦 What this repository contains

### Plant Growth Module (PGM) - DFS2 Map Generator

Generates spatially distributed DFS2 maps for DHI’s ECO Lab Plant Growth Module using land-use data and species parameters.

- Location: [plant-growth-module/](plant-growth-module/)
- Documentation: [plant-growth-module/README.md](plant-growth-module/README.md)

### Data Download Tool

Provides scripts and notebooks for dataset organization, downloads, and reproducible project structure setup.

- Location: [data-download-tool/](data-download-tool/)
- Documentation: [data-download-tool/README.md](data-download-tool/README.md)

## 📁 Repository structure (high level)

```
phishes-pdp/
├── README.md
├── REPOSITORY_DESIGN.md
├── SECURITY.md
├── .github/
├── images/
├── data-download-tool/
└── plant-growth-module/
```

## 📚 Documentation

- Repository-level design: [REPOSITORY_DESIGN.md](REPOSITORY_DESIGN.md)
- Module technical details:
  - [data-download-tool/README.md](data-download-tool/README.md)
  - [plant-growth-module/README.md](plant-growth-module/README.md)

---

**Version**: 1.0
**Last Updated**: February 9, 2026
**Contact**: PHISHES Research Team

## Security and Contribution Guidelines

This repository has branch protection rules enabled to ensure code quality and security.

### 🔒 Branch Protection

- **Direct pushes to `main` are not allowed**
- All changes must go through pull requests
- Pull requests require approval from code owners
- All CI/CD checks must pass before merging

### 📝 Contributing

1. Create a new branch from `main`
2. Make your changes
3. Open a pull request
4. Wait for code owner approval and CI checks to pass
5. Merge after approval

### 👥 Code Owners

Code reviews are required from designated code owners (defined in `.github/CODEOWNERS`).

**Note for administrators**: Before enabling branch protection with code owner requirements, ensure the team or users referenced in the CODEOWNERS file exist and have appropriate permissions.

### 📋 Documentation

- [Security Policy](SECURITY.md) - Security guidelines and vulnerability reporting
- [Branch Protection Guide](.github/BRANCH_PROTECTION.md) - Configuration instructions for administrators

For more information, see our [Security Policy](SECURITY.md).
