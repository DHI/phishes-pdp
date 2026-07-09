"""
PHISHES Digital Platform - GeoParquet (vector) I/O

Provides utilities for reading GeoParquet vector layers clipped to a catchment
into a GeoDataFrame, and for writing the clipped result back out as GeoParquet
or Shapefile.

GeoParquet layers are static (no time dimension) and vector (points/lines/polygons),
so they flow through GeoPandas rather than the xarray/raster pipeline used for Zarr
and COG datasets. The downloader resolves the blob URI/filesystem and passes it here.

Features that intersect the catchment are kept whole (no geometry truncation), which
is the correct behaviour for sample-point datasets such as LUCAS.

Author: DHI A/S
Date: June 2026
"""

from pathlib import Path
from typing import Optional, Sequence, Union

import geopandas as gpd


def open_geoparquet(
    uri: str,
    *,
    mask_geometry,
    mask_crs: str,
    bbox: Optional[Sequence[float]] = None,
    crs: Optional[str] = None,
    filesystem=None,
    columns: Optional[Sequence[str]] = None,
) -> gpd.GeoDataFrame:
    """
    Read a GeoParquet file and keep features intersecting the catchment.

    Parameters
    ----------
    uri : str
        Path to the .parquet file, relative to ``filesystem`` (e.g.
        ``"geoparquet/Soil/LUCAS_2018_bulk_density.parquet"``) or a full path.
    mask_geometry : shapely geometry
        Catchment geometry used to select intersecting features. Expressed in
        ``mask_crs``.
    mask_crs : str
        CRS of ``mask_geometry`` (e.g. ``"EPSG:4326"``).
    bbox : sequence of float, optional
        Catchment bounds (minx, miny, maxx, maxy) in the dataset CRS, used for
        row-group predicate pushdown when the file carries GeoParquet 1.1 bbox
        covering metadata. Ignored (with a fallback read) otherwise.
    crs : str, optional
        CRS to assign when the file itself lacks CRS metadata.
    filesystem : fsspec filesystem, optional
        Filesystem used to read the file (e.g. an ``adlfs.AzureBlobFileSystem``).
    columns : sequence of str, optional
        Subset of columns to read. The geometry column is always included.

    Returns
    -------
    geopandas.GeoDataFrame
        Features intersecting the catchment, geometries unchanged.
    """
    read_kwargs = {}
    if filesystem is not None:
        read_kwargs["filesystem"] = filesystem
    if columns is not None:
        read_kwargs["columns"] = list(columns)

    # Try bbox predicate pushdown first (fast for large files with bbox covering
    # metadata); fall back to a full read if the file does not support it.
    gdf = None
    if bbox is not None:
        try:
            gdf = gpd.read_parquet(uri, bbox=tuple(bbox), **read_kwargs)
            print(f"Read GeoParquet with bbox pushdown ({len(gdf)} features pre-filter)")
        except (TypeError, ValueError) as exc:
            print(f"bbox pushdown unavailable ({exc}); reading full file")
            gdf = None
    if gdf is None:
        gdf = gpd.read_parquet(uri, **read_kwargs)

    if gdf.crs is None and crs is not None:
        gdf = gdf.set_crs(crs)

    # Reproject the catchment mask into the data CRS, then keep intersecting
    # features whole via the spatial index (no geometry truncation).
    mask = gpd.GeoSeries([mask_geometry], crs=mask_crs)
    if gdf.crs is not None:
        mask = mask.to_crs(gdf.crs)
    geom = mask.iloc[0]

    idx = gdf.sindex.query(geom, predicate="intersects")
    clipped = gdf.iloc[sorted(idx)]
    print(f"Selected {len(clipped)} of {len(gdf)} features intersecting the catchment")
    return clipped


def write_geoparquet(
    gdf: gpd.GeoDataFrame,
    outfile: Union[str, Path],
    fmt: str = "parquet",
) -> None:
    """
    Write a GeoDataFrame to GeoParquet or Shapefile.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Vector data to write.
    outfile : str or Path
        Output path. ``.parquet`` for GeoParquet, ``.shp`` for Shapefile.
    fmt : str, default "parquet"
        Output format: ``"parquet"`` (GeoParquet) or ``"shp"`` (Shapefile).
    """
    outfile = Path(outfile)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "shp":
        print(f"Creating Shapefile {outfile}")
        gdf.to_file(outfile)
    else:
        print(f"Creating GeoParquet file {outfile}")
        gdf.to_parquet(outfile)
