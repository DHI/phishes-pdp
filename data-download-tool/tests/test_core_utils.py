from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from src.core import utils


def test_get_grid_resolution_with_array():
    coords = np.array([1.0, 1.25, 1.5])
    assert utils.get_grid_resolution(coords) == pytest.approx(0.25)


def test_get_grid_resolution_default_for_single_value():
    assert utils.get_grid_resolution(np.array([42.0]), default=0.5) == 0.5


def test_remove_path_with_retry_missing_path(tmp_path):
    assert utils.remove_path_with_retry(tmp_path / "does-not-exist") is False


def test_remove_path_with_retry_file(tmp_path):
    file_path = tmp_path / "x.txt"
    file_path.write_text("abc", encoding="utf-8")
    assert utils.remove_path_with_retry(file_path, max_retries=1) is True
    assert not file_path.exists()


def test_build_dataset_path_lowercases_format():
    path = utils.build_dataset_path("base", "climate", "precip", "NC")
    assert path == Path("base") / "data" / "climate" / "precip" / "precip.nc"


def test_open_dataset_any_zarr(monkeypatch, tmp_path):
    zarr_dir = tmp_path / "ds.zarr"
    zarr_dir.mkdir()

    called = {}

    def fake_open_zarr(path, consolidated=True):
        called["args"] = (path, consolidated)
        return "zarr_ds"

    monkeypatch.setattr(utils.xr, "open_zarr", fake_open_zarr)
    result = utils.open_dataset_any(zarr_dir)
    assert result == "zarr_ds"
    assert called["args"] == (zarr_dir, True)


def test_open_dataset_any_netcdf(monkeypatch, tmp_path):
    nc_file = tmp_path / "a.nc"
    nc_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(utils.xr, "open_dataset", lambda p, engine=None: (p, engine))
    assert utils.open_dataset_any(nc_file) == (nc_file, "netcdf4")


def test_open_dataset_any_dfs2(monkeypatch, tmp_path):
    class FakeReadResult:
        def to_xarray(self):
            return xr.Dataset({"v": (("y", "x"), np.ones((1, 1)))})

    monkeypatch.setattr(utils.mikeio, "read", lambda p: FakeReadResult())
    dfs_file = tmp_path / "a.dfs2"
    dfs_file.write_text("", encoding="utf-8")

    ds = utils.open_dataset_any(dfs_file)
    assert "lat" in ds.dims and "lon" in ds.dims


def test_open_dataset_any_unsupported(tmp_path):
    bad = tmp_path / "a.txt"
    bad.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        utils.open_dataset_any(bad)


def test_cleanup_existing_dataset_closes_and_removes(monkeypatch, tmp_path):
    called = {"closed": False, "removed": False}

    class Dummy:
        def close(self):
            called["closed"] = True

    monkeypatch.setattr(
        utils, "remove_path_with_retry", lambda _: called.__setitem__("removed", True) or True
    )

    utils.cleanup_existing_dataset(tmp_path / "anything", namespace={"ds": Dummy()})
    assert called["closed"]
    assert called["removed"]


def test_guess_data_variable_default_filter():
    ds = xr.Dataset(
        {
            "spatial_ref": ((), 1),
            "rain": ("x", np.array([1.0])),
            "temp": ("x", np.array([2.0])),
        }
    )
    assert utils.guess_data_variable(ds) == "rain"


def test_guess_data_variable_raises_for_non_dataset():
    with pytest.raises(ValueError):
        utils.guess_data_variable(np.array([1, 2, 3]))
