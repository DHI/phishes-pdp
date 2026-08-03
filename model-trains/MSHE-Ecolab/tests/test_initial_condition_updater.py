from pathlib import Path

import mikeio
import pytest

from plant_growth_module import initial_condition_updater as icu
from plant_growth_module import pgm_helper


# A minimal MIKE SHE PFS with the UZ WQ initial-condition skeleton: one species
# with no layers (Alpha) and one that already carries a template layer (Beta).
MINI_SHE = """[MIKESHE_FLOWMODEL]
   [Unsatzone]
      [Initial_Conditions]
         [Initial_Concentration]
            [Species_1]
               Name = 'Alpha'
               DistributionType = 0
               Distribution_UniformValue = 0.0
               MzSEPfsListItemCount = 0
               NumberOfLayers = 0
            EndSect  // Species_1
            [Species_2]
               Name = 'Beta'
               DistributionType = 0
               Distribution_UniformValue = 5.0
               MzSEPfsListItemCount = 1
               NumberOfLayers = 1
               [Layer_1]
                  Name = 'Layer'
                  [LowerLevel]
                     FixedValue = 0
                     Type = 0
                     RelativeToGround = 0
                  EndSect  // LowerLevel
                  [LayerData2DWQ]
                     FixedValue = 0
                     Type = 1
                     [DFS_2D_DATA_FILE]
                        FILE_NAME = |.\\old.dfs2|
                        ITEM_COUNT = 1
                        ITEM_NUMBERS = 1
                     EndSect  // DFS_2D_DATA_FILE
                  EndSect  // LayerData2DWQ
               EndSect  // Layer_1
            EndSect  // Species_2
         EndSect  // Initial_Concentration
      EndSect  // Initial_Conditions
   EndSect  // Unsatzone
EndSect  // MIKESHE_FLOWMODEL
"""


def _write_mini_she(tmp_path: Path) -> Path:
    path = tmp_path.joinpath("mini.she")
    path.write_text(MINI_SHE, encoding="utf-8")
    return path


def _conc(doc):
    return doc.MIKESHE_FLOWMODEL.Unsatzone.Initial_Conditions.Initial_Concentration


# --- pure helpers -----------------------------------------------------------


def test_layer_index_parses_number():
    assert icu._layer_index(Path("Layer_1.dfs2")) == 1
    assert icu._layer_index(Path("Layer_24.dfs2")) == 24
    assert icu._layer_index(Path("layer 7.dfs2")) == 7


def test_layer_index_raises_without_number():
    with pytest.raises(ValueError):
        icu._layer_index(Path("Layer.dfs2"))


def test_normalize_time_selector_wraps_scalars_and_keeps_lists():
    assert icu._normalize_time_selector(-1) == [-1]
    assert icu._normalize_time_selector("2020-08-31") == ["2020-08-31"]
    assert icu._normalize_time_selector([0, 1]) == [0, 1]


def test_ordered_layer_files_sorts_numerically(tmp_path):
    for k in (2, 10, 1):
        tmp_path.joinpath(f"Layer_{k}.dfs2").write_text("x", encoding="utf-8")
    files = icu._ordered_layer_files(tmp_path)
    assert [icu._layer_index(f) for f in files] == [1, 2, 10]


def test_ordered_layer_files_raises_when_empty(tmp_path):
    with pytest.raises(FileNotFoundError):
        icu._ordered_layer_files(tmp_path)


def test_relative_file_name_builds_clob(tmp_path):
    out = tmp_path.joinpath("out.she")
    dfs2 = tmp_path.joinpath("splitted", "Layer_3.dfs2")
    assert icu._relative_file_name(dfs2, out) == "|.\\splitted\\Layer_3.dfs2|"


# --- build_species_item_index ----------------------------------------------


def test_build_species_item_index_filters_groups(monkeypatch, tmp_path):
    class FakeItem:
        def __init__(self, name):
            self.name = name

    class FakeDfs2:
        def __init__(self, _path):
            self.items = [
                FakeItem("UZ concentration (matrix phase), Bentazone"),
                FakeItem("UZ fixed(undef) (matrix phase), BC1a_2D"),
                FakeItem("UZ mass flux (matrix phase), Bentazone"),
            ]

    monkeypatch.setattr(icu.mikeio, "Dfs2", FakeDfs2)
    index = icu.build_species_item_index(tmp_path.joinpath("Layer_1.dfs2"))
    assert index == {"Bentazone": 1, "BC1a_2D": 2}


def test_build_species_item_index_concentration_wins_duplicate(monkeypatch, tmp_path):
    class FakeItem:
        def __init__(self, name):
            self.name = name

    class FakeDfs2:
        def __init__(self, _path):
            # NH4 appears in both included groups; concentration must win.
            self.items = [
                FakeItem("UZ fixed(undef) (matrix phase), NH4"),
                FakeItem("UZ concentration (matrix phase), NH4"),
            ]

    monkeypatch.setattr(icu.mikeio, "Dfs2", FakeDfs2)
    index = icu.build_species_item_index(tmp_path.joinpath("Layer_1.dfs2"))
    assert index == {"NH4": 2}  # the concentration item, despite fixed coming first


