"""
PHISHES Digital Platform - Time Series Analysis Functions

Functions for computing basin averages, anomalies, and time series statistics.
"""

from typing import Dict

import xarray as xr


def compute_basin_average(
    data: xr.DataArray,
    weights: xr.DataArray,
    lat_dim: str = "lat",
    lon_dim: str = "lon",
) -> xr.DataArray:
    """
    Compute area-weighted basin average time series.

    Parameters
    ----------
    data : xarray.DataArray
        Data array with spatial dimensions (and optionally time).
    weights : xarray.DataArray
        2D weights array from compute_catchment_weights().
    lat_dim : str, default "lat"
        Name of latitude dimension.
    lon_dim : str, default "lon"
        Name of longitude dimension.

    Returns
    -------
    xarray.DataArray
        Basin-averaged time series (or scalar if no time dimension).
    """
    if weights.sum() == 0:
        raise ValueError("No grid cells intersect with catchment (all weights are zero)")

    # Compute weighted average: sum(data * weights) / sum(weights)
    basin_avg = (data * weights).sum(dim=[lat_dim, lon_dim]) / weights.sum()

    print("Basin average computed")
    print(f"  - Mean: {float(basin_avg.mean()):.4f}")
    print(f"  - Min: {float(basin_avg.min()):.4f}")
    print(f"  - Max: {float(basin_avg.max()):.4f}")

    return basin_avg


def compute_anomalies(
    data: xr.DataArray,
    time_dim: str = "time",
) -> Dict[str, xr.DataArray]:
    """
    Compute anomalies (deviation from temporal mean).

    Parameters
    ----------
    data : xarray.DataArray
        Time series data (1D with time dimension).
    time_dim : str, default "time"
        Name of time dimension.

    Returns
    -------
    dict
        Dictionary with keys:
        - "anomalies": DataArray of anomalies
        - "mean": temporal mean value
        - "std": standard deviation
        - "max_positive": maximum positive anomaly
        - "max_negative": minimum (most negative) anomaly
    """
    if time_dim not in data.dims:
        raise ValueError(f"Data does not have time dimension '{time_dim}'")

    temporal_mean = data.mean(dim=time_dim)
    anomalies = data - temporal_mean

    result = {
        "anomalies": anomalies,
        "mean": float(temporal_mean.values) if temporal_mean.ndim == 0 else temporal_mean,
        "std": float(anomalies.std().values),
        "max_positive": float(anomalies.max().values),
        "max_negative": float(anomalies.min().values),
    }

    print("Anomaly Analysis:")
    print(f"  - Mean anomaly: {float(anomalies.mean()):.4f}")
    print(f"  - Std anomaly: {result['std']:.4f}")
    print(f"  - Max positive anomaly: {result['max_positive']:.4f}")
    print(f"  - Max negative anomaly: {result['max_negative']:.4f}")

    return result
