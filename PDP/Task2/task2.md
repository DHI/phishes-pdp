# Data Download Module for PHISHES Digital Platform

## Project Overview

This project implements a Data Download Module that integrates with Azure Blob Storage to provide automated access to geospatial datasets for catchment-scale soil science modeling. The module processes user-provided catchment polygons and downloads spatially clipped datasets from cloud storage.

**Key Integration Points:**

- Azure Blob Storage: Cloud storage containing Zarr formatted datasets (outputs can be NetCDF/Zarr/DFS2)
- Catchment shapefiles: User-provided polygon defining study area
- Zarr format: Cloud-optimized format for efficient data access
- NetCDF format: Alternative format for compatibility
- DFS2 format: MIKE IO grid format for interoperability
- Primary datasets: Climate (ERA5), Soil (SoilGrids), Topography (EU-DEM), Land Use (CORINE)

## Critical Data Structures

### Catchment File Format (data/shp/)

**Supported Formats:**

1. **Shapefile** (`.shp`) - Requires supporting files:
   - `*.shp`: Polygon geometry file
   - `*.shx`: Shape index file
   - `*.dbf`: Attribute database
   - `*.prj`: Coordinate reference system

2. **GeoJSON** (`.geojson` or `.json`) - Single file format

3. **Manual Extent** (no file) - User provides bounding box and projection:
   - `extent`: `[minx, miny, maxx, maxy]`
   - `crs`: EPSG code or PROJ string (e.g., `EPSG:4326`)

**Requirements:**

- Geometry type: Polygon or MultiPolygon
- CRS: Any valid CRS (will be reprojected automatically)
- Multiple features: Automatically merged into single catchment
- Attributes: Not used (only geometry is processed)

### Azure Storage Structure

**Container Organization:**

```
pdp-datasets/
├── climate/
│   ├── temperature/
│   │   └── era5_temperature.zarr/
│   ├── precipitation/
│   │   └── era5_precipitation.zarr/
│   └── evapotranspiration/
├── soil/
│   ├── properties/
│   └── moisture/
├── topography/
│   └── dem/
├── landuse/
│   └── corine/
└── hydrology/
    └── discharge/
```

**Dataset Requirements:**

- Format: Zarr with consolidated metadata or NetCDF (outputs can be NetCDF/Zarr/DFS2)
- Dimensions: Must include spatial coordinates (x, y or lon, lat)
- Time dimension: Optional (for time-series data)
- CRS: Must be defined in dataset attributes

### Matching Logic

When catchment doesn't intersect dataset extent: **empty dataset is returned** with appropriate warning. Always verify catchment CRS matches expected coverage area.

## Project Structure

```
code/
  core/
    utils.py                  # Path building and dataset opening
    folder_structure.py       # Folder structure creation
    downloader.py             # Azure download functionality
  analysis/
    catchment.py              # Catchment loading and processing
    timeseries.py             # Time series analysis functions
    visualization.py          # Plotting utilities
  example_usage.ipynb         # Main tutorial notebook
data/
  shp/
    catchment_template/       # Example catchment shapefile
    Bavaria/                  # Example regional boundaries
```

## Development Workflow

### Working with Jupyter Notebooks

- Primary development in `code/example_usage.ipynb`
- Expected workflow: Load catchment → Create folders → Download data → Analyze → Visualize
- All cells should be executable sequentially

### Python Environment

- Required packages: xarray, zarr, adlfs, geopandas, shapely, rasterio, matplotlib, mikeio
- Use `uv sync` to install all dependencies
- Use `configure_python_environment` before executing notebook cells

### Data File Conventions

- Catchment files: Stored in `data/shp/` with descriptive names
- Downloaded data: Organized by category/subcategory hierarchy
- Log files: JSON format in `logs/` directory tracking all downloads

## Key Technical Considerations

### Azure Integration

Authentication uses SAS tokens for secure access to Azure Blob Storage.

Connection example:

```python
import adlfs

fs = adlfs.AzureBlobFileSystem(
    account_name="phishes_storage",
    sas_token="YOUR_SAS_TOKEN"
)
```

### Spatial Data Processing

- CRS handling: Automatic reprojection using pyproj
- Clipping: Uses rasterio/xarray for efficient spatial subsetting
- Buffer zones: Optional 5km buffer around catchment
- Area weights: Computed for accurate basin averaging

