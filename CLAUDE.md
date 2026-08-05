# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Before every push, review this file.** Whenever you push (or open a PR), re-read `CLAUDE.md` and check whether the change affects anything it documents — module layout, catalogs, public APIs, commands, conventions, or gotchas. If so, update `CLAUDE.md` in the same change. Keeping it current is part of the task, not an afterthought.

## What this repo does

A two-module pipeline that produces inputs for **DHI MIKE SHE + ECO Lab Plant Growth Module** simulations. End-to-end shape:

```
catchment shp/extent  ─►  data-download-tool  ─►  forcing DFS2 (precip, temp, PET, SSRD)
                                                            │
land-use DFS2 + LU CSV    ┐                                 ▼
soil-profile DFS2 + SP CSV ┼─►     MSHE-Ecolab-PGM       ─►  per-parameter DFS2 maps
parameter template CSVs    ┘     (template_maps)        (LAI_2D.dfs2, RD_2D.dfs2, SOC.dfs2, …)
                                                            │
soil-profile *.txt + preprocessed DFS2 ─► (soil_profile_setup) ─► WP_cell##.dfs2, FC_cell##.dfs2
                                                            │
                                                            ▼
                                                    MIKE SHE / ECO Lab
```

Both modules are independent Python projects (own `pyproject.toml`, `.venv`, tests, notebooks). Notebooks are **orchestrators only** — reusable logic lives in `src/`.

### Repository layout

`data-download-tool/` is shared infrastructure and sits at the repo root. Everything downstream of it is a **model train** and lives under `model-trains/`:

```
data-download-tool/                      # shared: pulls forcing + static layers from the datastore
model-trains/
├── MSHE-Ecolab-PGM/                     # was plant-growth-module/ — the only implemented train
├── MSHE-Daisy/                          # README stub only
└── HYDRUS-PHREEQC-MODFLOW2005-MT3D/     # README stub only
```

**`MSHE-Ecolab-PGM/` was `plant-growth-module/`.** The move was path-only: the Python package inside is still `plant_growth_module`, the distribution is still `plant-growth-module`, and `src/plant_growth_module/` is unchanged. Only the *containing folder* was renamed, so imports and `pyproject.toml` metadata are untouched. When adding a model train, create `model-trains/<train-name>/` as a self-contained project — do not add a second top-level module folder.

## Module 1: `data-download-tool/`

Pulls clipped raster **and vector** subsets from a remote datastore (Azure-backed): Zarr time series, COG static rasters, and GeoParquet static vectors.

