import io
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr
from shapely.geometry import Polygon

from src.core.downloader import PDPDataDownloader


def _catchment_gdf():
    return gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]},
        crs="EPSG:4326",
    )


def _minimal_catalog():
    return {
        "climate": {
            "rain": {
                "path": "climate/rain.zarr",
                "crs": "EPSG:4326",
                "temporal": True,
                "description": "Rain",
                "variable": "rain",
                "eumtype": "Precipitation_Rate",
                "eumunit": "mm_per_hour",
            }
        }
    }


def _new_downloader(tmp_path):
    d = PDPDataDownloader.__new__(PDPDataDownloader)
    d.output_base = tmp_path
    d.azure_container = "zarr"
    d.azure_account = "acct"
    d.azure_credential = "cred"
    d.buffer_cells = 1
    d.output_format = "nc"
    d.mask_on_catchment = False
    d.dataset_catalog = _minimal_catalog()
    d.catchment = _catchment_gdf()
    d.catchment_shp = Path("catchment.shp")
    d.download_history = {"downloads": []}
    d.log_file = tmp_path / "logs" / "download_log.json"
    return d


def test_init_validates_and_sets_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(PDPDataDownloader, "_load_catalog", lambda self: _minimal_catalog())
    monkeypatch.setattr(PDPDataDownloader, "_setup_azure_connection", lambda self, c: object())
    monkeypatch.setattr(PDPDataDownloader, "_load_download_history", lambda self: {"downloads": []})
    monkeypatch.setattr("src.core.downloader.validate_catchment_gdf", lambda gdf: gdf)

    d = PDPDataDownloader(catchment=_catchment_gdf(), output_base=tmp_path)
    assert d.output_format == "nc"


def test_init_rejects_bad_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(PDPDataDownloader, "_load_catalog", lambda self: _minimal_catalog())
    monkeypatch.setattr(PDPDataDownloader, "_setup_azure_connection", lambda self, c: object())
    monkeypatch.setattr(PDPDataDownloader, "_load_download_history", lambda self: {"downloads": []})
    monkeypatch.setattr("src.core.downloader.validate_catchment_gdf", lambda gdf: gdf)

    with pytest.raises(ValueError):
        PDPDataDownloader(catchment=_catchment_gdf(), output_base=tmp_path, buffer_cells=-1)

    with pytest.raises(ValueError):
        PDPDataDownloader(catchment=_catchment_gdf(), output_base=tmp_path, output_format="bad")


def test_open_zarr_store_skips_empty_and_uses_zarr_v2(monkeypatch):
    # Mimics a store whose stray v3 metadata yields an empty dataset until an
    # explicit zarr_format=2 read exposes the data (the ssebop_eta case).
    empty = xr.Dataset()
    full = xr.Dataset({"ETa": ("x", [1.0, 2.0])})
    calls = []

    def fake_open_zarr(store, **kwargs):
        calls.append(kwargs)
        if kwargs.get("consolidated") is True:
            raise ValueError("no consolidated metadata")
        if kwargs.get("zarr_format") == 2:
            return full
        return empty

    monkeypatch.setattr("src.core.downloader.xr.open_zarr", fake_open_zarr)
    ds = PDPDataDownloader._open_zarr_store(object())
    assert list(ds.data_vars) == ["ETa"]
    assert {"consolidated": False, "zarr_format": 2} in calls


