import numpy as np
import pytest
import rasterio
import xarray as xr
from rasterio.transform import from_bounds

from src.core import cogio


def _write_tif(path, value=1.0, bounds=(0.0, 0.0, 1.0, 1.0), width=4, height=4):
    """Write a tiny single-band GeoTIFF for tests."""
    transform = from_bounds(*bounds, width, height)
    data = np.full((1, height, width), value, dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)
    return path


def test_open_cog_single_file(tmp_path):
    local = str(_write_tif(tmp_path / "clc.tif", value=7.0))

    ds = cogio.open_cog([local], variable="landcover", crs="EPSG:4326")

    assert "landcover" in ds.data_vars
    assert ds.rio.crs.to_epsg() == 4326
    assert float(ds["landcover"].max()) == pytest.approx(7.0)


def test_open_cog_single_file_windows_to_bbox(tmp_path):
    # 10x10 raster over (0,0,10,10); request a small bbox and expect a windowed read.
    local = str(
        _write_tif(tmp_path / "big.tif", bounds=(0.0, 0.0, 10.0, 10.0), width=10, height=10)
    )

    full = cogio.open_cog([local], variable="v", crs="EPSG:4326")
    windowed = cogio.open_cog([local], variable="v", crs="EPSG:4326", bbox=(1.0, 1.0, 3.0, 3.0))

    assert windowed["v"].size < full["v"].size


def test_open_cog_tiled_selects_intersecting(tmp_path):
    inside = str(_write_tif(tmp_path / "t1.tif", value=1.0, bounds=(0.0, 0.0, 1.0, 1.0)))
    outside = str(_write_tif(tmp_path / "t2.tif", value=2.0, bounds=(10.0, 10.0, 11.0, 11.0)))

    ds = cogio.open_cog(
        [inside, outside],
        variable="clay",
        crs="EPSG:4326",
        bbox=(0.0, 0.0, 0.5, 0.5),
    )

    # Only the intersecting tile should contribute (value 1.0, not 2.0).
    assert "clay" in ds.data_vars
    assert float(ds["clay"].max()) == pytest.approx(1.0)


def test_open_cog_tiled_no_intersection_raises(tmp_path):
    inside = str(_write_tif(tmp_path / "t1.tif", bounds=(0.0, 0.0, 1.0, 1.0)))
    outside = str(_write_tif(tmp_path / "t2.tif", bounds=(2.0, 2.0, 3.0, 3.0)))

    with pytest.raises(ValueError):
        cogio.open_cog(
            [inside, outside],
            variable="clay",
            crs="EPSG:4326",
            bbox=(50.0, 50.0, 51.0, 51.0),
        )


def test_open_cog_empty_raises():
    with pytest.raises(FileNotFoundError):
        cogio.open_cog([], variable="x", crs="EPSG:4326")


def test_write_cog_roundtrip_from_latlon(tmp_path):
    ds = xr.Dataset(
        {"landcover": (("lat", "lon"), np.arange(4, dtype="float32").reshape(2, 2))},
        coords={"lat": [1.0, 0.0], "lon": [0.0, 1.0]},
    )
    out = tmp_path / "data" / "landuse" / "corine" / "corine.tif"

    cogio.write_cog(ds, out, crs="EPSG:4326", varname="landcover")

    assert out.exists()
    with rasterio.open(out) as src:
        assert src.crs.to_epsg() == 4326
        assert src.width == 2 and src.height == 2


def test_write_cog_drops_singleton_time(tmp_path):
    ds = xr.Dataset(
        {"v": (("time", "lat", "lon"), np.ones((1, 2, 2), dtype="float32"))},
        coords={"time": [0], "lat": [1.0, 0.0], "lon": [0.0, 1.0]},
    )
    out = tmp_path / "v.tif"

    cogio.write_cog(ds, out, crs="EPSG:4326")

    assert out.exists()
    with rasterio.open(out) as src:
        assert src.count == 1
