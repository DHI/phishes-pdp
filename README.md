# PHISHES

![logo](<images/2line _ LOGO PHISHES _ 2024.png>)

PHISHES seeks to bridge the gap between soil health data and actions, providing much-needed predictive capability in terms of the consequences of actions on the provision of soil functions and associated ecosystem services, taking into account soil use, soil contamination and various drivers such as climate change.

### Python tools for retrieving model input data

The repository contains jupyter notebooks with tools for downloading forcing data for the models that are relevant for the PHISHES simulation platform. The forcing data will be cropped to the model domain and can be converted to standard formats - like netcdf, Zarr or dfs2.

## Requirements

- Windows or Linux operating system
- Python x64 3.10 - 3.13

## Installation

## Getting started

## Where can I get help?

## Cloud enabled - To be enabled!!!!

It is possible to run PHISHES notebooks in your favorite cloud notebook environment e.g. [Deepnote](https://deepnote.com/), [Google Colab](https://colab.research.google.com/), etc...

## 📦 What this repository contains

### Task 1: Plant Growth Module (PGM) - DFS2 Map Generator

Generates spatially distributed DFS2 maps for DHI’s ECO Lab Plant Growth Module using land-use data and species parameters.

- Location: [PDP/Task1 Plant_Growth_Module/](PDP/Task1%20Plant_Growth_Module/)
- Documentation: [PDP/Task1 Plant_Growth_Module/README.md](PDP/Task1%20Plant_Growth_Module/README.md)

### Task 2: Data Management and Processing

Provides scripts and notebooks for dataset organization, downloads, and reproducible project structure setup.

- Location: [PDP/Task2/](PDP/Task2/)
- Documentation: [PDP/Task2/README.md](PDP/Task2/README.md)

## 📁 Repository structure (high level)

```
11829965_PHISHES/
├── README.md
├── pdp_agent.md
└── PDP/
	├── Task1 Plant_Growth_Module/
	└── Task2/
```

## 📚 Documentation

- Technical details: [pdp_agent.md](pdp_agent.md)

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
