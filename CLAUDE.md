# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Before every push, review this file.** Whenever you push (or open a PR), re-read `CLAUDE.md` and check whether the change affects anything it documents — module layout, catalogs, public APIs, commands, conventions, or gotchas. If so, update `CLAUDE.md` in the same change. Keeping it current is part of the task, not an afterthought.

## What this repo does

A two-module pipeline that produces inputs for **DHI MIKE SHE + ECO Lab Plant Growth Module** simulations. End-to-end shape:

```
catchment shp/extent  ─►  data-download-tool  ─►  forcing DFS2 (precip, temp, PET, SSRD)
                                                            │
land-use DFS2 + LU CSV    ┐                                 ▼
soil-profile DFS2 + SP CSV ┼─►  plant-growth-module  ─►  per-parameter DFS2 maps
parameter template CSVs    ┘     (template_maps)        (LAI_2D.dfs2, RD_2D.dfs2, SOC.dfs2, …)
                                                            │
soil-profile *.txt + preprocessed DFS2 ─► (soil_profile_setup) ─► WP_cell##.dfs2, FC_cell##.dfs2
                                                            │
                                                            ▼
                                                    MIKE SHE / ECO Lab
```

Both modules are independent Python projects (own `pyproject.toml`, `.venv`, tests, notebooks). Notebooks are **orchestrators only** — reusable logic lives in `src/`.

## Module 1: `data-download-tool/`

Pulls clipped raster **and vector** subsets from a remote datastore (Azure-backed): Zarr time series, COG static rasters, and GeoParquet static vectors.

- **`src/core/dataset_catalog.yaml`** — source of truth for Zarr (time-series) datasets. Schema: `category → dataset_id → {path, variable, crs, eumtype, eumunit, data_value_type, temporal}`. `eumtype/eumunit` are DHI EUM codes written into DFS2 headers. `data_value_type` is `StepAccumulated` vs `Instantaneous` and drives aggregation. **Adding a dataset = new YAML entry; no code change** unless it introduces a new category with different handling.
- **`src/core/cog_catalog.yaml`** — source of truth for **COG (Cloud Optimized GeoTIFF)** static raster layers, kept separate from the Zarr catalog and merged into it per-category in `_load_catalog()`. COG entries add `format: cog`, `container` (the COG container, e.g. `cogs`), `anon` (public/anonymous read), and `tiled` (`true` ⇒ `path` is a prefix mosaicked over intersecting tiles; `false` ⇒ single `.tif`). They are static (`temporal: false`) and downloaded with `output_format="tif"`. Reader is `src/core/cogio.py` (parallel header/extent reads via GDAL `/vsicurl`, window-read + merge, write COG).
- **`src/core/geoparquet_catalog.yaml`** — source of truth for **GeoParquet (vector)** static layers, also merged per-category in `_load_catalog()`. Entries add `format: geoparquet`, `container` (the vector container, e.g. `geoparquet`), and `anon`. They are static (`temporal: false`) vector data (a `GeoDataFrame`), so they bypass the xarray pipeline entirely: `download_dataset` branches to **`_download_geoparquet`** which reads + clips + writes in one pass. Reader/writer is `src/core/geoparquetio.py` (`open_geoparquet` reads via the fsspec filesystem with optional bbox pushdown, keeps **features intersecting the catchment whole** via the spatial index — no geometry truncation; `write_geoparquet` writes `.parquet` or `.shp`). Downloaded with `output_format="parquet"` or `"shp"` (a raster format falls back to parquet).
- **`src/core/downloader.py`** — `PDPDataDownloader` class. Loads catalog in `__init__`. Key entry point: `download_dataset(category, subcategory, time_range, variables)` → raster datasets write `nc`/`zarr`/`dfs2`/`tif` via open→process→save; geoparquet datasets write `parquet`/`shp` via `_download_geoparquet`. Output formats are split into `RASTER_OUTPUT_FORMATS` / `VECTOR_OUTPUT_FORMATS`. Zarr stores are opened via `_open_zarr_store`, which tries consolidated → non-consolidated → `zarr_format=2` and takes the first result exposing data variables (some stores carry both v2 `.zmetadata` and a stray v3 `zarr.json`, which otherwise reads back empty — e.g. `ssebop_eta`).
- **`src/analysis/`** — post-download layer. `catchment.py` loads/validates/reprojects AOI (hard limits: 0.01–500,000 km², ≤1000 features, ≥10% overlap with Europe AOI bbox, points/lines auto-buffered 1 km in EPSG:3035). `timeseries.py` does area-weighted basin averages and anomalies. `visualization.py` has three matplotlib helpers.
- Driven by `notebooks/data_download_tool.ipynb`.

