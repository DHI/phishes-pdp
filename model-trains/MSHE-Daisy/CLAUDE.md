# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Python research codebase for coupling DAISY (crop/soil model) outputs into a MIKE SHE (integrated hydrological model) simulation via the MShePy API. The Cernici field site in Romania is the primary test case. Coupling covers three water-balance terms:

- **Phase 1 — Runoff**: DAISY `Runoff` → MIKE SHE `OLDR_IN_FLO`
- **Phase 1 — Matrix percolation**: DAISY `Matrix percolation` → MIKE SHE `SZ_LEAK_FLX` + `UZ_WC` correction
- **Phase 3 — Matrix drain flow**: DAISY `Matrix drain flow` → MIKE SHE `SZDR_IN_FLO`

## Environment

Uses [pixi](https://pixi.sh) for dependency and environment management (Windows x64 only). MIKE Zero 2025 must be installed separately; its `bin/x64` path is set via `MIKE_ZERO_X64` in `pixi.toml` activation env.

## Commands

```powershell
# Activate environment
pixi shell

# Run tests
pixi run python -m pytest tests/

# Run a single test file
pixi run python -m pytest tests/test_coupling.py

# Run a single test by name
pixi run python -m pytest tests/test_coupling.py::TestClassName::test_method_name

# Full simulation (requires MIKE Zero + data files)
pixi run python -m src.Test_Cernici

# Smoke test: 10-day run, runoff coupling only (drain disabled)
just runoff-test

# Smoke test: 10-day run, matrix percolation only (runoff + drain disabled)
just percolation-test

# Smoke test: 10-day run, drain coupling only (runoff disabled); plots to docs/investigations/phase3/
just drain-test

# Print resolved configuration without running
pixi run python -m src.Test_Cernici --print-config

# Run an investigation probe (example)
pixi run phase1-runoff-double-count-probe
```

All `pixi run <task>` targets are defined in `pixi.toml`. Investigation probes write JSON artifacts under `docs/investigations/phaseN/`.

## Architecture

### Core simulation loop (`src/Test_Cernici.py`)

Entry point. Calls `ms.wm.performTimeStep()` in a loop, reads the current MIKE SHE time, looks up the matching DAISY interval, applies coupling functions, and calls `ms.wm.setValues(...)` to inject the results back into the running model. Also handles preprocessing (`MShe_Preprocessor.exe`), plugin registration, and diagnostics output.

### Coupling math (`src/coupling.py`)

Pure Python, no MShePy dependency. All unit-conversion, flux-to-flow, and water-content bookkeeping logic lives here. Key types:

- `CouplingRuntimeContext` — frozen dataclass holding dt, cell geometry, theta bounds
- `IntervalCellTransfer` — result of converting a DAISY depth [mm] over an interval to a per-cell flow [m³/s]
- `EffectiveUzCellBookkeepingResult` — result of applying a bounded theta shift to UZ_WC layers

### Spatial mapping (`src/spatial_mapping.py`)

`SpatialMapping` holds a list of `CoupledCellGroup` rectangles (row/col slices) and an index of per-cell metadata. `DEFAULT_SPATIAL_MAPPING` is the hardcoded Cernici footprint (derived from `blocks.py` + drained-cell shapefiles). All coupling functions iterate `DEFAULT_SPATIAL_MAPPING.iter_cell_mappings()` or `iter_drained_cell_mappings()`.

### DAISY I/O (`src/DaisyFunctions.py`)

Reads tab-separated DAISY output CSV files into a `DatetimeIndex` DataFrame. Key function: `findIntervalRowInDaisyResult(df, mshe_time)` — looks up the DAISY interval whose end time is at or after the current MIKE SHE timestep. DAISY timestamps are interval *end* times; interval totals (runoff, percolation, drain flow) must **not** use the legacy `findValueInDaisyResult` interpolation helper.

### Setup preprocessing (`src/setup_overrides.py`)

Generates modified `.she` copies before preprocessing:
- `write_saturated_zone_drain_override_setup` — zeroes native SZ drain to prevent double-counting with Phase 3 coupling
- `write_preprocessed_runoff_coefficient_override` — zeroes OL runoff coefficients in the preprocessed DFS2 for Phase 1 runoff suppression
- `derive_effective_uz_thickness_from_setup` — reads UZ soil profile depths from the `.she` PFS to auto-configure the effective UZ thickness

### Diagnostics (`src/diagnostics.py`, `src/diagnostics_plots.py`)

Per-timestep volume-closure accounting. Two modes: `detailed` (one row per cell per step, good for short runs) and `aggregated` (`VolumeClosureTimeseriesAggregator` — streams per-variable closure without retaining the full table). `write_diagnostics_plots` produces time-series PNGs for requested vs. applied vs. residual volumes.

### 3D SZ layer plotter (`src/plot_3dsz_layers.py`)

Plots per-layer 2D slices of a MIKE SHE DFS3 result file (e.g. `_3DSZflow.dfs3`). Two modes:

- **Single run** — one figure, one row per layer, showing spatial distribution at a selected timestep
- **Cross-run comparison** — two columns (primary vs. LongSim), one row per layer, shared colour scale

When `--setup` is given without `--compare-dfs3`, the LongSim results directory (`<setup> - Result Files - LongSim`) is detected automatically if it exists.

DFS3 data shape from mikeio is `(time, layer, y, x)` — layer 0 is the deepest layer.

```powershell
# List available items
pixi run python src/plot_3dsz_layers.py --dfs3 <path> --list-items

# All layers at last timestep, auto-detect LongSim comparison
pixi run plot-3dsz-crossrun

# Select specific layers and timestep
pixi run python src/plot_3dsz_layers.py --setup <path.she> --layers 0 1 2 --time 2020-08-04

# Explicit paths, all layers
pixi run python src/plot_3dsz_layers.py --dfs3 <primary.dfs3> --compare-dfs3 <longsim.dfs3> --time -1
```

The `--stem-suffix` argument switches between `3DSZflow`, `3DSZ`, and `3DUZ` result files. Axis swap (`swap_groups_for_display`) is applied to the footprint overlay for the same reason as the overland plotter.

### Overland 2D plotter (`src/plot_overland_coupling.py`)

Standalone CLI for plotting MIKE SHE overland DFS2 result files. Three modes:

- **Single timestep** — coupled-footprint mask + padded crop of one item at one timestep
- **Multi-timestep comparison** (`--compare-times`) — side-by-side panels with shared colour scale
- **Cross-run comparison** (`--compare-overland-dfs2 ... --compare-times`) — two-row grid (primary vs. secondary run) at matched dates

```powershell
# List available DFS2 items
pixi run python src/plot_overland_coupling.py --list-items

# Plot last timestep (default)
pixi run python src/plot_overland_coupling.py --overland-dfs2 <path>

# Compare specific dates side by side
pixi run python src/plot_overland_coupling.py --overland-dfs2 <path> --compare-times 2020-08-01 2020-08-04

# Cross-run comparison
pixi run python src/plot_overland_coupling.py --overland-dfs2 <primary> --compare-overland-dfs2 <secondary> --compare-times 2020-08-01 2020-08-04
```

Key detail: `swap_groups_for_display` swaps row/col axes on the coupled footprint overlay before plotting because the DFS2 axis convention differs from the runtime coupling convention. The underlying data is **not** transposed — only the block outlines are.

Output defaults to `docs/investigations/phase1/`. Time selectors accept integer indices (including negative) or ISO date strings.

### Investigations (`src/investigations/`)

One-off diagnostic scripts that probe specific hypotheses. Each writes a JSON artifact and is wired to a `pixi run` task. See `src/investigations/README.md` for conventions. New probes go here; reusable logic goes in `src/`.

## Key conventions

- `DEFAULT_SPATIAL_MAPPING` is the single source of truth for which MIKE SHE cells are coupled. Changing the spatial footprint means editing `src/blocks.py` (group rectangles) and/or `src/spatial_mapping.py` (drained-cell blocks).
- DAISY column names used for coupling: `"Matrix percolation"`, `"Runoff"`, `"Matrix drain flow"`. These must be present in the CSV; `requireDaisyColumn` guards this.
- The `.env` file at repo root can override `MSHE_SETUP`, `DAISY_OUTPUT_CSV`, and `EFFECTIVE_UZ_THICKNESS_M`. CLI args take precedence over env vars.
- Investigation probe outputs are committed under `docs/investigations/phaseN/` as JSON; legacy artifacts at `docs/` root are kept in place.
