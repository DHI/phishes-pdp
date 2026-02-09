"""
PHISHES Digital Platform - Analysis Module

This module provides functions for analyzing downloaded datasets.
"""

from .catchment import (
    CATCHMENT_RESTRICTIONS,
    EUROPE_AOI,
    compute_catchment_weights,
    create_catchment_from_extent,
    load_catchment,
    reproject_catchment,
    validate_catchment_gdf,
)
from .timeseries import compute_anomalies, compute_basin_average
from .visualization import plot_catchment, plot_spatial_map, plot_time_series

__all__ = [
    "CATCHMENT_RESTRICTIONS",
    "EUROPE_AOI",
    "compute_anomalies",
    "compute_basin_average",
    "compute_catchment_weights",
    "create_catchment_from_extent",
    "load_catchment",
    "plot_spatial_map",
    "plot_time_series",
    "plot_catchment",
    "reproject_catchment",
    "validate_catchment_gdf",
]
