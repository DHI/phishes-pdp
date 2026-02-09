# PHISHES Digital Platform (PDP) - Agent Documentation

## Project Overview

The PHISHES Digital Platform (PDP) is a toolkit for catchment-scale soil and hydrological modeling. This repository contains the Plant Growth Module component for MIKE SHE hydrological modeling workflow.

---

## Task 1: Plant Growth Module (PGM) - DFS2 Map Generator

### Purpose

Generates spatially distributed DFS2 maps for DHI's ECO Lab Plant Growth Module in MIKE SHE. Processes land use data and species-specific parameters to create model-ready input files.

### Key Capabilities

- **Spatial mapping**: Converts land use classifications to parameter maps
- **Template processing**: Batch processes multiple CSV parameter templates
- **DFS2 generation**: Creates MIKE SHE-compatible spatial files
- **Automatic validation**: Validates inputs and detects column mappings
- **Interactive & batch modes**: Supports both manual and automated workflows

### Main Components

- **Notebook**: `t1_plant_growth_module.ipynb` - Main processing workflow
- **Helper module**: `t1_pgm_helper.py` - Core functions and utilities
- **Environment**: Managed with `uv` and `pyproject.toml`

### Inputs Required

1. **Land use DFS2 file** - Spatial grid with numeric land use codes
2. **Land use classification CSV** - Maps codes to species names
3. **Parameter templates CSV** - Species-specific constants and initial conditions

### Outputs Generated

- Spatially distributed DFS2 maps for each parameter
- Ready for direct integration with MIKE SHE ECO Lab

### Technology Stack

- Python with mikeio, pandas, numpy
- Jupyter notebook interface
- VS Code or Jupyter Lab execution

---

## Project Structure

```
11829965_PHISHES/
├── pdp_agent.md                    # This file
├── README.md                       # Project overview
├── PDP/
│   └── Task1 Plant_Growth_Module/
│       ├── README.md              # Task 1 documentation
│       ├── pyproject.toml         # Dependencies
│       ├── .gitignore             # Ignore data/ and .venv
│       ├── code/
│       │   ├── t1_plant_growth_module.ipynb
│       │   └── t1_pgm_helper.py
│       └── data/                  # Input/output data (gitignored)
```

---

## Installation & Setup

### Prerequisites

- Python 3.9+
- `uv` package manager (recommended)
- Git
- MIKE Zero / MIKE SHE (for DFS2 files)

### Setup

```bash
cd "PDP/Task1 Plant_Growth_Module"
uv sync --link-mode copy
```

---

## Git Configuration

The `.gitignore` file is configured to exclude:

- Large data files (`data/` folder)
- Python environments (`.venv`, `__pycache__`)
- Environment files (`.env`, credentials)
- Package locks (`uv.lock`)
- System files (`.DS_Store`, `Thumbs.db`)

---

## Key Contacts & Resources

- **MIKE SHE Support**: DHI documentation and support channels
- **PHISHES Team**: Internal collaboration channels

---

## Technical Notes

- Requires DHI MIKE Zero installation for full DFS2 file compatibility
- Column names in templates are case-insensitive
- Supports batch processing with `AUTO_CONFIRM=True`
- Use absolute paths for all file references

---

## Future Development

- Additional parameter validation
- Support for more DFS2 formats
- Integration with MIKE SHE Python API

---

## Version Information

- **Last Updated**: January 29, 2026
- **Repository**: 11829965_PHISHES
- **Status**: Active development
- **License**: [To be specified]

---

## Quick Start Commands

```bash
cd "PDP/Task1 Plant_Growth_Module"
uv sync --link-mode copy
# Open t1_plant_growth_module.ipynb in VS Code
```
