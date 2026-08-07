# MSHE-Ecolab-PGM — MIKE SHE + MIKE ECO Lab Plant Growth Module

Input generation for the **MSHE-Ecolab-PGM** model train: DHI's MIKE SHE coupled to the MIKE ECO Lab
**Plant Growth Module (PGM)**. This project turns land use, soil profile and parameter templates into
the spatially distributed DFS2 files that MIKE SHE / ECO Lab consume, and can also build forcing
grids and re-inject simulated state as initial conditions.

> [!IMPORTANT]
> **Disclaimer:** This tool consumes land use, soil profile, and forcing data from third-party and
> partner sources, and is provided "as is" for research purposes with no warranty on its outputs.
> Read the full [DISCLAIMER.md](DISCLAIMER.md) before relying on its outputs.

For the full walkthrough — background, workflows and usage in one document — see the
[PGM User Guide (PDF)](PGM%20User%20Guide_v1.0.pdf).

## A note on names

Three names refer to the same thing — all three are correct and none is stale:

| Name                            | What it is                                                                                |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| `model-trains/MSHE-Ecolab-PGM/` | The **folder** (this project), named after the model train it feeds                       |
| `plant_growth_module`           | The **Python package** in `src/`, and the `plant-growth-module` distribution name         |
| PGM                             | The **abbreviation** used in notebook filenames (`pgm_*.ipynb`) and throughout these docs |

So `from plant_growth_module import ...` is the import path, regardless of the folder name. See
[model-trains/README.md](../README.md) for the other model trains.

## Table of Contents

