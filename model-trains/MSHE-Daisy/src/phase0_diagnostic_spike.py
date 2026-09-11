from __future__ import annotations

import argparse
import json
import os
import re
import subprocess as sp
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETUP = (
    REPO_ROOT / "data" / "Cernici_060126_Test02_2" / "Cernici16_Ben_v100_DAISYinput.she"
)
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "docs" / "investigations" / "phase0"
DEFAULT_OUTPUT = DEFAULT_ARTIFACT_DIR / "phase0_diagnostic_spike.json"
MIKE_ZERO_CANDIDATE_YEARS = ("2025", "2026", "2024")
THETA_PATTERN = re.compile(r"Theta([RS])\s*=\s*([-+0-9.eE]+)")
KNOWN_PARAM_IDS = {
    "OL_D": 61,
    "UZ_WC": 118,
    "UZ_SZ_EX_POSUP": 122,
    "SZ_LEAK_FLX": 242,
    "SZ_LEAK_FLO": 318,
    "SZDR_IN_FLO": 326,
    "OLDR_IN_FLO": 361,
}


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


load_dotenv(REPO_ROOT / ".env")


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def resolve_setup_path(cli_value: str | None) -> Path:
    if cli_value:
        return resolve_path(cli_value)
    return DEFAULT_SETUP.resolve()


def resolve_mike_zero_x64(cli_value: str | None) -> Path:
    candidates: list[Path] = []

    if cli_value:
        candidates.append(resolve_path(cli_value))
    else:
        env_path = os.environ.get("MIKE_ZERO_X64")
        if env_path:
            candidates.append(Path(env_path).expanduser())

        for year in MIKE_ZERO_CANDIDATE_YEARS:
            candidates.append(
                Path(rf"C:/Program Files (x86)/DHI/MIKE Zero/{year}/bin/x64")
            )

    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not resolve a MIKE Zero x64 installation. "
        "Provide --mike-zero-x64 or install MIKE Zero 2026/2025/2024."
    )


def write_probe_setup(setup_path: Path) -> Path:
    import mikeio

    probe_setup = setup_path.with_name(
        setup_path.stem + "_noplugin_nom1d_probe" + setup_path.suffix
    )
    pfs = mikeio.PfsDocument(str(setup_path), unique_keywords=False)
    pfs.MIKESHE_FLOWMODEL.SimSpec.ModelComp.Plugins = 0
    pfs.MIKESHE_FLOWMODEL.SimSpec.ModelComp.River = 0
    pfs.MIKESHE_FLOWMODEL.M1D.RiverCoupling = 0

    try:
        pfs.MIKESHE_FLOWMODEL.Plugins.PyResolve = 0
    except Exception:
        pass

    pfs.write(str(probe_setup))
    return probe_setup.resolve()


def find_sample_cell() -> tuple[int, int]:
    from src.spatial_mapping import DEFAULT_SPATIAL_MAPPING

    first_cell = next(iter(DEFAULT_SPATIAL_MAPPING.coupled_cells()))
    return first_cell


def extract_theta_bounds(setup_directory: Path) -> dict[str, Any]:
    uz_directory = setup_directory / "06_UZ"
    theta_r_values: set[float] = set()
    theta_s_values: set[float] = set()
    source_files: list[str] = []

    if not uz_directory.exists():
        return {
            "uz_directory": str(uz_directory),
            "source_files": source_files,
            "theta_r_values": [],
            "theta_s_values": [],
        }

    for uzs_file in sorted(uz_directory.glob("*.uzs")):
        source_files.append(str(uzs_file))
        text = uzs_file.read_text(encoding="utf-8", errors="ignore")
        for kind, raw_value in THETA_PATTERN.findall(text):
            value = float(raw_value)
            if kind == "R":
                theta_r_values.add(value)
            else:
                theta_s_values.add(value)

    return {
        "uz_directory": str(uz_directory),
        "source_files": source_files,
        "theta_r_values": sorted(theta_r_values),
        "theta_s_values": sorted(theta_s_values),
    }


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value