### Data Format Considerations

- Zarr advantages: Chunked storage, cloud-optimized, parallel access
- NetCDF compatibility: Fallback format for tools requiring CF conventions
- DFS2 compatibility: Interoperable with MIKE IO workflows and tools
- Coordinate systems: EPSG:4326 for lat/lon, EPSG:3035 for European projections
- Values must be physically meaningful (proper units and valid ranges)

## Naming Conventions

- Datasets: Lowercase with underscores (e.g., `era5_temperature`, `soilgrids_properties`)
- Functions: Lowercase with underscores following Python conventions
- Classes: PascalCase (e.g., `PDPDataDownloader`, `PDPFolderStructure`)
- Variables: Descriptive lowercase (e.g., `catchment_bounds`, `dataset_path`)

## Code Style Conventions

- **Path construction**: Use `Path.joinpath()` method or `/` operator consistently
  - Example: `base_path / "data" / "climate"` or `base_path.joinpath("data", "climate")`
- **Imports**: Organize in standard order: standard library → third-party → local
  - Example: `pathlib, os → xarray, geopandas → .core, .analysis`
- **Notebook cell order**: Sequential execution required
  - Correct sequence: imports → config → setup → download → analyze → visualize
- **Error handling**: Use try-except blocks with informative error messages
- **Documentation**: All functions have docstrings with parameters and return types

## Common Pitfalls

- Missing CRS in catchment shapefile causes reprojection failures
- Incorrect Azure credentials lead to authentication errors
- Large time ranges may exceed memory limits for basin averaging
- Network interruptions during downloads leave incomplete datasets
- Missing consolidated metadata (.zmetadata) slows Zarr opening

## External Dependencies

- Azure Blob Storage (phishes_storage account)
- ADLFS (Azure Data Lake File System for fsspec)
- Xarray/Zarr (data format and I/O)
- MIKE IO (DFS2 read/write)
- GeoPandas/Shapely (spatial operations)

## Available Datasets Catalog

**TODO: Complete this list from Overleaf document**

The following datasets are available in Azure Blob Storage:

| Dataset Name            | Variable           | Temporal Coverage | Temporal Resolution | Spatial Resolution | Format | Folder Destination                 |
| ----------------------- | ------------------ | ----------------- | ------------------- | ------------------ | ------ | ---------------------------------- |
| ERA5 Temperature        | t2m (2m temp)      | 1979-present      | 1h                  | 0.25° (~25km)      | Zarr   | `data/climate/temperature/`        |
| ERA5 Precipitation      | tp (total precip)  | 1979-present      | 1h                  | 0.25° (~25km)      | Zarr   | `data/climate/precipitation/`      |
| ERA5 Evapotranspiration | pet (potential ET) | 1979-present      | 1h                  | 0.25° (~25km)      | Zarr   | `data/climate/evapotranspiration/` |

**Notes:**

- All datasets cover European extent (approximately 25°W-45°E, 34°N-72°N)
- Time ranges can be specified for temporal datasets
- Static datasets (soil, topography) have no temporal dimension

## Folder Structure Details

The `create_pdp_folders()` function creates a standardized folder structure:

```
<user_workspace>/
├── data/                           # Downloaded datasets
│   ├── climate/
│   │   ├── temperature/
│   │   │   ├── era5_temperature.nc     # Downloaded data
│   │   │   └── metadata.json           # Dataset metadata
│   │   ├── precipitation/
│   │   │   └── era5_precipitation.nc
│   │   ├── evapotranspiration/
│   │   └── radiation/
│   ├── soil/
│   │   ├── properties/
│   │   │   └── soilgrids_properties.zarr/
│   │   └── moisture/
│   ├── topography/
│   │   └── dem/
│   │       └── eudem_elevation.zarr/
│   ├── landuse/
│   │   └── corine/
│   │       └── corine_landcover.zarr/
│   └── hydrology/
│       └── discharge/
├── inputs/                         # User-provided inputs
│   ├── catchment/                  # Catchment shapefiles
│   ├── parameters/                 # Model parameters
│   └── config/                     # Configuration files
├── outputs/                        # Analysis results
│   ├── results/                    # Processed outputs
│   ├── figures/                    # Plots and visualizations
│   └── reports/                    # Generated reports
├── scripts/                        # Custom processing scripts
│   └── README.md                   # Script documentation
└── logs/                           # Download and processing logs
    ├── download_log.json           # Detailed download history
    └── README.md                   # Log file descriptions
```

