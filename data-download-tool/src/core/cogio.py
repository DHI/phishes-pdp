"""
PHISHES Digital Platform - COG (Cloud Optimized GeoTIFF) I/O

Provides utilities for reading Cloud Optimized GeoTIFF layers (a single file or an
externally tiled mosaic) into xarray, and for writing catchment-clipped rasters back
out as COG GeoTIFFs.

COG layers are static (no time dimension). Tiles are read by GDAL/rasterio directly
from their URIs (e.g. ``https://...`` blob URLs that GDAL serves via ``/vsicurl``),
so only the byte ranges actually needed are fetched. The downloader resolves the list
of tile URIs and passes them here.

Author: DHI A/S
Date: June 2026
"""

import concurrent.futures
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

import rasterio
import rioxarray  # noqa: F401 - enables .rio accessor on xarray objects
import xarray as xr
from rioxarray.merge import merge_arrays

# GDAL options that make remote (/vsicurl) reads fast: skip directory listing on open
# and only consider .tif siblings, avoiding probes for non-existent sidecar files.
_GDAL_OPTS = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
}
_MAX_WORKERS = 16


def _intersects(bounds: Tuple[float, float, float, float], bbox) -> bool:
    """Return True if a raster's (minx, miny, maxx, maxy) bounds intersect bbox."""
    if bbox is None:
        return True
    minx, miny, maxx, maxy = bounds
    bminx, bminy, bmaxx, bmaxy = bbox
    return not (maxx < bminx or minx > bmaxx or maxy < bminy or miny > bmaxy)


def _read_bounds(uri: str) -> Tuple[float, float, float, float]:
    """Read just a raster's extent (header only, no pixels) from its URI."""
    with rasterio.Env(**_GDAL_OPTS):
        with rasterio.open(uri) as src:
            return tuple(src.bounds)


def _clip_to_bbox(da: xr.DataArray, bbox: Tuple[float, float, float, float]) -> xr.DataArray:
    """Window a lazily-opened raster to bbox (+ a small margin) before reading.

    Reads only the COG blocks overlapping the catchment instead of the whole
    raster. The margin keeps a few native cells around the bounds so the
    downstream buffer/clip still has data to work with. Falls back to the full
    raster if the box does not overlap.
    """
    minx, miny, maxx, maxy = bbox
    try:
        xres, yres = da.rio.resolution()
        mx, my = abs(xres) * 2, abs(yres) * 2
        return da.rio.clip_box(minx - mx, miny - my, maxx + mx, maxy + my)
    except Exception:
        return da


def _open_single(
    uri: str,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    masked: bool = True,
) -> xr.DataArray:
    """Open one .tif (local path or remote URI) as a (band, y, x) DataArray."""
    with rasterio.Env(**_GDAL_OPTS):
        # Open lazily, window to the catchment bbox, then read: COG range-reads
        # fetch only the blocks the window touches, not the whole raster.
        da = rioxarray.open_rasterio(uri, masked=masked)
        if bbox is not None:
            da = _clip_to_bbox(da, bbox)
        return da.load()


def open_cog(
    uris: Sequence[str],
    variable: str,
    crs: str,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> xr.Dataset:
    """
    Open a COG dataset (single file or tiled mosaic) as an xarray Dataset.

    Parameters
    ----------
    uris : sequence of str
        GDAL-readable URIs (local paths or ``https://`` blob URLs). A single URI
        is read directly; multiple URIs are treated as a tiled mosaic.
    variable : str
        Name to give the resulting data variable.
    crs : str
        Coordinate reference system to assign (e.g. ``"EPSG:4326"``).
    bbox : tuple of float, optional
        Catchment bounds (minx, miny, maxx, maxy) in the dataset CRS, used to
        select intersecting tiles and to window the read.

    Returns
    -------
    xarray.Dataset
        Dataset with ``y``/``x`` dimensions, CRS set, and the data named
        ``variable``.
    """
    uris = list(uris)
    if not uris:
        raise FileNotFoundError("No COG tiles to read")

    if len(uris) == 1:
        da = _open_single(uris[0], bbox=bbox)
    else:
        # Lazily read just the extents of every tile (header-only range reads) in
        # parallel, then read pixels only for the tiles intersecting the catchment.
        workers = min(_MAX_WORKERS, len(uris))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            all_bounds = list(ex.map(_read_bounds, uris))
        hits = [u for u, b in zip(uris, all_bounds) if _intersects(b, bbox)]

        print(f"Selected {len(hits)} of {len(uris)} tiles intersecting the catchment")
        if not hits:
            raise ValueError(f"No tiles intersect the catchment bounds {bbox}")

        workers = min(_MAX_WORKERS, len(hits))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            arrays = list(ex.map(lambda u: _open_single(u, bbox=bbox), hits))
        da = arrays[0] if len(arrays) == 1 else merge_arrays(arrays)

    da = da.rename(variable)
    da.rio.write_crs(crs, inplace=True)
    ds = da.to_dataset(name=variable)

    # Align dimension names with the rest of the pipeline (Zarr datasets and the
    # downloader's spatial subsetting use lat/lon, not rioxarray's default y/x).
    rename = {d: n for d, n in (("y", "lat"), ("x", "lon")) if d in ds.dims}
    return ds.rename(rename) if rename else ds


def write_cog(
    ds: Union[xr.DataArray, xr.Dataset],
    outfile: Union[str, Path],
    crs: str,
    varname: Optional[str] = None,
) -> None:
    """
    Write an xarray raster to a Cloud Optimized GeoTIFF.

    Parameters
    ----------
    ds : xarray.DataArray or xarray.Dataset
        Raster data with spatial dimensions named ``y``/``x``,
        ``lat``/``lon``, or ``latitude``/``longitude``.
    outfile : str or Path
        Output ``.tif`` path.
    crs : str
        Coordinate reference system to assign before writing.
    varname : str, optional
        Variable to write when ``ds`` is a Dataset with multiple variables.
        Defaults to the first data variable.
    """
    outfile = Path(outfile)

    if isinstance(ds, xr.Dataset):
        name = varname or next(iter(ds.data_vars))
        da = ds[name]
    else:
        da = ds

    # Normalize spatial dimension names to y/x for rioxarray.
    rename = {}
    for cand in ("lat", "latitude"):
        if cand in da.dims:
            rename[cand] = "y"
            break
    for cand in ("lon", "longitude"):
        if cand in da.dims:
            rename[cand] = "x"
            break
    if rename:
        da = da.rename(rename)

    # COGs are static; drop a singleton time dimension if present.
    if "time" in da.dims and da.sizes["time"] == 1:
        da = da.isel(time=0, drop=True)

    da = da.drop_vars("spatial_ref", errors="ignore")
    da.rio.write_crs(crs, inplace=True)

    print(f"Creating COG file {outfile}")
    outfile.parent.mkdir(parents=True, exist_ok=True)
    da.rio.to_raster(outfile, driver="COG")
