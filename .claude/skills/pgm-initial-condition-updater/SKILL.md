---
name: pgm-initial-condition-updater
description: >-
  Use when working on the Plant Growth Module "initial condition updater"
  (Workflow D): splitting a 3D UZ water-quality .dfs3 result into per-layer
  .dfs2 files and injecting them into a MIKE SHE .she (PFS) file as per-layer
  initial conditions. Triggers on ".she", "PFS", "read_pfs", "Initial_Concentration",
  "3D UZ", "hotstart", "Layer_N.dfs2", "split dfs3", or edits to
  initial_condition_updater.py / pgm_initial_condition_updater.ipynb.
---

# PGM Initial Condition Updater

Maintain the workflow that re-injects 3D UZ water-quality (WQ) state into a MIKE SHE `.she` file as
per-layer 2D initial conditions.

## Where the code lives

- Logic: `model-trains/MSHE-Ecolab/src/plant_growth_module/initial_condition_updater.py`
- Notebook (orchestrator): `model-trains/MSHE-Ecolab/notebooks/pgm_initial_condition_updater.ipynb`
- Tests: `model-trains/MSHE-Ecolab/tests/test_initial_condition_updater.py`
- Design note: `model-trains/MSHE-Ecolab/docs/initial_condition_updater.md`
- Facade re-exports: `pgm_helper.py` + `__init__.py` `__all__` (keep in sync)

## Pipeline

`backup_she` → `split_dfs3_to_layers` (writes `Layer_<k>.dfs2`, one per UZ layer, `reverse_z=True`
so `Layer_1` = top of column) → `update_initial_conditions` (edits the PFS, writes a new `.she`).

## Must-know invariants

- **Edit scope is strict**: only `MIKESHE_FLOWMODEL → Unsatzone → Initial_Conditions →
  Initial_Concentration → Species_k`. Never touch the Saturated Zone, which reuses `[Layer_N]`
  names (`GeoLayersSZ`/`CompLayersSZ`).
- **Reversal is handled in the split**, not the injection. Keep `Layer_1.dfs2` = top so injection is
  a direct `[Layer_k] ← Layer_k.dfs2`. `update_initial_conditions(reverse_layer_order=…)` is an
  escape hatch only.
- **Species match by name**: DFS2 item `"UZ … (matrix phase), <Name>"` → `Species_k.Name`. Only the
  `UZ concentration` / `UZ fixed(undef)` groups map (see `DEFAULT_SPECIES_ITEM_GROUPS`).
- **Do not compute `LowerLevel`** — for `DistributionType = 1` (dfs2-per-layer) layers map by order;
  the cloned template's `LowerLevel = 0` is correct.
- **Keep three counters consistent** per species: `MzSEPfsListItemCount`, `NumberOfLayers`, and the
  `[Layer_N]` count (all = N).
- **`FILE_NAME`** is a literal `|.\rel\path.dfs2|` clob, relative to the **output** `.she`.
- **Template discovery is generic** (`_find_template_layer`); do not hardcode a species like
  `Species_2`.

## Conventions (repo-wide)

`pathlib.Path` with `.joinpath()` (not `/`); `pd.Timestamp` for timestamps; docstring on every
function; ruff line length 100. Notebooks stay orchestrators — put logic in `src/`.

## Verify

```powershell
cd model-trains/MSHE-Ecolab
uv run pytest tests/test_initial_condition_updater.py
uvx ruff check . ; uvx ruff format --check .
```

Round-trip sanity: after `doc.write`, `mikeio.read_pfs(out)` must succeed and the `SaturatedZone`
subtree (`to_dict()`) must be unchanged. Definitive check: open the output `.she` in MIKE Zero.
mikeio ≥ 3.x provides the `PfsDocument` API; the installed version is pinned in `uv.lock`.
