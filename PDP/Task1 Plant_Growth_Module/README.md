# Plant Growth Module (PGM) - DFS2 Map Generator

A tool for generating spatially distributed DFS2 maps for DHI's ECO Lab Plant Growth Module. This notebook-based application processes land use data and species-specific parameters to create input files for MIKE SHE hydrological modeling.

## 🌱 What Does This Tool Do?

The Plant Growth Module processes:

- **Land use spatial data** (DFS2 format) containing numeric codes for different land cover types
- **Species classification** mapping land use codes to plant species names
- **Parameter templates** (CSV files) defining species-specific constants and initial conditions

And generates:

- **Spatially distributed DFS2 maps** for each parameter
- **MIKE SHE-compatible files** ready for integration with ECO Lab

### Key Features

- ✅ Automatic column detection with user confirmation
- ✅ Batch processing mode for automation
- ✅ Validation of all input files before processing
- ✅ Support for multiple parameter templates
- ✅ Spatial mapping based on land use classification

---

## 📦 Installation

### 1. Install `uv` (Python Package Manager)

`uv` is a fast Python package installer and environment manager. Install it following the instructions here: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### 2. Set Up the Environment

Navigate to the project directory and create the virtual environment with all dependencies:

```bash
cd "Task1 Plant_Growth_Module"
uv sync --link-mode copy
```

**Note:** The `--link-mode copy` flag is required when working with OneDrive or other cloud-synced directories.

This command will:

- Create a virtual environment in `.venv/`
- Install all required packages (pandas, numpy, mikeio, jupyter, etc.)
- Set up the development dependencies

---

## 🚀 How to Execute the Notebook

### Option 1: Using VS Code (Recommended)

1. **Open the notebook:**
   - Open VS Code
   - Navigate to `code/t1_plant_growth_module.ipynb`

2. **Select the Python kernel:**
   - Click on the kernel selector in the top-right corner
   - Choose the `.venv` environment created by `uv sync`

3. **Run the notebook:**

   **To run a single cell:**
   - Click the **▶️ Play button** on the left side of the cell, OR
   - Select the cell and press **`Shift + Enter`**
   - The cell will execute and move to the next cell

   **To run all cells:**
   - Click **Run All** in the toolbar at the top of the notebook, OR
   - Press **`Ctrl + Shift + P`** → Type "Run All Cells" → Press Enter

4. **Workflow:**
   - **Step 0**: Edit file paths in the configuration cell
   - **Step 0.1**: Run setup and validation
   - **Step 1**: Load land use data and create mapping
   - **Step 2**: Process templates and generate DFS2 maps
   - **Step 3**: Verify output files

### Option 2: Using Jupyter Lab/Notebook

#### Method A: Using `uv run` (Recommended - No activation needed)

```powershell
# Windows PowerShell
uv run jupyter notebook code/t1_plant_growth_module.ipynb
```

```bash
# macOS/Linux
uv run jupyter notebook code/t1_plant_growth_module.ipynb
```

#### Method B: Activate environment first

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
jupyter notebook code/t1_plant_growth_module.ipynb
```

**macOS/Linux:**

```bash
source .venv/bin/activate
jupyter notebook code/t1_plant_growth_module.ipynb
```

**To run cells in Jupyter:**

- Click the **Run** button in the toolbar for each cell
- Or use keyboard shortcuts: **`Shift + Enter`** to run and advance

---

## 📁 Project Structure

```
Task1 Plant_Growth_Module/
├── code/
│   ├── t1_plant_growth_module.ipynb   # Main notebook
│   ├── t1_pgm_helper.py                # Helper functions
├── pyproject.toml                      # Project dependencies
└── README.md                           # This file
```

---

## ⚙️ Configuration

### Input Files Required

**Important Notes:**

- ✅ All file paths must be **absolute paths** (full paths)
- ✅ Column names are **case-insensitive** (uppercase and lowercase letters don't matter)

#### 1. Land Use Spatial Data

**`LandUse.DFS2`**

- Binary spatial grid file containing numeric land use codes
- Each cell value represents a specific land cover/vegetation type

#### 2. Land Use Classification Mapping

**`LandUse_template.csv`** (or similar name)

- Maps numeric codes from the DFS2 file to plant species names
- **Required columns** (case-insensitive, one of each type):
  - **Code column**: `CODE`, `VALUE`
  - **Class/Species column**: `CLASS`, `SPECIESID`

**Example:**

| CODE | CLASS       |
| ---- | ----------- |
| 1    | Oak_Forest  |
| 2    | Pine_Forest |
| 3    | Grassland   |

#### 3. Species Parameter Templates

**`Constants_template.csv`**, **`InitConditions_template.csv`** (one or more files)

- Define species-specific parameter values for each plant type
- **Required columns** (case-insensitive, one of each type):
  - **Species column**: `SPECIESID`, `SPECIES`, `ID`, `CLASS`
  - **Parameter/Variable column**: `CONSTANT`, `VARIABLE`, `KEY`, `NAME`, `PARAM`, `PARAMETER`
  - **Value column**: `VALUE`, `VAL`, `AMOUNT`

**Example:**

| SPECIESID   | CONSTANT | VALUE |
| ----------- | -------- | ----- |
| Oak_Forest  | LAI_max  | 5.5   |
| Oak_Forest  | RD_max   | 2.0   |
| Pine_Forest | LAI_max  | 4.8   |
| Pine_Forest | RD_max   | 1.8   |

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

**OneDrive sync issues:**

- Always use `uv sync --link-mode copy` when working in OneDrive folders

**Column names not recognized in template files:**

- The tool automatically detects columns but only supports specific names (see Configuration section)
- If your CSV files use different column names, you have two options:

  **Option 1: Rename columns in your CSV files** (Recommended)
  - Open the CSV file in Excel or a text editor
  - Rename the columns to one of the supported names listed in the Configuration section
  - For example, if you have a column named `PlantType`, rename it to `SPECIESID` or `CLASS`

  **Option 2: Add support for new column names in the code**
  - Open [code/t1_pgm_helper.py](code/t1_pgm_helper.py)
  - Find the column name lists (e.g., `CODE_COLS`, `CLASS_COLS`, `SPECIES_COLS`, etc.)
  - Add your custom column name to the appropriate list
  - Example: If your file uses `PlantType`, add it to the `SPECIES_COLS` list

---

## 📝 License

This project is part of the PHISHES research initiative.
