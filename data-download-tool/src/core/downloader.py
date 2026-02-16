"""
PHISHES Digital Platform - Data Downloader

This module downloads Zarr datasets from Azure Blob Storage based on user-provided
catchment polygons. It handles spatial subsetting, coordinate transformations, and
local storage management. Output can be written as NetCDF, Zarr, or DFS2.

Author: DHI A/S
Date: January 2026

"""

import json
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Union
from datetime import datetime

import adlfs
import geopandas as gpd
import rioxarray  # noqa: F401 - enables .rio accessor on xarray objects
import xarray as xr

from .utils import build_dataset_path, get_grid_resolution, remove_path_with_retry
from ..analysis import load_catchment, validate_catchment_gdf, reproject_catchment
from . import dfsio


class PDPDataDownloader:
    """
    Downloads and manages PHISHES datasets from Azure Blob Storage.

    This class handles:
    - Connection to Azure Blob Storage
    - Spatial intersection with user catchment
    - Data subsetting and clipping
    - Local storage management
    - Download logging and metadata

    Environment Variables:
    - AZURE_ACCOUNT: Storage account name (default: phishesdatastore)
    - AZURE_CONTAINER: Blob container name (default: zarr)
    - AZURE_CREDENTIAL: SAS token for authentication
    """

    # Azure Storage Configuration
    DEFAULT_AZURE_ACCOUNT = "phishesdatastore"
    DEFAULT_AZURE_CONTAINER = "zarr"
    DEFAULT_AZURE_CREDENTIAL = "sp=rl&st=2026-02-09T10:22:14Z&se=2034-12-31T18:37:14Z&spr=https&sv=2024-11-04&sr=c&sig=buOnKjOpmc%2BDZw7lnyWhMf4z5cTGVKqYHzXRnA8OTBM%3D"

    DEFAULT_OUTPUT_FORMAT = "nc"
    SUPPORTED_OUTPUT_FORMATS = {"nc", "zarr", "dfs2"}
    CATALOG_FILE = Path(__file__).parent.joinpath("dataset_catalog.yaml")

    def __init__(
        self,
        catchment: Union[str, Path, gpd.GeoDataFrame],
        output_base: Union[str, Path],
        azure_account: Optional[str] = None,
        azure_container: Optional[str] = None,
        azure_credential: Optional[str] = None,
        buffer_cells: int = 1,
        output_format: Optional[str] = None,
        mask_on_catchment: bool = False,
    ):
        """
        Initialize the data downloader.

        Parameters
        ----------
        catchment : str, Path, or GeoDataFrame
            Either a path to the catchment shapefile, or a pre-loaded GeoDataFrame.
        output_base : str or Path
            Base directory for output data.
        azure_account : str, optional
            Azure storage account name. Uses default if None.
        azure_container : str, optional
            Azure container name. Uses default if None.
        azure_credential : str, optional
            SAS token for authentication.
            If None, attempts anonymous access.
        buffer_cells : int, default 1
            Buffer around catchment in number of grid cells.
        output_format : str, optional
            Output format for downloaded datasets. Supported: "nc", "zarr", "dfs2".
        """
        self.output_base = Path(output_base)
        self.azure_account = azure_account or self.DEFAULT_AZURE_ACCOUNT
        self.azure_container = azure_container or self.DEFAULT_AZURE_CONTAINER
        self.azure_credential = azure_credential or self.DEFAULT_AZURE_CREDENTIAL
        self.buffer_cells = int(buffer_cells)
        self.output_format = (output_format or self.DEFAULT_OUTPUT_FORMAT).lower()
        self.mask_on_catchment = bool(mask_on_catchment)

        if self.buffer_cells < 0:
            raise ValueError("buffer_cells must be a non-negative integer")

        if self.output_format not in self.SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(
                f"Unsupported output_format: {self.output_format}. "
                f"Use one of {sorted(self.SUPPORTED_OUTPUT_FORMATS)}."
            )

        # Load dataset catalog
        self.dataset_catalog = self._load_catalog()

        # Load or use provided catchment
        if isinstance(catchment, gpd.GeoDataFrame):
            self.catchment = validate_catchment_gdf(catchment)
            self.catchment_shp = None
        else:
            self.catchment_shp = Path(catchment)
            self.catchment = self._load_catchment()

        # Setup Azure connection
        self.fs = self._setup_azure_connection(azure_credential)

        # Create log file
        self.log_file = self.output_base.joinpath("logs", "download_log.json")
        self.download_history = self._load_download_history()

    def set_output_format(self, output_format: Optional[str] = None):
        """Set the output format for downloaded datasets."""
        if output_format:
            output_format = output_format.lower()
            if output_format not in self.SUPPORTED_OUTPUT_FORMATS:
                raise ValueError(
                    f"Unsupported output_format: {output_format}. "
                    f"Use one of {sorted(self.SUPPORTED_OUTPUT_FORMATS)}."
                )
            self.output_format = output_format
            print(f"Output format set to: {self.output_format}")
        else:
            print(f"Output format remains: {self.output_format}")

    def _load_catalog(self) -> Dict:
        """Load dataset catalog from YAML file."""
        if not self.CATALOG_FILE.exists():
            raise FileNotFoundError(f"Dataset catalog not found: {self.CATALOG_FILE}")
        with open(self.CATALOG_FILE, "r") as f:
            return yaml.safe_load(f)

    def _setup_azure_connection(self, credential: Optional[str] = None):
        """
        Setup Azure Blob Storage connection.

        Parameters
        ----------
        credential : str, optional
            Authentication credential. If None, uses the instance's stored credential.

        Returns
        -------
        AzureBlobFileSystem
            Configured Azure filesystem object.
        """
        print(f"Connecting to Azure: {self.azure_account}/{self.azure_container}")

        # Use provided credential or fall back to instance credential
        credential = credential or self.azure_credential

        try:
            if credential:
                # Use provided SAS token
                fs = adlfs.AzureBlobFileSystem(
                    account_name=self.azure_account, sas_token=credential
                )
            else:
                # Try anonymous access
                print("WARNING: No credential provided, attempting anonymous access")
                fs = adlfs.AzureBlobFileSystem(account_name=self.azure_account, anon=True)

            # Test connection
            try:
                fs.ls(self.azure_container)
                print("Successfully connected to Azure storage")
            except Exception as e:
                print(f"ERROR: Connection test failed: {e}")
                raise

            return fs

        except Exception as e:
            print(f"ERROR: Failed to connect to Azure: {e}")
            raise ConnectionError(
                f"Cannot connect to Azure storage. Please check:\n"
                f"1. Account name: {self.azure_account}\n"
                f"2. Container: {self.azure_container}\n"
                f"3. Credentials\n"
                f"Error: {e}"
            )

    def _load_catchment(self) -> gpd.GeoDataFrame:
        """
        Load and validate catchment shapefile using analysis.catchment.load_catchment.

        Returns
        -------
        GeoDataFrame
            Loaded and validated catchment geometry.
        """
        gdf, _ = load_catchment(
            self.catchment_shp,
            target_crs=None,  # Keep original CRS, will reproject per-dataset
            merge_features=True,
            validate_aoi=True,
            validate_size=True,
            buffer_points_lines=True,
        )
        return gdf

    def _load_download_history(self) -> Dict:
        """Load download history from JSON log file."""
        if self.log_file.exists():
            with open(self.log_file, "r") as f:
                return json.load(f)
        return {"downloads": []}

    def _save_download_history(self):
        """Save download history to JSON log file."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "w") as f:
            json.dump(self.download_history, f, indent=2)

    def list_available_datasets(self) -> Dict:
        """
        List all available datasets in the catalog.

        Returns
        -------
        dict
            Dataset catalog with descriptions.
        """
        return self.dataset_catalog

    def get_dataset_info(self, category: str, subcategory: str) -> Dict:
        """
        Get information about a specific dataset.

        Parameters
        ----------
        category : str
            Dataset category (e.g., 'climate', 'soil').
        subcategory : str
            Dataset subcategory (e.g., 'temperature', 'properties').

        Returns
        -------
        dict
            Dataset information.
        """
        try:
            return self.dataset_catalog[category][subcategory]
        except KeyError:
            raise ValueError(f"Dataset not found: {category}/{subcategory}")

    def download_dataset(
        self,
        category: str,
        subcategory: str,
        time_range: Optional[Tuple[str, str]] = None,
        variables: Optional[List[str]] = None,
    ) -> Path:
        """
        Download a specific dataset clipped to catchment extent.

        Parameters
        ----------
        category : str
            Dataset category (e.g., 'climate').
        subcategory : str
            Dataset subcategory (e.g., 'temperature').
        time_range : tuple of str, optional
            Start and end dates for temporal data (e.g., ('2010-01-01', '2020-12-31')).
        variables : list of str, optional
            Specific variables to download. If None, downloads all.

        Returns
        -------
        Path
            Path to downloaded dataset.
        """
        # Get dataset info
        dataset_info = self.get_dataset_info(category, subcategory)

        print(f"Starting download: {category} --> {subcategory}")
        print("This may take a few minutes depending on the data size and your connection.")

        # Setup paths
        azure_path = f"{self.azure_container}/{dataset_info['path']}"
        output_path = build_dataset_path(
            self.output_base, category, subcategory, self.output_format
        )

        # Get catchment in dataset CRS
        catchment_reproj = reproject_catchment(self.catchment, dataset_info["crs"])
        bounds = catchment_reproj.total_bounds  # (minx, miny, maxx, maxy)

        # Open remote dataset
        try:
            store = self.fs.get_mapper(azure_path)
            # Try opening with consolidated metadata first, then fall back
            try:
                ds = xr.open_zarr(store, consolidated=True)
            except Exception:
                # Fall back to non-consolidated
                ds = xr.open_zarr(store, consolidated=False)

        except Exception as e:
            print(f"ERROR: Failed to open dataset: {e}")
            raise

        # Spatial subsetting
        ds_subset = self._spatial_subset(ds, bounds, catchment_reproj, dataset_info["crs"])

        # Temporal subsetting
        if time_range and dataset_info["temporal"]:
            ds_subset = self._temporal_subset(ds_subset, time_range)

        # Variable selection
        if variables:
            ds_subset = ds_subset[variables]

        # Remove existing if present
        remove_path_with_retry(output_path)

        print(f"Writing output to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to disk
        if self.output_format == "zarr":
            # Write to zarr v2 format for compatibility
            # Use safe_chunks=False to handle chunking mismatches from spatial subsetting
            ds_subset.to_zarr(
                output_path, mode="w", consolidated=True, zarr_format=2, safe_chunks=False
            )
        elif self.output_format == "dfs2":
            dfsio.create_file(
                ds_subset,
                output_path,
                varname=dataset_info.get("variable"),
                eumtype=dataset_info.get("eumtype"),
                eumunit=dataset_info.get("eumunit"),
            )
        else:
            # NetCDF output
            ds_subset.to_netcdf(output_path, mode="w", engine="netcdf4")

        # Log download
        self._log_download(category, subcategory, dataset_info, output_path, bounds, time_range)

        print(f"Download complete: {output_path.relative_to(self.output_base)}")
        return output_path

    def _spatial_subset(
        self,
        ds: xr.Dataset,
        bounds: Tuple[float, float, float, float],
        catchment_reproj: gpd.GeoDataFrame,
        dataset_crs: str,
    ) -> xr.Dataset:
        """
        Subset dataset by spatial bounds.

        Parameters
        ----------
        ds : xarray.Dataset
            Input dataset.
        bounds : tuple
            Bounding box (minx, miny, maxx, maxy).

        Returns
        -------
        xarray.Dataset
            Spatially subsetted dataset.
        """
        minx, miny, maxx, maxy = bounds

        # Identify spatial dimensions (common names)
        x_dim = None
        y_dim = None

        for dim in ["x", "lon", "longitude"]:
            if dim in ds.dims:
                x_dim = dim
                break

        for dim in ["y", "lat", "latitude"]:
            if dim in ds.dims:
                y_dim = dim
                break

        if not (x_dim and y_dim):
            print("WARNING: Could not identify spatial dimensions, returning full dataset")
            return ds

        # Expand bounds by a number of grid cells (buffer_cells)
        if self.mask_on_catchment:
            # Standardize dimension names for rioxarray compatibility
            print("Clipping dataset to catchment boundary")
            ds = ds.rename({y_dim: "y", x_dim: "x"})

            # Keep only variables with spatial dimensions
            spatial_vars = [v for v in ds.data_vars if {"y", "x"}.issubset(ds[v].dims)]
            ds = ds[spatial_vars]

            # Clip to catchment boundary
            ds.rio.write_crs(dataset_crs, inplace=True)
            ds = ds.rio.clip(catchment_reproj.geometry, catchment_reproj.crs, all_touched=True)

            # Clean up and restore standard coordinate names
            ds = ds.drop_vars("spatial_ref", errors="ignore").rename({"y": "lat", "x": "lon"})

        elif self.buffer_cells > 0:
            x_coord = ds[x_dim]
            y_coord = ds[y_dim]

            x_spacing = get_grid_resolution(x_coord, default=0.0)
            y_spacing = get_grid_resolution(y_coord, default=0.0)

            if x_spacing > 0 and y_spacing > 0:
                minx -= self.buffer_cells * x_spacing
                maxx += self.buffer_cells * x_spacing
                miny -= self.buffer_cells * y_spacing
                maxy += self.buffer_cells * y_spacing
                print(f"Applied {self.buffer_cells} cell buffer to bounds")

        # Use slice-based selection with nearest neighbor interpolation
        try:
            ds_subset = ds.sel({x_dim: slice(minx, maxx), y_dim: slice(miny, maxy)})

            # If we got empty dimensions, fall back to nearest neighbor
            if ds_subset.dims.get(x_dim, 0) == 0 or ds_subset.dims.get(y_dim, 0) == 0:
                print("Slice selection returned empty, using nearest neighbor selection")

                center_x = (minx + maxx) / 2
                center_y = (miny + maxy) / 2

                x_coord = ds[x_dim]
                y_coord = ds[y_dim]

                x_spacing = get_grid_resolution(x_coord, default=0.25)
                y_spacing = get_grid_resolution(y_coord, default=0.25)

                grid_size = max(2 * self.buffer_cells + 1, 1)
                x_expand = (grid_size * x_spacing) / 2
                y_expand = (grid_size * y_spacing) / 2

                minx_nn = center_x - x_expand
                maxx_nn = center_x + x_expand
                miny_nn = center_y - y_expand
                maxy_nn = center_y + y_expand

                print(f"Using {grid_size}x{grid_size} grid centered on catchment")

                x_mask = (x_coord >= minx_nn) & (x_coord <= maxx_nn)
                y_mask = (y_coord >= miny_nn) & (y_coord <= maxy_nn)

                x_in_range = x_coord[x_mask]
                y_in_range = y_coord[y_mask]

                if len(x_in_range) == 0 or len(y_in_range) == 0:
                    print("WARNING: Could not find any coordinates, returning full dataset")
                    return ds

                ds_subset = ds.sel({x_dim: x_in_range, y_dim: y_in_range})
                print(f"Found {len(x_in_range)} x {len(y_in_range)} coordinates in range")

        except Exception as e:
            print(f"ERROR: Selection failed: {e}, returning full dataset")
            return ds

        print(f"Subset shape: {dict(ds_subset.dims)}")
        return ds_subset

    def _temporal_subset(self, ds: xr.Dataset, time_range: Tuple[str, str]) -> xr.Dataset:
        """
        Subset dataset by time range.

        Parameters
        ----------
        ds : xarray.Dataset
            Input dataset.
        time_range : tuple of str
            (start_date, end_date) in ISO format.

        Returns
        -------
        xarray.Dataset
            Temporally subsetted dataset.
        """
        start, end = time_range

        time_dim = None
        for dim in ["time", "date", "t"]:
            if dim in ds.dims:
                time_dim = dim
                break

        if not time_dim:
            print("WARNING: No time dimension found, skipping temporal subsetting")
            return ds

        print(f"Temporal subsetting: {start} to {end}")
        ds_subset = ds.sel({time_dim: slice(start, end)})

        return ds_subset

    def _log_download(
        self,
        category: str,
        subcategory: str,
        info: Dict,
        output_path: Path,
        bounds: Tuple,
        time_range: Optional[Tuple],
    ):
        """Log download to history."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "subcategory": subcategory,
            "description": info["description"],
            "output_path": str(output_path),
            "bounds": list(bounds),
            "time_range": time_range,
            "catchment_shp": str(self.catchment_shp),
        }

        self.download_history["downloads"].append(log_entry)
        self._save_download_history()

    def download_all(self, time_range: Optional[Tuple[str, str]] = None):
        """
        Download all datasets in the catalog.

        Parameters
        ----------
        time_range : tuple of str, optional
            Time range for temporal datasets.
        """
        print("Starting batch download of all datasets")

        for category, subcategories in self.dataset_catalog.items():
            for subcategory in subcategories.keys():
                try:
                    self.download_dataset(category, subcategory, time_range=time_range)
                except Exception as e:
                    print(f"ERROR: Failed to download {category}/{subcategory}: {e}")
                    continue

        print("Batch download complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download PHISHES datasets from Azure")
    parser.add_argument("--catchment", type=str, required=True, help="Path to catchment shapefile")
    parser.add_argument("--output", type=str, required=True, help="Output base directory")
    parser.add_argument("--account", type=str, help="Azure storage account name")
    parser.add_argument("--credential", type=str, help="Azure SAS token")
    parser.add_argument(
        "--dataset", type=str, help="Specific dataset to download (format: category/subcategory)"
    )

    args = parser.parse_args()

    downloader = PDPDataDownloader(
        catchment=args.catchment,
        output_base=args.output,
        azure_account=args.account,
        azure_credential=args.credential,
    )

    if args.dataset:
        category, subcategory = args.dataset.split("/")
        downloader.download_dataset(category, subcategory)
    else:
        downloader.download_all()
