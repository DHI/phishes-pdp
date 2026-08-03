"""MIKE SHE initial-condition updater for 3D UZ water-quality (WQ) state.

Wires the per-layer 2D grids of a 3D UZ WQ result into a MIKE SHE ``.she`` (PFS)
file as spatial initial conditions. End-to-end shape:

    3D UZ result (.dfs3)  --split-->  Layer_1.dfs2 .. Layer_N.dfs2
                                              |
    template .she (PFS)  --------------------/--> updated .she
        (Unsatzone -> Initial_Conditions -> Initial_Concentration -> Species_k)

For each WQ species and each UZ computational layer a ``[Layer_N]`` section is
created that points ``LayerData2DWQ -> DFS_2D_DATA_FILE`` at the matching
``Layer_N.dfs2`` file + item. A single ``[Layer_N]`` is cloned from the first
well-formed layer already in the file (``DistributionType = 1``), whose
``LowerLevel`` is left at ``0`` (unused for the dfs2-per-layer case; layers map
by order).
"""

import os
from pathlib import Path
import re
import shutil
import warnings

import mikeio
import pandas as pd

from .common_utils import _suppress_mikeio_static_timestep_warning

# PFS section path to the UZ WQ initial concentrations. Editing is scoped
# strictly here: [Layer_N] names are reused by the Saturated Zone.
_INITIAL_CONCENTRATION_PATH = (
    "MIKESHE_FLOWMODEL",
    "Unsatzone",
    "Initial_Conditions",
    "Initial_Concentration",
)

# dfs3 item-name groups that correspond 1:1 to WQ species (by the name after
# the last comma). Other groups (mass flux, external sources) are excluded.
DEFAULT_SPECIES_ITEM_GROUPS = (
    "UZ concentration (matrix phase)",
    "UZ fixed(undef) (matrix phase)",
)

# Sub-sections a usable [Layer_N] template must contain.
_LAYER_TEMPLATE_KEYS = ("LowerLevel", "LayerData2DWQ")


def _normalize_time_selector(time):
    """Wrap a single timestep selector in a list, passing a list/tuple through.

    Accepts an integer step index (e.g. ``-1`` for the last step) or an exact
    timestep as a ``str``/``pd.Timestamp``/``datetime`` (e.g. ``"2020-08-31"``).
    Keeping a length-1 time axis makes the written DFS2 single-step.
    """
    if isinstance(time, (list, tuple)):
        return list(time)
    return [time]


