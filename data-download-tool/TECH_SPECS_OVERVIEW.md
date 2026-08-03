# PHISHES Data Download Tool - Technical Specification (Overview)

Version: 1.1

## 1. Purpose

The PHISHES Data Download Tool is a Python toolkit for downloading and managing PDP datastore datasets by user-defined catchments. It connects to Azure Blob Storage, subsets datasets spatially (and temporally when applicable), and writes standardized outputs locally.

## 2. Intended Users

- Engineers maintaining the data download pipeline
- Data scientists or analysts running catchment-based downloads and analysis
- Non-technical stakeholders needing a high-level description of system behavior

## 3. System Context

- Data source: Azure Blob Storage, across four data kinds — Zarr time series, COG static rasters, GeoParquet static vectors, and partner zip bundles
- Primary interface: Jupyter notebook workflow
- Outputs: NetCDF, Zarr, DFS2, GeoTIFF, GeoParquet, Shapefile, or verbatim zip, organized in a standardized folder structure
- Logging: JSON download history

## 4. High-Level Architecture

- Core download pipeline: src/core/downloader.py
- Dataset catalogs: src/core/dataset_catalog.yaml (Zarr), cog_catalog.yaml (COG), geoparquet_catalog.yaml (vector), partner_data_catalog.yaml (zip bundles, public and restricted) — merged per-category at load time
- Format readers/writers: src/core/dfsio.py (DFS2), src/core/cogio.py (COG), src/core/geoparquetio.py (GeoParquet)
- Folder structure helpers: src/core/folder_structure.py
- Utilities: src/core/utils.py
- Catchment and analysis utilities: src/analysis/catchment.py, src/analysis/timeseries.py, src/analysis/visualization.py

## 5. Data Flow (Happy Path)

1. User configures catchment and options in the notebook.
2. Catchment is loaded and validated (geometry type, AOI overlap, size checks).
3. Dataset metadata is read from the merged catalog.
4. Azure storage connection is created — the built-in SAS filesystem, an anonymous one for public containers, or one built from the environment variable named by the entry's `credential_env`.
5. The entry's `format` selects one of four paths:
   - **Zarr** (default): open remotely → spatially subset to catchment bounds (optional mask on catchment) → temporal subset if a time range is given and the dataset is temporal → write as NetCDF, Zarr, DFS2, or GeoTIFF.
   - **COG**: read tile headers/extents in parallel, window-read and merge only the tiles intersecting the catchment → write GeoTIFF. Static, so no temporal step.
   - **GeoParquet**: read with optional bbox pushdown, keep every feature intersecting the catchment **whole** (no geometry truncation) → write GeoParquet or Shapefile. Bypasses the xarray pipeline entirely.
   - **Zip bundle**: stream the blob and copy it whole and as-is — no extraction, no clipping, `output_format` ignored. A failed copy removes the partial file.
6. Download log entry is appended to logs/download_log.json.

## 6. Inputs and Outputs

Inputs (configured in notebook):

- catchment: Shapefile path, GeoDataFrame, or manual extent
- output_base: Base directory for output data and logs
- time_range: Optional (start, end) dates for temporal datasets; `None` for static layers
- buffer_cells: Optional integer buffer applied around catchment bounds
- output_format: raster — nc, zarr, dfs2, tif; vector — parquet, shp (a raster format falls back to parquet); ignored for zip bundles
- mask_on_catchment: Boolean to clip to catchment geometry

Outputs:

- `data/{category}/{subcategory}/{subcategory}.{ext}`
- logs/download_log.json

## 7. Configuration and Defaults

- Azure account: phishesdatastore
- Containers: `zarr` (default), `cogs`, `geoparquet`, `external-shared-open-data` (public partner data), `external-shared-after-end` (restricted)
- Default output format: nc
- Default buffer_cells: 1
- Default mask_on_catchment: false

## 8. Dataset Catalog

The catalog is assembled from four YAML files listing datasets by category and subcategory. Common fields:

