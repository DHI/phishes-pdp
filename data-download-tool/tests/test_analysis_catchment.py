import geopandas as gpd
import numpy as np
import pytest
import xarray as xr
from shapely.geometry import LineString, Point, Polygon

from src.analysis import catchment


def _gdf(geom, crs="EPSG:4326"):
    return gpd.GeoDataFrame({"geometry": [geom]}, crs=crs)


def test_get_geometry_type_variants():
    assert (
        catchment._get_geometry_type(_gdf(Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]))) == "polygon"
    )
    assert catchment._get_geometry_type(_gdf(LineString([(0, 0), (1, 1)]))) == "line"
    assert catchment._get_geometry_type(_gdf(Point(0, 0))) == "point"


def test_buffer_geometry_returns_polygon():
    gdf = _gdf(Point(10.0, 50.0))
    buffered = catchment._buffer_geometry(gdf, buffer_distance_m=1000)
    assert catchment._get_geometry_type(buffered) == "polygon"


def test_validate_europe_aoi():
    valid, frac, _ = catchment._validate_europe_aoi(
        _gdf(Polygon([(10, 50), (11, 50), (11, 51), (10, 51)]))
    )
    assert valid is True
    assert frac > 0


def test_validate_europe_aoi_no_crs():
    gdf = gpd.GeoDataFrame({"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]})
    valid, _, message = catchment._validate_europe_aoi(gdf)
    assert valid is False
    assert "no CRS" in message


def test_create_catchment_from_extent_and_invalid():
    gdf = catchment.create_catchment_from_extent([0, 0, 1, 1], "EPSG:4326")
    assert len(gdf) == 1

    with pytest.raises(ValueError):
        catchment.create_catchment_from_extent([0, 0, 1], "EPSG:4326")


def test_load_catchment_from_extent_and_merge():
    gdf, merged = catchment.load_catchment(
        extent=[0, 0, 1, 1],
        extent_crs="EPSG:4326",
        validate_aoi=False,
        validate_size=False,
        merge_features=True,
    )
    assert len(gdf) == 1
    assert merged is not None


def test_validate_catchment_gdf_behaviors():
    one = _gdf(Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]))
    assert catchment.validate_catchment_gdf(one).equals(one)

    multi = gpd.GeoDataFrame(
        {
            "geometry": [
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
            ]
        },
        crs="EPSG:4326",
    )
    merged = catchment.validate_catchment_gdf(multi)
    assert len(merged) == 1

    with pytest.raises(ValueError):
        catchment.validate_catchment_gdf(gpd.GeoDataFrame({"geometry": []}, crs="EPSG:4326"))


def test_reproject_catchment():
    gdf = _gdf(Polygon([(10, 50), (11, 50), (11, 51), (10, 51)]))
    reproj = catchment.reproject_catchment(gdf, "EPSG:3857")
    assert str(reproj.crs) == "EPSG:3857"


def test_compute_catchment_weights():
    ds = xr.Dataset(
        coords={
            "lat": [50.0, 50.5],
            "lon": [8.0, 8.5],
        }
    )
    geom = Polygon([(7.75, 49.75), (8.75, 49.75), (8.75, 50.75), (7.75, 50.75)])
    weights = catchment.compute_catchment_weights(ds, geom)
    assert weights.shape == (2, 2)
    assert float(weights.sum()) > 0
