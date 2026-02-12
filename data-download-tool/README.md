# PHISHES Digital Platform - Data Download Tool

A Python toolkit for downloading and managing soil science datasets from the PDP datastore based on user-defined catchment boundaries.

## 🌍 What Does This Tool Do?

The PHISHES Digital Platform (PDP) Data Download Tool works with the following inputs and capabilities for catchment-scale soil science modeling:

- **Catchment spatial data** (Shapefile format or extent) defining your study area boundary
- **PDP datastore** containing curated datasets in Zarr format
- **Spatial subsetting** to extract only data within your catchment
- **Automated downloads** with proper folder organization

And generates:

- **Locally stored datasets** clipped to your catchment extent
- **Standardized folder structure** for organized data management
- **Download logs** tracking provenance and metadata

### Key Features

- ✅ Polygon-based spatial extraction (only download what you need)
- ✅ Zarr format for efficient cloud-optimized data access
- ✅ Optional DFS2 export
- ✅ Automatic catchment CRS (Coordinate Reference System) reprojection
- ✅ Support for multiple dataset categories (climate, soil, topography, landuse, hydrology)
- ✅ Area-weighted basin averaging and time series analysis
- ✅ European coverage for all datasets

---

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

---

## 📦 Installation

### 1. Install `uv` (Python Package Manager)

`uv` is a fast Python package installer and environment manager. Install it following the instructions here: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### 2. Set Up the Environment

Navigate to the project directory and create the virtual environment with all dependencies:

```bash
cd data-download-tool
uv sync --link-mode copy
```

**Note:** The `--link-mode copy` flag is required when working with OneDrive or other cloud-synced directories.

This command will:

- Create a virtual environment in `.venv/`
- Install all required packages (xarray, zarr, geopandas, adlfs, etc.)
- Set up the development dependencies

---

## 🚀 How to Execute the Notebook

### Option 1: Using VS Code (Recommended)