def test_open_zarr_store_raises_when_all_strategies_fail(monkeypatch):
    def fake_open_zarr(store, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr("src.core.downloader.xr.open_zarr", fake_open_zarr)
    with pytest.raises(ValueError, match="boom"):
        PDPDataDownloader._open_zarr_store(object())


def test_set_output_format_and_get_dataset_info(tmp_path):
    d = _new_downloader(tmp_path)
    d.set_output_format("zarr")
    assert d.output_format == "zarr"
    assert d.get_dataset_info("climate", "rain")["description"] == "Rain"
    with pytest.raises(ValueError):
        d.get_dataset_info("x", "y")


def test_load_catalog(tmp_path, monkeypatch):
    catalog = tmp_path / "dataset_catalog.yaml"
    catalog.write_text("climate:\n  rain:\n    description: Rain\n", encoding="utf-8")
    monkeypatch.setattr(PDPDataDownloader, "CATALOG_FILE", catalog)
    monkeypatch.setattr(PDPDataDownloader, "COG_CATALOG_FILE", tmp_path / "no_cog.yaml")
    monkeypatch.setattr(PDPDataDownloader, "GEOPARQUET_CATALOG_FILE", tmp_path / "no_gpq.yaml")
    monkeypatch.setattr(PDPDataDownloader, "PARTNER_CATALOG_FILE", tmp_path / "no_partner.yaml")
    d = _new_downloader(tmp_path)
    loaded = PDPDataDownloader._load_catalog(d)
    assert "climate" in loaded


def test_load_catalog_merges_cog_catalog(tmp_path, monkeypatch):
    catalog = tmp_path / "dataset_catalog.yaml"
    catalog.write_text("climate:\n  rain:\n    description: Rain\n", encoding="utf-8")
    cog = tmp_path / "cog_catalog.yaml"
    cog.write_text(
        "soil:\n  ksat_b000cm:\n    format: cog\n    description: Ksat\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(PDPDataDownloader, "CATALOG_FILE", catalog)
    monkeypatch.setattr(PDPDataDownloader, "COG_CATALOG_FILE", cog)
    monkeypatch.setattr(PDPDataDownloader, "GEOPARQUET_CATALOG_FILE", tmp_path / "no_gpq.yaml")
    monkeypatch.setattr(PDPDataDownloader, "PARTNER_CATALOG_FILE", tmp_path / "no_partner.yaml")
    d = _new_downloader(tmp_path)
    loaded = PDPDataDownloader._load_catalog(d)
    assert "climate" in loaded
    assert loaded["soil"]["ksat_b000cm"]["format"] == "cog"


def test_load_and_save_download_history(tmp_path):
    d = _new_downloader(tmp_path)
    d.download_history = {"downloads": [{"a": 1}]}
    d._save_download_history()
    loaded = d._load_download_history()
    assert loaded["downloads"][0]["a"] == 1


def test_setup_azure_connection(monkeypatch, tmp_path):
    class FakeFS:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def ls(self, _):
            return ["ok"]

    monkeypatch.setattr(
        "src.core.downloader.adlfs.AzureBlobFileSystem", lambda **kwargs: FakeFS(**kwargs)
    )
    d = _new_downloader(tmp_path)
    fs = d._setup_azure_connection("abc")
    assert isinstance(fs, FakeFS)


def test_load_catchment_delegates(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.catchment_shp = Path("dummy.shp")
    monkeypatch.setattr(
        "src.core.downloader.load_catchment", lambda *args, **kwargs: (_catchment_gdf(), None)
    )
    out = d._load_catchment()
    assert len(out) == 1


def test_open_dataset_tries_non_consolidated(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)

    class FakeFS:
        def get_mapper(self, p):
            return p

    d.fs = FakeFS()
    calls = []

    def fake_open_zarr(store, **kwargs):
        calls.append(kwargs)
        if kwargs.get("consolidated") is True:
            raise RuntimeError("fail first")
        return xr.Dataset({"rain": ("x", [1.0])})

    monkeypatch.setattr("src.core.downloader.xr.open_zarr", fake_open_zarr)
    ds = d.open_dataset("climate", "rain")
    assert list(ds.data_vars) == ["rain"]
    # First (consolidated) attempt raised; second (non-consolidated) succeeded.
    assert calls[0] == {"consolidated": True}
    assert calls[1] == {"consolidated": False}


def test_process_dataset_calls_subset_methods(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    ds = xr.Dataset(
        {"rain": (("time", "lat", "lon"), np.ones((1, 2, 2))), "x": (("time",), [1])},
        coords={"time": [0], "lat": [0, 1], "lon": [0, 1]},
    )
    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)
    monkeypatch.setattr(d, "_spatial_subset", lambda ds, bounds, c, crs: ds)
    monkeypatch.setattr(d, "_temporal_subset", lambda ds, tr: ds)
    out = d.process_dataset(ds, "climate", "rain", time_range=("2000", "2001"), variables=["rain"])
    assert list(out.data_vars) == ["rain"]


def test_save_dataset_netcdf(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.output_format = "nc"
    ds = xr.Dataset(
        {"rain": (("time", "lat", "lon"), np.ones((1, 1, 1)))},
        coords={"time": [0], "lat": [0], "lon": [0]},
    )
    output_path = tmp_path / "data" / "climate" / "rain" / "rain.nc"

    monkeypatch.setattr(
        "src.core.downloader.build_dataset_path", lambda *args, **kwargs: output_path
    )
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)
    monkeypatch.setattr(d, "_log_download", lambda *args, **kwargs: None)

    called = {}
    monkeypatch.setattr(
        xr.Dataset, "to_netcdf", lambda self, path, mode, engine: called.__setitem__("path", path)
    )

    out = d.save_dataset(ds, "climate", "rain")
    assert out == output_path
    assert called["path"] == output_path


def test_save_dataset_zarr_and_dfs2(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    ds = xr.Dataset(
        {"rain": (("time", "lat", "lon"), np.ones((1, 1, 1)))},
        coords={"time": [0], "lat": [0], "lon": [0]},
    )
    out = tmp_path / "data" / "climate" / "rain" / "rain.zarr"
    monkeypatch.setattr("src.core.downloader.build_dataset_path", lambda *args, **kwargs: out)
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)
    monkeypatch.setattr(d, "_log_download", lambda *args, **kwargs: None)

    zarr_called = {}
    monkeypatch.setattr(
        xr.Dataset, "to_zarr", lambda self, path, **kwargs: zarr_called.__setitem__("path", path)
    )
    d.output_format = "zarr"
    d.save_dataset(ds, "climate", "rain")
    assert zarr_called["path"] == out

    dfs_called = {}
    monkeypatch.setattr(
        "src.core.downloader.dfsio.create_file",
        lambda *args, **kwargs: dfs_called.__setitem__("ok", True),
    )
    d.output_format = "dfs2"
    d.save_dataset(ds, "climate", "rain")
    assert dfs_called["ok"] is True


def _cog_entry():
    return {
        "path": "corine/CLC.tif",
        "container": "cog",
        "format": "cog",
        "tiled": False,
        "crs": "EPSG:4326",
        "temporal": False,
        "description": "Land cover",
        "variable": "landcover",
    }


def test_open_dataset_routes_to_cog(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["landuse"] = {"corine": _cog_entry()}
    d.fs = object()

    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)

    captured = {}

    def fake_open_cog(uris, **kwargs):
        captured["uris"] = uris
        captured.update(kwargs)
        return "cog_ds"

    monkeypatch.setattr("src.core.downloader.cogio.open_cog", fake_open_cog)

    out = d.open_dataset("landuse", "corine")
    assert out == "cog_ds"
    assert len(captured["uris"]) == 1
    assert captured["uris"][0].startswith("https://acct.blob.core.windows.net/cog/corine/CLC.tif")
    assert captured["variable"] == "landcover"
    assert captured["bbox"] is not None


def test_open_dataset_routes_to_cog_tiled(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    entry = {
        "path": "static_layers/cop_dem",
        "container": "cogs",
        "format": "cog",
        "tiled": True,
        "anon": True,
        "crs": "EPSG:4326",
        "temporal": False,
        "description": "DEM",
        "variable": "elevation",
    }
    d.dataset_catalog["topography"] = {"cop_dem": entry}

    class FakeFS:
        def glob(self, pattern):
            assert pattern == "cogs/static_layers/cop_dem/**/*.tif"
            return ["cogs/static_layers/cop_dem/t2.tif", "cogs/static_layers/cop_dem/t1.tif"]

    d._anon_fs = FakeFS()
    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)

    captured = {}
    monkeypatch.setattr(
        "src.core.downloader.cogio.open_cog",
        lambda uris, **kwargs: captured.update(uris=uris, **kwargs) or "cog_ds",
    )

    out = d.open_dataset("topography", "cop_dem")
    assert out == "cog_ds"
    # Sorted tile list, mapped to anonymous (no SAS) HTTPS URLs.
    assert captured["uris"] == [
        "https://acct.blob.core.windows.net/cogs/static_layers/cop_dem/t1.tif",
        "https://acct.blob.core.windows.net/cogs/static_layers/cop_dem/t2.tif",
    ]


def test_save_dataset_tif(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["landuse"] = {"corine": _cog_entry()}
    d.output_format = "tif"
    ds = xr.Dataset(
        {"landcover": (("lat", "lon"), np.ones((2, 2)))},
        coords={"lat": [1.0, 0.0], "lon": [0.0, 1.0]},
    )
    out = tmp_path / "data" / "landuse" / "corine" / "corine.tif"

    monkeypatch.setattr("src.core.downloader.build_dataset_path", lambda *a, **k: out)
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)
    monkeypatch.setattr(d, "_log_download", lambda *a, **k: None)

    called = {}
    monkeypatch.setattr(
        "src.core.downloader.cogio.write_cog",
        lambda ds, path, **kwargs: called.__setitem__("path", path),
    )

    result = d.save_dataset(ds, "landuse", "corine")
    assert result == out
    assert called["path"] == out


def _geoparquet_entry():
    return {
        "path": "Soil/LUCAS_2018_bulk_density.parquet",
        "container": "geoparquet",
        "format": "geoparquet",
        "anon": False,
        "crs": "EPSG:4326",
        "temporal": False,
        "description": "LUCAS bulk density",
        "variable": "bulk_density",
    }


def test_download_dataset_routes_to_geoparquet(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["soil"] = {"lucas": _geoparquet_entry()}
    d.fs = object()
    d.output_format = "parquet"

    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)

    captured = {}

    def fake_open(blob_path, **kwargs):
        captured["blob_path"] = blob_path
        captured.update(kwargs)
        return "gdf"

    out_path = tmp_path / "data" / "soil" / "lucas" / "lucas.parquet"
    monkeypatch.setattr("src.core.downloader.geoparquetio.open_geoparquet", fake_open)

    def fake_build(base, cat, sub, fmt):
        captured["fmt"] = fmt
        return out_path

    monkeypatch.setattr("src.core.downloader.build_dataset_path", fake_build)
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    written = {}
    monkeypatch.setattr(
        "src.core.downloader.geoparquetio.write_geoparquet",
        lambda gdf, path, fmt: written.update(gdf=gdf, path=path, fmt=fmt),
    )
    monkeypatch.setattr(d, "_log_download", lambda *a, **k: None)

    result = d.download_dataset("soil", "lucas")
    assert result == out_path
    assert captured["blob_path"] == "geoparquet/Soil/LUCAS_2018_bulk_density.parquet"
    assert captured["fmt"] == "parquet"
    assert written == {"gdf": "gdf", "path": out_path, "fmt": "parquet"}


def test_download_geoparquet_falls_back_to_parquet_for_raster_format(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["soil"] = {"lucas": _geoparquet_entry()}
    d.fs = object()
    d.output_format = "nc"  # raster format -> should fall back to parquet

    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)
    monkeypatch.setattr("src.core.downloader.geoparquetio.open_geoparquet", lambda *a, **k: "gdf")
    captured = {}

    def fake_build(base, cat, sub, fmt):
        captured["fmt"] = fmt
        return tmp_path / "o.parquet"

    monkeypatch.setattr("src.core.downloader.build_dataset_path", fake_build)
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    monkeypatch.setattr("src.core.downloader.geoparquetio.write_geoparquet", lambda *a, **k: None)
    monkeypatch.setattr(d, "_log_download", lambda *a, **k: None)

    d.download_dataset("soil", "lucas")
    assert captured["fmt"] == "parquet"


def test_save_dataset_rejects_vector_format_for_raster(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.output_format = "shp"
    ds = xr.Dataset(
        {"rain": (("lat", "lon"), np.ones((1, 1)))},
        coords={"lat": [0], "lon": [0]},
    )
    monkeypatch.setattr(
        "src.core.downloader.build_dataset_path", lambda *a, **k: tmp_path / "x.shp"
    )
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    monkeypatch.setattr("src.core.downloader.reproject_catchment", lambda gdf, crs: gdf)
    monkeypatch.setattr(d, "_log_download", lambda *a, **k: None)

    with pytest.raises(ValueError):
        d.save_dataset(ds, "climate", "rain")


def test_load_catalog_merges_geoparquet_catalog(tmp_path, monkeypatch):
    catalog = tmp_path / "dataset_catalog.yaml"
    catalog.write_text("climate:\n  rain:\n    description: Rain\n", encoding="utf-8")
    gpq = tmp_path / "geoparquet_catalog.yaml"
    gpq.write_text(
        "soil:\n  lucas:\n    format: geoparquet\n    description: LUCAS\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(PDPDataDownloader, "CATALOG_FILE", catalog)
    monkeypatch.setattr(PDPDataDownloader, "COG_CATALOG_FILE", tmp_path / "no_cog.yaml")
    monkeypatch.setattr(PDPDataDownloader, "GEOPARQUET_CATALOG_FILE", gpq)
    monkeypatch.setattr(PDPDataDownloader, "PARTNER_CATALOG_FILE", tmp_path / "no_partner.yaml")
    d = _new_downloader(tmp_path)
    loaded = PDPDataDownloader._load_catalog(d)
    assert loaded["soil"]["lucas"]["format"] == "geoparquet"


def test_load_catalog_merges_partner_catalog(tmp_path, monkeypatch):
    catalog = tmp_path / "dataset_catalog.yaml"
    catalog.write_text("climate:\n  rain:\n    description: Rain\n", encoding="utf-8")
    partner = tmp_path / "partner_data_catalog.yaml"
    partner.write_text(
        "partner:\n  czech_globe_ms4:\n    format: zip\n    description: CG bundle\n"
        "restricted_partner:\n  cg_full:\n    format: zip\n"
        "    credential_env: PDP_AFTER_END_SAS\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(PDPDataDownloader, "CATALOG_FILE", catalog)
    monkeypatch.setattr(PDPDataDownloader, "COG_CATALOG_FILE", tmp_path / "no_cog.yaml")
    monkeypatch.setattr(PDPDataDownloader, "GEOPARQUET_CATALOG_FILE", tmp_path / "no_gpq.yaml")
    monkeypatch.setattr(PDPDataDownloader, "PARTNER_CATALOG_FILE", partner)
    d = _new_downloader(tmp_path)
    loaded = PDPDataDownloader._load_catalog(d)
    assert loaded["partner"]["czech_globe_ms4"]["format"] == "zip"
    assert loaded["restricted_partner"]["cg_full"]["credential_env"] == "PDP_AFTER_END_SAS"


def _zip_entry():
    # Blob names in the partner container contain spaces; keep one here to assert
    # the whole-blob copy path passes them through unchanged.
    return {
        "path": "MS4-CG data for PDP.zip",
        "container": "external-shared-open-data",
        "format": "zip",
        "anon": True,
        "temporal": False,
        "description": "Czech Globe MS4 bundle",
        "variable": "partner_bundle",
    }


class _FakeFS:
    """Filesystem stand-in exposing only open() - the zip path must not need list()."""

    def __init__(self, captured, payload=b"PK\x03\x04"):
        self.captured = captured
        self.payload = payload

    def open(self, rpath, mode="rb"):
        self.captured["rpath"] = rpath
        return io.BytesIO(self.payload)


def test_download_dataset_routes_to_zip(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["partner"] = {"czech_globe_ms4": _zip_entry()}
    d.output_format = "nc"  # ignored for zip entries

    captured = {}
    monkeypatch.setattr(d, "_dataset_filesystem", lambda info: _FakeFS(captured, b"PK\x03\x04"))

    out_path = tmp_path / "data" / "partner" / "czech_globe_ms4" / "czech_globe_ms4.zip"

    def fake_build(base, cat, sub, fmt):
        captured["fmt"] = fmt
        return out_path

    monkeypatch.setattr("src.core.downloader.build_dataset_path", fake_build)
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    monkeypatch.setattr(d, "_log_download", lambda *a, **k: None)

    result = d.download_dataset("partner", "czech_globe_ms4")

    assert result == out_path
    assert captured["fmt"] == "zip"
    assert captured["rpath"] == "external-shared-open-data/MS4-CG data for PDP.zip"
    assert out_path.parent.exists()  # parent dir created before download
    assert out_path.read_bytes() == b"PK\x03\x04"  # blob streamed through verbatim


def _restricted_zip_entry():
    return {
        "path": "MS4-CG data for PDP.zip",
        "container": "external-shared-after-end",
        "format": "zip",
        "anon": False,
        "credential_env": "PDP_AFTER_END_SAS",
        "temporal": False,
        "display_name": "Czech Globe MS4 data - full (restricted)",
        "description": "Restricted Czech Globe MS4 bundle",
        "variable": "partner_bundle",
    }


class _RecordingFS:
    """Stand-in for adlfs.AzureBlobFileSystem that records its constructor kwargs."""

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        _RecordingFS.instances.append(self)


@pytest.fixture
def recording_adlfs(monkeypatch):
    _RecordingFS.instances = []
    monkeypatch.setattr("src.core.downloader.adlfs.AzureBlobFileSystem", _RecordingFS)
    return _RecordingFS


def test_dataset_filesystem_uses_env_credential(monkeypatch, tmp_path, recording_adlfs):
    d = _new_downloader(tmp_path)
    monkeypatch.setenv("PDP_AFTER_END_SAS", "?sp=r&sig=secret")

    fs = d._dataset_filesystem(_restricted_zip_entry())

    assert len(recording_adlfs.instances) == 1
    # Leading '?' stripped, token used as SAS, and no anonymous fallback.
    assert fs.kwargs == {"account_name": "acct", "sas_token": "sp=r&sig=secret"}


def test_dataset_filesystem_caches_env_credential(monkeypatch, tmp_path, recording_adlfs):
    d = _new_downloader(tmp_path)
    monkeypatch.setenv("PDP_AFTER_END_SAS", "sp=r&sig=secret")

    first = d._dataset_filesystem(_restricted_zip_entry())
    second = d._dataset_filesystem(_restricted_zip_entry())

    assert first is second
    assert len(recording_adlfs.instances) == 1


def test_dataset_filesystem_missing_token_raises(monkeypatch, tmp_path, recording_adlfs):
    d = _new_downloader(tmp_path)
    monkeypatch.delenv("PDP_AFTER_END_SAS", raising=False)

    with pytest.raises(PermissionError) as excinfo:
        d._dataset_filesystem(_restricted_zip_entry())

    message = str(excinfo.value)
    assert "PDP_AFTER_END_SAS" in message
    assert "external-shared-after-end" in message
    assert ".env" in message
    assert not recording_adlfs.instances  # no connection attempted


def test_load_env_file_is_noop_without_dotenv(monkeypatch):
    """python-dotenv is an optional convenience; tokens can be exported directly."""
    monkeypatch.setattr("src.core.downloader._DOTENV_AVAILABLE", False)
    monkeypatch.setattr("src.core.downloader.load_dotenv", None)
    PDPDataDownloader._load_env_file()  # must not raise


def test_load_env_file_uses_dotenv_when_available(monkeypatch):
    calls = {}
    monkeypatch.setattr("src.core.downloader._DOTENV_AVAILABLE", True)
    monkeypatch.setattr("src.core.downloader.find_dotenv", lambda usecwd: "/tmp/.env")
    monkeypatch.setattr(
        "src.core.downloader.load_dotenv",
        lambda path, override: calls.update(path=path, override=override),
    )
    PDPDataDownloader._load_env_file()
    # Exported variables must win over the file.
    assert calls == {"path": "/tmp/.env", "override": False}


def test_missing_token_message_mentions_export_without_dotenv(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    monkeypatch.delenv("PDP_AFTER_END_SAS", raising=False)
    monkeypatch.setattr("src.core.downloader._DOTENV_AVAILABLE", False)

    with pytest.raises(PermissionError) as excinfo:
        d._dataset_filesystem(_restricted_zip_entry())

    message = str(excinfo.value)
    assert "python-dotenv is not installed" in message
    assert "PDP_AFTER_END_SAS" in message


def test_dataset_filesystem_blank_token_raises(monkeypatch, tmp_path, recording_adlfs):
    d = _new_downloader(tmp_path)
    monkeypatch.setenv("PDP_AFTER_END_SAS", "   ")

    with pytest.raises(PermissionError):
        d._dataset_filesystem(_restricted_zip_entry())


def test_dataset_filesystem_open_entries_unchanged(monkeypatch, tmp_path, recording_adlfs):
    d = _new_downloader(tmp_path)
    d.fs = object()

    # No anon, no credential_env -> the main (built-in SAS) filesystem.
    assert d._dataset_filesystem({"container": "zarr"}) is d.fs

    # anon: true -> a cached anonymous filesystem.
    anon_fs = d._dataset_filesystem({"anon": True})
    assert anon_fs.kwargs == {"account_name": "acct", "anon": True}
    assert d._dataset_filesystem({"anon": True}) is anon_fs


def test_download_dataset_restricted_zip_routes_with_token(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["restricted_partner"] = {"czech_globe_ms4_full": _restricted_zip_entry()}
    monkeypatch.setenv("PDP_AFTER_END_SAS", "sp=r&sig=secret")

    captured = {}
    monkeypatch.setattr(d, "_dataset_filesystem", lambda info: _FakeFS(captured))

    out_path = tmp_path / "data" / "restricted_partner" / "cg" / "cg.zip"
    monkeypatch.setattr("src.core.downloader.build_dataset_path", lambda *a: out_path)
    monkeypatch.setattr("src.core.downloader.remove_path_with_retry", lambda p: True)
    monkeypatch.setattr(d, "_log_download", lambda *a, **k: None)

    result = d.download_dataset("restricted_partner", "czech_globe_ms4_full")

    assert result == out_path
    assert captured["rpath"] == "external-shared-after-end/MS4-CG data for PDP.zip"


def test_download_zip_removes_partial_file_on_failure(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["restricted_partner"] = {"czech_globe_ms4_full": _restricted_zip_entry()}
    monkeypatch.setenv("PDP_AFTER_END_SAS", "sp=r&sig=secret")

    class _FailingFS:
        def open(self, rpath, mode="rb"):
            raise RuntimeError("AuthorizationPermissionMismatch")

    monkeypatch.setattr(d, "_dataset_filesystem", lambda info: _FailingFS())

    out_path = tmp_path / "data" / "restricted_partner" / "cg" / "cg.zip"
    monkeypatch.setattr("src.core.downloader.build_dataset_path", lambda *a: out_path)
    monkeypatch.setattr(d, "_log_download", lambda *a, **k: None)

    with pytest.raises(RuntimeError):
        d.download_dataset("restricted_partner", "czech_globe_ms4_full")

    assert not out_path.exists()


def test_download_dataset_restricted_zip_without_token_writes_nothing(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    d.dataset_catalog["restricted_partner"] = {"czech_globe_ms4_full": _restricted_zip_entry()}
    monkeypatch.delenv("PDP_AFTER_END_SAS", raising=False)

    with pytest.raises(PermissionError):
        d.download_dataset("restricted_partner", "czech_globe_ms4_full")

    assert not (tmp_path / "data").exists()


def test_restricted_datasets_stay_listable(monkeypatch, tmp_path):
    """The dataset name is public; only its contents are gated."""
    d = _new_downloader(tmp_path)
    d.dataset_catalog["restricted_partner"] = {"czech_globe_ms4_full": _restricted_zip_entry()}
    d.dataset_catalog["partner"] = {"czech_globe_ms4": _zip_entry()}

    monkeypatch.delenv("PDP_AFTER_END_SAS", raising=False)
    assert "czech_globe_ms4_full" in d.list_available_datasets()["restricted_partner"]
    assert d.dataset_requires_token("restricted_partner", "czech_globe_ms4_full") == (
        "PDP_AFTER_END_SAS"
    )
    assert d.is_dataset_accessible("restricted_partner", "czech_globe_ms4_full") is False

    monkeypatch.setenv("PDP_AFTER_END_SAS", "sp=r&sig=secret")
    assert "czech_globe_ms4_full" in d.list_available_datasets()["restricted_partner"]
    assert d.is_dataset_accessible("restricted_partner", "czech_globe_ms4_full") is True

    # Open datasets report no token requirement.
    assert d.dataset_requires_token("partner", "czech_globe_ms4") is None
    assert d.is_dataset_accessible("partner", "czech_globe_ms4") is True
    assert d.is_dataset_accessible("climate", "rain") is True


def test_blob_url_uses_entry_credential(tmp_path):
    d = _new_downloader(tmp_path)
    assert d._blob_url("cogs/a.tif") == ("https://acct.blob.core.windows.net/cogs/a.tif?cred")
    assert d._blob_url("cogs/a.tif", credential="?other") == (
        "https://acct.blob.core.windows.net/cogs/a.tif?other"
    )
    assert d._blob_url("cogs/a.tif", anon=True) == "https://acct.blob.core.windows.net/cogs/a.tif"


def test_download_dataset_pipeline(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    monkeypatch.setattr(d, "open_dataset", lambda *args, **kwargs: "raw")
    monkeypatch.setattr(d, "process_dataset", lambda *args, **kwargs: "proc")
    monkeypatch.setattr(d, "save_dataset", lambda *args, **kwargs: Path("out.nc"))
    assert d.download_dataset("climate", "rain") == Path("out.nc")


def test_spatial_subset_and_temporal_subset(tmp_path):
    d = _new_downloader(tmp_path)
    ds = xr.Dataset(
        {"v": (("time", "lat", "lon"), np.ones((1, 3, 3)))},
        coords={"time": [0], "lat": [0.0, 0.5, 1.0], "lon": [0.0, 0.5, 1.0]},
    )

    subset = d._spatial_subset(ds, (0.1, 0.1, 0.9, 0.9), _catchment_gdf(), "EPSG:4326")
    assert subset.sizes["lat"] >= 1 and subset.sizes["lon"] >= 1

    no_time = xr.Dataset(
        {"v": (("lat", "lon"), np.ones((2, 2)))}, coords={"lat": [0, 1], "lon": [0, 1]}
    )
    assert d._temporal_subset(no_time, ("2000", "2001")).equals(no_time)


def test_log_download_and_download_all(monkeypatch, tmp_path):
    d = _new_downloader(tmp_path)
    saved = {}
    monkeypatch.setattr(d, "_save_download_history", lambda: saved.__setitem__("ok", True))

    d._log_download(
        "climate", "rain", d.get_dataset_info("climate", "rain"), Path("x.nc"), (0, 0, 1, 1), None
    )
    assert len(d.download_history["downloads"]) == 1
    assert saved["ok"] is True

    calls = {"count": 0}

    def fake_download(category, subcategory, time_range=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("fail first")

    monkeypatch.setattr(d, "download_dataset", fake_download)
    d.download_all()
    assert calls["count"] == 1
