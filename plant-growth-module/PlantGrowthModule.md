# Plant Growth Module (PGM) — Copilot Agent Context

This is the technical documentation containing the details of script.

## Table of Contents

- [Installation](#installation)
- [How to Execute the Notebook](#how-to-execute-the-notebook)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Available Datasets](#available-datasets)
- [Troubleshooting](#troubleshooting)
- [Additional Documentation](#additional-documentation)
- [System Requirements](#system-requirements)
- [Acknowledgments](#acknowledgments)
- [Support](#support)

## Project Overview

For user-facing documentation (installation, execution, configuration, troubleshooting), see [README.md](README.md). This file focuses on internal technical context for the Plant Growth Module: code architecture, function signatures, conventions, and domain knowledge not covered in the README.

## Project Structure

```
plant-growth-module/
├── src/
│   ├── __init__.py
│   └── pgm_helper.py              # All reusable helper functions and column-name constants
├── notebooks/
│   └── plant_growth_module.ipynb   # Main processing workflow (sequential cells)
├── pyproject.toml                  # Dependencies: pandas, numpy, mikeio, streamlit, ipywidgets
├── PlantGrowthModule.md            # This agent file
└── README.md                       # User documentation
```

### External Data Structure (user-provided, absolute paths)

```
YYYYMMDD_LandUse/                   # Dated data folders
├── LandUse.DFS2                    # Binary spatial land use data
├── LandUse.gsf                     # MIKE Zero geometry file
├── LU_template.csv                 # Land use classification mapping
├── Constants_template.csv          # Species parameter constants
├── InitConditions_template.csv     # Initial state variables
└── Model/
    ├── *.she                       # MIKE SHE model configuration
    └── *.ecolab                    # ECO Lab process definitions
```

## Domain Knowledge

### ECO Lab Integration

The `.ecolab` file defines ~70+ constants and variables that PGM can utilize:

- Temperature selection (`sel_temp`): switch between forcing or MIKE SHE temperature
- Biomass compartments: BCa_2D, BCb_2D, BCc, BCs (above/belowground, coarse/fine)
- Nitrogen compartments: BNa_2D, BNb_2D, BNc
- Soil variables: SOC, SON, NH4, NO3, DO, AO

### Spatial Data Format

- DFS2: 2D gridded format; coordinate system and grid must match the input LandUse.DFS2
- Physically meaningful value ranges: LAI typically 0–8 m²/m², RD typically 0–3000 mm

### Matching Logic

When a `speciesID` in a template CSV has no matching land use class name: **silently skipped** (no error, no map cell written). Species names must match exactly including spacing and special characters.

### CSV Template Internals

- `type` column in Constants/InitConditions templates: `0` = uniform value (no spatial map), `1` = generate spatial DFS2 map
- The current notebook does **not** filter on the `type` column yet — all parameters get maps generated

## Module Documentation: `src/pgm_helper.py`

### Constants

```python
# Land use mapping columns
VAL_COLS   = ["CODE", "VALUE"]
CLASS_COLS = ["CLASS", "SPECIESID"]

# Template file columns
ID_COLS    = ["SPECIESID", "SPECIES", "ID", "CLASS"]
VALUE_COLS = ["VALUE", "VAL", "AMOUNT"]
KEY_COLS   = ["CONSTANT", "VARIABLE", "KEY", "NAME", "PARAM", "PARAMETER"]
```

### Functions

```python
def find_col(df: pd.DataFrame, cols: list[str]) -> str | None:
    """Find first matching column name (case-insensitive).
    Returns the actual column name from df, or None.
    """

def confirm_columns(
    column_dict: dict,
    auto_confirm: bool = False,
    context: str = "",
    multi_files: bool = True
) -> bool:
    """Prompt user to confirm detected columns.
    - auto_confirm=True skips the prompt.
    - multi_files=True: 'no' skips the file. multi_files=False: 'no' raises RuntimeError.
    """

def generate_dfs2_map(
    landuse_data: np.ndarray,       # 2D grid of numeric land use codes
    landuse_ds: mikeio.Dataset,     # source dataset (geometry + time metadata)
    code_to_species: dict,          # {code_int: species_name}
    species_values: dict,           # {species_name: numeric_value}
    output_path: Path,              # output .dfs2 file path
    variable_name: str              # DFS2 item name
) -> None:
    """Create a single-timestep DFS2 map:
    1. Init float32 grid of zeros (same shape as landuse_data)
    2. For each code→species, set matching cells to species value
    3. Wrap in mikeio.DataArray with source geometry/time
    4. Write DFS2 (suppresses 0-second time-step warning)
    """

def validate_paths(
    landuse_dfs2: Path,
    lu_template: Path,
    template_files: list[Path],
    output_dir: Path
) -> list[str]:
    """Check all inputs exist; create output_dir if missing.
    Returns list of error messages (empty = all valid).
    """
```

### Usage Example

```python
from src.pgm_helper import (
    VAL_COLS, CLASS_COLS, find_col, generate_dfs2_map, validate_paths,
)

errors = validate_paths(LANDUSE_DFS2, LU_TEMPLATE, TEMPLATE_FILES, OUTPUT_DIR)

lu_df = pd.read_csv(LU_TEMPLATE)
code_to_species = dict(zip(
    lu_df[find_col(lu_df, VAL_COLS)],
    lu_df[find_col(lu_df, CLASS_COLS)]
))

landuse_ds = mikeio.Dfs2(LANDUSE_DFS2)
landuse_data = landuse_ds.read()[0].to_numpy()

generate_dfs2_map(
    landuse_data, landuse_ds, code_to_species,
    {"Winter wheat": 5.0, "Spring barley": 4.2},
    OUTPUT_DIR.joinpath("LAI_2D.dfs2"), "LAI_2D"
)
```

## Notebook Cell Architecture

The notebook (`plant_growth_module.ipynb`) has 16 cells in this fixed order:

| #   | Type     | Purpose                                                                                                               |
| --- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| 1   | Markdown | Title + workflow overview                                                                                             |
| 2   | Code     | All imports (pathlib, pandas, numpy, mikeio, os, src.pgm_helper)                                                      |
| 3   | Markdown | Step 0 — Configuration instructions                                                                                   |
| 4   | Code     | Path definitions (`LANDUSE_DFS2`, `LU_TEMPLATE`, `TEMPLATE_FILES`, `OUTPUT_DIR`, `AUTO_CONFIRM`) + `validate_paths()` |
| 5   | Code     | Empty (scratch cell)                                                                                                  |
| 6   | Markdown | Step 1 header                                                                                                         |
| 7   | Markdown | Step 1.A — Load spatial grid                                                                                          |
| 8   | Code     | Read DFS2 via `mikeio.Dfs2()`, extract numpy array                                                                    |
| 9   | Markdown | Step 1.B — Create code→species mapping                                                                                |
| 10  | Code     | Read LU template, `find_col()`, `confirm_columns()`, build `code_to_species` dict                                     |
| 11  | Markdown | Step 2 header                                                                                                         |
| 12  | Markdown | Step 2.A — Processing loop description                                                                                |
| 13  | Code     | Loop over `TEMPLATE_FILES`, detect columns, generate DFS2 per parameter                                               |
| 14  | Markdown | Step 3 header                                                                                                         |
| 15  | Code     | List generated .dfs2 files with sizes                                                                                 |
| 16  | Code     | Verification — read sample file, check shape/range/geometry match                                                     |

## Code Style Conventions

- **Path construction**: Use `Path.joinpath()` — not the `/` operator
- **Imports**: All in cell 2. Order: stdlib → third-party → `src.pgm_helper`
- **Helper functions**: All reusable logic in `src/pgm_helper.py`, not inline in notebook
- **Notebook cells**: Must execute sequentially top-to-bottom with no out-of-order dependencies
- **Error handling**: `validate_paths()` before processing; raise `FileNotFoundError` or `ValueError` on bad input

## Naming Conventions

- Plant species: Exact agricultural names with original casing/spacing (e.g., "Winter wheat")
- Constants: lowercase + underscores (`tmax`, `topt`, `k_lai`)
- Variables: mixed/uppercase (`LAI_2D`, `RD_2D`, `SOC`)
- Output files: `{parameter_name}.dfs2`

## Common Pitfalls

- Species name matching is **case-sensitive** and must be exact between CSV files and land use classifications
- `type=0` vs `type=1` semantics exist in templates but the notebook currently generates maps for **all** parameters regardless
- Empty `Path(r"")` strings in notebook config cell — all must be filled with absolute paths before running
- `find_col()` returns `None` if no column variant matches — always check before using the result
- Output DFS2 files inherit geometry from the input LandUse.DFS2 — grid mismatch will produce incorrect spatial mapping
- Date folder naming: always check for latest `YYYYMMDD_LandUse/` folder

## External Dependencies

- DHI MIKE Zero 2023/2026 (file format context)
- MIKE SHE (hydrological modeling engine)
- ECO Lab 2125.176+ (biogeochemical process modeling)
- Python: mikeio ≥1.6, pandas ≥2.0, numpy ≥1.24, streamlit ≥1.30, ipywidgets ≥8.0

## Future Enhancements

- [ ] Filter on `type` column: only generate maps where type=1, skip type=0
- [ ] Streamlit web interface for non-programmer users
- [ ] Time-varying DFS2 map support
- [ ] MIKE SHE Python API integration
- [ ] Automated value-range validation per parameter

## References

- [README.md](README.md)
- https://docs.mikepoweredbydhi.com
- https://mikeio.readthedocs.io

---

**Last Updated**: February 2026
