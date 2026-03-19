from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plant_growth_module import common_utils
from plant_growth_module import pgm_helper
from plant_growth_module import forcing_repository


def test_find_col_case_insensitive():
    df = pd.DataFrame({"Code": [1], "SpeciesId": ["A"]})
    assert pgm_helper.find_col(df, ["CODE"]) == "Code"
    assert pgm_helper.find_col(df, ["CLASS"]) is None


def test_confirm_columns_auto_confirm():
    assert (
        pgm_helper.confirm_columns(
            {"Code column": "CODE"}, auto_confirm=True, context="x"
        )
        is True
    )


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

    monkeypatch.setattr(common_utils.mikeio, "DataArray", FakeDA)
    monkeypatch.setattr(common_utils.mikeio, "ItemInfo", lambda name: ("item", name))

    output = tmp_path.joinpath("map.dfs2")
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
    mapping, zero_classes = pgm_helper.split_lu_mapping_by_apply(
        df, "CODE", "CLASS", "APPLY"
    )
    assert mapping[1] == "A"
    assert "B" in zero_classes


def test_validate_paths(tmp_path):
    landuse = tmp_path.joinpath("landuse.dfs2")
    lu = tmp_path.joinpath("lu.csv")
    tpl1 = tmp_path.joinpath("tpl1.csv")
    output = tmp_path.joinpath("out")

    landuse.write_text("x", encoding="utf-8")
    lu.write_text("x", encoding="utf-8")
    tpl1.write_text("x", encoding="utf-8")

    errors = pgm_helper.validate_paths(landuse, lu, [tpl1], output)
    assert errors == []
    assert output.exists()

    errors2 = pgm_helper.validate_paths(Path("missing.dfs2"), lu, [tpl1], output)
    assert len(errors2) >= 1


def test_build_forcing_download_plan(monkeypatch):
    forcing_library = {
        "precipitation": {
            "item_name": "Precipitation Rate",
            "item_unit": "mm/d",
            "ts_type": "Mean Step Accumulated",
            "category": "climate",
            "subcategory": "era5_precipitation",
            "source_variable": "tp",
            "output_filename": "Precipitation.dfs2",
            "required": True,
        },
        "soil_temperature": {
            "item_name": "Temperature",
            "item_unit": "degC",
            "ts_type": "Mean Step Accumulated",
            "category": "climate",
            "subcategory": "era5_soil_temperature",
            "source_variable": "stl1",
            "output_filename": "Soil_Temperature.dfs2",
            "required": True,
        },
    }

    monkeypatch.setattr(
        forcing_repository,
        "load_data_downloader_catalog",
        lambda: {
            "climate": {
                "era5_precipitation": {"variable": "tp"},
                "era5_temperature": {"variable": "t2m"},
                "era5_surface_solar_radiation_downwards": {"variable": "ssrd"},
                "era5_potential_evapotranspiration": {"variable": "pev"},
            }
        },
    )
    monkeypatch.setattr(
        forcing_repository,
        "load_pgm_forcing_library",
        lambda: forcing_library,
    )

    plan = forcing_repository.build_forcing_download_plan()
    assert "precipitation" in plan["available"]
    assert "soil_temperature" in plan["missing"]


def test_download_forcing_dfs2_series(monkeypatch, tmp_path):
    class DummyDownloader:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.base = Path(kwargs["output_base"])

        def download_dataset(
            self, category, subcategory, time_range=None, variables=None
        ):
            out = self.base.joinpath(
                "data", category, subcategory, f"{subcategory}.dfs2"
            )
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(f"{subcategory}:{time_range}:{variables}", encoding="utf-8")
            return out

    forcing_library = {
        "precipitation": {
            "item_name": "Precipitation Rate",
            "item_unit": "mm/d",
            "ts_type": "Mean Step Accumulated",
            "category": "climate",
            "subcategory": "era5_precipitation",
            "source_variable": "tp",
            "output_filename": "Precipitation.dfs2",
            "required": True,
        },
        "air_temperature": {
            "item_name": "Temperature",
            "item_unit": "degC",
            "ts_type": "Mean Step Accumulated",
            "category": "climate",
            "subcategory": "era5_temperature",
            "source_variable": "t2m",
            "output_filename": "Air_Temperature.dfs2",
            "required": True,
        },
    }

    monkeypatch.setattr(
        forcing_repository,
        "build_forcing_download_plan",
        lambda include_optional=False: {
            "available": {
                "precipitation": forcing_library["precipitation"],
                "air_temperature": forcing_library["air_temperature"],
            },
            "missing": {},
        },
    )
    monkeypatch.setattr(
        forcing_repository,
        "get_data_downloader_classes",
        lambda: (DummyDownloader, lambda extent, crs: {"extent": extent, "crs": crs}),
    )

    result = forcing_repository.download_forcing_dfs2_series(
        output_base=tmp_path.joinpath("out"),
        time_range=("2015-01-01", "2015-01-03"),
        extent=[10.0, 55.0, 11.0, 56.0],
        strict_required=True,
    )

    assert "precipitation" in result["downloaded"]
    assert result["standardized"]["air_temperature"].exists()


def test_download_forcing_dfs2_series_strict_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        forcing_repository,
        "build_forcing_download_plan",
        lambda include_optional=False: {
            "available": {},
            "missing": {"soil_temperature": {"reason": "missing"}},
        },
    )

    with pytest.raises(ValueError):
        forcing_repository.download_forcing_dfs2_series(
            output_base=tmp_path.joinpath("out"),
            time_range=("2015-01-01", "2015-01-03"),
            extent=[10.0, 55.0, 11.0, 56.0],
            strict_required=True,
        )