## Module 2: `plant-growth-module/`

Three workflows, three notebooks:

### Workflow A — Template-driven maps (`template_maps.py`, `pgm_initial_condition_dfs2_map_generator.ipynb`)

Maps `species/profile → parameter value → spatial DFS2` via `code_to_species` and `code_to_profile` lookup dicts.

- **`STATE_VARIABLE_SCOPE`** (template_maps.py:20-42) is a **hardcoded dict** routing each variable name to either the `landuse` or `soilprofile` grid. `LAI_2D, RD_2D, BCa_2D…` → landuse. `SOC, NH4, NO3, S_NO3…` → soilprofile. A row's `TEMPLATE` column can override this per-row.
- **Landuse and soilprofile are independent, optional scopes.** Each scope needs a DFS2 grid + a classification CSV; leave a scope's inputs blank (empty string `""`, `None`, or empty `Path`) to skip it, but **at least one scope is required** and a provided scope needs *both* its grid and template (`_is_provided` in template_maps.py gates this). `validate_paths` (now takes optional `soilprofile_dfs2`/`sp_template`), `load_spatial_grids`, and `load_classification_mappings` all skip a missing scope (returning `None` grids / empty mapping dicts); `process_template_file` skips any variable whose scope grid wasn't loaded.
- **Column auto-detection** (`find_col` in common_utils.py:26-31) accepts case-insensitive aliases — `SPECIESID/SPECIES/ID/CLASS`, `VALUE/VAL/AMOUNT`, `CONSTANT/VARIABLE/KEY/NAME/PARAM/PARAMETER`, etc. Lists live at the top of `template_maps.py`. `confirm_columns()` prompts the user unless `AUTO_CONFIRM=True`.
- **`Apply=0` zero-fill**: optional `APPLY` column in `LU_template.csv`. Values `0/false/no/n` force that species to 0 in every landuse-scope map (use for water/urban classes).
- **Soil-profile lookup is fuzzy** (template_maps.py:316-329) — tries normalized name, raw code, `int(code)`, `float(code)`. Lets users mix `SP1`/`1`/`1.0` freely, but means renaming silently can mis-match.
- **`generate_dfs2_map`** (common_utils.py:68-105) is the actual writer. Builds `output_grid` with NumPy masks, wraps in `mikeio.DataArray` with `np.expand_dims(grid, axis=0)` (mikeio requires a time axis even for static maps), suppresses the `Time step is 0.0 seconds` UserWarning.

### Workflow B — Soil profile setup (`soil_profile_setup.py`, `pgm_soil_profile_setup.ipynb`)

MIKE SHE "Task 4". Parses PreProcessor `*.txt` files into per-cell wilting-point / field-capacity DFS2 stacks.

- **Grid code is inferred from filename** (`_extract_grid_code`, lines 45-66) — `SoilProf<N>` preferred, then several fallbacks; filename must contain an identifiable number.
- Parses two sections per text file: a UZ table of `(cell, soil_name)` collapsed into contiguous ranges (lines 99-143), and `Soil name:` / `Field Capacity ... Th: ...` / `Wilting Point ... Th: ...` blocks reading the **Th (theta, volumetric)** column only.
- **Escape hatches**: `manual_cell_ranges_overrides[grid_code]` replaces parsed ranges; `manual_property_overrides[grid_code][soil] = (wp, fc)` replaces parsed values.
- **Hard consistency check** (lines 258-272): refuses to write if any cell ends up with two different soil names or WP/FC values across profiles.
- Output: `grid_codes.dfs2` + `WP_cell##.dfs2` + `FC_cell##.dfs2` for `cell_index = 1..max_cell_index`, plus `profile_table.csv` and `summary.csv`.