def _layer_index(path: Path) -> int:
    """Return the integer N encoded in a ``Layer_<N>.dfs2`` filename."""
    m = re.search(r"layer[_\s]*(\d+)", path.stem, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    raise ValueError(
        f"Could not infer a layer number from file name '{path.name}'. "
        "Expected a name like 'Layer_3.dfs2'."
    )


def split_dfs3_to_layers(
    dfs3_path,
    out_dir,
    *,
    item_filter="(matrix phase)",
    time=-1,
    reverse_z=True,
):
    """Split a 3D UZ result into one ``Layer_<k>.dfs2`` per vertical layer.

    Items whose name contains ``item_filter`` are kept. With ``reverse_z=True``
    ``Layer_1.dfs2`` holds the *top* of the soil column (dfs3 layer index
    ``nz - 1``), so downstream ``.she`` ``[Layer_1]`` maps directly to
    ``Layer_1.dfs2``. With ``reverse_z=False`` the original order is kept
    (``Layer_{i+1}.dfs2`` <- dfs3 layer index ``i``).

    ``time`` selects a single timestep: an integer step index (default ``-1``,
    the last step) or an exact timestep as ``str``/``pd.Timestamp``/``datetime``.
    """
    dfs3_path = Path(dfs3_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dfs3 = mikeio.Dfs3(dfs3_path)
    items = [item.name for item in dfs3.items if item_filter in item.name]
    if not items:
        raise ValueError(
            f"No items matching '{item_filter}' found in {dfs3_path.name}."
        )

    nz = dfs3.geometry.nz
    written: list[Path] = []
    for k in range(1, nz + 1):
        layer_index = (nz - k) if reverse_z else (k - 1)
        ds = dfs3.read(
            items=items, layers=[layer_index], time=_normalize_time_selector(time)
        )
        out_path = out_dir.joinpath(f"Layer_{k}.dfs2")
        with warnings.catch_warnings():
            _suppress_mikeio_static_timestep_warning()
            ds.to_dfs(out_path)
        written.append(out_path)
        print(f"  📁 Layer_{k}.dfs2  <- dfs3 layer index {layer_index}")

    return written


def backup_she(she_path, *, suffix="orig"):
    """Copy a ``.she`` file to a timestamped sibling backup and return its path."""
    she_path = Path(she_path)
    stamp = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    backup_path = she_path.with_name(
        f"{she_path.stem}.{suffix}-{stamp}{she_path.suffix}"
    )
    shutil.copy2(she_path, backup_path)
    print(f"  💾 Backed up original .she -> {backup_path.name}")
    return backup_path


def build_species_item_index(layer_dfs2_path, *, groups=DEFAULT_SPECIES_ITEM_GROUPS):
    """Map species name -> 1-based item index within a ``Layer_<k>.dfs2`` file.

    Item names look like ``"UZ fixed(undef) (matrix phase), BC1a_2D"``; the group
    is the text before the first comma and the species name the text after the
    last comma. Only items whose group is in ``groups`` are included.

    A species may appear in more than one group (e.g. Bentazone/NH4/NO3/DO exist
    as both ``UZ concentration`` and ``UZ mass flux``/``External sources``). When
    a name is present in several *included* groups, the earlier entry in
    ``groups`` wins, so ``UZ concentration`` takes priority over ``UZ fixed``.
    """
    dfs2 = mikeio.Dfs2(Path(layer_dfs2_path))
    group_priority = {group: rank for rank, group in enumerate(groups)}

    index: dict[str, int] = {}
    chosen_priority: dict[str, int] = {}
    for item_number, item in enumerate(dfs2.items, start=1):
        name = item.name
        group = name.split(",", 1)[0].strip()
        if group not in group_priority:
            continue
        species_name = name.rsplit(",", 1)[-1].strip()
        priority = group_priority[group]
        if species_name not in index or priority < chosen_priority[species_name]:
            index[species_name] = item_number
            chosen_priority[species_name] = priority
    return index


def _ordered_layer_files(splitted_dir):
    """Return ``Layer_<k>.dfs2`` files in ascending layer-number order."""
    splitted_dir = Path(splitted_dir)
    files = sorted(splitted_dir.glob("Layer_*.dfs2"), key=_layer_index)
    if not files:
        raise FileNotFoundError(
            f"No 'Layer_*.dfs2' files found in {splitted_dir}. "
            "Run split_dfs3_to_layers first."
        )
    return files


def _relative_file_name(dfs2_path: Path, she_outfile: Path) -> str:
    """Build the ``|.\\rel\\path.dfs2|`` FILE_NAME clob relative to the output .she."""
    out_dir = she_outfile.parent.resolve()
    try:
        rel = dfs2_path.resolve().relative_to(out_dir)
    except ValueError:
        rel = Path(os.path.relpath(dfs2_path.resolve(), out_dir))
    rel_str = str(rel).replace("/", "\\")
    return f"|.\\{rel_str}|"


def _get_conc_section(doc):
    """Navigate to the Initial_Concentration PFS section (raising if absent)."""
    section = doc
    for key in _INITIAL_CONCENTRATION_PATH:
        try:
            section = getattr(section, key)
        except AttributeError as exc:
            raise KeyError(
                "Could not find PFS section "
                f"{' -> '.join(_INITIAL_CONCENTRATION_PATH)}: missing '{key}'. "
                "Is this a MIKE SHE .she with UZ water-quality initial conditions?"
            ) from exc
    return section


def _find_template_layer(conc):
    """Return a copy of the first well-formed ``[Layer_1]`` to use as a template.

    Scans the ``Species_*`` sections for one whose ``Layer_1`` carries both a
    ``LowerLevel`` and a ``LayerData2DWQ`` sub-section, so the updater does not
    depend on a specific species being present in a given ``.she``.
    """
    for section_key in conc.keys():
        species_section = getattr(conc, section_key)
        layer = getattr(species_section, "Layer_1", None)
        if layer is None:
            continue
        if all(key in layer.keys() for key in _LAYER_TEMPLATE_KEYS):
            return layer.copy()
    raise ValueError(
        "No existing [Layer_1] with LowerLevel + LayerData2DWQ was found to use "
        "as a template. Define at least one layered species in the .she first."
    )


def update_initial_conditions(
    she_infile,
    she_outfile,
    splitted_dir,
    *,
    reverse_layer_order=False,
    species=None,
):
    """Inject per-layer WQ initial conditions into a MIKE SHE ``.she`` file.

    For every species matched by name between the split ``Layer_*.dfs2`` items
    and the PFS ``Initial_Concentration`` section, replaces its ``[Layer_N]``
    sections with one per layer (``DistributionType = 1``) pointing at the
    matching layer file + item. Mapping is direct (``[Layer_k] <- Layer_k.dfs2``)
    unless ``reverse_layer_order=True``. Only species in ``species`` (a list of
    names) are touched when that argument is given. Writes ``she_outfile`` and
    returns a summary dict.
    """
    she_infile = Path(she_infile)
    she_outfile = Path(she_outfile)
    she_outfile.parent.mkdir(parents=True, exist_ok=True)

    layer_files = _ordered_layer_files(splitted_dir)
    n_layers = len(layer_files)
    species_item_index = build_species_item_index(layer_files[0])
    species_filter = set(species) if species is not None else None

    doc = mikeio.read_pfs(she_infile)
    conc = _get_conc_section(doc)
    template_layer = _find_template_layer(conc)

    # Precompute the FILE_NAME clob for each .she layer position (1..n_layers).
    file_names: dict[int, str] = {}
    for k in range(1, n_layers + 1):
        source = (
            layer_files[n_layers - k] if reverse_layer_order else layer_files[k - 1]
        )
        file_names[k] = _relative_file_name(source, she_outfile)

    updated: list[str] = []
    for section_key in list(conc.keys()):
        species_section = getattr(conc, section_key)
        name = getattr(species_section, "Name", None)
        if name is None or name not in species_item_index:
            continue
        if species_filter is not None and name not in species_filter:
            continue

        item_number = species_item_index[name]

        # Drop any existing layer sections, then set the three counters.
        for layer_key in [
            k for k in list(species_section.keys()) if k.startswith("Layer_")
        ]:
            species_section.pop(layer_key)
        species_section.DistributionType = 1
        species_section.NumberOfLayers = n_layers
        species_section.MzSEPfsListItemCount = n_layers

        for k in range(1, n_layers + 1):
            layer = template_layer.copy()
            layer.Name = f"{name} - Layer {k}"
            data = layer.LayerData2DWQ
            data.Touched = 1
            data.IsDataUsedInSetup = 1
            data.Type = 1
            data_file = data.DFS_2D_DATA_FILE
            data_file.Touched = 1
            data_file.IsDataUsedInSetup = 1
            data_file.FILE_NAME = file_names[k]
            data_file.ITEM_COUNT = 1
            data_file.ITEM_NUMBERS = item_number
            species_section[f"Layer_{k}"] = layer

        updated.append(name)

    doc.write(she_outfile)

    matched_species = set(species_item_index)
    all_species_names = {
        getattr(getattr(conc, key), "Name", None) for key in conc.keys()
    }
    summary = {
        "outfile": str(she_outfile),
        "n_layers": n_layers,
        "species_updated": updated,
        "n_species_updated": len(updated),
        "items_without_species": sorted(matched_species - all_species_names),
    }
    print(
        f"  ✅ Updated {len(updated)} species x {n_layers} layers -> {she_outfile.name}"
    )
    return summary
