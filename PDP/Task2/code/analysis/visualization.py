"""
PHISHES Digital Platform - Visualization Functions

Functions for plotting spatial data, time series, and catchments.
"""

from typing import Optional, Tuple

import matplotlib.pyplot as plt
import geopandas as gpd
import xarray as xr


def plot_catchment(
    catchment: gpd.GeoDataFrame,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[int, int] = (10, 8),
    title: str = "Catchment Boundary",
    facecolor: str = "lightblue",
    edgecolor: str = "black",
    linewidth: float = 2,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot catchment boundary.

    Parameters
    ----------
    catchment : GeoDataFrame
        Catchment geometry.
    ax : matplotlib Axes, optional
        Axes to plot on. If None, creates new figure.
    figsize : tuple, default (10, 8)
        Figure size if creating new figure.
    title : str, default "Catchment Boundary"
        Plot title.
    facecolor : str, default "lightblue"
        Fill color for catchment.
    edgecolor : str, default "black"
        Edge color for catchment.
    linewidth : float, default 2
        Edge line width.

    Returns
    -------
    tuple
        (Figure, Axes)
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    catchment.plot(ax=ax, facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Longitude" if catchment.crs.is_geographic else "X [m]")
    ax.set_ylabel("Latitude" if catchment.crs.is_geographic else "Y [m]")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    return fig, ax


def plot_spatial_map(
    data: xr.DataArray,
    catchment: Optional[gpd.GeoDataFrame] = None,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[int, int] = (12, 8),
    cmap: str = "viridis",
    title: Optional[str] = None,
    catchment_color: str = "red",
    catchment_linewidth: float = 2,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot spatial data with optional catchment overlay.

    Parameters
    ----------
    data : xarray.DataArray
        2D spatial data to plot.
    catchment : GeoDataFrame, optional
        Catchment to overlay. Will be reprojected to EPSG:4326 if needed.
    ax : matplotlib Axes, optional
        Axes to plot on. If None, creates new figure.
    figsize : tuple, default (12, 8)
        Figure size if creating new figure.
    cmap : str, default "viridis"
        Colormap for data.
    title : str, optional
        Plot title.
    catchment_color : str, default "red"
        Color for catchment boundary.
    catchment_linewidth : float, default 2
        Line width for catchment boundary.

    Returns
    -------
    tuple
        (Figure, Axes)
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    # Plot data
    data.plot(ax=ax, cmap=cmap)

    # Overlay catchment
    if catchment is not None:
        if catchment.crs != "EPSG:4326":
            catchment_plot = catchment.to_crs("EPSG:4326")
        else:
            catchment_plot = catchment
        catchment_plot.boundary.plot(
            ax=ax, color=catchment_color, linewidth=catchment_linewidth, label="Catchment"
        )
        ax.legend()

    if title:
        ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.tight_layout()

    return fig, ax


def plot_time_series(
    data: xr.DataArray,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[int, int] = (12, 6),
    label: str = "Basin Average",
    title: Optional[str] = None,
    xlabel: str = "Time",
    ylabel: Optional[str] = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plot time series data.

    Parameters
    ----------
    data : xarray.DataArray
        1D time series data.
    ax : matplotlib Axes, optional
        Axes to plot on. If None, creates new figure.
    figsize : tuple, default (12, 6)
        Figure size if creating new figure.
    label : str, default "Basin Average"
        Legend label.
    title : str, optional
        Plot title.
    xlabel : str, default "Time"
        X-axis label.
    ylabel : str, optional
        Y-axis label. If None, uses data.name.

    Returns
    -------
    tuple
        (Figure, Axes)
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    data.plot(ax=ax, label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel or data.name or "Value")
    if title:
        ax.set_title(title)
    ax.legend()
    plt.tight_layout()

    return fig, ax