- **`src/core/dataset_catalog.yaml`** — source of truth for Zarr (time-series) datasets. Schema: `category → dataset_id → {path, variable, crs, eumtype, eumunit, data_value_type, temporal}`. `eumtype/eumunit` are DHI EUM codes written into DFS2 headers. `data_value_type` is `StepAccumulated` vs `Instantaneous` and drives aggregation. **Adding a dataset = new YAML entry; no code change** unless it introduces a new category with different handling.
- **`src/core/cog_catalog.yaml`** — source of truth for **COG (Cloud Optimized GeoTIFF)** static raster layers, kept separate from the Zarr catalog and merged into it per-category in `_load_catalog()`. COG entries add `format: cog`, `container` (the COG container, e.g. `cogs`), `anon` (public/anonymous read), and `tiled` (`true` ⇒ `path` is a prefix mosaicked over intersecting tiles; `false` ⇒ single `.tif`). They are static (`temporal: false`) and downloaded with `output_format="tif"`. Reader is `src/core/cogio.py` (parallel header/extent reads via GDAL `/vsicurl`, window-read + merge, write COG).
- **`src/core/geoparquet_catalog.yaml`** — source of truth for **GeoParquet (vector)** static layers, also merged per-category in `_load_catalog()`. Entries add `format: geoparquet`, `container` (the vector container, e.g. `geoparquet`), and `anon`. They are static (`temporal: false`) vector data (a `GeoDataFrame`), so they bypass the xarray pipeline entirely: `download_dataset` branches to **`_download_geoparquet`** which reads + clips + writes in one pass. Reader/writer is `src/core/geoparquetio.py` (`open_geoparquet` reads via the fsspec filesystem with optional bbox pushdown, keeps **features intersecting the catchment whole** via the spatial index — no geometry truncation; `write_geoparquet` writes `.parquet` or `.shp`). Downloaded with `output_format="parquet"` or `"shp"` (a raster format falls back to parquet).
- **`src/core/partner_data_catalog.yaml`** — source of truth for **partner / externally-shared open data** delivered as **zip bundles**, also merged per-category in `_load_catalog()`. Entries add `format: zip`, `container: external-shared-open-data` (a public container), and `anon: true`. Contents are mixed/arbitrary (shapefiles, CSVs, Word metadata), so `download_dataset` branches to **`_download_zip`** which copies the `.zip` blob whole and as-is — **no extraction, no catchment clipping**; `output_format` is ignored (always written `.zip`). The whole-blob copy **streams** the blob (`fs.open()` + `shutil.copyfileobj`) on the filesystem from `_dataset_filesystem()` — deliberately *not* `fs.get()`, whose remote path expansion requires *list* permission on the container; streaming keeps a read-only (`sp=r`) SAS token sufficient. A failed copy removes the partial file. **Adding a partner zip = new YAML entry; no code change.** (Blob names may contain spaces — kept verbatim in `path`.) The same file also holds the **`restricted_partner`** category — zip bundles in the SAS-protected `external-shared-after-end` container, with `anon: false` + `credential_env: <ENV_VAR>` (see *Access-restricted datasets* below).
- **Access-restricted datasets** — any catalog entry (any format) may set `credential_env: <ENV_VAR>`. `_dataset_filesystem()` then builds an `adlfs` filesystem from `os.environ[<ENV_VAR>]` (cached per variable in `self._env_fs`) instead of the built-in SAS or anonymous filesystem; `_dataset_credential()` supplies the same token to `_blob_url()` for GDAL/vsicurl. A missing/blank variable raises **`PermissionError`** with the variable name and container, before anything is written — never log the token. `__init__` calls `load_dotenv(find_dotenv(usecwd=True), override=False)`, so tokens come from the nearest `.env` (gitignored; template in `data-download-tool/.env.example`) while exported shell/CI variables win. Restricted entries stay **fully listable** — the name/description are public and the catalog exposes nothing about the contents; only downloading is gated. `dataset_requires_token()` / `is_dataset_accessible()` report lock status without touching the network (the notebook's Step 6 listing marks locked entries 🔒).
- **`src/core/downloader.py`** — `PDPDataDownloader` class. Loads catalog in `__init__`. Key entry point: `download_dataset(category, subcategory, time_range, variables)` → partner zip datasets copy the `.zip` whole via `_download_zip`; geoparquet datasets write `parquet`/`shp` via `_download_geoparquet`; raster datasets write `nc`/`zarr`/`dfs2`/`tif` via open→process→save. Output formats are split into `RASTER_OUTPUT_FORMATS` / `VECTOR_OUTPUT_FORMATS`. Zarr stores are opened via `_open_zarr_store`, which tries consolidated → non-consolidated → `zarr_format=2` and takes the first result exposing data variables (some stores carry both v2 `.zmetadata` and a stray v3 `zarr.json`, which otherwise reads back empty — e.g. `ssebop_eta`).
- **`src/analysis/`** — post-download layer. `catchment.py` loads/validates/reprojects AOI (hard limits: 0.01–500,000 km², ≤1000 features, ≥10% overlap with Europe AOI bbox, points/lines auto-buffered 1 km in EPSG:3035). `timeseries.py` does area-weighted basin averages and anomalies. `visualization.py` has three matplotlib helpers.
- Driven by `notebooks/data_download_tool.ipynb`.

## Module 2: `model-trains/MSHE-Ecolab-PGM/`

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

- **`forcing_generator_native.py`** (`pgm_forcing_generator.ipynb`) — convert local DFS0/CSV time series into DFS2 grids. **One external YAML file defines all forcings** (`sample_data/pgm_forcing_generator/timeseries_inputs.yaml`), loaded via `load_forcing_configs` → `build_forcing_rows` (validation) → `run_forcing_setups` (one DFS2 per forcing; `continue_on_error` turns a failure into a `status: "failed"` result instead of an exception). **There is exactly one config schema** — `timeseries_inputs:` is a *mapping* of forcing name → that forcing's settings (`grid_code_dfs2`, `output_grid`, `item_name`, `eum_type`, `eum_unit`, `inputs`), or → a plain list of series when `defaults:` covers everything else. Anything else (a top-level list, a flat `timeseries_inputs:` list) is rejected with a message showing the expected shape; the earlier `forcings:` list form and `load_timeseries_inputs()` were removed. A `defaults:` block is inherited by every forcing that doesn't override it, and `resolve_forcing` raises naming the forcing + missing fields (`REQUIRED_FORCING_FIELDS`). `output_grid` defaults to `<name>.dfs2` and is joined onto `defaults.output_dir` when relative; `item_name` defaults to the forcing name. **Grid codes present in the grid DFS2 but absent from a forcing are zero-filled** (not an error) — `run_native_setup` reports them in `zero_filled_grid_codes`; only an *empty* input set raises. `resolve_source` is the single place the DFS0-vs-CSV decision is made (extension wins over `source:`), used by both the reader and the validation printout. `normalize_daily_if_needed` snaps sub-daily to midnight if ≥80% of intervals are 23–25 h.
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

`model-trains/MSHE-Ecolab-PGM/pyproject.toml` declares:
```
phishes-data-downloader @ git+https://github.com/DHI/phishes-pdp.git@main#subdirectory=data-download-tool
```
So PGM resolves DDT from **`main` on GitHub**, not from the local sibling folder. After merging a DDT change, PGM users need to re-run `uv sync` to pick it up. For coordinated changes, merge DDT first.

### Legacy facade

`pgm_helper.py` is a flat re-export of everything from the five real modules (`common_utils`, `template_maps`, `soil_profile_setup`, `forcing_repository`, `initial_condition_updater`). Older notebook cells still import from it — keep the re-exports in sync when adding new public names.

## Common commands

All commands run **inside a module directory**, not the repo root.

```powershell
cd data-download-tool                    # or: cd model-trains/MSHE-Ecolab-PGM
uv sync --link-mode copy                # --link-mode copy is required on OneDrive

uv run pytest                            # all tests
uv run pytest tests/test_X.py::test_y    # single test
uv run pytest --cov-report=html          # HTML coverage (PGM)

uv run ruff check .                      # always `uv run`, never a system ruff
uv run ruff format .                     # CI checks this but does not block on it

uv run jupyter notebook notebooks/<name>.ipynb
```

**Always `uv run ruff`, never a bare `ruff`.** Each module pins `ruff==0.16.0` in its dev dependencies; a system-wide ruff is a different version enforcing a different rule set, and will disagree with CI.

### CI contract

Checks are split by what a failure means. **Blocking** — the change is wrong: `Lint and Test (<module>)` (ruff lint + pytest, per module), `File Size Check (10 MB)`, `Secret Scan (trufflehog)`, `Dependency Audit (<module>)` (pip-audit + bandit). **Advisory** — the change is untidy; reported in the job summary, never blocks: `Format (advisory)`, `Markdown Lint (advisory)`, `Notebook Lint (advisory)`. Formatting must not block external contributors.

Three invariants keep the gates honest — breaking any of them reintroduces a class of phantom failure we have already had:

1. **Pin every tool.** `ruff==0.16.0` appears in both `pyproject.toml` files and as the `rev` in `.pre-commit-config.yaml`; bump all three together. Unpinned ruff went from a narrow default rule set to a broad one and turned the module red with no code change.
2. **Never hand-maintain a dependency list in CI.** Jobs run `uv sync`, resolving from `pyproject.toml`. The old `test_deps:` matrix list drifted when geoparquet support added `pyarrow`, failing five tests for an unrelated reason.
3. **`pip-audit --skip-editable`.** Without it, pip-audit looks up the just-installed editable module on PyPI, does not find it, and exits non-zero on every run.
4. **Pin the interpreter.** Each module has a `.python-version` of `3.11`, matching CI, and `requires-python = ">=3.10,<3.14"` matching the range README advertises. The bound is load-bearing: with an unbounded `>=3.10`, a fresh `uv sync` picks the newest interpreter present, and on 3.14 the resolve dies building `fiona` from source (`A GDAL API version must be specified`) because no wheel exists for that ABI.

`pre-commit` is the local mirror of the blocking checks and the only auto-fixer available to fork contributors (fork PRs get a read-only token). There is deliberately **no** auto-format workflow: fixing one would need `pull_request_target`, i.e. a write-token workflow running untrusted fork code.

## Coding conventions (from `.github/agents/*.agent.md`, not enforced by linters)

- Timestamps: `pd.Timestamp`, not `datetime`.
- Paths: `pathlib.Path` everywhere. **Use `Path.joinpath()`, not the `/` operator.** Refactor `/` to `joinpath()` when touching nearby code.
- Every method needs a docstring (one-liner is fine).
- Ruff: line length 100, target py310, `select = ["E","F","W","I","N"]`, `ignore = ["E501","I001"]`. Declared per module in `[tool.ruff]` — DDT and MSHE-Ecolab-PGM match, except MSHE-Ecolab-PGM also ignores `N999` (its stray root `__init__.py` makes ruff read the hyphenated folder name as the top-level module).

## Agent routing (`.github/agents/`)

- `phishes-pdp.agent.md` — root coordinator: cross-module, CI, governance. Delegates to the three below.
- `data-download-tool.agent.md` — DDT source/tests/notebook/catalogs.
- `plant-growth-module.agent.md` — PGM source/tests/notebooks (Workflows A–C).
- `pgm-initial-condition-updater.agent.md` — Workflow D only: `initial_condition_updater.py`, its notebook, tests and design doc.

Prefer the matching agent for module-scoped work.

**Duplicated copies.** DDT and MSHE-Ecolab-PGM each carry a module-scoped copy of their own agent at
`<module>/.github/agents/<name>.agent.md`. The content matches the root copy except that paths are
module-relative instead of repo-relative. They drift easily — update both halves together, and note
that only the root `.github/agents/` copies are picked up repo-wide.

There is also a skill at `.claude/skills/pgm-initial-condition-updater/SKILL.md` covering Workflow D.

## Gotchas

- **DFS2 timestep warning**: mikeio prints `Time step is 0.0 seconds...` for every static-map write. Both `common_utils.py` and `soil_profile_setup.py` have a `_suppress_mikeio_static_timestep_warning()` helper applied via `warnings.catch_warnings()`. Use it when adding new DFS2 write code; don't disable warnings globally.
- **DFS2 axis regularization**: DFS2 grids must be equidistant, but some sources store lat/lon rounded to a few decimals (e.g. `modis_snowcover` on a 0.05° grid), producing occasional off-by-a-decimal steps that mikeio rejects. `utils.regularize_axis` snaps a *near*-equidistant axis (within `rtol` of its median step) to an exact `linspace`; genuinely irregular grids pass through unchanged and still raise. Applied in `dfsio.dfs_from_xr`.
- **Sample data is load-bearing**: tests in both modules read from `<module>/sample_data/`. Don't rename/move without updating fixtures.
- **Direct pushes to `main` are blocked.** PRs require code-owner approval (`@DHI/phishes-maintainers` per `.github/CODEOWNERS`). All *blocking* CI checks must pass; advisory ones (format, markdown, notebook lint) never block.
- **PGM↔DDT runtime import is brittle by design**: probes `core/downloader.py` and `analysis/catchment.py` paths directly. Restructuring DDT's `src/` layout will break PGM's `forcing_repository.py`.
- **Catalog YAML drives behavior, not Python constants**: dataset selection, EUM units, value-accumulation type, and (eventually) PGM forcing routing come from the four catalogs in `src/core/` (`dataset_catalog.yaml`, `cog_catalog.yaml`, `geoparquet_catalog.yaml`, `partner_data_catalog.yaml`), merged per-category at load time. Check them before grepping for hardcoded dataset names.
- **Docs duplicated in two places**: DDT and MSHE-Ecolab-PGM each keep a module-scoped copy of their agent file under `<module>/.github/agents/`. Same content, module-relative paths. Update both halves together.
