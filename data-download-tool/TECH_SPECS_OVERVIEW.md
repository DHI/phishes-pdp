# PHISHES Data Download Tool - Technical Specification (Overview)

Version: 1.0
Last Updated: 2026-02-24

## 1. Purpose

The PHISHES Data Download Tool is a Python toolkit for downloading and managing PDP datastore datasets by user-defined catchments. It connects to Azure Blob Storage, subsets datasets spatially (and temporally when applicable), and writes standardized outputs locally.

## 2. Intended Users

- Engineers maintaining the data download pipeline
- Data scientists or analysts running catchment-based downloads and analysis
- Non-technical stakeholders needing a high-level description of system behavior

## 3. System Context

- Data source: Azure Blob Storage (Zarr datasets)
- Primary interface: Jupyter notebook workflow
- Outputs: NetCDF, Zarr, or DFS2 files organized in a standardized folder structure
- Logging: JSON download history

## 4. High-Level Architecture

- Core download pipeline: src/core/downloader.py
- Dataset catalog: src/core/dataset_catalog.yaml
- Folder structure helpers: src/core/folder_structure.py
- Utilities: src/core/utils.py and src/core/dfsio.py
- Catchment and analysis utilities: src/analysis/catchment.py, src/analysis/timeseries.py, src/analysis/visualization.py

## 5. Data Flow (Happy Path)

1. User configures catchment and options in the notebook.
2. Catchment is loaded and validated (geometry type, AOI overlap, size checks).
3. Dataset metadata is read from the catalog.
4. Azure storage connection is created.
5. Dataset is opened remotely from Zarr.
6. Dataset is spatially subset to catchment bounds (optional mask on catchment).
7. Temporal subset is applied if a time range is provided and dataset is temporal.
8. Output is written as NetCDF, Zarr, or DFS2.
9. Download log entry is appended to logs/download_log.json.

## 6. Inputs and Outputs

Inputs (configured in notebook):

- catchment: Shapefile path, GeoDataFrame, or manual extent
- output_base: Base directory for output data and logs
- time_range: Optional (start, end) dates for temporal datasets
- buffer_cells: Optional integer buffer applied around catchment bounds
- output_format: nc, zarr, or dfs2
- mask_on_catchment: Boolean to clip to catchment geometry

Outputs:

- data/<category>/<subcategory>/<subcategory>.<ext>
- logs/download_log.json

## 7. Configuration and Defaults

- Azure account: phishesdatastore
- Azure container: zarr
- Default output format: nc
- Default buffer_cells: 1
- Default mask_on_catchment: false

## 8. Dataset Catalog

The catalog is a YAML file listing datasets by category and subcategory. Each entry includes:

- path: Azure Zarr path
- description and display_name
- variable: primary variable name
- temporal: true or false
- crs: spatial reference
- eumtype and eumunit for DFS2 export

## 9. Logging

- Log file: logs/download_log.json
- Each entry records timestamp, dataset, output path, bounds, time range, and catchment source

## 10. Dependencies

- Geospatial: geopandas, shapely, rasterio, rioxarray, pyproj, fiona
- Data: xarray, zarr, netCDF4, dask, numpy, pandas
- Azure: adlfs, fsspec, azure-storage-blob, azure-identity
- Optional: mikeio for DFS2, matplotlib/cartopy for visualization

## 11. Assumptions and Constraints

- European AOI validation is enforced by default
- Catchment size limits are enforced by default
- Datasets are expected to have spatial dimensions named x/y or lon/lat
- Default SAS token is embedded unless overridden

## 12. Security Considerations

- Default SAS token is embedded in code; production use should move this to environment variables or a secrets store
- Download logs may contain local paths and catchment references

## 13. Known Documentation Gaps

- The project scripts in pyproject.toml reference setup_folder_structure:main and download_datasets:main, but those modules are not in src
- DataDownloadTool.md references example_usage.ipynb, while the README points to notebooks/data_download_tool.ipynb
