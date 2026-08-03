"""Tests for the native forcing generator's multi-forcing YAML configuration."""

from pathlib import Path

import mikeio
import numpy as np
import pandas as pd
import pytest
import yaml

from plant_growth_module import forcing_generator_native as fgn

MODULE_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CONFIG = MODULE_ROOT.joinpath(
    "sample_data", "pgm_forcing_generator", "timeseries_inputs.yaml"
)


def write_yaml(tmp_path: Path, data: dict | list) -> Path:
    """Dump a config dict/list to a YAML file and return its path."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    cfg_path = tmp_path.joinpath("config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return cfg_path


def make_grid_dfs2(path: Path, codes: np.ndarray) -> Path:
    """Write a single-timestep grid-code DFS2 holding ``codes``."""
    da = mikeio.DataArray(
        data=np.expand_dims(codes.astype(np.float32), axis=0),
        time=pd.DatetimeIndex([pd.Timestamp("2020-01-01")]),
        geometry=mikeio.Grid2D(nx=codes.shape[1], dx=1.0, ny=codes.shape[0], dy=1.0),
        item=mikeio.ItemInfo("grid codes"),
    )
    da.to_dfs(path)
    return path


def make_csv(path: Path, values: list[float]) -> Path:
    """Write a two-column daily time/value CSV."""
    df = pd.DataFrame(
        {
            "time": pd.date_range("2020-01-01", periods=len(values), freq="D"),
            "value": values,
        }
    )
    df.to_csv(path, index=False)
    return path


def test_sample_config_defines_multiple_forcings():
    """The shipped sample config loads as several fully specified forcings."""
    forcings = fgn.load_forcing_configs(MODULE_ROOT, SAMPLE_CONFIG)

    assert len(forcings) >= 2
    names = [f["name"] for f in forcings]
    assert names == sorted(set(names), key=names.index)

    for forcing in forcings:
        resolved = fgn.resolve_forcing(forcing)
        assert Path(str(resolved["grid_code_dfs2"])).name.endswith(".dfs2")
        assert str(resolved["output_grid"]).endswith(".dfs2")
        assert resolved["timeseries_inputs"]


def test_named_mapping_inherits_defaults(tmp_path):
    """Forcings inherit `defaults:` and only override what differs."""
    cfg = write_yaml(
        tmp_path,
        {
            "defaults": {
                "grid_code_dfs2": "grid.dfs2",
                "output_dir": "out",
                "eum_type": "Concentration",
                "eum_unit": "kg_per_meter_pow_3",
            },
            "timeseries_inputs": {
                "var1": {
                    "item_name": "Seed Application Rate",
                    "inputs": [{"grid_code": 1, "path": "a.csv"}],
                },
                "var2": {
                    "output_grid": "custom.dfs2",
                    "eum_unit": "gram_per_meter_pow_3",
                    "inputs": [{"grid_code": 5, "path": "b.csv"}],
                },
            },
        },
    )

    var1, var2 = fgn.load_forcing_configs(MODULE_ROOT, cfg)

    assert var1["name"] == "var1"
    assert var1["item_name"] == "Seed Application Rate"
    assert var1["grid_code_dfs2"] == "grid.dfs2"
    assert Path(var1["output_grid"]) == Path("out").joinpath("var1.dfs2")
    assert var1["eum_unit"] == "kg_per_meter_pow_3"

    assert var2["item_name"] == "var2"
    assert Path(var2["output_grid"]) == Path("out").joinpath("custom.dfs2")
    assert var2["eum_unit"] == "gram_per_meter_pow_3"


def test_named_mapping_accepts_plain_lists(tmp_path):
    """A forcing may be a bare list of timeseries entries."""
    cfg = write_yaml(
        tmp_path,
        {
            "defaults": {"grid_code_dfs2": "grid.dfs2", "eum_type": "Concentration"},
            "timeseries_inputs": {
                "var1": [{"grid_code": 1, "path": "a.csv"}],
                "var2": [{"grid_code": 5, "path": "b.csv", "item": 5}],
            },
        },
    )

    forcings = fgn.load_forcing_configs(MODULE_ROOT, cfg)

    assert [f["name"] for f in forcings] == ["var1", "var2"]
    assert [f["output_grid"] for f in forcings] == ["var1.dfs2", "var2.dfs2"]
    assert forcings[1]["timeseries_inputs"][0]["item"] == 5


def test_config_without_named_forcings_is_rejected(tmp_path):
    """A bare list of timeseries entries is not a valid config any more."""
    list_cfg = write_yaml(tmp_path, [{"grid_code": 1, "path": "a.csv"}])
    with pytest.raises(ValueError, match="mapping of forcing name"):
        fgn.load_forcing_configs(MODULE_ROOT, list_cfg)

    flat_cfg = write_yaml(
        tmp_path.joinpath("flat"), {"timeseries_inputs": [{"grid_code": 1, "path": "a.csv"}]}
    )
    with pytest.raises(ValueError, match="mapping of forcing name"):
        fgn.load_forcing_configs(MODULE_ROOT, flat_cfg)


def test_incomplete_forcing_reports_missing_fields(tmp_path):
    """A forcing missing required fields is reported by name, not silently run."""
    cfg = write_yaml(
        tmp_path,
        {"timeseries_inputs": {"var1": [{"grid_code": 1, "path": "a.csv"}]}},
    )
    (forcing,) = fgn.load_forcing_configs(MODULE_ROOT, cfg)

    with pytest.raises(ValueError, match="var1.*missing required field"):
        fgn.resolve_forcing(forcing)


def test_bad_timeseries_entry_rejected(tmp_path):
    """Timeseries entries still need both grid_code and path."""
    cfg = write_yaml(
        tmp_path,
        {"timeseries_inputs": {"var1": [{"grid_code": 1}]}},
    )

    with pytest.raises(ValueError, match="grid_code' and 'path'"):
        fgn.load_forcing_configs(MODULE_ROOT, cfg)


def test_run_forcing_setups_writes_one_dfs2_per_forcing(tmp_path):
    """Two forcings in one config produce two distinct DFS2 outputs."""
    codes = np.array([[1, 1], [5, 5]], dtype=np.int32)
    make_grid_dfs2(tmp_path.joinpath("grid.dfs2"), codes)
    make_csv(tmp_path.joinpath("a.csv"), [1.0, 2.0, 3.0])
    make_csv(tmp_path.joinpath("b.csv"), [10.0, 20.0, 30.0])

    cfg = write_yaml(
        tmp_path,
        {
            "defaults": {
                "grid_code_dfs2": "grid.dfs2",
                "output_dir": "out",
                "eum_type": "Concentration",
                "eum_unit": "kg_per_meter_pow_3",
            },
            "timeseries_inputs": {
                "var1": {
                    "item_name": "Seed Application Rate",
                    "inputs": [{"grid_code": 1, "path": "a.csv"}],
                },
                "var2": {"inputs": [{"grid_code": 5, "path": "b.csv"}]},
            },
        },
    )

    forcings = fgn.load_forcing_configs(tmp_path, cfg)
    results = fgn.run_forcing_setups(tmp_path, forcings)

    assert [r["status"] for r in results] == ["ok", "ok"]
    assert [r["name"] for r in results] == ["var1", "var2"]

    first = mikeio.read(Path(results[0]["output_grid"]))[0]
    assert first.item.name == "Seed Application Rate"
    # Grid code 1 carries the series; grid code 5 is zero-filled.
    assert first.to_numpy()[0, 0, 0] == pytest.approx(1.0)
    assert first.to_numpy()[0, 1, 0] == pytest.approx(0.0)
    assert results[0]["zero_filled_grid_codes"] == [5]

    second = mikeio.read(Path(results[1]["output_grid"]))[0]
    assert second.item.name == "var2"
    assert second.to_numpy()[0, 1, 0] == pytest.approx(10.0)
    assert second.to_numpy()[0, 0, 0] == pytest.approx(0.0)


def test_run_forcing_setups_continue_on_error(tmp_path):
    """With continue_on_error, a broken forcing is recorded and the rest still run."""
    codes = np.array([[1, 1]], dtype=np.int32)
    make_grid_dfs2(tmp_path.joinpath("grid.dfs2"), codes)
    make_csv(tmp_path.joinpath("a.csv"), [1.0, 2.0])

    cfg = write_yaml(
        tmp_path,
        {
            "defaults": {
                "grid_code_dfs2": "grid.dfs2",
                "output_dir": "out",
                "eum_type": "Concentration",
                "eum_unit": "kg_per_meter_pow_3",
            },
            "timeseries_inputs": {
                "broken": [{"grid_code": 1, "path": "missing.csv"}],
                "good": [{"grid_code": 1, "path": "a.csv"}],
            },
        },
    )

    forcings = fgn.load_forcing_configs(tmp_path, cfg)

    with pytest.raises(Exception):
        fgn.run_forcing_setups(tmp_path, forcings)

    results = fgn.run_forcing_setups(tmp_path, forcings, continue_on_error=True)
    assert [r["status"] for r in results] == ["failed", "ok"]
    assert results[0]["error"]
    assert Path(results[1]["output_grid"]).exists()


def test_build_forcing_rows_flags_missing_files(tmp_path):
    """Validation rows report missing grid and timeseries files without raising."""
    cfg = write_yaml(
        tmp_path,
        {
            "defaults": {
                "grid_code_dfs2": "grid.dfs2",
                "eum_type": "Concentration",
                "eum_unit": "kg_per_meter_pow_3",
            },
            "timeseries_inputs": {"var1": [{"grid_code": 1, "path": "nope.csv"}]},
        },
    )

    (row,) = fgn.build_forcing_rows(tmp_path, fgn.load_forcing_configs(tmp_path, cfg))

    assert row["error"] is None
    assert row["grid_code_dfs2_exists"] is False
    assert row["missing_timeseries_inputs"] == [str(tmp_path.joinpath("nope.csv"))]
