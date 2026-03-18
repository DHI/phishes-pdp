"""Forcing integration with data-download-tool catalog and downloader APIs."""

import importlib
import importlib.util
import json
import sys
import shutil
import types
from urllib.parse import unquote, urlparse
from pathlib import Path


def _get_installed_data_downloader_src_dir():
    """Return installed phishes-data-downloader src directory if available."""
    try:
        metadata = importlib.import_module("importlib.metadata")
        dist = metadata.distribution("phishes-data-downloader")
    except Exception:
        return None

    def _is_valid_src_root(path: Path):
        return (
            path.joinpath("core", "downloader.py").exists()
            and path.joinpath("analysis", "catchment.py").exists()
        )

    src_dir = dist.locate_file("src")
    src_dir_path = Path(src_dir)
    if src_dir_path.exists() and _is_valid_src_root(src_dir_path):
        return src_dir_path

    # Editable installs often keep sources outside site-packages.
    try:
        direct_url_text = dist.read_text("direct_url.json")
        if direct_url_text:
            direct_url = json.loads(direct_url_text)
            repo_url = direct_url.get("url", "")
            if repo_url.startswith("file://"):
                repo_path = Path(unquote(urlparse(repo_url).path.lstrip("/")))
                candidate_src = repo_path.joinpath("src")
                if candidate_src.exists() and _is_valid_src_root(candidate_src):
                    return candidate_src
                if repo_path.exists() and _is_valid_src_root(repo_path):
                    return repo_path
    except Exception:
        pass

    # Last-resort probe: infer source root from sys.path entries.
    for path_entry in sys.path:
        try:
            base = Path(path_entry)
        except Exception:
            continue

        if _is_valid_src_root(base):
            return base

    return None


def _load_module_from_file(module_name, file_path, is_package=False):
    """Load a Python module from an explicit file path."""
    submodule_paths = [str(file_path.parent)] if is_package else None
    spec = importlib.util.spec_from_file_location(
        module_name,
        str(file_path),
        submodule_search_locations=submodule_paths,
    )
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"Cannot create import spec for {module_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _import_data_downloader_via_runtime_package(src_dir):
    """Import data-downloader modules via an isolated runtime package namespace."""
    base_pkg = "_phishes_data_downloader_runtime"

    if base_pkg not in sys.modules:
        pkg = types.ModuleType(base_pkg)
        pkg.__path__ = [str(src_dir)]
        sys.modules[base_pkg] = pkg

    analysis_pkg_name = f"{base_pkg}.analysis"
    if analysis_pkg_name not in sys.modules:
        analysis_pkg = types.ModuleType(analysis_pkg_name)
        analysis_pkg.__path__ = [str(src_dir.joinpath("analysis"))]
        sys.modules[analysis_pkg_name] = analysis_pkg
    else:
        analysis_pkg = sys.modules[analysis_pkg_name]

    catchment_mod = _load_module_from_file(
        f"{analysis_pkg_name}.catchment",
        src_dir.joinpath("analysis", "catchment.py"),
    )

    # Export required names so downloader's `from ..analysis import ...` works.
    for attr_name in [
        "load_catchment",
        "validate_catchment_gdf",
        "reproject_catchment",
        "create_catchment_from_extent",
    ]:
        setattr(analysis_pkg, attr_name, getattr(catchment_mod, attr_name))

    core_pkg_name = f"{base_pkg}.core"
    if core_pkg_name not in sys.modules:
        core_pkg = types.ModuleType(core_pkg_name)
        core_pkg.__path__ = [str(src_dir.joinpath("core"))]
        sys.modules[core_pkg_name] = core_pkg

    downloader_mod = _load_module_from_file(
        f"{core_pkg_name}.downloader",
        src_dir.joinpath("core", "downloader.py"),
    )

    return downloader_mod, catchment_mod


def _import_data_downloader_modules():
    """Import data-download-tool modules from an installed package."""
    try:
        downloader_mod = importlib.import_module("core.downloader")
        catchment_mod = importlib.import_module("analysis.catchment")
        return downloader_mod, catchment_mod
    except (ModuleNotFoundError, ImportError) as exc:
        src_dir = _get_installed_data_downloader_src_dir()
        if src_dir is not None:
            try:
                downloader_mod, catchment_mod = (
                    _import_data_downloader_via_runtime_package(src_dir)
                )
                return downloader_mod, catchment_mod
            except Exception:
                pass

        raise ModuleNotFoundError(
            "data-download-tool modules could not be imported. Install with 'uv sync' or "
            "install directly: "
            'uv pip install "phishes-data-downloader @ git+https://github.com/DHI/phishes-pdp.git@main#subdirectory=data-download-tool"'
        ) from exc