0. **Install VS Code (free):**
   - Download and install from [https://code.visualstudio.com/](https://code.visualstudio.com/)

1. **Open the correct folder in VS Code:**

   > ⚠️ **Critical:** You must open the `data-download-tool` folder itself as the workspace root in VS Code. If you open a higher-level parent folder (e.g., the repository root), VS Code **will not detect** the `.venv` Python environment and the Jupyter kernel will not appear in the kernel picker.

   **How to open the correct folder:**
   - Launch VS Code
   - Go to **File → Open Folder…** (or press `Ctrl + K`, `Ctrl + O`)
   - Browse to and select the `data-download-tool` folder, then click **Select Folder**
   - Verify the VS Code Explorer sidebar shows `data-download-tool` as the top-level folder

   **Why this matters:**
   - VS Code discovers Python environments (`.venv/`) relative to the opened workspace root
   - The `.venv` created by `uv sync` lives inside `data-download-tool/.venv/`
   - If your workspace root is a parent folder, VS Code won't look inside nested subdirectories for virtual environments, so the kernel won't be found

2. **Open the notebook:**
   - In the VS Code Explorer, navigate to `notebooks/data_download_tool.ipynb` and click to open it

3. **Select the Python kernel:**
   - Click on the kernel selector in the top-right corner of the notebook
   - Choose the `.venv` environment (e.g., `phishes-data-downloader (.venv)`) created by `uv sync`. `phishes-data-downloader` should be the recommended environment.
   - If it does not appear, confirm you opened the correct folder (see step 1) and that you ran `uv sync` successfully

4. **Run the notebook:**

   **To run a single cell:**
   - Click the **▶️ Play button** on the left side of the cell, OR
   - Select the cell and press **`Shift + Enter`**
   - The cell will execute and move to the next cell

   **To run all cells:**
   - Click **Run All** in the toolbar at the top of the notebook, OR
   - Press **`Ctrl + Shift + P`** → Type "Run All Cells" → Press Enter

### Option 2: Using Jupyter Lab/Notebook

#### Method A: Using `uv run` (Recommended - No activation needed)

```powershell
# Windows PowerShell
uv run jupyter notebook notebooks/data_download_tool.ipynb
```

```bash
# macOS/Linux
uv run jupyter notebook notebooks/data_download_tool.ipynb
```

#### Method B: Activate environment first

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
jupyter notebook notebooks/data_download_tool.ipynb
```

**macOS/Linux:**

```bash
source .venv/bin/activate
jupyter notebook notebooks/data_download_tool.ipynb
```

**To run cells in Jupyter:**

- Click the **Run** button in the toolbar for each cell
- Or use keyboard shortcuts: **`Shift + Enter`** to run and advance

---

## 📁 Project Structure

```
data-download-tool/
├── src/
│   ├── core/                       # Core functionality modules
│   │   ├── __init__.py             # Package exports
│   │   ├── utils.py                # Utility functions
│   │   ├── folder_structure.py     # Folder structure creation
│   │   ├── downloader.py           # Data downloader
│   │   ├── dfsio.py                # DFS file I/O utilities
│   │   └── dataset_catalog.yaml    # Available datasets definition
│   ├── analysis/                   # Analysis modules
│   │   ├── __init__.py             # Package exports
│   │   ├── catchment.py            # Catchment processing & validation
│   │   ├── timeseries.py           # Time series analysis
│   │   └── visualization.py        # Plotting functions
├── notebooks/
│   └── data_download_tool.ipynb     # Main tutorial notebook
├── data/
│   └── shp/                        # Catchment shapefiles
│       └── catchment_template/     # Example catchment
├── pyproject.toml                  # Project dependencies
├── README.md                       # This file
└── DataDownloadTool.md             # Technical documentation
```

---

## ⚙️ Configuration

All configuration is done inside the notebook. The cells in **Step 1** let you set the study area, time range, and output format before running any downloads.

### Input Required

The tool downloads datasets clipped to a study area that you define. There are two ways to specify it:

1. **Catchment shapefile** — provide all supporting files (`.shp`, `.shx`, `.dbf`, `.prj`). CRS is automatically reprojected if needed; multiple features are merged into a single catchment.
2. **Manual extent** — provide four bounding-box coordinates `[minx, miny, maxx, maxy]` and a CRS (e.g., `EPSG:4326`). No file needed.

### Processing Options

Configure these settings in the notebook when initializing the downloader:

- **`catchment`**: Path to catchment shapefile, pre-loaded GeoDataFrame, or manual extent
- **`output_base`**: Base directory for downloaded data
- **`time_range`**: Tuple of start and end dates (e.g., `('2015-01-01', '2020-12-31')`)
- **`buffer_cells`**: Buffer in grid cells around catchment (default: 1)
- **`output_format`**: Output format - `"nc"` (NetCDF), `"zarr"`, or `"dfs2"`
- **`mask_on_catchment`**: If `True`, clips data to exact catchment boundary

---

## 📚 Available Datasets

The following datasets are currently available in PDP datastore:

| Category | Subcategory                            | Variable | Unit | Timestep | Spatial Res.   |
| -------- | -------------------------------------- | -------- | ---- | -------- | -------------- |
| climate  | era5_precipitation                     | tp       | mm   | 1 h      | 0.25° (~25 km) |
| climate  | era5_temperature                       | t2m      | °C   | 1 h      | 0.25° (~25 km) |
| climate  | era5_potential_evapotranspiration      | pev      | mm   | 1 h      | 0.25° (~25 km) |
| climate  | era5_surface_solar_radiation_downwards | ssrd     | W/m² | 1 h      | 0.25° (~25 km) |

Additional categories (soil, topography, landuse, hydrology) will be added as they become available.

---

## 🔧 Troubleshooting

### Quick Fixes

**Connection Error:**

```
Cannot connect to PDP datastore
```

- Check internet connection
- Credentials are built into the downloader

**Catchment CRS Error:**

```
Catchment shapefile has no CRS defined
```

- Ensure your shapefile has a `.prj` file
- CRS will be automatically reprojected if needed

**Import Errors:**

```
ModuleNotFoundError: No module named 'geopandas'
```

- Run: `uv sync` to install all dependencies

---

## 📖 Additional Documentation

- **Technical Details**: See [DataDownloadTool.md](DataDownloadTool.md) for architecture and implementation

---

## 🖥️ System Requirements

The following are needed to run the tool:

- Python 3.9+
- ~2 GB RAM minimum (more for large catchments)
- Internet connection for data access
- Disk space varies by catchment size and time range

---

## 🙏 Acknowledgments

- **ERA5 data**: Copernicus Climate Change Service
- **SoilGrids**: ISRIC World Soil Information
- **EU-DEM**: European Environment Agency
- **CORINE**: European Environment Agency

---

## 📞 Support

For questions or issues:

1. Review [DataDownloadTool.md](DataDownloadTool.md) for technical details
2. Explore [notebooks/data_download_tool.ipynb](notebooks/data_download_tool.ipynb) for examples

---

**Version**: 1.0
**Last Updated**: February 2026
