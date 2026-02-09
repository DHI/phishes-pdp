# PHISHES Digital Platform - Data Download Module

A Python toolkit for downloading and managing soil science datasets from Azure cloud storage based on user-defined catchment boundaries.

## 🌍 What Does This Tool Do?

The PHISHES Digital Platform (PDP) Data Download Module provides automated access to geospatial datasets for catchment-scale soil science modeling:

- **Catchment spatial data** (Shapefile format) defining your study area boundary
- **Azure Blob Storage** containing curated datasets in Zarr format
- **Spatial subsetting** to extract only data within your catchment
- **Automated downloads** with proper folder organization

And generates:

- **Locally stored datasets** clipped to your catchment extent
- **Standardized folder structure** for organized data management
- **Download logs** tracking provenance and metadata

### Key Features

- ✅ Polygon-based spatial extraction (only download what you need)
- ✅ Zarr format for efficient cloud-optimized data access
- ✅ Optional DFS2 export for MIKE IO interoperability
- ✅ Automatic catchment CRS reprojection
- ✅ Support for multiple dataset categories (climate, soil, topography, landuse, hydrology)
- ✅ Area-weighted basin averaging and time series analysis
- ✅ European coverage for all datasets

---

## 📦 Installation

### 1. Install `uv` (Python Package Manager)

`uv` is a fast Python package installer and environment manager. Install it following the instructions here: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### 2. Set Up the Environment

Navigate to the project directory and create the virtual environment with all dependencies:

```bash
cd Task2
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

1. **Open the notebook:**
   - Open VS Code
   - Navigate to `code/t2_data_downloader.ipynb`

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
   - **Step 1**: Configure Azure connection and catchment path
   - **Step 2**: Create folder structure
   - **Step 3**: Download datasets
   - **Step 4**: Load and analyze data
   - **Step 5**: Visualize results

### Option 2: Using Jupyter Lab/Notebook

#### Method A: Using `uv run` (Recommended - No activation needed)

```powershell
# Windows PowerShell
uv run jupyter notebook code/t2_data_downloader.ipynb
```

```bash
# macOS/Linux
uv run jupyter notebook code/t2_data_downloader.ipynb
```

#### Method B: Activate environment first

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
jupyter notebook code/t2_data_downloader.ipynb
```

**macOS/Linux:**

```bash
source .venv/bin/activate
jupyter notebook code/t2_data_downloader.ipynb
```

**To run cells in Jupyter:**

- Click the **Run** button in the toolbar for each cell
- Or use keyboard shortcuts: **`Shift + Enter`** to run and advance

---

## 📁 Project Structure

```
Task2/
├── code/
│   ├── core/                       # Core functionality modules
│   │   ├── __init__.py             # Package exports
│   │   ├── utils.py                # Utility functions
│   │   ├── folder_structure.py     # Folder structure creation
│   │   ├── downloader.py           # Azure data downloader
│   │   ├── dfsio.py                # DFS file I/O utilities
│   │   └── dataset_catalog.yaml    # Available datasets definition
│   ├── analysis/                   # Analysis modules
│   │   ├── __init__.py             # Package exports
│   │   ├── catchment.py            # Catchment processing & validation
│   │   ├── timeseries.py           # Time series analysis
│   │   └── visualization.py        # Plotting functions
│   └── t2_data_downloader.ipynb    # Main tutorial notebook
├── data/
│   └── shp/                        # Catchment shapefiles
│       └── catchment_template/     # Example catchment
├── pyproject.toml                  # Project dependencies
├── README.md                       # This file
└── task2.md                        # Technical documentation
```

---

## ⚙️ Configuration

### Input Files Required

**Important Notes:**

- ✅ Catchment shapefile must include all supporting files (`.shp`, `.shx`, `.dbf`, `.prj`)
- ✅ CRS will be automatically reprojected if needed
- ✅ Multiple polygon features are automatically merged into single catchment

#### 1. Catchment Shapefile

**Required Files:**

- `catchment.shp` - Polygon geometry
- `catchment.shx` - Shape index
- `catchment.dbf` - Attribute data
- `catchment.prj` - Coordinate reference system

**Example Location:** `data/shp/catchment_template/catchment_template.shp`

#### 2. Manual Extent (No File)

Provide a bounding box and projection instead of a polygon file:

- `extent`: `[minx, miny, maxx, maxy]`
- `crs`: EPSG code or PROJ string (e.g., `EPSG:4326`)

### Processing Options

Configure these settings in the notebook when initializing the downloader:

- **`catchment`**: Path to catchment shapefile or pre-loaded GeoDataFrame
- **`output_base`**: Base directory for downloaded data
- **`time_range`**: Tuple of start and end dates (e.g., `('2015-01-01', '2020-12-31')`)
- **`buffer_cells`**: Buffer in grid cells around catchment (default: 1)
- **`output_format`**: Output format - `"nc"` (NetCDF), `"zarr"`, or `"dfs2"`
- **`mask_on_catchment`**: If `True`, clips data to exact catchment boundary

