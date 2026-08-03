# Initial Condition Updater — design & usage

Durable design note for the PGM **initial condition updater** (Workflow D). Companion to the
code in [`src/plant_growth_module/initial_condition_updater.py`](../src/plant_growth_module/initial_condition_updater.py)
and the notebook [`notebooks/pgm_initial_condition_updater.ipynb`](../notebooks/pgm_initial_condition_updater.ipynb).

## Why

A MIKE SHE **hotstart** needs the 3D UZ water-quality (WQ) state re-injected as **per-layer 2D
initial conditions**. Doing this by hand in MIKE Zero means, for every WQ species and every UZ
computational layer, pointing a `[Layer_N]` section at a 2D DFS2 grid + item — with ~97 species ×
24 layers that is ~2,300 entries. This tool automates it.

## Pipeline

```
3D UZ result (.dfs3)  --split-->  Layer_1.dfs2 .. Layer_N.dfs2
                                          |
template .she (PFS)  --------------------/--> updated .she
   (Unsatzone → Initial_Conditions → Initial_Concentration → Species_k)
```

The notebook runs three steps in one pass: **backup** the original `.she`, **split** the `.dfs3`,
then **update** and write a new `.she`. Any matching `.she`/`.dfs3` pair works — nothing is
hardcoded to a specific model or species.

## Public API

| Function | Purpose |
| --- | --- |
| `split_dfs3_to_layers(dfs3, out_dir, *, item_filter, time, reverse_z)` | Write one `Layer_<k>.dfs2` per vertical layer (single timestep). |
| `backup_she(she_path, *, suffix)` | Timestamped copy of the original `.she`. |
| `build_species_item_index(layer_dfs2, *, groups)` | Map species name → 1-based item index in a layer file. |
| `update_initial_conditions(she_in, she_out, splitted_dir, *, reverse_layer_order, species)` | Inject per-layer ICs and write the new `.she`. Returns a summary dict. |

## Key design decisions

- **Reversal lives in the split.** `split_dfs3_to_layers(reverse_z=True)` writes `Layer_1.dfs2`
  from dfs3 layer index `nz-1` (the **top** of the soil column). Injection is then a trivial
  direct map `[Layer_k] ← Layer_k.dfs2` — "layer_1 receives layer_1.dfs2, to avoid confusion".
  Confirmed against a MIKE Zero example (`[Layer_1] → …layer23`) and by comparing split output to
  the pre-existing files. `update_initial_conditions(reverse_layer_order=…)` is an escape hatch
  only; leave it `False`.
- **Species matched by name.** DFS2 item names look like `"UZ … (matrix phase), <Name>"`. Only the
  `UZ concentration` and `UZ fixed(undef)` groups map to species (the `mass flux` / `external
  source` groups do not). On the reference model this is a clean 1:1 of 97 items ↔ 97 species.
- **`LowerLevel` is not computed.** For the dfs2-per-layer case (`DistributionType = 1`) the layers
  map by order, so the cloned template's `LowerLevel` (Type 0, value 0) is left untouched. This was
  verified against the working `BC1a_2D` example, whose layers also have `LowerLevel = 0`.
- **Scoped edit.** Only `MIKESHE_FLOWMODEL → Unsatzone → Initial_Conditions → Initial_Concentration`
  is touched. `[Layer_N]` names are reused by the Saturated Zone (`GeoLayersSZ`/`CompLayersSZ`);
  those are never modified. A round-trip check confirmed the `SaturatedZone` subtree is unchanged.
- **Three counters kept consistent.** Per updated species, `MzSEPfsListItemCount`, `NumberOfLayers`,
  and the number of `[Layer_N]` sections are all set to N.
- **Each layer is named** `"<species> - Layer <k>"` (the `[Layer_N] → Name` entry) for readability
  in MIKE Zero, replacing the template's generic `'Layer'`.
- **Generic template discovery.** `_find_template_layer` clones the first species with a `Layer_1`
  carrying `LowerLevel` + `LayerData2DWQ`, so no species name is hardcoded.
- **PFS I/O via mikeio.** `mikeio.read_pfs` → mutate the tree → `doc.write`. `FILE_NAME` is written
  relative to the **output** `.she` as `|.\<stem>_splitted\Layer_k.dfs2|`. If MIKE SHE ever rejects
  the reformatted PFS, the fallback is a surgical text-splice at each species' byte range.

## Running it

Open [`notebooks/pgm_initial_condition_updater.ipynb`](../notebooks/pgm_initial_condition_updater.ipynb),
set `DFS3_PATH`, `SHE_INFILE`, `OUTPUT_DIR` (and optionally `TIMESTEP`, `REVERSE_Z`, `SPECIES`),
then Run All. The split files land in `OUTPUT_DIR/<dfs3-stem>_splitted/` and the updated `.she` next
to them. Finally, **open the output `.she` in MIKE Zero / MIKE SHE** to confirm it loads and the WQ
initial conditions render — that is the definitive end-to-end check.

## Tests

`tests/test_initial_condition_updater.py` covers the pure helpers, `build_species_item_index`
group filtering, and `update_initial_conditions` against a minimal in-memory PFS fixture (direct &
reversed order, species filter, missing-section error, backup).
