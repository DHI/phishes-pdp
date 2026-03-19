from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plant_growth_module import common_utils
from plant_growth_module import pgm_helper
from plant_growth_module import soil_profile_setup
from plant_growth_module import template_maps


def _write_profile_text(
    path: Path, soil_a: str = "Soil_A", soil_b: str = "Soil_B"
) -> None:
    text = "\n".join(
        [
            f"1 0.10 0.20 {soil_a}",
            "2 0.10 0.20 -",
            f"3 0.10 0.20 {soil_b}",
            "4 0.10 0.20 -",
            "",
            f"Soil name : {soil_a}",
            "Field Capacity pF,psi[m],Th : 2 3 0.31",
            "Wilting Point pF,psi[m],Th : 2 3 0.11",
            "",
            f"Soil name : {soil_b}",
            "Field Capacity pF,psi[m],Th : 2 3 0.41",
            "Wilting Point pF,psi[m],Th : 2 3 0.21",
        ]
    )
    path.write_text(text, encoding="utf-8")


def test_common_utils_suppress_warning_helper_runs():
    common_utils._suppress_mikeio_static_timestep_warning()


def test_soil_normalize_name():
    assert soil_profile_setup._normalize_name("Soil-Name 01") == "soilname01"


def test_extract_grid_code_from_multiple_naming_patterns():
    assert (
        soil_profile_setup._extract_grid_code(Path("PreProcessed_SoilProf12.txt")) == 12
    )
    assert soil_profile_setup._extract_grid_code(Path("profile_7_report.txt")) == 7
    assert soil_profile_setup._extract_grid_code(Path("grid-code_15_result.txt")) == 15


@pytest.mark.parametrize("filename", ["no_index.txt", "profile_x.txt"])
def test_extract_grid_code_raises_without_detectable_number(filename):
    with pytest.raises(ValueError):
        soil_profile_setup._extract_grid_code(Path(filename))


def test_normalize_txt_glob_patterns_default_and_custom():
    assert soil_profile_setup._normalize_txt_glob_patterns(None) == [
        "*SoilProf*.txt",
        "*profile*.txt",
        "*.txt",
    ]
    assert soil_profile_setup._normalize_txt_glob_patterns("*abc*.txt") == ["*abc*.txt"]


def test_find_profile_txt_files_uses_given_pattern(tmp_path):
    a = tmp_path.joinpath("A_SoilProf1.txt")
    b = tmp_path.joinpath("notes.txt")
    a.write_text("x", encoding="utf-8")
    b.write_text("x", encoding="utf-8")

    files, patterns = soil_profile_setup._find_profile_txt_files(
        tmp_path, "*SoilProf*.txt"
    )
    assert patterns == ["*SoilProf*.txt"]
    assert files == [a]


def test_extract_cell_ranges_with_contiguous_same_soil():
    text = "\n".join(
        [
            "1 0.1 0.2 SoilA",
            "2 0.1 0.2 -",
            "3 0.1 0.2 SoilB",
            "4 0.1 0.2 -",
        ]
    )
    assert soil_profile_setup._extract_cell_ranges(text) == [
        ("SoilA", 1, 2),
        ("SoilB", 3, 4),
    ]


def test_extract_properties_by_section_parses_fc_wp_values():
    text = "\n".join(
        [
            "Soil name : SoilA",
            "Field Capacity pF,psi[m],Th : 2 3 0.30",
            "Wilting Point pF,psi[m],Th : 2 3 0.10",
            "Soil name : SoilB",
            "Field Capacity pF,psi[m],Th : 2 3 0.45",
            "Wilting Point pF,psi[m],Th : 2 3 0.20",
        ]
    )
    props = soil_profile_setup._extract_properties_by_section(text)
    assert props["soila"].field_capacity == 0.30
    assert props["soila"].wilting_point == 0.10
    assert props["soilb"].field_capacity == 0.45
    assert props["soilb"].wilting_point == 0.20