**Design Rationale:**

- `data/`: Organized by dataset category for easy navigation
- `inputs/`: Separates user data from downloaded data
- `outputs/`: Designed for future result viewer integration
- `scripts/`: Placeholder for user's custom processing scripts
- `logs/`: JSON format for programmatic access and analysis

## Module Documentation

### Module Overview

The codebase is organized into two packages within `code/`:

#### `core/` - Core Functionality

| Module                | Purpose                   | Key Exports                                        |
| --------------------- | ------------------------- | -------------------------------------------------- |
| `utils.py`            | Utility functions         | `build_dataset_path()`, `open_dataset_any()`       |
| `folder_structure.py` | Folder hierarchy creation | `create_pdp_folders()`, `PDPFolderStructure` class |
| `downloader.py`       | Azure data download       | `PDPDataDownloader` class                          |

#### `analysis/` - Analysis Functions

| Module             | Purpose              | Key Exports                                                    |
| ------------------ | -------------------- | -------------------------------------------------------------- |
| `catchment.py`     | Catchment processing | `load_catchment()`, `compute_catchment_weights()`              |
| `timeseries.py`    | Time series analysis | `compute_basin_average()`, `compute_anomalies()`               |
| `visualization.py` | Plotting utilities   | `plot_spatial_map()`, `plot_time_series()`, `plot_catchment()` |

### 1. `core/utils.py`

Utility functions for path construction and data loading.

**Functions:**

```python
def build_dataset_path(
    base_path: str | Path,
    category: str,
    subcategory: str,
    extension: str = "nc"
) -> Path:
    """
    Build standardized path to dataset file.

    Parameters:
        base_path: Project root directory
        category: Dataset category (e.g., 'climate', 'soil')
        subcategory: Dataset subcategory (e.g., 'temperature', 'properties')
        extension: File extension ('nc' for NetCDF, 'zarr' for Zarr, 'dfs2' for MIKE IO)

    Returns:
        Path to dataset file
    """

def open_dataset_any(path: str | Path) -> xr.Dataset:
    """
    Open dataset in any supported format (NetCDF, Zarr, or DFS2).

    Parameters:
        path: Path to dataset file or directory

    Returns:
        xarray Dataset
    """
```

**Usage:**

```python
from core import build_dataset_path, open_dataset_any

path = build_dataset_path("./my_project", "climate", "temperature", "nc")
ds = open_dataset_any(path)
```

### 2. `core/folder_structure.py`

Creates standardized folder structure for PDP projects.

**Class: PDPFolderStructure**

```python
class PDPFolderStructure:
    """Manages PDP folder structure creation and validation."""

    def __init__(self, base_path: str | Path):
        """Initialize with base project path."""

    def create_all(self, add_gitkeep: bool = False) -> None:
        """Create all folders in the structure."""

    def verify(self) -> bool:
        """Verify all required folders exist."""
```

**Function:**

```python
def create_pdp_folders(
    base_path: str | Path = ".",
    add_gitkeep: bool = False
) -> Path:
    """
    Create PDP folder structure.

    Parameters:
        base_path: Root directory for project
        add_gitkeep: Add .gitkeep files to empty folders

    Returns:
        Path to created project directory
    """
```

**Usage:**

```python
from core import create_pdp_folders

project_path = create_pdp_folders(
    base_path="./bavaria_study",
    add_gitkeep=True
)
```

### 3. `core/downloader.py`

Downloads datasets from Azure Blob Storage with spatial clipping.

**Class: PDPDataDownloader**