- path: Azure blob path (a prefix rather than a single object for tiled COGs)
- description and display_name
- variable: primary variable name
- temporal: true or false
- crs: spatial reference
- eumtype and eumunit for DFS2 export
- data_value_type: StepAccumulated or Instantaneous, which drives temporal aggregation

Format-specific fields:

- `format`: omitted or `zarr`, else `cog`, `geoparquet`, or `zip`
- `container`: the Azure container holding the data
- `anon`: true to read the container with anonymous (public) access
- `tiled` (COG only): false ⇒ `path` is one `.tif`; true ⇒ `path` is a prefix mosaicked over intersecting tiles
- `credential_env`: name of the environment variable holding a SAS token for access-restricted entries

Adding a dataset is normally a catalog-only change — a new YAML entry, with no Python edit, unless it introduces a category needing different handling.

## 8a. Access-Restricted Datasets

Any entry may set `credential_env: <ENV_VAR>`. The downloader then builds its filesystem from `os.environ[<ENV_VAR>]` (cached per variable) and supplies the same token to GDAL/vsicurl. A missing or blank variable raises `PermissionError`, naming the variable and container, before anything is written; the token is never logged.

Restricted entries remain **fully listable** — name and description are public and the catalog reveals nothing about the contents. Only downloading is gated. `dataset_requires_token()` and `is_dataset_accessible()` report lock status without touching the network.

Tokens are read from the nearest `.env` (gitignored; see `.env.example`) via `load_dotenv(..., override=False)`, so exported shell and CI variables take precedence. Whole-blob copies stream the blob rather than using `fs.get()`, whose remote path expansion would require *list* permission — streaming keeps a read-only (`sp=r`) token sufficient.

## 9. Logging

- Log file: logs/download_log.json
- Each entry records timestamp, dataset, output path, bounds, time range, and catchment source

## 10. Dependencies

- Geospatial: geopandas, shapely, rasterio, rioxarray, pyproj, fiona
- Data: xarray, zarr, netCDF4, dask, numpy, pandas
- Azure: adlfs, fsspec, azure-storage-blob, azure-identity
- Optional: mikeio for DFS2, matplotlib/cartopy for visualization
- Vector/tabular: pyarrow (GeoParquet), python-dotenv (restricted-dataset tokens)

Dependencies are resolved from pyproject.toml via `uv sync`; there is deliberately no hand-maintained
list anywhere in CI.

## 11. Assumptions and Constraints

- European AOI validation is enforced by default
- Catchment size limits are enforced by default
- Raster datasets are expected to have spatial dimensions named x/y or lon/lat
- Default SAS token is embedded unless overridden; public containers are read anonymously, and restricted entries require their `credential_env` variable
- Zarr stores are opened by trying consolidated → non-consolidated → `zarr_format=2`, taking the first result that exposes data variables (some stores carry both a v2 `.zmetadata` and a stray v3 `zarr.json`, which otherwise reads back empty)
- DFS2 output requires equidistant axes; near-equidistant grids are snapped by `utils.regularize_axis`, and genuinely irregular ones still raise

## 12. Security Considerations

- Default SAS token is embedded in code; production use should move this to environment variables or a secrets store
- Access-restricted entries take their token from the environment variable named by `credential_env`, loaded from the nearest `.env`. `.env` is gitignored and must never be committed; only `.env.example` belongs in git. Tokens are never logged, and a missing token fails before any file is written
- A read-only (`sp=r`) SAS token is sufficient for restricted bundles by design — do not introduce calls that need *list* permission on the container
- Download logs may contain local paths and catchment references

## 13. Known Gaps

- The project scripts in pyproject.toml reference `setup_folder_structure:main` and `download_datasets:main`, but those modules are not in src, so both console entry points are broken
- `[project.urls]` points at `github.com/phishes/data-downloader`, not the actual `github.com/DHI/phishes-pdp`
- The catalog has no top-level `pgm_forcings:` section, so the MSHE-Ecolab forcing-repository path (`load_pgm_forcing_library()`) raises until one is added
