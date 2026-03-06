# PHISHES Data Download Tool - Repository Design Specification

Version: 1.0
Date: 2026-02-25
Status: Proposed baseline for subrepository integration

## 1. Purpose

This document defines the design of the `data-download-tool` repository as a **subrepository** of the larger PHISHES platform codebase.

It provides:

- Repository scope and boundaries
- Architectural decomposition and module responsibilities
- Operational workflows and data contracts
- Integration contracts with parent-level orchestration
- Security, reliability, and maintainability constraints

## 2. Subrepository Scope and Boundaries

### In scope

- Catchment-based dataset download from Azure Blob Storage (Zarr source)
- Spatial and optional temporal subsetting
- Output writing to NetCDF, Zarr, or DFS2
- Download logging and minimal project folder scaffolding
- Post-download analysis helpers (weights, basin averages, anomalies, plotting)
- Notebook-first user workflow

### Out of scope

- Parent platform orchestration and workflow scheduling
- Access management and secret rotation infrastructure
- End-user web UI and DSS integration
- Script download feature (documented requirement, not implemented)
- Complex project-run family folder orchestration

## 3. Design Goals

1. **Reproducible catchment downloads** from a controlled dataset catalog
2. **Low-friction usage** through Jupyter and Python API
3. **Storage efficiency** via subsetting before local write
4. **Interoperable outputs** for downstream hydrology/analysis tools
5. **Deterministic filesystem contract** for parent-repository consumers

## 4. System Context

### Upstream dependencies

- Azure Blob Storage account/container with catalog-backed Zarr datasets
- User-provided catchment geometry (file, GeoDataFrame, or manual extent)

### Downstream consumers

- Notebook users and analysis scripts
- Parent repository components that consume files under `data/` and logs under `logs/`

## 5. Architecture Overview

The repository follows a layered Python package structure:

- `src/core`: download pipeline, catalog, I/O, folder and utility primitives
- `src/analysis`: catchment QA/processing and analytics/visualization helpers
- `notebooks`: primary user-facing execution entry point

### Core components

1. `core/downloader.py`
   - `PDPDataDownloader` is the central orchestration class
   - Manages catalog access, Azure connection, processing, writing, and logging
2. `core/dataset_catalog.yaml`
   - Canonical list of supported datasets and metadata (path, variable, CRS, temporal, DFS typing)
3. `core/utils.py`
   - Path construction, format-agnostic open, file lock-safe cleanup, variable inference
4. `core/dfsio.py`
   - Conversion and write bridge from xarray to DFS2 via mikeio
5. `core/folder_structure.py`
   - Creates minimal shared structure (`logs/`, readmes, metadata)

### Analysis components

1. `analysis/catchment.py`
   - Load and validate catchment
   - AOI overlap and area constraints
   - Geometry buffering for points/lines
   - Reprojection and grid-cell intersection weights
2. `analysis/timeseries.py`
   - Area-weighted basin average and anomaly computation
3. `analysis/visualization.py`
   - Catchment, spatial map, and timeseries plotting helpers

## 6. Primary Runtime Flows

### 6.1 Single dataset download

1. Initialize `PDPDataDownloader`
2. Validate catchment and initialize Azure filesystem connection
3. Resolve dataset metadata from catalog
4. Open remote Zarr lazily
5. Spatial subset (bounds or catchment clip)
6. Optional temporal subset
7. Optional variable filtering
8. Write output (`.nc`, `.zarr`, `.dfs2`)
9. Append log entry to `logs/download_log.json`

### 6.2 Batch download

1. Iterate all categories/subcategories from catalog
2. Run single-download flow per dataset
3. Continue on per-dataset failure with error print

### 6.3 Analysis flow (post-download)

1. Open local output (`open_dataset_any`)
2. Compute catchment weights (`compute_catchment_weights`)
3. Compute basin average and anomalies
4. Visualize with plotting helpers

## 7. Data and Storage Contracts

### Input contracts

- Catchment: path, GeoDataFrame, or extent+CRS
- Dataset key: `category/subcategory` from YAML catalog
- Optional: `time_range`, `variables`, output format, masking/buffer options

### Output contracts

- Dataset path pattern: `data/<category>/<subcategory>/<subcategory>.<ext>`
- Log file: `logs/download_log.json`
- Log record fields: timestamp, category, subcategory, description, output_path, bounds, time_range, catchment_shp

### Catalog schema (current)

- `path`, `display_name` (optional in some entries), `description`
- `variable`, `temporal`, `crs`
- `eumtype`, `eumunit` (for DFS2)

## 8. Integration Contract with Parent Repository

This subrepository is designed to be consumed by parent-level orchestration through:

1. **Python API contract**
   - `PDPDataDownloader` for download orchestration
   - Analysis helper functions for optional post-processing
2. **Filesystem contract**
   - Stable output layout under `data/`
   - Stable run history under `logs/download_log.json`
3. **Configuration contract**
   - Parent workflows should pass catchment, output location, dataset keys, and time range
4. **Catalog extension contract**
   - New datasets are introduced by catalog entry additions, not downloader code changes

## 9. Security and Credential Handling

### Current state

- Downloader has default Azure account/container values
- A default SAS credential is embedded as a class constant fallback

### Design requirement for parent integration

- Parent repository should inject credentials via environment or runtime secrets
- Embedded credentials should be treated as temporary development behavior
- Logs should be considered operational metadata and may expose local paths

## 10. Reliability and Error Strategy

- Input validation uses explicit `ValueError`/`FileNotFoundError`
- Azure connection failures are wrapped into `ConnectionError`
- Spatial subset failures return full dataset with warnings
- Existing output deletion uses retry logic for Windows file-lock behavior
- Batch mode isolates per-dataset failures and continues processing

## 11. Performance Characteristics

- Remote Zarr access is lazy through xarray/adlfs
- Spatial slicing reduces transferred data for typical workflows
- Catchment masking and DFS2 conversion are more expensive paths
- Zarr output writes with v2 format and `safe_chunks=False` for compatibility

## 12. Known Gaps and Design Risks

1. `pyproject.toml` script entry points reference modules not present in `src`
2. Script download feature is specified but not implemented
3. Some docs still reference outdated notebook/module paths
4. Embedded default credential creates security and governance risk

## 13. Extension Strategy

Preferred extension order:

1. Externalize credential management
2. Align CLI entry points with implemented modules
3. Implement script registry/download capability with log integration
4. Add automated tests for catchment validation and downloader happy path
5. Introduce parent-repo integration smoke tests using fixture catchments

## 14. Acceptance Criteria for Parent-Level Adoption

The subrepository is considered integration-ready when:

- Parent workflow can call downloader API with explicit credentials
- At least one dataset can be downloaded end-to-end with expected output path
- Download logs are generated and machine-parseable
- Catalog changes can be added without code modification in downloader logic
- Scripted entry points in packaging are either corrected or removed