```python
class PDPDataDownloader:
    """Download datasets from Azure storage clipped to catchment extent."""

    def __init__(
        self,
        catchment_shp: str | Path,
        output_base: str | Path,
        azure_account: str,
        azure_credential: str,
        azure_container: str = "pdp-datasets",
        buffer_km: float = 5.0
    ):
        """
        Initialize downloader.

        Parameters:
            catchment_shp: Path to catchment shapefile
            output_base: Base directory for outputs
            azure_account: Azure storage account name
            azure_credential: SAS token for authentication
            azure_container: Container name (default: 'pdp-datasets')
            buffer_km: Buffer distance around catchment (default: 5.0)
        """

    def download_dataset(
        self,
        category: str,
        subcategory: str,
        time_range: tuple[str, str] | None = None,
        variables: list[str] | None = None
    ) -> Path:
        """
        Download single dataset.

        Parameters:
            category: Dataset category (e.g., 'climate')
            subcategory: Dataset subcategory (e.g., 'temperature')
            time_range: Optional (start_date, end_date) tuple
            variables: Optional list of variable names to download

        Returns:
            Path to downloaded dataset
        """

    def download_all(
        self,
        time_range: tuple[str, str] | None = None
    ) -> dict[str, Path]:
        """
        Download all available datasets.

        Parameters:
            time_range: Optional (start_date, end_date) for temporal datasets

        Returns:
            Dictionary mapping dataset names to paths
        """
```

**Usage:**

```python
from core import PDPDataDownloader

downloader = PDPDataDownloader(
    catchment_shp="data/shp/catchment.shp",
    output_base="./my_project",
    azure_account="phishes_storage",
    azure_credential="YOUR_SAS_TOKEN"
)

# Download specific dataset
path = downloader.download_dataset(
    category='climate',
    subcategory='temperature',
    time_range=('2018-01-01', '2020-12-31')
)
```

### 4. `analysis/catchment.py`

Catchment loading and spatial weight computation.

**Functions:**

```python
def load_catchment(
    shapefile_path: str | Path,
    target_crs: str = "EPSG:4326",
    merge_features: bool = True
) -> tuple[gpd.GeoDataFrame, str]:
    """
    Load catchment shapefile with CRS handling.

    Parameters:
        shapefile_path: Path to shapefile
        target_crs: CRS to reproject to (default: EPSG:4326)
        merge_features: Merge multiple polygons into one (default: True)

    Returns:
        (GeoDataFrame with catchment, CRS string)
    """

def compute_catchment_weights(
    dataset: xr.Dataset,
    catchment: gpd.GeoDataFrame
) -> xr.DataArray:
    """
    Compute area-weighted intersection fractions for basin averaging.

    Parameters:
        dataset: xarray Dataset with spatial coordinates
        catchment: GeoDataFrame with catchment polygon

    Returns:
        DataArray of weights (0-1) for each grid cell
    """
```

**Usage:**

```python
from analysis import load_catchment, compute_catchment_weights

catchment, crs = load_catchment(
    "catchment.shp",
    target_crs="EPSG:4326",
    merge_features=True
)
weights = compute_catchment_weights(ds, catchment)
```

### 5. `analysis/timeseries.py`

Time series analysis and basin averaging.

**Functions:**

```python
def compute_basin_average(
    data_array: xr.DataArray,
    weights: xr.DataArray
) -> xr.DataArray:
    """
    Compute area-weighted basin average time series.

    Parameters:
        data_array: Input data with spatial and optional time dimensions
        weights: Area weights from compute_catchment_weights()

    Returns:
        Basin-averaged DataArray (time series or scalar)
    """

def compute_anomalies(
    time_series: xr.DataArray,
    method: str = "standardized",
    baseline_period: tuple[str, str] | None = None
) -> xr.DataArray:
    """
    Compute anomalies from climatology.

    Parameters:
        time_series: Input time series
        method: 'standardized' or 'absolute' anomalies
        baseline_period: Optional (start, end) for baseline

    Returns:
        Anomaly time series
    """
```

**Usage:**

```python
from analysis import compute_basin_average, compute_anomalies

basin_avg = compute_basin_average(ds['temperature'], weights)
anomalies = compute_anomalies(basin_avg, method='standardized')
```

### 6. `analysis/visualization.py`

Plotting utilities for spatial and temporal data.

**Functions:**

```python
def plot_catchment(
    catchment: gpd.GeoDataFrame,
    title: str = "Catchment Boundary",
    ax: plt.Axes | None = None
) -> plt.Axes:
    """Plot catchment boundary."""

def plot_spatial_map(
    data: xr.DataArray,
    catchment: gpd.GeoDataFrame | None = None,
    title: str = "",
    cmap: str = "viridis",
    ax: plt.Axes | None = None
) -> plt.Axes:
    """Plot spatial map with optional catchment overlay."""

def plot_time_series(
    data: xr.DataArray,
    title: str = "",
    ylabel: str = "",
    ax: plt.Axes | None = None
) -> plt.Axes:
    """Plot time series with proper date formatting."""
```

