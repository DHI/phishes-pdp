from pathlib import Path

import numpy as np
import xarray as xr

from src.core import dfsio


def _sample_dataarray():
    return xr.DataArray(
        np.ones((1, 2, 2), dtype=float),
        dims=("time", "lat", "lon"),
        coords={"time": [0], "lat": [50.0, 50.5], "lon": [8.0, 8.5]},
        name="rain",
    )


def test_dfs_from_xr_uses_dataset_variable(monkeypatch):
    da = _sample_dataarray()
    ds = da.to_dataset(name="rain")

    captured = {}

    class FakeGrid2D:
        def __init__(self, **kwargs):
            captured["grid"] = kwargs

    class FakeDataArray:
        def __init__(self, **kwargs):
            captured["da"] = kwargs

    monkeypatch.setattr(dfsio.mikeio, "DataArray", FakeDataArray)
    monkeypatch.setattr(dfsio.mikeio.spatial, "Grid2D", FakeGrid2D)
    monkeypatch.setattr(dfsio, "ItemInfo", lambda *args: ("item",) + args)

    result = dfsio.dfs_from_xr(ds, "rain", eumtype="Precipitation_Rate", eumunit="mm_per_hour")
    assert isinstance(result, FakeDataArray)
    assert "x" in captured["grid"] and "y" in captured["grid"]


def test_create_file_writes_output(monkeypatch, tmp_path):
    da = _sample_dataarray()
    out = tmp_path / "maps" / "x.dfs2"
    called = {}

    class FakeDfsDA:
        def to_dfs(self, path: Path):
            called["path"] = path

    monkeypatch.setattr(dfsio, "dfs_from_xr", lambda *args, **kwargs: FakeDfsDA())

    dfsio.create_file(
        da,
        out,
        varname="rain",
        eumtype=dfsio.EUMType.Precipitation_Rate,
        eumunit=dfsio.EUMUnit.mm_per_hour,
    )

    assert called["path"] == out
    assert out.parent.exists()