### Workflow C — Forcing generation (two paths)

- **`forcing_generator_native.py`** (`pgm_forcing_generator.ipynb`) — convert local DFS0/CSV time series into DFS2 grids. `normalize_daily_if_needed` snaps sub-daily to midnight if ≥80% of intervals are 23–25 h.
- **`forcing_repository.py`** — pulls forcing via `data-download-tool` at runtime. Three-stage import strategy (site-packages → `importlib.metadata`+`direct_url.json` → `sys.path` scan) that loads DDT source into a synthetic `_phishes_data_downloader_runtime` package. **Why it's like this:** DDT's source layout (`src/core/`, `src/analysis/`) is not a proper Python package — there's no `data_download_tool` namespace. `_is_valid_src_root` validates by probing exactly `core/downloader.py` + `analysis/catchment.py`; moving either file will break PGM imports.
- **Requires a `pgm_forcings:` section in DDT's `dataset_catalog.yaml`** that maps PGM forcing keys (precipitation, temperature, …) to DDT `(category, subcategory, source_variable)` plus a target `output_filename`. **As of writing this, the catalog does NOT have that section** — `load_pgm_forcing_library()` will raise until it's added.

### Workflow D — Initial condition updater (`initial_condition_updater.py`, `pgm_initial_condition_updater.ipynb`)

Re-injects a 3D UZ water-quality (WQ) result into a MIKE SHE `.she` (PFS) file as **per-layer 2D initial conditions** for a hotstart. Two stages, both in the one notebook:

1. **Split** (`split_dfs3_to_layers`) — reads a 3D UZ result `.dfs3`, keeps items whose name contains `item_filter` (default `"(matrix phase)"`), and writes one `Layer_<k>.dfs2` per vertical layer (single timestep — int index, default `-1`, or an exact timestamp). **`reverse_z=True` (default)** writes `Layer_1.dfs2` as the *top* of the column (dfs3 layer index `nz-1`), so `.she [Layer_1]` maps **directly** to `Layer_1.dfs2`. The physical dfs2 files are required by the model.
2. **Update** (`update_initial_conditions`) — edits **only** `MIKESHE_FLOWMODEL → Unsatzone → Initial_Conditions → Initial_Concentration → Species_k` (scoped strictly there; `[Layer_N]` names are reused by the Saturated Zone). For every species matched **by name** (dfs2 item `"UZ … (matrix phase), <Name>"` → `Species_k.Name`; only the `UZ concentration`/`UZ fixed(undef)` groups map, giving a 1:1 species↔item mapping), it replaces the `[Layer_N]` sections with one per layer: `DistributionType=1`, all three counters (`MzSEPfsListItemCount`, `NumberOfLayers`, `[Layer_N]` count) set to N, and each layer's `LayerData2DWQ → DFS_2D_DATA_FILE` pointing at `Layer_k.dfs2` (item = the species' 1-based index). Mapping is direct `[Layer_k] ← Layer_k.dfs2`. `LowerLevel` is left at the cloned template's `0` (**unused** for the dfs2-per-layer case — layers map by order, not depth). `FILE_NAME` is written **relative to the output `.she`** as `|.\<stem>_splitted\Layer_k.dfs2|`.

- The layer template is discovered generically (`_find_template_layer` — first species with a `Layer_1` carrying `LowerLevel` + `LayerData2DWQ`), so any matching `.she`/`.dfs3` pair works; no species name is hardcoded.
- `backup_she` writes a timestamped copy of the original before editing (belt-and-braces; the notebook also writes to a *new* `.she`, leaving the input untouched).
- Writing uses **mikeio's `PfsDocument` round-trip** (`mikeio.read_pfs` → mutate → `doc.write`). Verified: only `Initial_Concentration` changes and the file re-reads cleanly. If MIKE SHE ever rejects the reformatted PFS, the fallback is a surgical text-splice (see the plan notes). Installed `mikeio` is 3.x (`PfsDocument` API).

