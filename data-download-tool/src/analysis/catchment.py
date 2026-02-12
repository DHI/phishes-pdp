"""
PHISHES Digital Platform - Catchment Processing Functions

Functions for loading, reprojecting, and processing catchment geometries.
"""

from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import shapely.geometry
import xarray as xr
from shapely.ops import unary_union

from ..core.utils import get_grid_resolution

# European Area of Interest bounding box (EPSG:4326)
EUROPE_AOI = {
    "min_lon": -25.0,
    "max_lon": 70.0,
    "min_lat": 35.0,
    "max_lat": 72.0,
}

# Restrictions and validation limits
CATCHMENT_RESTRICTIONS = {
    "max_area_km2": 500_000,  # Maximum catchment area (km²)
    "min_area_km2": 0.01,  # Minimum catchment area (km²)
    "max_features": 1000,  # Maximum number of features
    "buffer_distance_m": 1000,  # Buffer distance for points/lines (meters)
}


def _get_geometry_type(gdf: gpd.GeoDataFrame) -> str:
    """Determine the dominant geometry type in a GeoDataFrame."""
    geom_types = gdf.geometry.geom_type.unique()

    # Check for polygons first
    polygon_types = {"Polygon", "MultiPolygon"}
    if any(gt in polygon_types for gt in geom_types):
        return "polygon"

    # Check for lines
    line_types = {"LineString", "MultiLineString"}
    if any(gt in line_types for gt in geom_types):
        return "line"

    # Check for points
    point_types = {"Point", "MultiPoint"}
    if any(gt in point_types for gt in geom_types):
        return "point"

    return "unknown"


def _buffer_geometry(
    gdf: gpd.GeoDataFrame, buffer_distance_m: float = CATCHMENT_RESTRICTIONS["buffer_distance_m"]
) -> gpd.GeoDataFrame:
    """
    Buffer point/line geometries to create polygon catchment areas.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input GeoDataFrame with point or line geometries.
    buffer_distance_m : float
        Buffer distance in meters.

    Returns
    -------
    GeoDataFrame
        GeoDataFrame with buffered polygon geometries.
    """
    original_crs = gdf.crs

    # Project to a meter-based CRS for accurate buffering
    # Use EPSG:3035 (ETRS89-LAEA Europe) for European data
    gdf_projected = gdf.to_crs("EPSG:3035")
    gdf_projected["geometry"] = gdf_projected.geometry.buffer(buffer_distance_m)

    # Project back to original CRS
    gdf_buffered = gdf_projected.to_crs(original_crs)

    print(f"Buffered geometries by {buffer_distance_m}m")
    return gdf_buffered


def _validate_europe_aoi(
    gdf: gpd.GeoDataFrame, min_overlap_fraction: float = 0.1
) -> Tuple[bool, float, str]:
    """
    Validate that catchment overlaps with European Area of Interest.

    Parameters
    ----------
    gdf : GeoDataFrame
        Catchment geometry (must be in EPSG:4326).
    min_overlap_fraction : float
        Minimum fraction of catchment that must overlap with Europe AOI.

    Returns
    -------
    tuple
        (is_valid, overlap_fraction, message)
    """
    # Ensure we're in WGS84
    if gdf.crs is None:
        return False, 0.0, "Catchment has no CRS defined"

    gdf_4326 = gdf.to_crs("EPSG:4326") if gdf.crs != "EPSG:4326" else gdf

    # Create Europe AOI box
    europe_box = shapely.geometry.box(
        EUROPE_AOI["min_lon"], EUROPE_AOI["min_lat"], EUROPE_AOI["max_lon"], EUROPE_AOI["max_lat"]
    )

    # Get catchment bounds
    catchment_geom = unary_union(gdf_4326.geometry)

    if not catchment_geom.intersects(europe_box):
        return False, 0.0, "Catchment does not overlap with European AOI"

    # Calculate overlap fraction
    intersection = catchment_geom.intersection(europe_box)
    overlap_fraction = intersection.area / catchment_geom.area if catchment_geom.area > 0 else 0

    if overlap_fraction < min_overlap_fraction:
        return (
            False,
            overlap_fraction,
            f"Only {overlap_fraction:.1%} of catchment overlaps with European AOI (minimum: {min_overlap_fraction:.1%})",
        )

    return True, overlap_fraction, f"Catchment overlaps {overlap_fraction:.1%} with European AOI"


