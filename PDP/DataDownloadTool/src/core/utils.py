"""
PHISHES Digital Platform - Utility Functions

Provides helper functions for data loading, visualization, and processing.
"""

from pathlib import Path
from typing import Union, Iterable, Mapping, Optional

import gc
import shutil
import time

import xarray as xr
import numpy as np
import mikeio


def get_grid_resolution(
    coords: Union[xr.DataArray, np.ndarray],
    default: float = 0.1,
) -> float:
    """
    Calculate grid resolution (spacing) from coordinate array.

    Parameters
    ----------
    coords : xarray.DataArray or numpy.ndarray
        Coordinate values (e.g., lat or lon).
    default : float, default 0.1
        Default resolution if coordinates have fewer than 2 values.

    Returns
    -------
    float
        Resolution (spacing) of the coordinate.
    """
    if hasattr(coords, "values"):
        coords = coords.values
    if len(coords) < 2:
        return default
    return float(np.abs(coords[1] - coords[0]))


def remove_path_with_retry(
    path: Path,
    max_retries: int = 5,
    retry_delays: Optional[list] = None,
) -> bool:
    """
    Remove a file or directory with retry logic for Windows file locking.

    Parameters
    ----------
    path : Path
        Path to remove.
    max_retries : int, default 5
        Maximum number of retry attempts.
    retry_delays : list, optional
        Progressive delay times in seconds. Defaults to [0.5, 1.0, 2.0, 3.0, 5.0].

    Returns
    -------
    bool
        True if successfully removed, False if path didn't exist.

    Raises
    ------
    OSError
        If removal fails after all retries.
    """
    if not path.exists():
        return False

    retry_delays = retry_delays or [0.5, 1.0, 2.0, 3.0, 5.0]

    for attempt in range(max_retries):
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=False)
            else:
                path.unlink()
            print(f"Removed: {path}")
            return True
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                print(
                    f"WARNING: File locked, retrying in {delay:.1f}s "
                    f"(attempt {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(delay)
            else:
                print(f"ERROR: Failed to remove after {max_retries} attempts: {e}")
                raise

    return False


def build_dataset_path(
    project_base: Union[str, Path],
    category: str,
    subcategory: str,
    output_format: str = "nc",
) -> Path:
    """
    Build the full path for a dataset based on category and subcategory.

    Parameters
    ----------
    project_base : str or Path
        Base path of the project.
    category : str
        Dataset category (e.g., "climate", "hydrology", "soil", "topography", "landuse").
    subcategory : str
        Dataset subcategory (e.g., "precipitation", "temperature", "discharge", "dem").
    output_format : str, optional
        Output format, "nc", "zarr", or "dfs2". Default is "nc".

    Returns
    -------
    Path
        Full path to the dataset file.

    Examples
    --------
    >>> path = build_dataset_path(Path("data/my_project"), "climate", "precipitation")
    >>> path = build_dataset_path(Path("data/my_project"), "climate", "temperature", "zarr")
    """
    project_base = Path(project_base)

    return project_base.joinpath(
        "data", category, subcategory, f"{subcategory}.{output_format.lower()}"
    )


def open_dataset_any(path: Union[str, Path]) -> xr.Dataset:
    """
    Open a dataset from Zarr, NetCDF, or DFS2 format.

    Automatically detects the format based on file extension and opens accordingly.

    Parameters
    ----------
    path : str or Path
        Path to the dataset file (.zarr folder or .nc file).

    Returns
    -------
    xarray.Dataset
        Opened dataset.

    Examples
    --------
    >>> ds = open_dataset_any(Path("data").joinpath("climate", "temperature", "temperature.zarr"))
    >>> ds = open_dataset_any(Path("data").joinpath("climate", "temperature", "temperature.nc"))
    """
    path = Path(path)

    if path.suffix == ".zarr" or path.is_dir():
        return xr.open_zarr(path, consolidated=True)
    elif path.suffix == ".nc":
        return xr.open_dataset(path, engine="netcdf4")
    elif path.suffix == ".dfs2":
        return mikeio.read(path).to_xarray().rename(x="lon", y="lat")
    else:
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            f"Supported formats: .zarr (directory), .nc (NetCDF), .dfs2 (MIKE IO)"
        )


def cleanup_existing_dataset(
    dataset_path: Union[str, Path],
    namespace: Optional[Mapping[str, object]] = None,
    dataset_var_names: Iterable[str] = ("ds", "ds_downloaded"),
) -> None:
    """
    Close open datasets, force garbage collection, and remove existing dataset files.

    This helps avoid Windows file locking errors when re-downloading data.

    Parameters
    ----------
    dataset_path : str or Path
        Path to the dataset file or directory.
    namespace : Mapping[str, object], optional
        Namespace to search for open dataset variables (e.g., locals()).
    dataset_var_names : iterable of str, optional
        Variable names to close if present in the namespace.
    """
    dataset_path = Path(dataset_path)

    if namespace:
        for name in dataset_var_names:
            obj = namespace.get(name)
            if obj is not None and hasattr(obj, "close"):
                try:
                    obj.close()
                    print(f"Closed previously opened dataset '{name}'")
                except Exception as exc:
                    print(f"WARNING: Could not close dataset '{name}': {exc}")

    gc.collect()
    print("Garbage collection completed. File handles released.")

    try:
        removed = remove_path_with_retry(dataset_path)
        if removed:
            print("Removed successfully. Now try the download again.")
        else:
            print("No existing data found. Ready to download.")
    except OSError:
        print("Manual fix:")
        print("1. Close any programs that might have the file open")
        print(f"2. Delete manually: {dataset_path}")
        print("3. Then run the download cell again")


def guess_data_variable(ds, filter_vars=["spatial_ref", "crs"]):
    """Determine the primary data variable from an xarray dataset.

    This function inspects the provided xarray Dataset to identify and return
    the primary data variable. It can optionally filter out specified variables
    from consideration, ensuring that the returned variable is not in the filter list.

    Args:
        ds (xr.Dataset): The xarray dataset from which to guess the data variable.
        filter_vars (str or list, optional): A variable or list of variables to exclude
            from consideration when guessing the data variable.

    Returns:
        str: The name of the guessed data variable.

    Raises:
        ValueError: If the input is not an xarray Dataset.
    """

    if not isinstance(ds, xr.Dataset):
        raise ValueError(f"Unable to guess data variable for {type(ds)}. Need xr.Dataset.")
    if filter_vars is not None:
        if isinstance(filter_vars, str):
            filter_vars = [filter_vars]

        for v in iter(ds.data_vars.keys()):
            if v not in filter_vars:
                return v

    return next(iter(ds.data_vars.keys()))
