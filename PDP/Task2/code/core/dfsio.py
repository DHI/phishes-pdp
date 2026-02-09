"""
PHISHES Digital Platform - DFS File I/O

Provides utilities for converting xarray DataArrays to MIKE IO DFS2 format.

Author: DHI A/S
Date: January 2026
"""

from pathlib import Path
from typing import Union, Optional

import mikeio
from mikeio.eum import EUMType, EUMUnit
from mikeio import ItemInfo
import xarray as xr
import numpy as np

from .utils import get_grid_resolution, guess_data_variable


def dfs_from_xr(
    da: Union[xr.DataArray, xr.Dataset],
    varname: str,
    eumtype: EUMType,
    eumunit: EUMUnit,
    res: Optional[float] = None,
    **kwargs,
) -> mikeio.DataArray:
    """
    Create a MIKE IO DataArray from an xarray DataArray.

    Parameters
    ----------
    da : xarray.DataArray or xarray.Dataset
        Input data. If Dataset, the main data variable will be guessed.
    varname : str
        Name for the output variable.
    eumtype : EUMType
        EUM type for the variable.
    eumunit : EUMUnit
        EUM unit for the variable.
    res : float, optional
        Resolution override. If None, resolution is calculated from coordinates.
    **kwargs
        Additional keyword arguments (unused).

    Returns
    -------
    mikeio.DataArray
        MIKE IO DataArray ready for DFS export.
    """
    if isinstance(da, xr.Dataset):
        da = da[guess_data_variable(da)]

    if 1 in [np.ma.count(da["lon"].values), np.ma.count(da["lat"].values)]:
        dx = res or get_grid_resolution(da["lon"], default=0.1)
        dy = res or get_grid_resolution(da["lat"], default=0.1)
        bbox = (
            np.min(da["lon"].values) - dx / 2,
            np.min(da["lat"].values) - dy / 2,
            np.max(da["lon"].values),
            np.max(da["lat"].values),
        )
    else:
        bbox = None
        dx = None
        dy = None

    geom = mikeio.spatial.Grid2D(
        x=da["lon"].values,
        y=da["lat"].values,
        projection="LONG/LAT",
        dx=dx,
        dy=dy,
        bbox=bbox,
    )

    return mikeio.DataArray(
        data=da.values,
        time=da.time.values,
        geometry=geom,
        item=ItemInfo(varname, eumtype, eumunit),
    )


def create_file(
    da: Union[xr.DataArray, xr.Dataset],
    outfile: Union[str, Path],
    varname: str,
    eumtype: Union[str, EUMType],
    eumunit: Union[str, EUMUnit],
    **kwargs,
) -> None:
    """
    Create a DFS2 file from an xarray DataArray.

    Parameters
    ----------
    da : xarray.DataArray or xarray.Dataset
        Input data to write.
    outfile : str or Path
        Output file path.
    varname : str
        Name for the output variable.
    eumtype : str or EUMType
        EUM type for the variable (name or EUMType enum).
    eumunit : str or EUMUnit
        EUM unit for the variable (name or EUMUnit enum).
    **kwargs
        Additional keyword arguments passed to dfs_from_xr.
    """
    outfile = Path(outfile)

    dfs_da = dfs_from_xr(
        da,
        varname=varname,
        eumtype=eumtype if isinstance(eumtype, EUMType) else EUMType[eumtype],
        eumunit=eumunit if isinstance(eumunit, EUMUnit) else EUMUnit[eumunit],
        **kwargs,
    )

    print(f"Creating file {outfile}")
    print(f"Time range {da.time.values[0]} - {da.time.values[-1]}")

    outfile.parent.mkdir(parents=True, exist_ok=True)
    dfs_da.to_dfs(outfile)
