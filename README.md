# PHISHES Digital Platform (PDP)

A comprehensive toolkit for catchment-scale soil and hydrological modeling, developed for the PHISHES research initiative.

## 🎯 What is PDP?

The PHISHES Digital Platform provides a tool for:

**Plant Growth Module DFS2 Generation** - Convert land use data and species parameters into spatially distributed maps for MIKE SHE ECO Lab

## 📦 Project Components

### Task 1: Plant Growth Module (PGM) - DFS2 Map Generator

Generates spatially distributed DFS2 maps for DHI's ECO Lab Plant Growth Module.

**Key Features:**

- ✅ Processes land use spatial data and species-specific parameters
- ✅ Creates MIKE SHE-compatible DFS2 files
- ✅ Interactive notebook with automatic validation
- ✅ Batch processing mode for automation

**Location:** [`PDP/Task1 Plant_Growth_Module/`](PDP/Task1%20Plant_Growth_Module/)

**Documentation:** [Task 1 README](PDP/Task1%20Plant_Growth_Module/README.md)

## 🚀 Quick Start

### Installation

Uses `uv` for Python package management:

```bash
# Install uv first (if not already installed)
# See: https://docs.astral.sh/uv/getting-started/installation/

# Setup
cd "PDP/Task1 Plant_Growth_Module"
uv sync --link-mode copy
```

### Usage

```bash
cd "PDP/Task1 Plant_Growth_Module"
# Open code/t1_plant_growth_module.ipynb in VS Code
# Select .venv kernel and run cells
```

## 📁 Repository Structure

```
11829965_PHISHES/
├── README.md                       # This file
├── pdp_agent.md                    # Technical documentation
├── PDP/
│   ├── Task1 Plant_Growth_Module/
│   │   ├── README.md              # Full documentation
│   │   ├── code/
│   │   │   ├── t1_plant_growth_module.ipynb
│   │   │   └── t1_pgm_helper.py
│   │   └── data/                  # Input/output data
```

## 🔧 Requirements

### Common

- Python 3.9+
- `uv` package manager
- Git

### Specific

- MIKE Zero / MIKE SHE (for working with DFS2 files)
- mikeio library

## 📚 Documentation

- **Technical Details**: [pdp_agent.md](pdp_agent.md)
- **Full Documentation**: [Task 1 README](PDP/Task1%20Plant_Growth_Module/README.md)

## 🔄 Typical Workflow

1. **Prepare Data** - Obtain land use spatial data and parameter templates
2. **Generate Maps** - Create spatially distributed DFS2 parameter maps
3. **Model Setup** (MIKE SHE) - Import maps into ECO Lab and run simulations

## 🤝 Support

For questions or issues:

- See [README](PDP/Task1%20Plant_Growth_Module/README.md) troubleshooting section
- Review [pdp_agent.md](pdp_agent.md) for technical details

## 📝 License

[To be specified] - PHISHES Digital Platform

## 🙏 Acknowledgments

- DHI for MIKE SHE and ECO Lab

---

**Version**: 1.0
**Last Updated**: January 29, 2026
**Contact**: PHISHES Research Team
