# PHISHES PDP — Copilot Agent Context

This file provides technical context for the entire repository. For user-facing setup and execution steps, see the module README files.

## Table of Contents

- [Project Overview](#project-overview)
- [Repository Structure](#repository-structure)
- [Modules](#modules)
- [Installation](#installation)
- [Configuration](#configuration)
- [Data and Outputs](#data-and-outputs)
- [Troubleshooting](#troubleshooting)
- [System Requirements](#system-requirements)
- [Support](#support)

## Project Overview

PHISHES PDP is a collection of Python tools and notebooks that support catchment-scale soil and hydrological modeling workflows. The repository includes two primary modules:

- Data Download Tool for retrieving and processing model forcing data
- Plant Growth Module (PGM) for generating DFS2 maps for DHI ECO Lab / MIKE SHE

## Repository Structure

```
phishes-pdp/
├── README.md
├── phishes-pdp.md
├── SECURITY.md
├── .github/
├── images/
├── data-download-tool/
└── plant-growth-module/
```

## Modules

### Data Download Tool

- Location: [data-download-tool/](data-download-tool/)
- User documentation: [data-download-tool/README.md](data-download-tool/README.md)
- Agent context: [data-download-tool/DataDownloadTool.md](data-download-tool/DataDownloadTool.md)

Key capabilities:

- Azure-based dataset discovery and download
- Catchment clipping and optional masking
- Output formats: NetCDF, Zarr, DFS2
- Basin statistics and visualization helpers

### Plant Growth Module (PGM)

- Location: [plant-growth-module/](plant-growth-module/)
- User documentation: [plant-growth-module/README.md](plant-growth-module/README.md)
- Agent context: [plant-growth-module/PlantGrowthModule.md](plant-growth-module/PlantGrowthModule.md)

Key capabilities:

- Land use to parameter mapping
- DFS2 map generation for ECO Lab / MIKE SHE
- CSV template validation and batch processing

## Installation

Installations are handled per sub-project. See the module README files for setup steps:

- [data-download-tool/README.md](data-download-tool/README.md)
- [plant-growth-module/README.md](plant-growth-module/README.md)

## Configuration

Configuration is done in the notebooks for each module. Common editable parameters include:

- Project base path and output format (Data Download Tool)
- Catchment inputs (shapefile or manual extent)
- Dataset category and subcategory selection
- PGM input paths (LandUse DFS2, LU template, parameter templates)

Refer to each module README and agent context file for exact parameters and defaults.

## Data and Outputs

- Large input and output datasets are stored within each module folder (often gitignored).
- Downloaded datasets and logs are written under the configured project base path.
- PGM outputs are DFS2 files matching the geometry of the input LandUse DFS2.

## Troubleshooting

Module-specific troubleshooting is documented in each README:

- [data-download-tool/README.md](data-download-tool/README.md)
- [plant-growth-module/README.md](plant-growth-module/README.md)

## System Requirements

- Windows, Linux, or macOS
- Python x64 3.10 - 3.13

## Support

- Project overview: [README.md](README.md)
- Module docs: see links above

---

**Last Updated**: February 2026