def test_parse_soil_profile_text_success(tmp_path):
    txt = tmp_path.joinpath("X_PreProcessed_SoilProf1.txt")
    _write_profile_text(txt)

    grid_code, df = soil_profile_setup.parse_soil_profile_text(txt)
    assert grid_code == 1
    assert list(df.columns) == [
        "cell_index",
        "soil_name",
        "wilting_point",
        "field_capacity",
    ]
    assert df["cell_index"].tolist() == [1, 2, 3, 4]


def test_parse_soil_profile_text_manual_overrides(tmp_path):
    txt = tmp_path.joinpath("X_PreProcessed_SoilProf5.txt")
    _write_profile_text(txt, soil_a="S1", soil_b="S2")

    grid_code, df = soil_profile_setup.parse_soil_profile_text(
        txt,
        manual_cell_ranges_overrides={5: [("S1", 1, 1), ("S2", 2, 2)]},
        manual_property_overrides={5: {"S1": (0.12, 0.32), "S2": (0.22, 0.42)}},
    )
    assert grid_code == 5
    assert df["cell_index"].tolist() == [1, 2]
    assert df["wilting_point"].tolist() == [0.12, 0.22]
    assert df["field_capacity"].tolist() == [0.32, 0.42]


def test_parse_soil_profile_text_raises_when_no_ranges(tmp_path):
    txt = tmp_path.joinpath("X_PreProcessed_SoilProf1.txt")
    txt.write_text("Soil name : SoilA", encoding="utf-8")
    with pytest.raises(ValueError):
        soil_profile_setup.parse_soil_profile_text(txt)


def test_parse_soil_profile_text_raises_on_duplicate_cell_mapping(tmp_path):
    txt = tmp_path.joinpath("X_PreProcessed_SoilProf1.txt")
    _write_profile_text(txt)

    with pytest.raises(ValueError):
        soil_profile_setup.parse_soil_profile_text(
            txt,
            manual_cell_ranges_overrides={1: [("A", 1, 1), ("B", 1, 1)]},
            manual_property_overrides={1: {"A": (0.1, 0.2), "B": (0.2, 0.3)}},
        )


def test_parse_soil_profile_texts_writes_csv(tmp_path):
    f1 = tmp_path.joinpath("Any_SoilProf1.txt")
    f2 = tmp_path.joinpath("Any_SoilProf2.txt")
    _write_profile_text(f1)
    _write_profile_text(f2)

    csv_out = tmp_path.joinpath("profile_table.csv")
    parsed, table, max_cell = soil_profile_setup.parse_soil_profile_texts(
        results_dir=tmp_path,
        soil_profile_txt_glob="*SoilProf*.txt",
        profile_table_csv_path=csv_out,
    )

    assert sorted(parsed.keys()) == [1, 2]
    assert max_cell == 4
    assert not table.empty
    assert csv_out.exists()


def test_parse_soil_profile_texts_raises_when_no_matches(tmp_path):
    with pytest.raises(FileNotFoundError):
        soil_profile_setup.parse_soil_profile_texts(
            results_dir=tmp_path,
            soil_profile_txt_glob="*missing*.txt",
            profile_table_csv_path=tmp_path.joinpath("x.csv"),
        )


def test_build_soil_profile_summary_sets_existence_flags(tmp_path):
    wp = tmp_path.joinpath("wp.dfs2")
    fc = tmp_path.joinpath("fc.dfs2")
    wp.write_text("x", encoding="utf-8")

    output_index = pd.DataFrame(
        [
            {
                "cell_index": 1,
                "wilting_point_dfs2": str(wp),
                "field_capacity_dfs2": str(fc),
            }
        ]
    )
    summary_path = tmp_path.joinpath("summary.csv")
    summary = soil_profile_setup.build_soil_profile_summary(output_index, summary_path)

    assert bool(summary.loc[0, "wp_exists"])
    assert not bool(summary.loc[0, "fc_exists"])
    assert summary_path.exists()