---

## 💡 Basic Usage

### Quick Start Example

```python
from pathlib import Path
from core import create_pdp_folders, PDPDataDownloader
from analysis import load_catchment

# Step 1: Create folder structure
PROJECT_BASE = Path("./my_project")
create_pdp_folders(base_path=PROJECT_BASE)

# Step 2: Load catchment
catchment, catchment_geom = load_catchment(
    "data/shp/catchment_template/catchment_template.shp",
    target_crs="EPSG:4326"
)

# Step 3: Initialize downloader
downloader = PDPDataDownloader(
    catchment=catchment,
    output_base=PROJECT_BASE,
    output_format="nc",
    mask_on_catchment=True,
)

# Step 4: Download a dataset
downloader.download_dataset(
    category="climate",
    subcategory="era5_precipitation",
    time_range=("2015-01-01", "2020-12-31")
)
```

### Analysis Example

```python
from core import build_dataset_path, open_dataset_any
from analysis import (
    load_catchment, compute_catchment_weights,
    compute_basin_average, compute_anomalies,
    plot_spatial_map, plot_time_series
)

# Load downloaded dataset
dataset_path = build_dataset_path("./my_project", "climate", "era5_precipitation", "nc")
ds = open_dataset_any(dataset_path)

# Load catchment
catchment, catchment_geom = load_catchment(
    "data/shp/catchment_template/catchment_template.shp",
    target_crs="EPSG:4326"
)

# Compute area-weighted basin average
weights = compute_catchment_weights(ds, catchment_geom)
basin_avg = compute_basin_average(ds['tp'], weights)

# Compute anomalies
anomaly_stats = compute_anomalies(basin_avg)

# Plot results
plot_time_series(basin_avg, title="Basin Average Precipitation")
plot_spatial_map(ds['tp'].isel(time=0), catchment, title="Precipitation Map")
```

---

## 📊 Generated Folder Structure

When you run `create_pdp_folders()`, it creates a minimal structure:

```
<your_project>/
└── logs/                   # Download logs
    └── download_log.json
```

Data folders are created automatically during downloads:

```
<your_project>/
├── data/                   # Downloaded datasets (created on download)
│   └── climate/
│       └── era5_precipitation/
│           └── era5_precipitation.nc
└── logs/
    └── download_log.json
```

---

## 📚 Available Datasets

The following datasets are currently available in Azure storage:

| Category | Subcategory        | Description        | Variables |
| -------- | ------------------ | ------------------ | --------- |
| climate  | era5_precipitation | ERA5 precipitation | tp        |
| climate  | era5_temperature   | ERA5 temperature   | t2m       |

**Note**: Additional datasets (soil, topography, landuse, hydrology) will be added as they become available in the Azure storage.

---

## 🔧 Troubleshooting

### Quick Fixes

**Connection Error:**

```
Cannot connect to Azure storage
```

- Check internet connection
- Azure credentials are built into the downloader

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

- **Technical Details**: See [task2.md](task2.md) for architecture and implementation

---

## 🔬 Advanced Usage

### Batch Download

Use `download_all()` to download all available datasets at once:

```python
downloader.download_all(time_range=('2015-01-01', '2020-12-31'))
```

### Masking to Catchment

Enable `mask_on_catchment=True` to clip data exactly to your catchment boundary (instead of just the bounding box):

```python
downloader = PDPDataDownloader(
    catchment=catchment,
    output_base=PROJECT_BASE,
    mask_on_catchment=True,  # Clip to exact catchment shape
)
```

---

## 🛠️ Development

### Requirements

- Python 3.9+
- ~2GB RAM minimum (more for large catchments)
- Internet connection for Azure access
- Disk space varies by catchment size and time range

### Data Format

- **Storage**: Zarr format (cloud-optimized), NetCDF, and DFS2
- **Compression**: Optimized chunking for spatial and temporal access
- **Metadata**: Consolidated metadata (`.zmetadata`) for fast opening
- **CRS**: European datasets use EPSG:3035 (ETRS89 / LAEA Europe)

---

## 🙏 Acknowledgments

- **ERA5 data**: Copernicus Climate Change Service
- **SoilGrids**: ISRIC World Soil Information
- **EU-DEM**: European Environment Agency
- **CORINE**: European Environment Agency

---

## 📞 Support

For questions or issues:

1. Review [task2.md](task2.md) for technical details
2. Explore [code/t2_data_downloader.ipynb](code/t2_data_downloader.ipynb) for examples

---

**Version**: 1.0
**Last Updated**: February 2026