# --- update_initial_conditions ----------------------------------------------


def _patch_layers(monkeypatch, tmp_path, item_index, n=3):
    splitted = tmp_path.joinpath("sd")
    splitted.mkdir(exist_ok=True)
    files = [splitted.joinpath(f"Layer_{k}.dfs2") for k in range(1, n + 1)]
    monkeypatch.setattr(icu, "_ordered_layer_files", lambda _: list(files))
    monkeypatch.setattr(icu, "build_species_item_index", lambda _: dict(item_index))
    return splitted


def test_update_direct_order_all_species(monkeypatch, tmp_path):
    infile = _write_mini_she(tmp_path)
    splitted = _patch_layers(monkeypatch, tmp_path, {"Alpha": 3, "Beta": 7})
    out = tmp_path.joinpath("out.she")

    summary = icu.update_initial_conditions(infile, out, splitted)
    assert summary["n_layers"] == 3
    assert sorted(summary["species_updated"]) == ["Alpha", "Beta"]

    conc = _conc(mikeio.read_pfs(out))
    alpha = conc.Species_1
    assert alpha.NumberOfLayers == 3
    assert alpha.MzSEPfsListItemCount == 3
    assert alpha.DistributionType == 1
    layer_keys = [k for k in alpha.keys() if k.startswith("Layer_")]
    assert layer_keys == ["Layer_1", "Layer_2", "Layer_3"]
    df = alpha.Layer_1.LayerData2DWQ.DFS_2D_DATA_FILE
    assert df.ITEM_NUMBERS == 3
    assert df.FILE_NAME == "|.\\sd\\Layer_1.dfs2|"
    assert alpha.Layer_1.Name == "Alpha - Layer 1"
    assert alpha.Layer_3.Name == "Alpha - Layer 3"
    assert (
        alpha.Layer_3.LayerData2DWQ.DFS_2D_DATA_FILE.FILE_NAME
        == "|.\\sd\\Layer_3.dfs2|"
    )
    # LowerLevel is left at the template's unused zero.
    assert alpha.Layer_1.LowerLevel.FixedValue == 0


def test_update_reversed_order(monkeypatch, tmp_path):
    infile = _write_mini_she(tmp_path)
    splitted = _patch_layers(monkeypatch, tmp_path, {"Beta": 7})
    out = tmp_path.joinpath("out.she")

    icu.update_initial_conditions(infile, out, splitted, reverse_layer_order=True)

    beta = _conc(mikeio.read_pfs(out)).Species_2
    assert (
        beta.Layer_1.LayerData2DWQ.DFS_2D_DATA_FILE.FILE_NAME == "|.\\sd\\Layer_3.dfs2|"
    )
    assert (
        beta.Layer_3.LayerData2DWQ.DFS_2D_DATA_FILE.FILE_NAME == "|.\\sd\\Layer_1.dfs2|"
    )


def test_update_species_filter_leaves_others_untouched(monkeypatch, tmp_path):
    infile = _write_mini_she(tmp_path)
    splitted = _patch_layers(monkeypatch, tmp_path, {"Alpha": 3, "Beta": 7})
    out = tmp_path.joinpath("out.she")

    summary = icu.update_initial_conditions(infile, out, splitted, species=["Beta"])
    assert summary["species_updated"] == ["Beta"]

    conc = _conc(mikeio.read_pfs(out))
    assert conc.Species_1.NumberOfLayers == 0  # Alpha untouched
    assert conc.Species_2.NumberOfLayers == 3


def test_update_raises_on_missing_section(monkeypatch, tmp_path):
    infile = tmp_path.joinpath("bad.she")
    infile.write_text(
        "[MIKESHE_FLOWMODEL]\nEndSect  // MIKESHE_FLOWMODEL\n", encoding="utf-8"
    )
    splitted = _patch_layers(monkeypatch, tmp_path, {"Alpha": 1})
    with pytest.raises(KeyError):
        icu.update_initial_conditions(infile, tmp_path.joinpath("out.she"), splitted)


# --- backup + facade --------------------------------------------------------


def test_backup_she_creates_timestamped_copy(tmp_path):
    original = tmp_path.joinpath("model.she")
    original.write_text("data", encoding="utf-8")
    backup = icu.backup_she(original)
    assert backup.exists()
    assert backup != original
    assert backup.read_text(encoding="utf-8") == "data"
    assert backup.suffix == ".she"


def test_pgm_helper_exports_initial_condition_updater():
    assert hasattr(pgm_helper, "split_dfs3_to_layers")
    assert hasattr(pgm_helper, "update_initial_conditions")
    assert hasattr(pgm_helper, "backup_she")
    assert hasattr(pgm_helper, "build_species_item_index")