def test_generate_soil_property_dfs2_outputs_success(monkeypatch, tmp_path):
    preprocessed = tmp_path.joinpath("pre.dfs2")
    preprocessed.write_text("x", encoding="utf-8")

    profile_grid = np.array([[1.0, 2.0], [2.0, np.nan]], dtype=np.float32)
    written_paths = []

    class FakeItem:
        def __init__(self, name):
            self.name = name

    class FakeDARead:
        def __init__(self, data):
            self._data = data
            self.time = [pd.Timestamp("2024-01-01")]
            self.geometry = "geom"

        def to_numpy(self):
            return self._data

    class FakeReadDataset:
        def __init__(self, data):
            self.items = [FakeItem("Profile Grid Codes")]
            self._da = FakeDARead(data)

        def __getitem__(self, index):
            assert index == 0
            return self._da

    class FakeWriteDA:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def to_dfs(self, path):
            written_paths.append(Path(path))

    monkeypatch.setattr(
        soil_profile_setup.mikeio, "read", lambda _: FakeReadDataset(profile_grid)
    )
    monkeypatch.setattr(soil_profile_setup.mikeio, "DataArray", FakeWriteDA)
    monkeypatch.setattr(soil_profile_setup.mikeio, "ItemInfo", lambda name: name)

    parsed_by_grid = {
        1: pd.DataFrame(
            {"wilting_point": [0.10, 0.11], "field_capacity": [0.30, 0.31]},
            index=[1, 2],
        ),
        2: pd.DataFrame(
            {"wilting_point": [0.20, 0.21], "field_capacity": [0.40, 0.41]},
            index=[1, 2],
        ),
    }

    output = soil_profile_setup.generate_soil_property_dfs2_outputs(
        preprocessed_dfs2=preprocessed,
        profile_grid_item_hint="Profile Grid",
        parsed_by_grid=parsed_by_grid,
        max_cell_index=2,
        wp_output_dir=tmp_path.joinpath("wp"),
        fc_output_dir=tmp_path.joinpath("fc"),
        output_prefix_wp="wp",
        output_prefix_fc="fc",
        grid_codes_dfs2_path=tmp_path.joinpath("grid_codes.dfs2"),
    )

    assert len(output) == 2
    assert len(written_paths) == 5


def test_generate_soil_property_dfs2_outputs_missing_grid_code(monkeypatch, tmp_path):
    preprocessed = tmp_path.joinpath("pre.dfs2")
    preprocessed.write_text("x", encoding="utf-8")

    profile_grid = np.array([[1.0, 2.0]], dtype=np.float32)

    class FakeItem:
        def __init__(self, name):
            self.name = name

    class FakeDARead:
        def __init__(self, data):
            self._data = data
            self.time = [pd.Timestamp("2024-01-01")]
            self.geometry = "geom"

        def to_numpy(self):
            return self._data

    class FakeReadDataset:
        def __init__(self, data):
            self.items = [FakeItem("Profile Grid Codes")]
            self._da = FakeDARead(data)

        def __getitem__(self, index):
            return self._da

    monkeypatch.setattr(
        soil_profile_setup.mikeio, "read", lambda _: FakeReadDataset(profile_grid)
    )

    with pytest.raises(ValueError):
        soil_profile_setup.generate_soil_property_dfs2_outputs(
            preprocessed_dfs2=preprocessed,
            profile_grid_item_hint="Profile Grid",
            parsed_by_grid={
                1: pd.DataFrame(
                    {"wilting_point": [0.1], "field_capacity": [0.3]}, index=[1]
                )
            },
            max_cell_index=1,
            wp_output_dir=tmp_path.joinpath("wp"),
            fc_output_dir=tmp_path.joinpath("fc"),
            output_prefix_wp="wp",
            output_prefix_fc="fc",
            grid_codes_dfs2_path=tmp_path.joinpath("grid_codes.dfs2"),
        )