**Usage:**

```python
from analysis import plot_spatial_map, plot_time_series

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
plot_spatial_map(ds['temperature'].isel(time=0), catchment, ax=ax1)
plot_time_series(basin_avg, title="Basin Average", ax=ax2)
```

### 7. `example_usage.ipynb`

Jupyter notebook demonstrating complete workflow from setup to visualization.

**Notebook Structure:**

1. **Setup**: Install dependencies and import modules
2. **Configuration**: Set paths and Azure credentials
3. **Folder Creation**: Initialize project structure
4. **Data Download**: Download datasets for catchment
5. **Data Loading**: Open and inspect downloaded data
6. **Analysis**: Compute basin averages and anomalies
7. **Visualization**: Create plots and maps

## Azure Storage Connection

### Connection Method

**SAS Token Authentication**

```python
import adlfs
import xarray as xr

# Connect to Azure Blob Storage with SAS token
fs = adlfs.AzureBlobFileSystem(
    account_name="phishes_storage",
    sas_token="YOUR_SAS_TOKEN"
)

# Open Zarr dataset
store = fs.get_mapper("pdp-datasets/climate/temperature/era5_temp.zarr")
ds = xr.open_zarr(store, consolidated=True)
print(ds)
```

### Authentication Best Practices

- Store credentials in environment variables (never hardcode)
- Use `.env` files with `python-dotenv` for local development
- Implement token refresh for long-running processes

**Example with environment variables:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

downloader = PDPDataDownloader(
    catchment_shp="catchment.shp",
    output_base="./project",
    azure_account=os.getenv("AZURE_ACCOUNT"),
    azure_credential=os.getenv("AZURE_SAS_TOKEN")
)
```

## Data Processing Workflow

### Complete Workflow Steps

1. **Initialize Project**
   - User provides catchment shapefile
   - Create standardized folder structure
   - Configure Azure connection

2. **Validate Inputs**
   - Check shapefile validity (geometry, CRS)
   - Verify Azure connection
   - Test catchment extent against dataset coverage

3. **Query Datasets**
   - List available datasets in Azure container
   - Determine which datasets intersect catchment
   - Calculate approximate download size

4. **Download Data**
   - Stream data from Azure blob storage
   - Clip to catchment extent (with optional buffer)
   - Apply temporal filtering if specified
   - Save locally in Zarr/NetCDF/DFS2 format

5. **Log Metadata**
   - Record download timestamp
   - Store provenance information
   - Track dataset versions
   - Document processing parameters

6. **Analysis**
   - Load downloaded datasets
   - Compute basin averages
   - Generate time series
   - Create visualizations

### Implementation Example

```python
from core import create_pdp_folders, PDPDataDownloader
from analysis import load_catchment, compute_catchment_weights, compute_basin_average

# Step 1: Initialize
project_path = create_pdp_folders("./bavaria_study")

# Step 2: Setup downloader
downloader = PDPDataDownloader(
    catchment_shp="data/shp/Bavaria/Areas.shp",
    output_base=project_path,
    azure_account="phishes_storage",
    azure_credential="YOUR_SAS_TOKEN"
)

# Step 3: Download
temp_path = downloader.download_dataset(
    'climate', 'temperature',
    time_range=('2015-01-01', '2020-12-31')
)

# Step 4: Analyze
ds = xr.open_dataset(temp_path)
catchment, _ = load_catchment("data/shp/Bavaria/Areas.shp")
weights = compute_catchment_weights(ds, catchment)
basin_avg = compute_basin_average(ds['t2m'], weights)

# Step 5: Results
print(f"Mean temperature: {float(basin_avg.mean()):.2f} K")
basin_avg.plot()
```

## Technical Requirements

### Python Dependencies

Managed via `pyproject.toml` with `uv` package manager:

```toml
[project]
name = "pdp-task2"
version = "1.0.0"
requires-python = ">=3.9"
dependencies = [
    "xarray>=2023.1.0",
    "zarr>=2.14.0",
    "adlfs>=2023.1.0",
    "geopandas>=0.12.0",
    "shapely>=2.0.0",
    "rasterio>=1.3.0",
    "pyproj>=3.4.0",
    "fsspec>=2023.1.0",
    "mikeio>=1.0.0",
    "pandas>=1.5.0",
    "numpy>=1.23.0",
    "matplotlib>=3.6.0",
]

