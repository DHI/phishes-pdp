from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plant_growth_module import pgm_helper


def test_find_col_case_insensitive():
    df = pd.DataFrame({"Code": [1], "SpeciesId": ["A"]})
    assert pgm_helper.find_col(df, ["CODE"]) == "Code"
    assert pgm_helper.find_col(df, ["CLASS"]) is None


def test_confirm_columns_auto_confirm():
    assert pgm_helper.confirm_columns({"Code column": "CODE"}, auto_confirm=True, context="x") is True


def test_confirm_columns_user_paths(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    assert pgm_helper.confirm_columns({"Code": "CODE"}) is True

    monkeypatch.setattr("builtins.input", lambda _: "no")
    assert pgm_helper.confirm_columns({"Code": "CODE"}, multi_files=True) is False

    monkeypatch.setattr("builtins.input", lambda _: "no")
    with pytest.raises(RuntimeError):
        pgm_helper.confirm_columns({"Code": "CODE"}, multi_files=False)


def test_generate_dfs2_map(monkeypatch, tmp_path):
    landuse_data = np.array([[1, 2], [2, 3]])

    class DummyDs:
        time = [0]
        geometry = "geom"

    called = {}

    class FakeDA:
        def __init__(self, **kwargs):
            called["kwargs"] = kwargs

        def to_dfs(self, output_path):
            called["output"] = output_path

    monkeypatch.setattr(pgm_helper.mikeio, "DataArray", FakeDA)
    monkeypatch.setattr(pgm_helper.mikeio, "ItemInfo", lambda name: ("item", name))

    output = tmp_path / "map.dfs2"
    pgm_helper.generate_dfs2_map(
        landuse_data=landuse_data,
        landuse_ds=DummyDs(),
        code_to_species={1: "A", 2: "B", 3: "C"},
        species_values={"A": 10, "B": 20},
        default_species_values={"C": 30},
        output_path=output,
        variable_name="LAI",
    )

    assert called["output"] == output
    assert called["kwargs"]["data"].shape == (1, 2, 2)


def test_split_lu_mapping_by_apply():
    df = pd.DataFrame({"CODE": [1, 2], "CLASS": ["A", "B"], "APPLY": [1, 0]})
    mapping, zero_classes = pgm_helper.split_lu_mapping_by_apply(df, "CODE", "CLASS", "APPLY")
    assert mapping[1] == "A"
    assert "B" in zero_classes


def test_validate_paths(tmp_path):
    landuse = tmp_path / "landuse.dfs2"
    lu = tmp_path / "lu.csv"
    tpl1 = tmp_path / "tpl1.csv"
    output = tmp_path / "out"

    landuse.write_text("x", encoding="utf-8")
    lu.write_text("x", encoding="utf-8")
    tpl1.write_text("x", encoding="utf-8")

    errors = pgm_helper.validate_paths(landuse, lu, [tpl1], output)
    assert errors == []
    assert output.exists()

    errors2 = pgm_helper.validate_paths(Path("missing.dfs2"), lu, [tpl1], output)
    assert len(errors2) >= 1