def test_generate_soil_property_dfs2_outputs_duplicate_cell_row(monkeypatch, tmp_path):
    preprocessed = tmp_path.joinpath("pre.dfs2")
    preprocessed.write_text("x", encoding="utf-8")

    profile_grid = np.array([[1.0]], dtype=np.float32)

    class FakeItem:
        def __init__(self, name):
            self.name = name

    class FakeDARead:
        def __init__(self, data):
            self._data = data
            self.time = [pd.Timestamp("2024-01-01")]
            self.geometry = "geom"

        def to_numpy(self):
            return self._data

    class FakeReadDataset:
        def __init__(self, data):
            self.items = [FakeItem("Profile Grid Codes")]
            self._da = FakeDARead(data)

        def __getitem__(self, index):
            return self._da

    class FakeWriteDA:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def to_dfs(self, path):
            pass

    monkeypatch.setattr(
        soil_profile_setup.mikeio, "read", lambda _: FakeReadDataset(profile_grid)
    )
    monkeypatch.setattr(soil_profile_setup.mikeio, "DataArray", FakeWriteDA)
    monkeypatch.setattr(soil_profile_setup.mikeio, "ItemInfo", lambda name: name)

    dup = pd.DataFrame(
        {"wilting_point": [0.1, 0.2], "field_capacity": [0.3, 0.4]},
        index=[1, 1],
    )

    with pytest.raises(ValueError):
        soil_profile_setup.generate_soil_property_dfs2_outputs(
            preprocessed_dfs2=preprocessed,
            profile_grid_item_hint="Profile Grid",
            parsed_by_grid={1: dup},
            max_cell_index=1,
            wp_output_dir=tmp_path.joinpath("wp"),
            fc_output_dir=tmp_path.joinpath("fc"),
            output_prefix_wp="wp",
            output_prefix_fc="fc",
            grid_codes_dfs2_path=tmp_path.joinpath("grid_codes.dfs2"),
        )


def test_template_norm_and_type_is_map():
    assert template_maps._norm("  Aa ") == "aa"
    s = pd.Series([1, "1", "true", "map", "0", "no"])
    mask = template_maps._type_is_map(s)
    assert mask.tolist() == [True, True, True, True, False, False]


def test_load_classification_mappings_success(tmp_path):
    lu = tmp_path.joinpath("lu.csv")
    sp = tmp_path.joinpath("sp.csv")

    pd.DataFrame(
        {
            "CODE": [1, 2, 3],
            "CLASS": ["Oak", "Pine", "Grass"],
            "APPLY": [1, 1, 0],
        }
    ).to_csv(lu, index=False)
    pd.DataFrame({"CODE": [10], "CLASS": ["SP1"]}).to_csv(sp, index=False)

    code_to_species, zero_fill, code_to_soilprofile = (
        template_maps.load_classification_mappings(lu, sp, auto_confirm=True)
    )

    assert code_to_species[1] == "Oak"
    assert zero_fill == {"Grass": 0.0}
    assert code_to_soilprofile[10] == "SP1"


def test_load_classification_mappings_raises_on_missing_columns(tmp_path):
    lu = tmp_path.joinpath("lu.csv")
    sp = tmp_path.joinpath("sp.csv")

    pd.DataFrame({"BAD": [1], "CLASS": ["Oak"]}).to_csv(lu, index=False)
    pd.DataFrame({"CODE": [10], "CLASS": ["SP1"]}).to_csv(sp, index=False)

    with pytest.raises(ValueError):
        template_maps.load_classification_mappings(lu, sp, auto_confirm=True)


def test_load_spatial_grids_success_and_shape_mismatch(monkeypatch):
    import mikeio

    data_by_path = {
        "lu.dfs2": np.array([[1, 2], [2, 3]], dtype=np.float32),
        "sp_ok.dfs2": np.array([[10, 11], [11, 12]], dtype=np.float32),
        "sp_bad.dfs2": np.array([[10, 11, 12]], dtype=np.float32),
    }

    class FakeArray:
        def __init__(self, arr):
            self._arr = arr

        def to_numpy(self):
            return self._arr

    class FakeDfs2:
        def __init__(self, path):
            self.path = str(path)

        def read(self):
            return [FakeArray(data_by_path[self.path])]

    monkeypatch.setattr(mikeio, "Dfs2", FakeDfs2)

    lu_ds, lu_data, sp_ds, sp_data = template_maps.load_spatial_grids(
        "lu.dfs2", "sp_ok.dfs2"
    )
    assert lu_data.shape == sp_data.shape
    assert str(lu_ds.path) == "lu.dfs2"
    assert str(sp_ds.path) == "sp_ok.dfs2"

    with pytest.raises(ValueError):
        template_maps.load_spatial_grids("lu.dfs2", "sp_bad.dfs2")


