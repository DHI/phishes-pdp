import matplotlib

matplotlib.use("Agg")

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr
from shapely.geometry import Polygon

from src.analysis.timeseries import compute_anomalies, compute_basin_average
from src.analysis.visualization import plot_catchment, plot_spatial_map, plot_time_series


def test_compute_basin_average():
    data = xr.DataArray(
        np.array([[[1.0, 2.0], [3.0, 4.0]]]),
        dims=("time", "lat", "lon"),
        coords={"time": [0], "lat": [0, 1], "lon": [0, 1]},
    )
    weights = xr.DataArray(np.array([[1.0, 0.0], [0.0, 1.0]]), dims=("lat", "lon"))
    basin = compute_basin_average(data, weights)
    assert float(basin.values[0]) == pytest.approx(2.5)


def test_compute_basin_average_raises_for_zero_weights():
    data = xr.DataArray(np.ones((1, 2, 2)), dims=("time", "lat", "lon"))
    weights = xr.DataArray(np.zeros((2, 2)), dims=("lat", "lon"))
    with pytest.raises(ValueError):
        compute_basin_average(data, weights)


def test_compute_anomalies():
    data = xr.DataArray([1.0, 2.0, 3.0], dims=("time",), coords={"time": [0, 1, 2]})
    out = compute_anomalies(data)
    assert set(out.keys()) == {"anomalies", "mean", "std", "max_positive", "max_negative"}
    assert out["mean"] == pytest.approx(2.0)


def test_compute_anomalies_missing_time_raises():
    data = xr.DataArray([1.0, 2.0], dims=("x",))
    with pytest.raises(ValueError):
        compute_anomalies(data)


def test_plot_catchment_and_spatial_and_timeseries():
    catch = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]},
        crs="EPSG:4326",
    )
    fig1, ax1 = plot_catchment(catch)
    assert fig1 is not None and ax1 is not None

    spatial = xr.DataArray(
        np.array([[1.0, 2.0], [3.0, 4.0]]),
        dims=("lat", "lon"),
        coords={"lat": [0, 1], "lon": [0, 1]},
    )
    fig2, ax2 = plot_spatial_map(spatial, catchment=catch)
    assert fig2 is not None and ax2 is not None

    ts = xr.DataArray([1.0, 2.0], dims=("time",), coords={"time": [0, 1]}, name="v")
    fig3, ax3 = plot_time_series(ts, eumtype="Rainfall")
    assert fig3 is not None and ax3 is not None