def load_data_downloader_catalog():
    """Load data-download-tool dataset catalog YAML."""
    downloader_mod, _ = _import_data_downloader_modules()
    catalog_path = Path(downloader_mod.PDPDataDownloader.CATALOG_FILE)

    try:
        yaml = importlib.import_module("yaml")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency 'pyyaml'. Install project dependencies with 'uv sync'."
        ) from exc

    with open(catalog_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pgm_forcing_library():
    """Load PGM forcing mapping from data-downloader catalog.

    Expected shape in data-downloader catalog:

    pgm_forcings:
      precipitation:
        item_name: Precipitation Rate
        item_unit: mm/d
        ts_type: Mean Step Accumulated
        category: climate
        subcategory: era5_precipitation
        source_variable: tp
        output_filename: Precipitation.dfs2
        required: true
    """
    catalog = load_data_downloader_catalog()
    pgm_forcings = catalog.get("pgm_forcings")

    if not isinstance(pgm_forcings, dict) or not pgm_forcings:
        raise ValueError(
            "data-download-tool catalog must define top-level 'pgm_forcings' mapping."
        )

    required_fields = {
        "item_name",
        "item_unit",
        "ts_type",
        "category",
        "subcategory",
        "source_variable",
        "output_filename",
        "required",
    }

    validated = {}
    for forcing_key, meta in pgm_forcings.items():
        if not isinstance(meta, dict):
            raise ValueError(f"pgm_forcings.{forcing_key} must be a mapping")

        missing = sorted(required_fields - set(meta.keys()))
        if missing:
            raise ValueError(
                f"pgm_forcings.{forcing_key} missing fields: {', '.join(missing)}"
            )

        validated[forcing_key] = dict(meta)

    return validated


def build_forcing_download_plan(include_optional=False):
    """Build forcing availability plan using data-downloader catalog and pgm_forcings."""
    catalog = load_data_downloader_catalog()
    climate_catalog = catalog.get("climate", {})
    forcing_library = load_pgm_forcing_library()

    available = {}
    missing = {}

    for forcing_key, meta in forcing_library.items():
        if (not include_optional) and (not meta.get("required", True)):
            continue

        subcategory = meta["subcategory"]
        if subcategory in climate_catalog:
            available[forcing_key] = {
                **meta,
                "catalog_entry": climate_catalog[subcategory],
            }
        else:
            missing[forcing_key] = {
                **meta,
                "reason": f"Missing climate subcategory '{subcategory}' in dataset catalog",
            }

    return {
        "available": available,
        "missing": missing,
    }


def get_data_downloader_classes():
    """Import data-downloader classes from the installed package."""
    downloader_mod, catchment_mod = _import_data_downloader_modules()
    return downloader_mod.PDPDataDownloader, catchment_mod.create_catchment_from_extent


def _resolve_catchment_input(
    catchment_shapefile=None,
    extent=None,
    extent_crs="EPSG:4326",
):
    if catchment_shapefile:
        return Path(catchment_shapefile)

    if extent is None:
        raise ValueError(
            "Provide either catchment_shapefile or extent=[minx, miny, maxx, maxy]."
        )

    _, create_catchment_from_extent = get_data_downloader_classes()
    return create_catchment_from_extent(extent=extent, crs=extent_crs)


def download_forcing_dfs2_series(
    output_base,
    time_range,
    catchment_shapefile=None,
    extent=None,
    extent_crs="EPSG:4326",
    include_optional=False,
    strict_required=True,
    buffer_cells=1,
    mask_on_catchment=True,
):
    """Download and standardize forcing DFS2 grid series using data-download-tool."""
    if not time_range or len(time_range) != 2:
        raise ValueError(
            "time_range must be a tuple/list with two values: (start_date, end_date)"
        )

    plan = build_forcing_download_plan(include_optional=include_optional)

    if strict_required and plan["missing"]:
        missing_names = ", ".join(sorted(plan["missing"].keys()))
        raise ValueError(
            f"Required forcing datasets missing from data-download-tool catalog: {missing_names}"
        )

    PDPDataDownloader, _ = get_data_downloader_classes()
    catchment_input = _resolve_catchment_input(
        catchment_shapefile=catchment_shapefile,
        extent=extent,
        extent_crs=extent_crs,
    )

    output_base = Path(output_base)
    output_base.mkdir(parents=True, exist_ok=True)

    downloader = PDPDataDownloader(
        catchment=catchment_input,
        output_base=output_base,
        output_format="dfs2",
        buffer_cells=buffer_cells,
        mask_on_catchment=mask_on_catchment,
    )

    standardized_dir = output_base.joinpath("pgm_forcings")
    standardized_dir.mkdir(parents=True, exist_ok=True)

    downloaded = {}
    standardized = {}
    for forcing_key, meta in plan["available"].items():
        ds_path = downloader.download_dataset(
            category=meta["category"],
            subcategory=meta["subcategory"],
            time_range=time_range,
            variables=[meta["source_variable"]],
        )
        downloaded[forcing_key] = ds_path

        output_name = meta["output_filename"]
        target_path = standardized_dir.joinpath(output_name)
        shutil.copy2(ds_path, target_path)
        standardized[forcing_key] = target_path

    return {
        "downloaded": downloaded,
        "standardized": standardized,
        "missing": plan["missing"],
        "output_dir": standardized_dir,
    }