def test_process_template_file_missing_required_columns(tmp_path):
    tpl = tmp_path.joinpath("template.csv")
    pd.DataFrame({"X": [1], "Y": [2]}).to_csv(tpl, index=False)

    count = template_maps.process_template_file(
        template_file=tpl,
        auto_confirm=True,
        output_dir=tmp_path,
        landuse_data=np.array([[1]], dtype=np.float32),
        landuse_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_species={1: "Oak"},
        zero_fill_values={},
        soilprofile_data=np.array([[10]], dtype=np.float32),
        soilprofile_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_soilprofile={10: "SP1"},
    )
    assert count == 0


def test_process_template_file_confirm_rejects(monkeypatch, tmp_path):
    tpl = tmp_path.joinpath("template.csv")
    pd.DataFrame({"SPECIESID": ["Oak"], "CONSTANT": ["LAI_2D"], "VALUE": [5]}).to_csv(
        tpl, index=False
    )

    monkeypatch.setattr(template_maps, "confirm_columns", lambda *args, **kwargs: False)

    count = template_maps.process_template_file(
        template_file=tpl,
        auto_confirm=False,
        output_dir=tmp_path,
        landuse_data=np.array([[1]], dtype=np.float32),
        landuse_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_species={1: "Oak"},
        zero_fill_values={},
        soilprofile_data=np.array([[10]], dtype=np.float32),
        soilprofile_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_soilprofile={10: "SP1"},
    )
    assert count == 0


def test_process_template_file_landuse_and_soilprofile(monkeypatch, tmp_path):
    tpl = tmp_path.joinpath("template.csv")
    pd.DataFrame(
        {
            "SPECIESID": ["Oak", "Pine", "SP1", "SP1"],
            "CONSTANT": ["LAI_2D", "LAI_2D", "SOC", "SOC"],
            "VALUE": [5.0, 4.0, 1.2, 9.9],
            "TEMPLATE": ["landuse", "landuse", "soilprofile", "soilprofile"],
            "TYPE": [1, 1, 1, 0],
        }
    ).to_csv(tpl, index=False)

    calls = []

    def _fake_generate(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(template_maps, "generate_dfs2_map", _fake_generate)

    count = template_maps.process_template_file(
        template_file=tpl,
        auto_confirm=True,
        output_dir=tmp_path,
        landuse_data=np.array([[1, 2]], dtype=np.float32),
        landuse_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_species={1: "Oak", 2: "Pine"},
        zero_fill_values={"Grass": 0.0},
        soilprofile_data=np.array([[10]], dtype=np.float32),
        soilprofile_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_soilprofile={10: "SP1"},
    )

    assert count == 2
    assert len(calls) == 2


def test_process_template_file_unknown_scope_skips(monkeypatch, tmp_path):
    tpl = tmp_path.joinpath("template.csv")
    pd.DataFrame(
        {
            "SPECIESID": ["Oak"],
            "CONSTANT": ["MY_VAR"],
            "VALUE": [1.0],
            "TEMPLATE": ["unknown"],
            "TYPE": [1],
        }
    ).to_csv(tpl, index=False)

    calls = []
    monkeypatch.setattr(
        template_maps, "generate_dfs2_map", lambda *args, **kwargs: calls.append(1)
    )

    count = template_maps.process_template_file(
        template_file=tpl,
        auto_confirm=True,
        output_dir=tmp_path,
        landuse_data=np.array([[1]], dtype=np.float32),
        landuse_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_species={1: "Oak"},
        zero_fill_values={},
        soilprofile_data=np.array([[10]], dtype=np.float32),
        soilprofile_ds=type("Ds", (), {"time": [0], "geometry": "g"})(),
        code_to_soilprofile={10: "SP1"},
    )

    assert count == 0
    assert calls == []


def test_pgm_helper_exports_include_refactored_functions():
    assert hasattr(pgm_helper, "parse_soil_profile_texts")
    assert hasattr(pgm_helper, "process_template_file")