def _validate_catchment_size(gdf: gpd.GeoDataFrame) -> Tuple[bool, float, str]:
    """
    Validate catchment area is within acceptable limits.

    Parameters
    ----------
    gdf : GeoDataFrame
        Catchment geometry.

    Returns
    -------
    tuple
        (is_valid, area_km2, message)
    """
    # Project to equal-area CRS for accurate area calculation
    gdf_projected = gdf.to_crs("EPSG:3035")
    area_m2 = gdf_projected.geometry.area.sum()
    area_km2 = area_m2 / 1e6

    min_area = CATCHMENT_RESTRICTIONS["min_area_km2"]
    max_area = CATCHMENT_RESTRICTIONS["max_area_km2"]

    if area_km2 < min_area:
        return (
            False,
            area_km2,
            f"Catchment area ({area_km2:.4f} km²) is below minimum ({min_area} km²)",
        )

    if area_km2 > max_area:
        return (
            False,
            area_km2,
            f"Catchment area ({area_km2:.0f} km²) exceeds maximum ({max_area:,} km²)",
        )

    return True, area_km2, f"Catchment area: {area_km2:.2f} km²"


def create_catchment_from_extent(
    extent: Iterable[float],
    crs: str,
) -> gpd.GeoDataFrame:
    """
    Create a catchment GeoDataFrame from a manual extent.

    Parameters
    ----------
    extent : iterable of float
        Bounding box [minx, miny, maxx, maxy].
    crs : str
        CRS of the extent (e.g., "EPSG:4326").

    Returns
    -------
    GeoDataFrame
        Catchment polygon with the specified CRS.
    """
    extent_list = list(extent)
    if len(extent_list) != 4:
        raise ValueError("extent must be a 4-item list or tuple: [minx, miny, maxx, maxy]")

    minx, miny, maxx, maxy = extent_list
    if minx >= maxx or miny >= maxy:
        raise ValueError("extent is invalid: min values must be less than max values")

    geom = shapely.geometry.box(minx, miny, maxx, maxy)
    return gpd.GeoDataFrame({"geometry": [geom]}, crs=crs)


def load_catchment(
    shp_path: Optional[Union[str, Path]] = None,
    target_crs: Optional[str] = None,
    merge_features: bool = True,
    validate_aoi: bool = True,
    validate_size: bool = True,
    buffer_points_lines: bool = True,
    extent: Optional[Iterable[float]] = None,
    extent_crs: Optional[str] = None,
) -> Tuple[gpd.GeoDataFrame, Optional[shapely.geometry.base.BaseGeometry]]:
    """
    Load catchment shapefile and optionally reproject and merge features.

    Supports polygon, line, and point geometries. Points and lines are
    automatically buffered to create polygon catchment areas.

    Parameters
    ----------
    shp_path : str or Path, optional
        Path to the catchment shapefile.
        extent : iterable of float, optional
            Bounding box [minx, miny, maxx, maxy] used instead of a file.
        extent_crs : str, optional
            CRS for the extent (required if extent is provided).
    target_crs : str, optional
        Target CRS to reproject to (e.g., "EPSG:4326").
    merge_features : bool, default True
        If True and multiple features exist, merge into single geometry.
    validate_aoi : bool, default True
        If True, validate that catchment overlaps with European AOI.
    validate_size : bool, default True
        If True, validate catchment area is within acceptable limits.
    buffer_points_lines : bool, default True
        If True, buffer point/line geometries to create polygons.

    Returns
    -------
    tuple
        (GeoDataFrame, merged_geometry or None)
        If merge_features=True and multiple features, returns merged geometry.
        Otherwise merged_geometry is None.

    Raises
    ------
    FileNotFoundError
        If shapefile does not exist.
    ValueError
        If shapefile is empty or fails validation.
    """
    if extent is not None:
        if extent_crs is None:
            raise ValueError("extent_crs must be provided when using extent")
        print("Loading catchment from manual extent")
        gdf = create_catchment_from_extent(extent, extent_crs)
    else:
        if shp_path is None:
            raise ValueError("Either shp_path or extent must be provided")
        shp_path = Path(shp_path)
        if not shp_path.exists():
            raise FileNotFoundError(f"Catchment shapefile not found: {shp_path}")

        print(f"Loading catchment from: {shp_path}")
        gdf = gpd.read_file(shp_path)

    if len(gdf) == 0:
        raise ValueError("Catchment shapefile is empty")

    # Check feature count
    max_features = CATCHMENT_RESTRICTIONS["max_features"]
    if len(gdf) > max_features:
        raise ValueError(f"Too many features ({len(gdf)}). Maximum allowed: {max_features}")

    print(f"Catchment CRS: {gdf.crs}")
    print(f"Number of features: {len(gdf)}")

    # Detect and handle geometry type
    geom_type = _get_geometry_type(gdf)
    print(f"Geometry type: {geom_type}")

    if geom_type in ("point", "line"):
        if buffer_points_lines:
            print(f"Converting {geom_type} geometry to polygon via buffering")
            gdf = _buffer_geometry(gdf)
        else:
            raise ValueError(
                f"Catchment contains {geom_type} geometries. "
                "Set buffer_points_lines=True to convert to polygons."
            )
    elif geom_type == "unknown":
        raise ValueError("Catchment contains unsupported geometry types")

    # Reproject if requested
    if target_crs and gdf.crs != target_crs:
        print(f"Reprojecting catchment to {target_crs}")
        gdf = gdf.to_crs(target_crs)

    # Validate European AOI overlap
    if validate_aoi:
        is_valid, overlap, message = _validate_europe_aoi(gdf)
        print(f"AOI validation: {message}")
        if not is_valid:
            raise ValueError(f"AOI validation failed: {message}")

    # Validate catchment size
    if validate_size:
        is_valid, area_km2, message = _validate_catchment_size(gdf)
        print(message)
        if not is_valid:
            raise ValueError(f"Size validation failed: {message}")

    # Merge features if requested
    merged_geom = None
    if merge_features and len(gdf) > 1:
        print(f"Creating catchment outline from {len(gdf)} features")
        merged_geom = unary_union(gdf.geometry)
    elif len(gdf) == 1:
        merged_geom = gdf.geometry.iloc[0]

    return gdf, merged_geom


