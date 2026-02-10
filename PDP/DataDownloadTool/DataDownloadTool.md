# Data Download Tool — Copilot Agent Context

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

## Installation

See [README.md](README.md) for installation and environment setup.

## How to Execute the Notebook

See [README.md](README.md) for notebook execution steps in VS Code or Jupyter.

## Project Structure

```
DataDownloadTool/
├── src/
│   ├── core/
│   │   ├── utils.py                # Path helpers and dataset opening
│   │   ├── folder_structure.py     # Folder hierarchy creation
│   │   └── downloader.py           # Azure download functionality
│   ├── analysis/
│   │   ├── catchment.py            # Catchment loading and processing
│   │   ├── timeseries.py           # Time series analysis
│   │   └── visualization.py        # Plotting utilities
│   └── example_usage.ipynb         # Main tutorial notebook
├── data/
│   └── shp/                        # Example shapefiles and templates
├── pyproject.toml                  # Dependencies
├── DataDownloadTool.md             # This agent file
└── README.md                       # User documentation
```

## Configuration

Core configuration is done in the notebook (`src/example_usage.ipynb`). The key values are:

- Catchment input: shapefile path or manual extent
- Azure connection: `azure_account`, `azure_credential` (SAS token), `azure_container`
- Output base path for downloaded data and logs
- Optional buffer distance around catchment (`buffer_km`)
- Dataset selection: category, subcategory, optional time range, optional variable list

## Available Datasets

See [README.md](README.md) for the dataset list and availability. The Azure container layout is:

```
pdp-datasets/
├── climate/
├── soil/
├── topography/
├── landuse/
└── hydrology/
```

## Troubleshooting

See [README.md](README.md) for common issues and fixes (CRS, credentials, missing metadata, etc.).

## Additional Documentation

### Core Behavior

- Catchment input supports Shapefile, GeoJSON, or manual extent
- CRS is automatically reprojected as needed for dataset alignment
- If catchment does not intersect dataset extent, an empty dataset is returned with a warning
- Outputs can be NetCDF, Zarr, or DFS2 (depending on selected output path/format)

### Module Documentation

#### `src/core/utils.py`

- `build_dataset_path(base_path, category, subcategory, extension="nc")`
- `open_dataset_any(path)`

#### `src/core/folder_structure.py`

- `PDPFolderStructure(base_path)`
- `create_all(add_gitkeep=False)`
- `verify()`
- `create_pdp_folders(base_path=".", add_gitkeep=False)`

#### `src/core/downloader.py`

- `PDPDataDownloader(catchment_shp, output_base, azure_account, azure_credential, azure_container="pdp-datasets", buffer_km=5.0)`
- `download_dataset(category, subcategory, time_range=None, variables=None)`
- `download_all(time_range=None)`

#### `src/analysis/catchment.py`

- `load_catchment(shapefile_path, target_crs="EPSG:4326", merge_features=True)`
- `compute_catchment_weights(dataset, catchment)`

#### `src/analysis/timeseries.py`

- `compute_basin_average(data_array, weights)`
- `compute_anomalies(time_series, method="standardized", baseline_period=None)`

#### `src/analysis/visualization.py`

- `plot_catchment(catchment, title="Catchment Boundary", ax=None)`
- `plot_spatial_map(data, catchment=None, title="", cmap="viridis", ax=None)`
- `plot_time_series(data, title="", ylabel="", ax=None)`

## System Requirements

See [README.md](README.md) for system requirements and dependency details.

## Acknowledgments

See [README.md](README.md).

## Support

See [README.md](README.md).

---

**Last Updated**: February 2026
