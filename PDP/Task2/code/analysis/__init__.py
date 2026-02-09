"""
PHISHES Digital Platform - Analysis Module

This module provides functions for analyzing downloaded datasets.
"""

from .catchment import (
    load_catchment,
    create_catchment_from_extent,
    validate_catchment_gdf,
    reproject_catchment,
    compute_catchment_weights,
    EUROPE_AOI,
    CATCHMENT_RESTRICTIONS,
)
from .timeseries import compute_basin_average, compute_anomalies
from .visualization import plot_spatial_map, plot_time_series, plot_catchment

__all__ = [
    "load_catchment",
    "create_catchment_from_extent",
    "validate_catchment_gdf",
    "reproject_catchment",
    "compute_catchment_weights",
    "EUROPE_AOI",
    "CATCHMENT_RESTRICTIONS",
    "compute_basin_average",
    "compute_anomalies",
    "plot_spatial_map",
    "plot_time_series",
    "plot_catchment",
]