def validate_catchment_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Validate a pre-loaded catchment GeoDataFrame.

    Performs minimal validation on an already-loaded GeoDataFrame:
    - Ensures it's not empty
    - Ensures it has a CRS defined
    - Merges multiple features into a single geometry if needed

    Parameters
    ----------
    gdf : GeoDataFrame
        Catchment geometry to validate.

    Returns
    -------
    GeoDataFrame
        Validated catchment geometry (single feature).

    Raises
    ------
    ValueError
        If catchment is empty or has no CRS.
    """
    # If already validated (single geometry with CRS), just log and return
    if len(gdf) == 1 and gdf.crs is not None:
        print(f"Using pre-loaded catchment (CRS: {gdf.crs})")
        return gdf

    # Minimal validation
    if len(gdf) == 0:
        raise ValueError("Catchment is empty")

    if gdf.crs is None:
        raise ValueError("Catchment has no CRS defined")

    # Merge if needed
    if len(gdf) > 1:
        print(f"Merging {len(gdf)} features into single geometry")
        merged_geometry = unary_union(gdf.geometry)
        gdf = gpd.GeoDataFrame({"geometry": [merged_geometry]}, crs=gdf.crs)

    print(f"Catchment CRS: {gdf.crs}")
    return gdf


def reproject_catchment(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    """
    Reproject catchment to target CRS.

    Parameters
    ----------
    gdf : GeoDataFrame
        Catchment geometry to reproject.
    target_crs : str
        Target CRS (e.g., 'EPSG:4326').

    Returns
    -------
    GeoDataFrame
        Reprojected catchment.
    """
    return gdf.to_crs(target_crs)


def compute_catchment_weights(
    ds: xr.Dataset,
    catchment_geom: shapely.geometry.base.BaseGeometry,
    lat_dim: str = "lat",
    lon_dim: str = "lon",
) -> xr.DataArray:
    """
    Compute area-weighted intersection of grid cells with catchment.

    For each grid cell, calculates the fraction of cell area that intersects
    with the catchment geometry. This enables proper area-weighted averaging.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset with lat/lon coordinates.
    catchment_geom : shapely geometry
        Catchment geometry (should be in same CRS as data, typically EPSG:4326).
    lat_dim : str, default "lat"
        Name of latitude dimension.
    lon_dim : str, default "lon"
        Name of longitude dimension.

    Returns
    -------
    xarray.DataArray
        2D array of weights (0-1) for each grid cell.
    """
    lat = ds[lat_dim].values
    lon = ds[lon_dim].values

    # Calculate grid resolution using shared utility
    lat_res = get_grid_resolution(lat, default=0.1)
    lon_res = get_grid_resolution(lon, default=0.1)

    print(f"Grid resolution: ~{lat_res:.4f}° lat x {lon_res:.4f}° lon")

    # Create meshgrid
    lon_2d, lat_2d = np.meshgrid(lon, lat)

    # Calculate intersection weights
    weights = np.zeros(lon_2d.shape, dtype=float)

    for i in range(lon_2d.shape[0]):
        for j in range(lon_2d.shape[1]):
            cell_box = shapely.geometry.box(
                lon_2d[i, j] - lon_res / 2,
                lat_2d[i, j] - lat_res / 2,
                lon_2d[i, j] + lon_res / 2,
                lat_2d[i, j] + lat_res / 2,
            )
            if cell_box.intersects(catchment_geom):
                intersection = cell_box.intersection(catchment_geom)
                weights[i, j] = intersection.area / cell_box.area

    cells_intersecting = (weights > 0).sum()
    print(f"Grid cells intersecting catchment: {cells_intersecting}/{weights.size}")
    print(f"Total weight (sum of fractions): {weights.sum():.2f} cells equivalent")

    # Convert to xarray DataArray
    weights_da = xr.DataArray(
        weights,
        dims=[lat_dim, lon_dim],
        coords={lat_dim: ds[lat_dim], lon_dim: ds[lon_dim]},
    )

    return weights_da
