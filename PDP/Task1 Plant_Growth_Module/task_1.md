# Plant Growth Module (PGM) for MIKE SHE Integration

## Project Overview

This project implements a Plant Growth Module (PGM) that integrates with DHI's MIKE SHE hydrological modeling software and ECO Lab. The module processes land use data and plant species parameters to generate spatially distributed maps for hydrological modeling.

**Key Integration Points:**

- MIKE SHE model files: `*.she` (MSHE_PGM_eg.she)
- ECO Lab process files: `*.ecolab` (PHISHES_8_v2.ecolab)
- DFS2 format: Binary gridded data format used by MIKE Zero tools
- Primary variables: LAI (Leaf Area Index, m²/m²), RD (Rooting Depth, mm)

## Critical Data Structures

### CSV Template Format (data/20260109_LandUse/)

**Constants_template.csv**: Plant species parameters

- Columns: `speciesID, constant, value, type`
- `speciesID`: Must match land use class names exactly (e.g., "Winter wheat", "Spring barley")
- `constant`: PGM constant names (tmax, topt, k_lai, etc.)
- `value`: Numeric constant value
- `type`: 0=uniform (no map), 1=generate spatial map

**InitConditions_template.csv**: Initial state variables

- Columns: `speciesID, variable, value, type`
- `variable`: LAI_2D, RD_2D, BCa_2D, BNa_2D, SOC, SON, NH4, NO3, etc.
- Same speciesID matching rules apply

**LU_template.csv**: Land use class mapping

- Columns: `CLASS, CODE`
- Maps plant species names to numeric codes used in DFS2 files

### Matching Logic

When `speciesID` doesn't match any land use class: **no action is taken** (silently skipped). Always verify species names match exactly, including special characters and spacing.

## Project Structure

```
code/
  t1_plant_growth_module.ipynb  # Main implementation notebook
data/
  YYYYMMDD_LandUse/            # Dated data folders
    LandUse.DFS2                # Binary spatial land use data
    LandUse.gsf                 # MIKE Zero geometry file
    *_template.csv              # Parameter templates
    Model/
      *.she                     # MIKE SHE model configuration
      *.ecolab                  # ECO Lab process definitions
```

## Development Workflow

### Working with Jupyter Notebooks

- Primary development in `code/t1_plant_growth_module.ipynb`
- Currently empty - implementation pending
- Expected workflow: Read CSV templates → Process land use → Generate DFS2 outputs

### Python Environment

- DHI MIKE SDK may be required for DFS2 file operations
- Common packages: pandas, numpy, potentially mikeio for DFS2 reading/writing
- Use `configure_python_environment` before executing notebook cells

### Data File Conventions

- Date-stamped folders: `YYYYMMDD_LandUse/` format
- Template files are **input specifications**, not to be modified by code
- Generated outputs should match MIKE SHE/ECO Lab requirements

## Key Technical Considerations

### ECO Lab Integration

The `.ecolab` file defines ~70+ constants and variables that PGM can utilize:

- Temperature selection (`sel_temp`): switch between forcing or MIKE SHE temperature
- Multiple biomass compartments: BCa_2D, BCb_2D, BCc, BCs (above/belowground, coarse/fine)
- Nitrogen compartments: BNa_2D, BNb_2D, BNc
- Soil variables: SOC, SON, NH4, NO3, DO, AO

### Spatial Data Format

- DFS2: 2D gridded format requiring DHI tools or mikeio library
- Coordinate system and grid must match existing LandUse.DFS2 specifications
- Values must be physically meaningful (e.g., LAI typically 0-8 m²/m², RD 0-3000 mm)

## Naming Conventions

- Plant species: Use full descriptive names, preserving exact spelling from agricultural classifications
- Constants: Lowercase with underscores (e.g., `tmax`, `topt`, `k_lai`)
- Variables: Mixed case or uppercase (e.g., `LAI_2D`, `RD_2D`, `SOC`)

## Code Style Conventions

- **Path construction**: Use `Path.joinpath()` method instead of `/` operator for explicit path joining
  - Example: `DATA_DIR.joinpath("data", "20260109_LandUse")` not `DATA_DIR / "data" / "20260109_LandUse"`
- **Imports**: Consolidate all package imports in the first cell of notebooks
  - Standard order: pandas, numpy, pathlib.Path, mikeio, os
- **Notebook cell order**: Cells must be executable sequentially from top to bottom
  - Ensure all dependencies (variables, functions) are defined before use
  - Correct sequence: imports → config → load data → create mappings → define functions → process data → verify outputs

## Common Pitfalls

- Case-sensitive species name matching between CSV files and land use classifications
- Type=0 vs Type=1: Controls whether spatial maps are generated or uniform values applied
- Missing DHI libraries: DFS2 operations require proprietary MIKE SDK or open-source mikeio
- Date folder structure: Always check for latest YYYYMMDD_LandUse folder

## External Dependencies

- DHI MIKE Zero 2023/2026 (commercial software, file format definitions)
- MIKE SHE (hydrological modeling engine)
- ECO Lab 2125.176+ (biogeochemical process modeling)
