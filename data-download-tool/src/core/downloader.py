"""
PHISHES Digital Platform - Data Downloader

This module downloads Zarr datasets from Azure Blob Storage based on user-provided
catchment polygons. It handles spatial subsetting, coordinate transformations, and
local storage management. Output can be written as NetCDF, Zarr, or DFS2.

Author: DHI A/S
Date: January 2026

"""

import json
import os
import shutil
import yaml
from pathlib import Path
from typing import Any, Optional, List, Dict, Tuple, Union
from datetime import datetime

import adlfs
import geopandas as gpd
import rioxarray  # noqa: F401 - enables .rio accessor on xarray objects
import xarray as xr
from shapely.ops import unary_union

from .utils import build_dataset_path, get_grid_resolution, remove_path_with_retry
from ..analysis import load_catchment, validate_catchment_gdf, reproject_catchment
from . import dfsio
from . import cogio
from . import geoparquetio

try:
    # Optional convenience: read restricted-dataset tokens from a .env file. Tokens can
    # always be exported directly, so a missing python-dotenv only disables .env lookup.
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - exercised via the _DOTENV_AVAILABLE flag
    find_dotenv = load_dotenv = None

_DOTENV_AVAILABLE = load_dotenv is not None


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
    Open datasets need no configuration; the account, container and read-only SAS
    token for them are built in. Access-restricted catalog entries declare a
    ``credential_env`` field naming the environment variable that must hold the SAS
    token for their container (e.g. ``PDP_AFTER_END_SAS``). Those variables are read
    from the process environment, which is populated from a ``.env`` file on init if
    one is found; see ``.env.example``. Already-exported variables take precedence
    over the ``.env`` file.
    """

    # Azure Storage Configuration
    DEFAULT_AZURE_ACCOUNT = "phishesdatastore"
    DEFAULT_AZURE_CONTAINER = "zarr"
    DEFAULT_AZURE_CREDENTIAL = "sp=rl&st=2026-02-09T10:22:14Z&se=2034-12-31T18:37:14Z&spr=https&sv=2024-11-04&sr=c&sig=buOnKjOpmc%2BDZw7lnyWhMf4z5cTGVKqYHzXRnA8OTBM%3D"

    DEFAULT_OUTPUT_FORMAT = "nc"
    # Raster outputs flow through the xarray pipeline; vector (GeoParquet) outputs
    # flow through GeoPandas. Both sets are accepted by output_format validation.
    RASTER_OUTPUT_FORMATS = {"nc", "zarr", "dfs2", "tif"}
    VECTOR_OUTPUT_FORMATS = {"parquet", "shp"}
    SUPPORTED_OUTPUT_FORMATS = RASTER_OUTPUT_FORMATS | VECTOR_OUTPUT_FORMATS
    CATALOG_FILE = Path(__file__).parent.joinpath("dataset_catalog.yaml")
    COG_CATALOG_FILE = Path(__file__).parent.joinpath("cog_catalog.yaml")
    GEOPARQUET_CATALOG_FILE = Path(__file__).parent.joinpath("geoparquet_catalog.yaml")
    PARTNER_CATALOG_FILE = Path(__file__).parent.joinpath("partner_data_catalog.yaml")

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

        self._load_env_file()

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

    @staticmethod
    def _load_env_file():
        """Populate the environment from the nearest .env file, if one is discoverable.

        Restricted catalog entries read their SAS token from the environment. The search
        runs upwards from the working directory, and ``override=False`` means a variable
        already exported in the shell or CI wins over the file. A no-op when
        ``python-dotenv`` is not installed - export the variable instead.
        """
        if not _DOTENV_AVAILABLE:
            return
        load_dotenv(find_dotenv(usecwd=True), override=False)

    def _load_catalog(self) -> Dict:
        """Load the dataset catalog, merging the COG, GeoParquet, and partner catalogs into it.

        Zarr time-series datasets live in ``dataset_catalog.yaml``, COG raster
        layers in ``cog_catalog.yaml``, GeoParquet vector layers in
        ``geoparquet_catalog.yaml``, and partner zip bundles in
        ``partner_data_catalog.yaml``; all are merged per-category so they share a
        single namespace for ``download_dataset(category, subcategory)``.
        """
        if not self.CATALOG_FILE.exists():
            raise FileNotFoundError(f"Dataset catalog not found: {self.CATALOG_FILE}")
        with open(self.CATALOG_FILE, "r") as f:
            catalog = yaml.safe_load(f) or {}

        for extra_catalog in (
            self.COG_CATALOG_FILE,
            self.GEOPARQUET_CATALOG_FILE,
            self.PARTNER_CATALOG_FILE,
        ):
            if extra_catalog.exists():
                with open(extra_catalog, "r") as f:
                    entries = yaml.safe_load(f) or {}
                for category, subcategories in entries.items():
                    catalog.setdefault(category, {}).update(subcategories)

        return catalog

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

    def dataset_requires_token(self, category: str, subcategory: str) -> Optional[str]:
        """
        Return the environment variable gating this dataset, or None if it is open.

        Parameters
        ----------
        category : str
            Dataset category (e.g., 'restricted_partner').
        subcategory : str
            Dataset subcategory (e.g., 'czech_globe_ms4_full').

        Returns
        -------
        str or None
            Name of the environment variable that must hold the SAS token, or None
            for datasets that need no user-supplied credential.
        """
        return self.get_dataset_info(category, subcategory).get("credential_env") or None

    def is_dataset_accessible(self, category: str, subcategory: str) -> bool:
        """
        Check whether this dataset can be downloaded with the current credentials.

        Purely local: reads the catalog and the environment, never the network, so
        restricted datasets stay listable even when their token is missing.

        Parameters
        ----------
        category : str
            Dataset category.
        subcategory : str
            Dataset subcategory.

        Returns
        -------
        bool
            True if the dataset is open, or its required token is set.
        """
        env_var = self.dataset_requires_token(category, subcategory)
        if env_var is None:
            return True
        return bool(os.environ.get(env_var, "").strip())

    def open_dataset(self, category: str, subcategory: str) -> xr.Dataset:
        """
        Open a remote dataset from Azure Blob Storage.

        Parameters
        ----------
        category : str
            Dataset category (e.g., 'climate').
        subcategory : str
            Dataset subcategory (e.g., 'temperature').

        Returns
        -------
        xarray.Dataset
            The opened remote dataset (lazy-loaded).
        """
        dataset_info = self.get_dataset_info(category, subcategory)

        print(f"Opening remote dataset: {category} --> {subcategory}")

        if dataset_info.get("format", "zarr") == "cog":
            return self._open_cog_dataset(dataset_info)

        azure_path = f"{self.azure_container}/{dataset_info['path']}"
        try:
            store = self.fs.get_mapper(azure_path)
            ds = self._open_zarr_store(store)
        except Exception as e:
            print(f"ERROR: Failed to open dataset: {e}")
            raise

        return ds

    @staticmethod
    def _open_zarr_store(store) -> xr.Dataset:
        """Open a Zarr store, tolerating stores whose metadata mixes Zarr v2/v3.

        Some stores carry both a Zarr v2 ``.zmetadata`` and a stray v3
        ``zarr.json`` group marker. zarr-python then reads the (array-less) v3
        group and returns an *empty* dataset without raising, so a plain
        consolidated/non-consolidated fallback silently yields no variables.
        Try consolidated, non-consolidated, then an explicit ``zarr_format=2``
        read, and take the first result that actually exposes data variables.
        """
        attempts = (
            {"consolidated": True},
            {"consolidated": False},
            {"consolidated": False, "zarr_format": 2},
        )
        last_err = None
        for kwargs in attempts:
            try:
                ds = xr.open_zarr(store, **kwargs)
            except Exception as e:  # noqa: BLE001 - try the next strategy
                last_err = e
                continue
            if len(ds.data_vars) > 0:
                return ds
        if last_err is not None:
            raise last_err
        raise ValueError("Opened Zarr store contains no data variables")

    def _open_cog_dataset(self, dataset_info: Dict) -> xr.Dataset:
        """
        Open a COG dataset (single file or tiled mosaic) from Azure Blob Storage.

        Parameters
        ----------
        dataset_info : dict
            Catalog entry with ``path``, ``crs``, ``variable``, optional
            ``container`` (defaults to the downloader's container), ``tiled``,
            and ``anon`` (use anonymous access for the COG container).

        Returns
        -------
        xarray.Dataset
            Dataset with ``y``/``x`` dimensions and CRS set.
        """
        container = dataset_info.get("container", self.azure_container)

        # Catchment bounds in the dataset CRS, used to select intersecting tiles.
        catchment_reproj = reproject_catchment(self.catchment, dataset_info["crs"])
        bbox = tuple(catchment_reproj.total_bounds)

        # Resolve the list of tile URIs. For a tiled mosaic we list the prefix via the
        # filesystem; for a single file we use its path directly. The blobs are read by
        # GDAL/rasterio from their HTTPS URLs (range reads) rather than streamed through
        # the filesystem object, which is much faster for many tiles.
        if dataset_info.get("tiled", False):
            fs = self._dataset_filesystem(dataset_info)
            prefix = f"{container}/{dataset_info['path']}".rstrip("/")
            blob_paths = sorted(fs.glob(prefix + "/**/*.tif"))
            if not blob_paths:
                raise FileNotFoundError(f"No .tif tiles found under prefix: {prefix}")
        else:
            blob_paths = [f"{container}/{dataset_info['path']}"]

        anon = dataset_info.get("anon", False)
        credential = self._dataset_credential(dataset_info)
        uris = [self._blob_url(p, anon=anon, credential=credential) for p in blob_paths]

        try:
            return cogio.open_cog(
                uris,
                variable=dataset_info["variable"],
                crs=dataset_info["crs"],
                bbox=bbox,
            )
        except Exception as e:
            print(f"ERROR: Failed to open COG dataset: {e}")
            raise

    def _blob_url(
        self, blob_path: str, anon: bool = False, credential: Optional[str] = None
    ) -> str:
        """Build an HTTPS blob URL (with SAS token unless anonymous) for GDAL/vsicurl."""
        url = f"https://{self.azure_account}.blob.core.windows.net/{blob_path}"
        if credential is None:
            credential = self.azure_credential
        if not anon and credential:
            url += "?" + credential.lstrip("?")
        return url

    def _dataset_filesystem(self, dataset_info: Dict):
        """Return the filesystem to read a catalog entry with, honouring its access mode.

        Containers other than the default Zarr one may use different credentials.
        Three modes, in precedence order:

        - ``credential_env: <VAR>`` -> SAS token supplied by the user through that
          environment variable (typically via a ``.env`` file). Access-restricted.
        - ``anon: true`` -> cached anonymous filesystem (public container).
        - neither -> the main filesystem with the built-in read-only SAS token.
        """
        env_var = dataset_info.get("credential_env")
        if env_var:
            return self._env_credential_filesystem(env_var, dataset_info)
        if not dataset_info.get("anon", False):
            return self.fs
        if getattr(self, "_anon_fs", None) is None:
            self._anon_fs = adlfs.AzureBlobFileSystem(account_name=self.azure_account, anon=True)
        return self._anon_fs

    def _dataset_credential(self, dataset_info: Dict) -> Optional[str]:
        """Return the SAS token for a catalog entry, or None for anonymous access."""
        env_var = dataset_info.get("credential_env")
        if env_var:
            return self._require_token(env_var, dataset_info)
        if dataset_info.get("anon", False):
            return None
        return self.azure_credential

    def _require_token(self, env_var: str, dataset_info: Dict) -> str:
        """Read a restricted dataset's SAS token from the environment, or explain how to set it."""
        token = os.environ.get(env_var, "").strip()
        if not token:
            name = dataset_info.get("display_name", "This dataset")
            container = dataset_info.get("container", self.azure_container)
            where = (
                "in a .env file next to your notebook (or export it)"
                if _DOTENV_AVAILABLE
                # Without python-dotenv installed, .env files are never read.
                else "as an exported environment variable (python-dotenv is not installed, "
                "so .env files are not read)"
            )
            raise PermissionError(
                f"'{name}' is access-restricted. "
                f"Set {env_var} {where} with the SAS token for container "
                f"'{container}'. See .env.example. "
                f"Contact the data owner to request a token."
            )
        return token.lstrip("?")

    def _env_credential_filesystem(self, env_var: str, dataset_info: Dict):
        """Return a cached filesystem authenticated with a SAS token from the environment."""
        token = self._require_token(env_var, dataset_info)
        env_filesystems: Dict[str, Any] = getattr(self, "_env_fs", None) or {}
        if env_var not in env_filesystems:
            env_filesystems[env_var] = adlfs.AzureBlobFileSystem(
                account_name=self.azure_account, sas_token=token
            )
            self._env_fs = env_filesystems
        return env_filesystems[env_var]

    def _download_geoparquet(self, category: str, subcategory: str) -> Path:
        """
        Download a GeoParquet (vector) dataset clipped to the catchment.

        Vector data is a GeoDataFrame, not a raster, so it bypasses the xarray
        ``open_dataset``/``process_dataset``/``save_dataset`` pipeline: this method
        reads, spatially filters (keeping intersecting features whole), and writes
        the result as GeoParquet or Shapefile in one pass.

        Parameters
        ----------
        category : str
            Dataset category (e.g., 'soil').
        subcategory : str
            Dataset subcategory (e.g., 'lucas_2018_bulk_density').

        Returns
        -------
        Path
            Path to the saved vector dataset.
        """
        info = self.get_dataset_info(category, subcategory)
        container = info.get("container", self.azure_container)

        # Catchment bounds and geometry in the dataset CRS.
        catchment_reproj = reproject_catchment(self.catchment, info["crs"])
        bbox = tuple(catchment_reproj.total_bounds)
        geom = unary_union(catchment_reproj.geometry)

        fs = self._dataset_filesystem(info)
        blob_path = f"{container}/{info['path']}"

        try:
            gdf = geoparquetio.open_geoparquet(
                blob_path,
                mask_geometry=geom,
                mask_crs=info["crs"],
                bbox=bbox,
                crs=info["crs"],
                filesystem=fs,
            )
        except Exception as e:
            print(f"ERROR: Failed to open GeoParquet dataset: {e}")
            raise

        # Vector data can only be written as a vector format; if the downloader's
        # output_format is a raster format, fall back to GeoParquet.
        if self.output_format in self.VECTOR_OUTPUT_FORMATS:
            fmt = self.output_format
        else:
            fmt = "parquet"
            print(
                f"Output format '{self.output_format}' is raster-only; "
                f"writing vector dataset as '{fmt}' instead."
            )

        output_path = build_dataset_path(self.output_base, category, subcategory, fmt)
        remove_path_with_retry(output_path)

        print(f"Writing output to: {output_path}")
        geoparquetio.write_geoparquet(gdf, output_path, fmt)

        self._log_download(category, subcategory, info, output_path, bbox, None)

        print(f"Download complete: {output_path.relative_to(self.output_base)}")
        return output_path

    def _download_zip(self, category: str, subcategory: str) -> Path:
        """
        Download a partner zip bundle whole and as-is.

        Partner datasets in the ``external-shared-open-data`` container are zip
        files with mixed/arbitrary contents (shapefiles, CSVs, metadata). They are
        not gridded or vector-clippable, so this method bypasses every processing
        pipeline: it copies the ``.zip`` blob to the output folder unchanged, with
        no extraction and no catchment clipping. The downloader's ``output_format``
        is ignored; the file is always written as ``.zip``.

        Entries in a restricted container (``credential_env`` set) resolve their SAS
        token from the environment first, so a missing token raises ``PermissionError``
        before anything is written.

        Parameters
        ----------
        category : str
            Dataset category (e.g., 'partner').
        subcategory : str
            Dataset subcategory (e.g., 'czech_globe_ms4').

        Returns
        -------
        Path
            Path to the downloaded zip file.
        """
        info = self.get_dataset_info(category, subcategory)
        container = info.get("container", self.azure_container)

        fs = self._dataset_filesystem(info)
        blob_path = f"{container}/{info['path']}"

        if self.output_format != "zip":
            print(
                f"Output format '{self.output_format}' is ignored for zip entries; "
                "the partner bundle is delivered verbatim as '.zip'."
            )

        output_path = build_dataset_path(self.output_base, category, subcategory, "zip")
        remove_path_with_retry(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Downloading zip bundle to: {output_path}")
        try:
            # Stream the blob rather than fs.get(): fsspec's get() expands the remote
            # path first, which needs *list* permission on the container. A restricted
            # bundle's SAS token may be read-only (sp=r), so copy the bytes directly.
            with fs.open(blob_path, "rb") as remote, open(output_path, "wb") as local:
                shutil.copyfileobj(remote, local)
        except Exception as e:
            print(f"ERROR: Failed to download zip bundle: {e}")
            if info.get("credential_env"):
                print(
                    f"If this is an authorization error, check that {info['credential_env']} "
                    f"holds a current SAS token with read access to '{container}' "
                    "(tokens expire)."
                )
            # Never leave a partial file behind for the next run to mistake for a download.
            remove_path_with_retry(output_path)
            raise

        self._log_download(
            category, subcategory, info, output_path, tuple(self.catchment.total_bounds), None
        )

        print(f"Download complete: {output_path.relative_to(self.output_base)}")
        return output_path

    def process_dataset(
        self,
        ds: xr.Dataset,
        category: str,
        subcategory: str,
        time_range: Optional[Tuple[str, str]] = None,
        variables: Optional[List[str]] = None,
    ) -> xr.Dataset:
        """
        Apply spatial subsetting, temporal subsetting, and variable selection.

        Parameters
        ----------
        ds : xarray.Dataset
            Input dataset (e.g., from :meth:`open_dataset`).
        category : str
            Dataset category (e.g., 'climate').
        subcategory : str
            Dataset subcategory (e.g., 'temperature').
        time_range : tuple of str, optional
            Start and end dates for temporal data (e.g., ('2010-01-01', '2020-12-31')).
        variables : list of str, optional
            Specific variables to keep. If None, keeps all.

        Returns
        -------
        xarray.Dataset
            Processed (subsetted) dataset.
        """
        dataset_info = self.get_dataset_info(category, subcategory)

        # Get catchment in dataset CRS
        catchment_reproj = reproject_catchment(self.catchment, dataset_info["crs"])
        bounds = catchment_reproj.total_bounds  # (minx, miny, maxx, maxy)

        # Spatial subsetting
        ds = self._spatial_subset(ds, bounds, catchment_reproj, dataset_info["crs"])

        # Temporal subsetting
        if time_range and dataset_info["temporal"]:
            ds = self._temporal_subset(ds, time_range)

        # Variable selection
        if variables:
            ds = ds[variables]

        return ds

    def save_dataset(
        self,
        ds: xr.Dataset,
        category: str,
        subcategory: str,
        time_range: Optional[Tuple[str, str]] = None,
    ) -> Path:
        """
        Save a processed dataset to disk and log the download.

        Parameters
        ----------
        ds : xarray.Dataset
            Dataset to save (e.g., from :meth:`process_dataset`).
        category : str
            Dataset category (e.g., 'climate').
        subcategory : str
            Dataset subcategory (e.g., 'temperature').
        time_range : tuple of str, optional
            Time range used during processing (logged for reference).

        Returns
        -------
        Path
            Path to the saved dataset.
        """
        dataset_info = self.get_dataset_info(category, subcategory)

        output_path = build_dataset_path(
            self.output_base, category, subcategory, self.output_format
        )

        # Remove existing if present
        remove_path_with_retry(output_path)

        print(f"Writing output to: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to disk
        if self.output_format == "zarr":
            ds.to_zarr(output_path, mode="w", consolidated=True, zarr_format=2, safe_chunks=False)
        elif self.output_format == "dfs2":
            dfsio.create_file(
                ds,
                output_path,
                varname=dataset_info.get("variable"),
                eumtype=dataset_info.get("eumtype"),
                eumunit=dataset_info.get("eumunit"),
            )
        elif self.output_format == "tif":
            cogio.write_cog(
                ds,
                output_path,
                crs=dataset_info["crs"],
                varname=dataset_info.get("variable"),
            )
        elif self.output_format in self.VECTOR_OUTPUT_FORMATS:
            raise ValueError(
                f"Output format '{self.output_format}' is vector-only and cannot be "
                f"used for the raster dataset {category}/{subcategory}. "
                f"Use one of {sorted(self.RASTER_OUTPUT_FORMATS)}."
            )
        else:
            ds.to_netcdf(output_path, mode="w", engine="netcdf4")

        # Log download
        catchment_reproj = reproject_catchment(self.catchment, dataset_info["crs"])
        bounds = catchment_reproj.total_bounds
        self._log_download(category, subcategory, dataset_info, output_path, bounds, time_range)

        print(f"Download complete: {output_path.relative_to(self.output_base)}")
        return output_path

    def download_dataset(
        self,
        category: str,
        subcategory: str,
        time_range: Optional[Tuple[str, str]] = None,
        variables: Optional[List[str]] = None,
    ) -> Path:
        """
        Download a specific dataset clipped to catchment extent.

        Convenience method that calls :meth:`open_dataset`, :meth:`process_dataset`,
        and :meth:`save_dataset` in sequence.

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
        print(f"Starting download: {category} --> {subcategory}")
        print("This may take a few minutes depending on the data size and your connection.")

        # Non-raster datasets bypass the xarray open/process/save pipeline: partner
        # zip bundles are copied whole, and vector (GeoParquet) layers use a
        # dedicated GeoPandas path.
        fmt = self.get_dataset_info(category, subcategory).get("format")
        if fmt == "zip":
            return self._download_zip(category, subcategory)
        if fmt == "geoparquet":
            return self._download_geoparquet(category, subcategory)

        ds = self.open_dataset(category, subcategory)
        ds = self.process_dataset(ds, category, subcategory, time_range, variables)
        return self.save_dataset(ds, category, subcategory, time_range)

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

            # The clip is the spatial subset; return it directly. Falling through to the
            # slice-based selection below would re-subset and, for rasters with descending
            # latitude (e.g. COG DEM tiles), collapse to the nearest-neighbor fallback grid.
            print(f"Subset shape: {dict(ds.sizes)}")
            return ds

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
            if ds_subset.sizes.get(x_dim, 0) == 0 or ds_subset.sizes.get(y_dim, 0) == 0:
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

        print(f"Subset shape: {dict(ds_subset.sizes)}")
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
