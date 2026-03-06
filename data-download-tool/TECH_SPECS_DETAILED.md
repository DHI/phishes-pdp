# PHISHES Data Download Tool - Technical Specification (Detailed)

Version: 1.0
Last Updated: 2026-02-24

## 1. System Overview

The tool downloads datasets from Azure Blob Storage and subsets them by a user-defined catchment. It produces local NetCDF, Zarr, or DFS2 outputs in a standardized folder structure and logs each download.

Primary entry points:

- Notebook workflow (notebooks/data_download_tool.ipynb)
- Python API via core.PDPDataDownloader
- Optional CLI in src/core/downloader.py (module main)

## 2. Module Specifications

### 2.1 src/core/downloader.py

Class: PDPDataDownloader

Constructor

- Parameters:
  - catchment: str | Path | GeoDataFrame
  - output_base: str | Path
  - azure_account: optional str (default phishesdatastore)
  - azure_container: optional str (default zarr)
  - azure_credential: optional str (default SAS token)
  - buffer_cells: int (default 1)
  - output_format: str (default nc)
  - mask_on_catchment: bool (default false)
- Behavior:
  - Validates buffer_cells and output_format
  - Loads dataset catalog from dataset_catalog.yaml
  - Loads or validates catchment
  - Initializes Azure connection and download log

Public methods

- set_output_format(output_format)
  - Validates output_format and updates state
- list_available_datasets()
  - Returns the in-memory dataset catalog
- get_dataset_info(category, subcategory)
  - Returns catalog entry; raises ValueError if missing
- download_dataset(category, subcategory, time_range=None, variables=None)
  - Loads catalog entry
  - Opens remote Zarr via adlfs mapper
  - Spatial subset by catchment bounds or clip to catchment geometry
  - Optional temporal slice if dataset is temporal
  - Optional variable selection
  - Writes output to NetCDF, Zarr (v2), or DFS2
  - Appends log entry
- download_all(time_range=None)
  - Iterates all catalog entries and calls download_dataset

Internal methods

- \_load_catalog()
  - Loads YAML and returns dict
- \_setup_azure_connection(credential=None)
  - Creates adlfs AzureBlobFileSystem and tests connection
- \_load_catchment()
  - Calls analysis.load_catchment with validation defaults
- \_spatial_subset(ds, bounds, catchment_reproj, dataset_crs)
  - Detects spatial dims (x/y or lon/lat)
  - If mask_on_catchment: clip using rioxarray and rename dims back to lat/lon
  - Else: uses bounds with optional buffer_cells expansion
  - Falls back to nearest-neighbor selection when slice yields empty results
- \_temporal_subset(ds, time_range)
  - Finds time dimension and slices by start/end
- \_log_download(...)
  - Appends to logs/download_log.json

CLI (module **main**)

- Arguments:
  - --catchment (required)
  - --output (required)
  - --account, --credential (optional)
  - --dataset (optional category/subcategory)
- Behavior:
  - Downloads a specific dataset or all datasets

### 2.2 src/core/dataset_catalog.yaml

Structure

- Top-level keys: dataset categories (for example climate)
- Second-level keys: subcategory names
- Each dataset entry includes:
  - path (Azure Zarr path)
  - display_name and description
  - variable (primary variable name)
  - temporal (boolean)
  - crs (spatial reference)
  - eumtype and eumunit (for DFS2 export)

### 2.3 src/core/utils.py

Functions

- get_grid_resolution(coords, default=0.1)
  - Returns coordinate spacing or default if insufficient length
- remove_path_with_retry(path, max_retries=5, retry_delays=[0.5,1,2,3,5])
  - Removes files or folders with retry logic for Windows locks
- build_dataset_path(project_base, category, subcategory, output_format="nc")
  - Builds `data/{category}/{subcategory}/{subcategory}.{ext}`
- open_dataset_any(path)
  - Opens Zarr, NetCDF, or DFS2 based on extension
