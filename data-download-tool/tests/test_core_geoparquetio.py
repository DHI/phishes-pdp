import geopandas as gpd
from shapely.geometry import Point, Polygon, box

from src.core import geoparquetio


def _points_gdf(crs="EPSG:4326"):
    """Three points: two inside the unit square, one well outside."""
    return gpd.GeoDataFrame(
        {"id": [1, 2, 3], "geometry": [Point(0.25, 0.25), Point(0.75, 0.75), Point(5.0, 5.0)]},
        crs=crs,
    )


def _mask():
    return Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])


def test_open_geoparquet_keeps_intersecting_features_whole(tmp_path):
    path = tmp_path / "points.parquet"
    _points_gdf().to_parquet(path)

    out = geoparquetio.open_geoparquet(
        str(path),
        mask_geometry=_mask(),
        mask_crs="EPSG:4326",
        bbox=(0, 0, 1, 1),
        crs="EPSG:4326",
    )

    # Only the two points inside the unit square survive; geometries unchanged.
    assert sorted(out["id"].tolist()) == [1, 2]
    assert out.geometry.iloc[0].equals(Point(0.25, 0.25))


def test_open_geoparquet_assigns_crs_when_missing(tmp_path):
    path = tmp_path / "nocrs.parquet"
    gdf = _points_gdf(crs=None)
    gdf.to_parquet(path)

    out = geoparquetio.open_geoparquet(
        str(path),
        mask_geometry=_mask(),
        mask_crs="EPSG:4326",
        crs="EPSG:4326",
    )

    assert out.crs is not None
    assert out.crs.to_epsg() == 4326


def test_open_geoparquet_falls_back_without_bbox_support(tmp_path, monkeypatch):
    path = tmp_path / "points.parquet"
    _points_gdf().to_parquet(path)

    calls = {"n": 0}
    real_read = gpd.read_parquet

    def fake_read(uri, **kwargs):
        if "bbox" in kwargs:
            calls["n"] += 1
            raise ValueError("bbox covering not present")
        return real_read(uri, **kwargs)

    monkeypatch.setattr(geoparquetio.gpd, "read_parquet", fake_read)

    out = geoparquetio.open_geoparquet(
        str(path),
        mask_geometry=_mask(),
        mask_crs="EPSG:4326",
        bbox=(0, 0, 1, 1),
        crs="EPSG:4326",
    )
    assert calls["n"] == 1  # bbox attempt was made and failed
    assert sorted(out["id"].tolist()) == [1, 2]


def test_write_geoparquet_roundtrip_parquet(tmp_path):
    gdf = _points_gdf()
    out = tmp_path / "out.parquet"
    geoparquetio.write_geoparquet(gdf, out, fmt="parquet")
    assert out.exists()
    assert len(gpd.read_parquet(out)) == 3


def test_write_geoparquet_roundtrip_shapefile(tmp_path):
    gdf = _points_gdf()
    out = tmp_path / "nested" / "out.shp"
    geoparquetio.write_geoparquet(gdf, out, fmt="shp")
    assert out.exists()  # parent dir created
    assert len(gpd.read_file(out)) == 3


def test_open_geoparquet_reprojects_mask(tmp_path):
    # Data in EPSG:3857, mask given in EPSG:4326 -> must be reprojected to match.
    gdf = _points_gdf(crs="EPSG:4326").to_crs("EPSG:3857")
    path = tmp_path / "webmerc.parquet"
    gdf.to_parquet(path)

    out = geoparquetio.open_geoparquet(
        str(path),
        mask_geometry=box(0, 0, 1, 1),
        mask_crs="EPSG:4326",
        crs="EPSG:3857",
    )
    assert sorted(out["id"].tolist()) == [1, 2]