- [What Does This Tool Do?](#-what-does-this-tool-do)
- [Installation](#-installation)
- [How to Execute the Notebook](#-how-to-execute-the-notebook)
- [Notebook Workflows](#-notebook-workflows)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

## 🌱 What Does This Tool Do?

The Plant Growth Module processes:

- **Land use spatial data** (DFS2 format) containing numeric codes for different land cover types
- **Land use classification** mapping land use codes to plant species names (with optional `Apply` flag)
- **Soil profile spatial data** (DFS2 format) and soil profile classification
- **Parameter templates** (CSV files) defining species-specific constants and initial conditions
- **Local or downloaded time series** for forcing grids
- **MIKE SHE results** (`.dfs3`) for hotstart initial conditions

And generates:

- **Spatially distributed DFS2 maps** for each parameter
- **Per-cell wilting point / field capacity DFS2 stacks** from PreProcessor text files
- **Forcing DFS2 grids** from DFS0/CSV time series or from the shared `data-download-tool`
- **MIKE SHE-compatible files** ready for integration with ECO Lab

### Key Features

- ✅ Automatic column detection with user confirmation
- ✅ Batch processing mode for automation
- ✅ Validation of all input files before processing
- ✅ Support for multiple parameter templates
- ✅ Spatial mapping based on land use and soil profile classification
- ✅ Land use and soil profile scopes are **independent** — supply either or both
- ✅ `Apply=0` support to force selected land use classes to zero in generated landuse-based maps

---

## 📦 Installation

### 1. Install `uv` (Python Package Manager)

`uv` is a fast Python package installer and environment manager. Install it following the instructions here: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### 2. Set Up the Environment

Navigate to the project directory and create the virtual environment with all dependencies:

```bash
cd "model-trains/MSHE-Ecolab-PGM"
uv sync --link-mode copy
```

**Note:** The `--link-mode copy` flag is required when working with OneDrive or other cloud-synced directories.

This command will:

- Create a virtual environment in `.venv/`
- Install all required packages (pandas, numpy, mikeio, jupyter, etc.)
- Set up the development dependencies

**Python version:** this project supports Python 3.10–3.13 and pins `3.11` in `.python-version` to
match CI. `uv` downloads that interpreter for you. Do not override it — several geospatial
dependencies publish no wheels for the newest Python and would be built from source against a
system GDAL.

**Shared dependency:** `pyproject.toml` resolves the forcing repository helper from the
`data-download-tool` module on GitHub `main`, not from the local sibling folder:

```
phishes-data-downloader @ git+https://github.com/DHI/phishes-pdp.git@main#subdirectory=data-download-tool
```

After a `data-download-tool` change is merged, re-run `uv sync --link-mode copy` here to pick it up.

---

## 🚀 How to Execute the Notebook

### Notebook Selection

Choose the notebook based on your task:

| Notebook                                                   | Workflow                                                                            |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `notebooks/pgm_initial_condition_dfs2_map_generator.ipynb` | **A** — template-driven land use and soil profile map generation                    |
| `notebooks/pgm_soil_profile_setup.ipynb`                   | **B** — soil profile text files → per-cell wilting point / field capacity DFS2      |
| `notebooks/pgm_forcing_generator.ipynb`                    | **C** — DFS0/CSV time series → forcing DFS2 grids                                   |
| `notebooks/pgm_initial_condition_updater.ipynb`            | **D** — 3D UZ water-quality `.dfs3` → per-layer initial conditions in a `.she` file |

Each workflow is described under [Notebook Workflows](#-notebook-workflows) below.

### Option 1: Using VS Code (Recommended)

0. **Install VS Code (free):**
   - Download and install from [https://code.visualstudio.com/](https://code.visualstudio.com/)

1. **Open the correct folder in VS Code:**

   > ⚠️ **Critical:** You must open the `model-trains/MSHE-Ecolab-PGM` folder itself as the workspace root in VS Code. If you open a higher-level parent folder (e.g., the repository root or `model-trains/`), VS Code **will not detect** the `.venv` Python environment and the Jupyter kernel will not appear in the kernel picker.

   **How to open the correct folder:**
   - Launch VS Code
   - Go to **File → Open Folder…** (or press `Ctrl + K`, `Ctrl + O`)
   - Browse to and select the `model-trains/MSHE-Ecolab-PGM` folder, then click **Select Folder**
   - Verify the VS Code Explorer sidebar shows `MSHE-Ecolab-PGM` as the top-level folder

   **Why this matters:**
   - VS Code discovers Python environments (`.venv/`) relative to the opened workspace root
   - The `.venv` created by `uv sync` lives inside `model-trains/MSHE-Ecolab-PGM/.venv/`
   - If your workspace root is a parent folder, VS Code won't look inside nested subdirectories for virtual environments, so the kernel won't be found

2. **Open the notebook:**
   - In the VS Code Explorer, navigate to `notebooks/` and click the notebook for your workflow (see [Notebook Selection](#notebook-selection))

3. **Select the Python kernel:**
   - Click on the kernel selector in the top-right corner of the notebook
   - Choose the `.venv` environment (e.g., `Python 3.11 (.venv)`) created by `uv sync`
   - If it does not appear, confirm you opened the correct folder (see step 1) and that you ran `uv sync` successfully

4. **Run the notebook:**

   **To run a single cell:**
   - Click the **▶️ Play button** on the left side of the cell, OR
   - Select the cell and press **`Shift + Enter`**
   - The cell will execute and move to the next cell

   **To run all cells:**
   - Click **Run All** in the toolbar at the top of the notebook, OR
   - Press **`Ctrl + Shift + P`** → Type "Run All Cells" → Press Enter

5. **Workflow:**
   - For `notebooks/pgm_initial_condition_dfs2_map_generator.ipynb`:
     - **Step 0**: Edit file paths in the configuration cell
     - **Step 0.1**: Run setup and validation
     - **Step 1**: Load land use + soil profile data and create mappings
     - **Step 2**: Process templates and generate DFS2 maps
     - **Step 3**: Verify output files

   - For `notebooks/pgm_soil_profile_setup.ipynb`:
     - **Step 1**: Set source folder/file names and output naming
     - **Step 2**: Build derived paths and optional parsing overrides
     - **Step 3**: Parse soil profile text files and save `profile_table.csv`
     - **Step 4**: Generate `grid_codes.dfs2` and per-cell FC/WP DFS2 outputs
     - **Step 5**: Save `summary.csv` and run diagnostics

### Option 2: Using Jupyter Lab/Notebook

#### Method A: Using `uv run` (Recommended - No activation needed)

```powershell
# Windows PowerShell
uv run jupyter notebook notebooks/pgm_initial_condition_dfs2_map_generator.ipynb
```

```bash
# macOS/Linux
uv run jupyter notebook notebooks/pgm_initial_condition_dfs2_map_generator.ipynb
```

#### Method B: Activate environment first

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
jupyter notebook notebooks/pgm_initial_condition_dfs2_map_generator.ipynb
```

**macOS/Linux:**

```bash
source .venv/bin/activate
jupyter notebook notebooks/pgm_initial_condition_dfs2_map_generator.ipynb
```

**To run cells in Jupyter:**

- Click the **Run** button in the toolbar for each cell
- Or use keyboard shortcuts: **`Shift + Enter`** to run and advance

---

## 📁 Project Structure

```
model-trains/MSHE-Ecolab-PGM/
├── src/
│   └── plant_growth_module/
│       ├── __init__.py                     # Package entry point
│       ├── pgm_helper.py                   # Backward-compatible helper facade
│       ├── template_maps.py                # Workflow A: template-based mapping
│       ├── soil_profile_setup.py           # Workflow B: soil profile parsing, Task 4 outputs
│       ├── forcing_generator_native.py     # Workflow C: local DFS0/CSV -> forcing DFS2
│       ├── forcing_repository.py           # Workflow C: forcing pulled via data-download-tool
│       ├── initial_condition_updater.py    # Workflow D: 3D UZ WQ -> MIKE SHE .she initial conditions
│       └── common_utils.py                 # Shared DFS2 and utility helpers
├── notebooks/
│   ├── pgm_initial_condition_dfs2_map_generator.ipynb  # Workflow A
│   ├── pgm_soil_profile_setup.ipynb                    # Workflow B
│   ├── pgm_forcing_generator.ipynb                     # Workflow C
│   ├── pgm_initial_condition_updater.ipynb             # Workflow D
│   └── result-inspection/                              # Ad-hoc result QA, see below
├── tests/                                  # pytest suite (also reads sample_data/)
├── sample_data/
│   ├── plant_growth_module/                # Templates, land use / soil profile DFS2, example model
│   ├── soil-profile-setup/                 # PreProcessor .txt + .DFS2 for Workflow B
│   └── pgm_forcing_generator/              # Example DFS0/CSV + multi-forcing timeseries_inputs.yaml
├── docs/
│   └── initial_condition_updater.md         # Workflow D design & usage
├── PGM User Guide_v1.0.pdf                  # Full user guide (background, workflows, usage)
├── .python-version                          # Pinned interpreter (3.11), matches CI
├── pyproject.toml                           # Project dependencies and ruff config
└── README.md                                # This file
```

> **Sample data is load-bearing:** the test suite reads from `sample_data/`. Do not rename or move
> those files without updating the fixtures in `tests/`.

---

## 📓 Notebook Workflows

### A. Main Template Workflow

- Notebook: `notebooks/pgm_initial_condition_dfs2_map_generator.ipynb`
- Source: `template_maps.py`
- Use this when generating variable maps from template CSV files and land use/soil profile classification inputs.
- Each variable is routed to the land use grid or the soil profile grid by `STATE_VARIABLE_SCOPE`
  in `template_maps.py`; a template row's `TEMPLATE` column overrides that per row.
- The two scopes are independent — provide land use inputs only, soil profile inputs only, or both.
  A scope you leave blank is skipped, and maps that need it are reported as skipped rather than failing.
- Typical outputs: one DFS2 map per variable/species mapping rule.

### B. Soil Profile Setup Workflow

- Notebook: `notebooks/pgm_soil_profile_setup.ipynb`
- Source: `soil_profile_setup.py`
- Use this when preparing Task 4 soil profile outputs from preprocessed soil profile text files and profile grid codes.
- Typical outputs:
  - `output_data/task4_pgm_soil_profile_setup/<run_name>/grid_codes.dfs2`
  - `output_data/task4_pgm_soil_profile_setup/<run_name>/wilting_point/*.dfs2`
  - `output_data/task4_pgm_soil_profile_setup/<run_name>/field_capacity/*.dfs2`
  - `profile_table.csv` and `summary.csv`

### C. Forcing Generation Workflow

- Notebook: `notebooks/pgm_forcing_generator.ipynb`
- Sources: `forcing_generator_native.py` (local time series) and `forcing_repository.py` (downloaded)
- Two paths:
  - **Native** — convert local DFS0/CSV time series into DFS2 forcing grids. **One YAML file
    declares any number of forcings** (see `sample_data/pgm_forcing_generator/timeseries_inputs.yaml`):
    each named entry under `timeseries_inputs:` carries its own output DFS2, item name, EUM
    type/unit and per-grid-code series, and inherits anything it does not set from a `defaults:`
    block. The notebook loops over them and writes one DFS2 per forcing, so adding a forcing is a
    YAML edit, not a notebook edit — the notebook holds no per-forcing settings at all.
    Grid codes present in the grid DFS2 but absent from a forcing are **zero-filled**, not an
    error; only an entirely empty input set raises.
  - **Repository** — pull forcing (precipitation, temperature, PET, solar radiation) through the
    shared [data-download-tool](../../data-download-tool/README.md) at runtime.
    ⚠️ **Not yet usable:** this path needs a top-level `pgm_forcings:` section in the download tool's
    `dataset_catalog.yaml` mapping each forcing key to a `(category, subcategory, source_variable)`
    and an output filename. That section does not exist yet, so `load_pgm_forcing_library()` raises.
    Use the native path until it is added.
- Sub-daily series are snapped to midnight when at least 80% of intervals are 23–25 h apart.

### D. Initial Condition Updater Workflow

- Notebook: `notebooks/pgm_initial_condition_updater.ipynb`
- Source: `initial_condition_updater.py`
- Use this to build MIKE SHE hotstart inputs: split a 3D UZ water-quality result (`.dfs3`) into
  per-layer DFS2 files and inject them into a `.she` (PFS) file as per-layer initial conditions for
  every matched WQ species.
- Inputs: a `.dfs3` result and the matching `.she` model file.
- Outputs: `Layer_<k>.dfs2` files in `<dfs3-stem>_splitted/`, a timestamped backup of the original
  `.she`, and an updated `.she`.
- Details and design rationale: [docs/initial_condition_updater.md](docs/initial_condition_updater.md).

### Result Inspection (ad-hoc)

- Folder: `notebooks/result-inspection/`
- `obs_res_compare_cernici.ipynb` — compares PGM/MIKE SHE outputs (harvest, GWL, porewater, …) against
  processed Cernici field observations.
- `plot_mikeshe_veg_cernizi_sz.py` — plots UZ/SZ 3D MIKE SHE results layer-by-layer (depth profiles
  and time series) for the Cernici vegetation run.
- These are **scratch QA scripts, not a formal workflow**: paths are hardcoded to a specific machine
  (`P:\WP1_PGM\...`, `C:\DHI\Cernici_060125\...`), logic lives inline rather than in
  `src/plant_growth_module/`, and they are not covered by `tests/`. Edit the paths at the top before
  running; treat them as a starting point for inspecting a specific run, not a reusable pipeline.

---

## ⚙️ Configuration

### Input Files Required

**Important Notes:**

- ✅ All file paths must be **absolute paths** (full paths)
- ✅ Column names are **case-insensitive** (uppercase and lowercase letters don't matter)
- ✅ Land use and soil profile are independent scopes — supply either or both, but each scope needs
  **both** its DFS2 grid and its classification template

#### 1. Land Use Spatial Data

**`LandUse.DFS2`**

- Binary spatial grid file containing numeric land use codes
- Each cell value represents a specific land cover/vegetation type

#### 2. Land Use Classification Mapping

**`LU_template.csv`** (or similar name)

- Maps numeric codes from the DFS2 file to plant species names
- **Required columns** (case-insensitive, one of each type):
  - **Code column**: `CODE`, `VALUE`
  - **Class/Species column**: `CLASS`, `SPECIESID`
- **Optional column**:
  - **Apply column**: `APPLY`, `USE`, `ACTIVE` (set `0`, `false`, `no` or `n` to force all
    landuse-based variables to zero for that class — use it for water and urban classes)

- **Example:**

  | CODE | CLASS       |
  | ---- | ----------- |
  | 1    | Oak_Forest  |
  | 2    | Pine_Forest |
  | 3    | Grassland   |

#### 3. Soil Profile Spatial Data + Classification

**`SoilProfile_gridcodes.dfs2`** and **`SP_template.csv`**

- Soil profile grid used for soilprofile-based initial conditions
- `SP_template.csv` maps soil profile codes to soil profile IDs/classes
- **Required columns** (case-insensitive):
  - **Code column**: `CODE`, `VALUE`
  - **Profile column**: `CLASS`, `SPECIESID`
- Profile lookup is deliberately forgiving: `SP1`, `1` and `1.0` all match the same profile, so you
  can mix styles between the template and the grid. The flip side is that renaming a profile in only
  one place mis-matches silently rather than erroring.

#### 4. Parameter Templates

**`Constants_template.csv`**, **`InitConditions_template.csv`** (one or more files)

- Define species-specific parameter values for each plant type
- **Required columns** (case-insensitive, one of each type):
  - **ID column**: `SPECIESID`, `SPECIES`, `ID`, `CLASS`
  - **Parameter/Variable column**: `CONSTANT`, `VARIABLE`, `KEY`, `NAME`, `PARAM`, `PARAMETER`
  - **Value column**: `VALUE`, `VAL`, `AMOUNT`
- **Optional columns**:
  - **Template/scope column**: `TEMPLATE`, `SCOPE`, `SOURCE` (values such as `landuse` or `soilprofile`)
  - **Type column**: `TYPE`, `MAPTYPE`, `MAP` (`1` = generate map, `0` = skip)

- **Example:**

  | SPECIESID   | CONSTANT | VALUE |
  | ----------- | -------- | ----- |
  | Oak_Forest  | LAI_max  | 5.5   |
  | Oak_Forest  | RD_max   | 2.0   |
  | Pine_Forest | LAI_max  | 4.8   |
  | Pine_Forest | RD_max   | 1.8   |

Working examples of all four input types live in `sample_data/plant_growth_module/`.

### Processing Options

Configure these settings in the notebook's configuration cell (Step 0):

- **`AUTO_CONFIRM`**: Set to `True` for batch processing mode
  - Skips interactive confirmation prompts
  - Useful for automated workflows and repeated runs

- **`OUTPUT_DIR`**: Specify the output directory path
  - All generated DFS2 files will be saved here
  - Use absolute paths for reliability

---

## 🔧 Troubleshooting

### Common Issues

**Import errors (e.g., `ModuleNotFoundError: No module named 'mikeio'`):**

- Ensure you've run `uv sync`
- Verify the correct kernel is selected in VS Code

**File not found errors:**

- Check that all paths in Step 0 use absolute paths
- Verify file names and extensions match exactly

**DFS2 reading errors:**

- Ensure `mikeio` is compatible with your MIKE Zero version
- Check that DFS2 files are not corrupted

**`Time step is 0.0 seconds` warning when writing DFS2:**

- Expected and harmless. Static maps have no time dimension, but `mikeio` requires a time axis, so
  the writers add a single zero-length step. The helpers suppress this specific warning.

**OneDrive sync issues:**

- Always use `uv sync --link-mode copy` when working in OneDrive folders

**Forcing repository import errors:**

- `forcing_repository.py` loads the `data-download-tool` source at runtime and probes for
  `core/downloader.py` and `analysis/catchment.py`. If those moved, re-run
  `uv sync --link-mode copy` to refresh the dependency from GitHub `main`.

**Column names not recognized in template files:**

- The tool automatically detects columns but only supports specific names (see Configuration section)
- If your CSV files use different column names, you have two options:

  **Option 1: Rename columns in your CSV files** (Recommended)
  - Open the CSV file in Excel or a text editor
  - Rename the columns to one of the supported names listed in the Configuration section
  - For example, if you have a column named `PlantType`, rename it to `SPECIESID` or `CLASS`

  **Option 2: Add support for new column names in the code**
  - Open [src/plant_growth_module/template_maps.py](src/plant_growth_module/template_maps.py)
  - Find the column name lists at the top of the file (`VAL_COLS`, `CLASS_COLS`, `APPLY_COLS`,
    `ID_COLS`, `VALUE_COLS`, `KEY_COLS`, `TEMPLATE_COLS`, `TYPE_COLS`)
  - Add your custom column name to the appropriate list
  - Example: if your file uses `PlantType` for the species, add it to `ID_COLS`

---

## 📝 License

This project is part of the PHISHES research initiative. See [LICENSE](../../LICENSE).