- cleanup_existing_dataset(dataset_path, namespace=None, dataset_var_names=("ds","ds_downloaded"))
  - Closes open datasets, runs GC, and removes existing files
- guess_data_variable(ds, filter_vars=["spatial_ref","crs"])
  - Returns the first non-filtered data variable

### 2.4 src/core/dfsio.py

Functions

- dfs_from_xr(da, varname, eumtype, eumunit, res=None, \*\*kwargs)
  - Converts xarray data to a mikeio.DataArray with Grid2D geometry
- create_file(da, outfile, varname, eumtype, eumunit, \*\*kwargs)
  - Writes a DFS2 file using mikeio

### 2.5 src/core/folder_structure.py

Class: PDPFolderStructure

- Creates and verifies a basic folder structure (default: logs)
- Writes README.md files for leaf folders
- Writes .pdp_metadata.json with project metadata

Functions

- create_pdp_folders(base_path=None, custom_structure=None)
  - Convenience wrapper for structure creation

### 2.6 src/analysis/catchment.py

Functions

- load_catchment(shp_path=None, target_crs=None, merge_features=True, validate_aoi=True, validate_size=True, buffer_points_lines=True, extent=None, extent_crs=None)
  - Loads shapefile or manual extent
  - Validates CRS, AOI overlap, and size limits
  - Buffers points/lines to polygons when requested
  - Optionally merges multiple features
- validate_catchment_gdf(gdf)
  - Minimal validation for a pre-loaded GeoDataFrame
- reproject_catchment(gdf, target_crs)
  - CRS conversion helper
- compute_catchment_weights(ds, catchment_geom, lat_dim="lat", lon_dim="lon")
  - Area-weighted grid cell intersection for basin averages

### 2.7 src/analysis/timeseries.py

Functions

- compute_basin_average(data, weights, lat_dim="lat", lon_dim="lon")
  - Weighted spatial mean; raises when weights are all zeros
- compute_anomalies(data, time_dim="time")
  - Returns anomalies and summary statistics

### 2.8 src/analysis/visualization.py

Functions

- plot_catchment(catchment, ax=None, figsize=(10,8), title="Catchment Boundary", ...)
- plot_spatial_map(data, catchment=None, ax=None, figsize=(12,8), cmap="viridis", ...)
- plot_time_series(data, ax=None, figsize=(12,6), label="Basin Average", ...)

## 3. Data Formats

- Remote storage: Zarr on Azure Blob Storage
- Local outputs: NetCDF (.nc), Zarr (directory), DFS2 (.dfs2)
- Logs: JSON with a downloads array

Log entry schema

- timestamp (ISO string)
- category
- subcategory
- description
- output_path
- bounds (minx, miny, maxx, maxy)
- time_range (optional)
- catchment_shp (path or None)

## 4. Error Handling

- Invalid inputs raise ValueError (catchment size, AOI overlap, format errors)
- Azure connection failures raise ConnectionError with contextual hints
- Spatial subsetting failures fall back to full dataset with warnings

## 5. Performance Considerations

- Uses xarray to slice Zarr and avoids full dataset reads
- Spatial subset uses bounds; mask-on-catchment triggers clip
- Writes Zarr v2 for compatibility; safe_chunks is false to avoid chunk mismatch

## 6. Configuration and Defaults

- Default Azure account, container, and SAS token are baked into the class
- Output format defaults to nc
- buffer_cells defaults to 1
- mask_on_catchment defaults to false

## 7. Dependencies

See pyproject.toml for declared dependencies and versions.

## 8. Known Documentation Gaps

- pyproject.toml scripts reference setup_folder_structure:main and download_datasets:main, but no such modules exist in src
- DataDownloadTool.md references example_usage.ipynb, while README points to notebooks/data_download_tool.ipynb

## 9. Future Enhancements (Optional)

- Externalize Azure credentials via environment variables
- Add unit tests for catchment validation and downloader flows
- Document catalog extension process for new datasets