[project.optional-dependencies]
dev = [
    "jupyter>=1.0.0",
    "ipykernel>=6.20.0",
    "pytest>=7.2.0",
]
```

**Installation:**

```bash
# Basic installation
uv sync --link-mode copy

# With development tools
uv sync --all-extras --link-mode copy
```

### System Requirements

- **Python**: 3.9 or higher
- **RAM**: 2GB minimum, 8GB recommended for large catchments
- **Disk Space**: Varies by catchment size and time range
  - Climate data: ~100-500 MB per year per catchment
  - Soil data: ~50-200 MB per catchment
  - Topography: ~10-100 MB per catchment
- **Network**: Stable internet connection for Azure access
  - Download speed impacts performance
  - Interrupted downloads can be resumed (if implemented)

### Performance Considerations

- **Chunking**: Zarr datasets use optimized chunks for parallel I/O
- **Dask integration**: Future enhancement for large-scale processing
- **Caching**: Local storage reduces repeated Azure requests
- **Parallel downloads**: Not yet implemented (future enhancement)

## Future Enhancements

### Planned Features

- [ ] **Result Viewer Integration**: Folder structure ready for visualization tool
- [ ] **Resume Downloads**: Handle interrupted downloads gracefully
- [ ] **Parallel Downloads**: Download multiple datasets simultaneously
- [ ] **Dataset Versioning**: Track and manage dataset updates
- [ ] **Batch Processing**: Process multiple catchments in one operation
- [ ] **Web Interface**: Browser-based tool for non-programmers
- [ ] **Command Line Tool**: Complete CLI implementation
- [ ] **Data Validation**: Automatic quality checks on downloaded data
- [ ] **Caching Strategy**: Smart caching to avoid redundant downloads
- [ ] **Progress Indicators**: Real-time download progress feedback

### Integration Opportunities

- QGIS plugin for catchment selection
- Integration with MIKE SHE/ECO Lab workflows
- Connection to other PDP modules (Task 1, Task 3, etc.)
- Cloud-based processing pipeline

## Development Notes

### Dataset Storage on Azure

- All source datasets must be in Zarr or NetCDF format (outputs can be NetCDF/Zarr/DFS2)
- Zarr preferred for cloud optimization
- Required metadata:
  - Coordinate reference system (CRS)
  - Variable names and units
  - Temporal extent (for time-series data)
  - Spatial extent and resolution

### European Extent Standards

- **Recommended CRS**: ETRS89 / LAEA Europe (EPSG:3035)
- **Fallback CRS**: WGS84 (EPSG:4326)
- **Coverage**: Approximately 25°W-45°E, 34°N-72°N
- **Resolution**: Variable by dataset (25m to 0.25°)

### Zarr Optimization

- **Chunking strategy**: Balance between spatial and temporal access patterns
  - Time-series access: Larger time chunks
  - Spatial analysis: Larger spatial chunks
- **Compression**: Use zstd or blosc for optimal compression ratio
- **Consolidated metadata**: Always include `.zmetadata` for fast opening
- **Coordinate encoding**: Store coordinates explicitly for clarity

### Testing Considerations

- Test with small catchments first
- Verify CRS transformations for different input CRS
- Check memory usage with long time ranges
- Validate downloaded data integrity
- Test network error handling

## Contact and Support

**Primary Contact**: JLA (Jan Lukas)

For access to:

- Azure storage credentials
- Complete dataset catalog
- Dataset specifications and metadata
- Technical support and questions

**Documentation**:

- [README.md](README.md): User guide and quick start
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md): Implementation status
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md): Common issues and solutions

## References

- **Zarr Format**: https://zarr.readthedocs.io/
- **Xarray**: https://docs.xarray.dev/
- **ADLFS**: https://github.com/fsspec/adlfs
- **GeoPandas**: https://geopandas.org/
- **PHISHES Project**: [TBD - Add project website]

---

**Document Version**: 1.0
**Last Updated**: February 2026
**Status**: Implementation complete, dataset catalog pending JLA confirmation
