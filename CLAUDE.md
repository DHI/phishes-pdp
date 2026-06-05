# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

Pulls clipped raster subsets from a remote Zarr datastore (Azure-backed).

- **`src/core/dataset_catalog.yaml`** — source of truth for Zarr (time-series) datasets. Schema: `category → dataset_id → {path, variable, crs, eumtype, eumunit, data_value_type, temporal}`. `eumtype/eumunit` are DHI EUM codes written into DFS2 headers. `data_value_type` is `StepAccumulated` vs `Instantaneous` and drives aggregation. **Adding a dataset = new YAML entry; no code change** unless it introduces a new category with different handling.
- **`src/core/cog_catalog.yaml`** — source of truth for **COG (Cloud Optimized GeoTIFF)** static raster layers, kept separate from the Zarr catalog and merged into it per-category in `_load_catalog()`. COG entries add `format: cog`, `container` (the COG container, e.g. `cogs`), `anon` (public/anonymous read), and `tiled` (`true` ⇒ `path` is a prefix mosaicked over intersecting tiles; `false` ⇒ single `.tif`). They are static (`temporal: false`) and downloaded with `output_format="tif"`. Reader is `src/core/cogio.py` (parallel header/extent reads via GDAL `/vsicurl`, window-read + merge, write COG).
- **`src/core/downloader.py`** — `PDPDataDownloader` class. Loads catalog in `__init__`. Key entry point: `download_dataset(category, subcategory, time_range, variables)` → writes to disk in `nc`/`zarr`/`dfs2`.
- **`src/analysis/`** — post-download layer. `catchment.py` loads/validates/reprojects AOI (hard limits: 0.01–500,000 km², ≤1000 features, ≥10% overlap with Europe AOI bbox, points/lines auto-buffered 1 km in EPSG:3035). `timeseries.py` does area-weighted basin averages and anomalies. `visualization.py` has three matplotlib helpers.
- Driven by `notebooks/data_download_tool.ipynb`.

## Module 2: `plant-growth-module/`

Three workflows, three notebooks:

### Workflow A — Template-driven maps (`template_maps.py`, `plant_growth_module.ipynb`)

Maps `species/profile → parameter value → spatial DFS2` via `code_to_species` and `code_to_profile` lookup dicts.

- **`STATE_VARIABLE_SCOPE`** (template_maps.py:20-42) is a **hardcoded dict** routing each variable name to either the `landuse` or `soilprofile` grid. `LAI_2D, RD_2D, BCa_2D…` → landuse. `SOC, NH4, NO3, S_NO3…` → soilprofile. A row's `TEMPLATE` column can override this per-row.
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

### Cross-module dependency

`plant-growth-module/pyproject.toml` declares:
```
phishes-data-downloader @ git+https://github.com/DHI/phishes-pdp.git@main#subdirectory=data-download-tool
```
So PGM resolves DDT from **`main` on GitHub**, not from the local sibling folder. After merging a DDT change, PGM users need to re-run `uv sync` to pick it up. For coordinated changes, merge DDT first.

### Legacy facade

`pgm_helper.py` is a flat re-export of everything from the four real modules. Older notebook cells still import from it — keep the re-exports in sync when adding new public names.

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
- **Sample data is load-bearing**: tests in both modules read from `<module>/sample_data/`. Don't rename/move without updating fixtures.
- **Direct pushes to `main` are blocked.** PRs require code-owner approval (`@DHI/phishes-maintainers` per `.github/CODEOWNERS`). All CI checks must pass.
- **PGM↔DDT runtime import is brittle by design**: probes `core/downloader.py` and `analysis/catchment.py` paths directly. Restructuring DDT's `src/` layout will break PGM's `forcing_repository.py`.
- **Catalog YAML drives behavior, not Python constants**: dataset selection, EUM units, value-accumulation type, and (eventually) PGM forcing routing all come from `dataset_catalog.yaml`. Check it before grepping for hardcoded dataset names.