def run_subprocess_probe(
    script_path: Path,
    probe_setup: Path,
    mike_zero_x64: Path,
    sample_row: int,
    sample_col: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script_path),
        "--internal-runtime-probe",
        "--probe-setup",
        str(probe_setup),
        "--mike-zero-x64",
        str(mike_zero_x64),
        "--sample-row",
        str(sample_row),
        "--sample-col",
        str(sample_col),
    ]
    result = sp.run(command, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        raise RuntimeError(
            "Runtime probe failed.\n"
            f"stdout:\n{result.stdout}\n\n"
            f"stderr:\n{result.stderr}"
        )

    return json.loads(result.stdout)


def resolve_runtime_param_type(ms: Any, name: str) -> tuple[int, str]:
    try:
        return int(getattr(ms.paramTypes, name)), "runtime_name"
    except AttributeError:
        if name in KNOWN_PARAM_IDS:
            return KNOWN_PARAM_IDS[name], "known_param_id_fallback"
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MIKE SHE Phase 0 API diagnostic spike."
    )
    parser.add_argument("--setup", help="Path to the MIKE SHE .she setup file.")
    parser.add_argument(
        "--mike-zero-x64",
        help="Path to the MIKE Zero bin/x64 folder to use for the runtime probe.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the JSON diagnostic report.",
    )
    parser.add_argument(
        "--internal-runtime-probe",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--probe-setup", help=argparse.SUPPRESS)
    parser.add_argument("--sample-row", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--sample-col", type=int, help=argparse.SUPPRESS)
    return parser.parse_args()


def internal_runtime_probe(args: argparse.Namespace) -> int:
    probe_setup = resolve_path(args.probe_setup)
    mike_zero_x64 = resolve_mike_zero_x64(args.mike_zero_x64)

    sys.path.insert(0, str(mike_zero_x64))
    import MShePy as ms

    before_init_names = {
        name: hasattr(ms.paramTypes, name)
        for name in (
            "OL_D",
            "OLDR_IN_FLO",
            "SZ_LEAK_FLO",
            "SZ_LEAK_FLX",
            "UZ_SZ_EX_POSUP",
            "UZ_WC",
        )
    }

    pp_exe = Path(ms.__file__).resolve().with_name("MShe_Preprocessor.exe")
    pp_result = sp.run(
        [str(pp_exe), str(probe_setup)],
        capture_output=True,
        text=True,
        cwd=str(probe_setup.parent),
        check=False,
    )
    if pp_result.returncode != 0:
        raise RuntimeError(
            f"MIKE SHE preprocessor failed with exit code {pp_result.returncode}.\n"
            f"stdout:\n{pp_result.stdout}\n\n"
            f"stderr:\n{pp_result.stderr}"
        )

    ms.wm.initialize(str(probe_setup))
    first_step = ms.wm.performTimeStep()

    origin_x, origin_y = ms.wm.gridCellToCoord(0, 0)
    east_x, east_y = ms.wm.gridCellToCoord(1, 0)
    north_x, north_y = ms.wm.gridCellToCoord(0, 1)
    cell_dx = east_x - origin_x
    cell_dy = north_y - origin_y

    key_param_names = [
        "OL_D",
        "OLDR_S",
        "OLDR_IN_FLO",
        "OLDR_IN_FLX",
        "SZ_LEAK_FLO",
        "SZ_LEAK_FLX",
        "UZ_SZ_EX_POSUP",
        "UZ_WC",
        "SZDR_IN_FLO",
        "OL_SOURCE",
        "OL_H",
    ]
    dataset_probes: dict[str, Any] = {}

    for name in key_param_names:
        try:
            ptype, resolution_method = resolve_runtime_param_type(ms, name)
        except AttributeError:
            dataset_probes[name] = {"available_after_init": False}
            continue

        probe_result: dict[str, Any] = {
            "available_after_init": True,
            "param_id": int(ptype),
            "resolution_method": resolution_method,
        }

        try:
            start_time, end_time, data = ms.wm.getValues(ptype)
            probe_result["get_values"] = {
                "success": True,
                "start_time": _to_jsonable(start_time),
                "end_time": _to_jsonable(end_time),
                "dataset_len": len(data),
                "sample_value": _to_jsonable(data[args.sample_row][args.sample_col]),
            }
            try:
                ms.wm.setValues(data)
                probe_result["set_values_from_current"] = {"success": True}
            except Exception as exc:
                probe_result["set_values_from_current"] = {
                    "success": False,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
        except Exception as exc:
            probe_result["get_values"] = {
                "success": False,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }

        try:
            dataset = ms.dataset(ptype)
            probe_result["dataset_factory"] = {
                "success": True,
                "dataset_len": len(dataset),
                "sample_value": _to_jsonable(dataset[args.sample_row][args.sample_col]),
            }
            try:
                ms.wm.setValues(dataset)
                probe_result["set_values_from_dataset"] = {"success": True}
            except Exception as exc:
                probe_result["set_values_from_dataset"] = {
                    "success": False,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
        except Exception as exc:
            probe_result["dataset_factory"] = {
                "success": False,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }

        dataset_probes[name] = probe_result

    registry_names = [name for name in dir(ms.paramTypes) if not name.startswith("_")]
    runtime_report = {
        "module_file": str(ms.__file__),
        "mike_zero_x64": str(mike_zero_x64),
        "probe_setup": str(probe_setup),
        "param_types_visible_before_initialize": before_init_names,
        "param_type_names_matching_wc_porosity_theta": [
            name
            for name in registry_names
            if any(token in name for token in ("THETA", "POR", "SAT", "RES", "WC"))
        ],
        "sim_period": _to_jsonable(ms.wm.simPeriod()),
        "first_step": _to_jsonable(first_step),
        "grid_geo_info": _to_jsonable(ms.wm.gridGeoInfo()),
        "grid_metrics": {
            "cell_origin_center": _to_jsonable((origin_x, origin_y)),
            "cell_dx_m": cell_dx,
            "cell_dy_m": cell_dy,
            "cell_area_m2": cell_dx * cell_dy,
        },
        "sample_cell": {"row": args.sample_row, "col": args.sample_col},
        "dataset_probes": dataset_probes,
    }

    ms.wm.terminate(True)
    print(json.dumps(runtime_report, indent=2))
    return 0


def main() -> int:
    args = parse_args()
    if args.internal_runtime_probe:
        return internal_runtime_probe(args)

    setup_path = resolve_setup_path(args.setup)
    mike_zero_x64 = resolve_mike_zero_x64(args.mike_zero_x64)
    probe_setup = write_probe_setup(setup_path)
    sample_row, sample_col = find_sample_cell()
    runtime_report = run_subprocess_probe(
        Path(__file__).resolve(),
        probe_setup,
        mike_zero_x64,
        sample_row,
        sample_col,
    )

    def probe_success(name: str, field: str) -> bool:
        return bool(
            runtime_report.get("dataset_probes", {})
            .get(name, {})
            .get(field, {})
            .get("success", False)
        )

    report = {
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "setup_path": str(setup_path),
        "configured_env_mike_zero_x64": os.environ.get("MIKE_ZERO_X64"),
        "selected_mike_zero_x64": str(mike_zero_x64),
        "probe_setup": str(probe_setup),
        "probe_setup_modifications": {
            "plugins_disabled": True,
            "simspec_modelcomp_river_disabled": True,
            "m1d_river_coupling_disabled": True,
        },
        "soil_bound_sources": extract_theta_bounds(setup_path.parent),
        "runtime_report": runtime_report,
        "findings": {
            "param_types_materialize_only_after_initialize": True,
            "ol_d_writable_in_current_setup": probe_success(
                "OL_D", "set_values_from_dataset"
            ),
            "oldr_in_flo_writable": probe_success(
                "OLDR_IN_FLO", "set_values_from_dataset"
            ),
            "sz_leak_flo_writable": probe_success(
                "SZ_LEAK_FLO", "set_values_from_dataset"
            ),
            "sz_leak_flx_writable": probe_success(
                "SZ_LEAK_FLX", "set_values_from_dataset"
            ),
            "szdr_in_flo_writable": probe_success(
                "SZDR_IN_FLO", "set_values_from_dataset"
            ),
            "uz_wc_writable": probe_success("UZ_WC", "set_values_from_dataset"),
            "ol_source_writable": probe_success("OL_SOURCE", "set_values_from_dataset"),
            "theta_bounds_exposed_in_runtime_param_registry": any(
                token in name
                for name in runtime_report[
                    "param_type_names_matching_wc_porosity_theta"
                ]
                for token in ("THETA", "POR", "SAT", "RES")
            ),
        },
    }

    output_path = resolve_path(args.output) if args.output else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Phase 0 diagnostic report written to {output_path}")
    print(json.dumps(report["findings"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
