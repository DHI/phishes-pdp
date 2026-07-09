import os
import sys
from importlib.util import find_spec
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


def _ensure_bundled_proj_data():
    """Prefer the venv's bundled PROJ data for rasterio/GDAL during tests.

    A system-wide ``PROJ_LIB`` (e.g. from a PostgreSQL/PostGIS install) can shadow
    rasterio's bundled ``proj.db`` and break CRS lookups. Point PROJ at rasterio's
    own data unless it already resolves inside this project's environment. Must run
    before rasterio is imported, so it lives at conftest import time.
    """
    current = os.environ.get("PROJ_DATA") or os.environ.get("PROJ_LIB")
    if current and str(PACKAGE_ROOT) in str(Path(current).resolve()):
        return

    spec = find_spec("rasterio")
    if not spec or not spec.submodule_search_locations:
        return
    bundled = Path(list(spec.submodule_search_locations)[0]).joinpath("proj_data")
    if bundled.joinpath("proj.db").exists():
        os.environ["PROJ_DATA"] = str(bundled)
        os.environ["PROJ_LIB"] = str(bundled)


_ensure_bundled_proj_data()