### Cross-module dependency

`plant-growth-module/pyproject.toml` declares:
```
phishes-data-downloader @ git+https://github.com/DHI/phishes-pdp.git@main#subdirectory=data-download-tool
```
So PGM resolves DDT from **`main` on GitHub**, not from the local sibling folder. After merging a DDT change, PGM users need to re-run `uv sync` to pick it up. For coordinated changes, merge DDT first.

### Legacy facade

`pgm_helper.py` is a flat re-export of everything from the five real modules (`common_utils`, `template_maps`, `soil_profile_setup`, `forcing_repository`, `initial_condition_updater`). Older notebook cells still import from it — keep the re-exports in sync when adding new public names.

## Common commands

All commands run **inside a module directory**, not the repo root.

```powershell
cd <module>
uv sync --link-mode copy                # --link-mode copy is required on OneDrive

uv run pytest                            # all tests
uv run pytest tests/test_X.py::test_y    # single test
uv run pytest --cov-report=html          # HTML coverage (PGM)

ruff check .
ruff format --check .                    # CI uses --check; drop it locally to fix

uv run jupyter notebook notebooks/<name>.ipynb
```

CI (`.github/workflows/ci.yml`) on Python 3.11 runs ruff lint + format check + pytest per module, plus repo-wide `markdownlint-cli2` and a 10 MB max-file-size check. Pre-commit is opt-in (`pip install pre-commit && pre-commit install`).

## Coding conventions (from `.github/agents/*.agent.md`, not enforced by linters)

- Timestamps: `pd.Timestamp`, not `datetime`.
- Paths: `pathlib.Path` everywhere. **Use `Path.joinpath()`, not the `/` operator.** Refactor `/` to `joinpath()` when touching nearby code.
- Every method needs a docstring (one-liner is fine).
- Ruff: line length 100, target py310, `select = ["E","F","W","I","N"]`, `ignore = ["E501","I001"]`.

## Agent routing (`.github/agents/`)

- `phishes-pdp.agent.md` — root coordinator: cross-module, CI, governance.
- `data-download-tool.agent.md` — DDT source/tests/notebook.
- `plant-growth-module.agent.md` — PGM source/tests/notebooks.

Prefer the matching agent for module-scoped work.

## Gotchas

- **DFS2 timestep warning**: mikeio prints `Time step is 0.0 seconds...` for every static-map write. Both `common_utils.py` and `soil_profile_setup.py` have a `_suppress_mikeio_static_timestep_warning()` helper applied via `warnings.catch_warnings()`. Use it when adding new DFS2 write code; don't disable warnings globally.
- **DFS2 axis regularization**: DFS2 grids must be equidistant, but some sources store lat/lon rounded to a few decimals (e.g. `modis_snowcover` on a 0.05° grid), producing occasional off-by-a-decimal steps that mikeio rejects. `utils.regularize_axis` snaps a *near*-equidistant axis (within `rtol` of its median step) to an exact `linspace`; genuinely irregular grids pass through unchanged and still raise. Applied in `dfsio.dfs_from_xr`.
- **Sample data is load-bearing**: tests in both modules read from `<module>/sample_data/`. Don't rename/move without updating fixtures.
- **Direct pushes to `main` are blocked.** PRs require code-owner approval (`@DHI/phishes-maintainers` per `.github/CODEOWNERS`). All CI checks must pass.
- **PGM↔DDT runtime import is brittle by design**: probes `core/downloader.py` and `analysis/catchment.py` paths directly. Restructuring DDT's `src/` layout will break PGM's `forcing_repository.py`.
- **Catalog YAML drives behavior, not Python constants**: dataset selection, EUM units, value-accumulation type, and (eventually) PGM forcing routing all come from `dataset_catalog.yaml`. Check it before grepping for hardcoded dataset names.
