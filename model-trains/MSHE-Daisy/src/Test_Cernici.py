# Subject:      This is a python script demonstrating how to run a MIKE She model using the MShePy API taking one or more time steps.
# Usage:        Execute as a standalone script. Paths can be configured with CLI options or a .env file.
# Dependencies: mikeio, MIKE Zero
#               In order to make the MShePy module (MIKE Zero) accessible either
#                 - add the MIKE Zero installation path/bin/x64 directory to the system/user variable PYTHONPATH (preferred) or
#                 - call sys.path.append("MIKE Zero installation path/bin/x64")
# Data:         Configure MSHE_SETUP and DAISY_OUTPUT_CSV (or use the bundled default .she file)
# \author dhi\uha
# \date 06/2025

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETUP = (
    REPO_ROOT / "data" / "Cernici_060126_Test02_2" / "Cernici16_Ben_v100_DAISYinput.she"
)
DEFAULT_DAISY_OUTPUT = (
    REPO_ROOT / "data" / "Cernici_060126_Test02_2" / "Monthly_FWater.csv"
)
DEMO_MODEL = str(DEFAULT_SETUP)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")


def find_mike_zero_x64():
    candidates = []

    env_path = os.environ.get("MIKE_ZERO_X64")
    if env_path:
        candidates.append(env_path)

    # for year in ("2026", "2025", "2024"):
    #     candidates.append(rf"C:\Program Files (x86)\DHI\MIKE Zero\{year}\bin\x64")

    for path in candidates:
        if path and os.path.isdir(path):
            return path

    raise FileNotFoundError(
        "Could not find a MIKE Zero x64 installation. "
        "Set the MIKE_ZERO_X64 environment variable to your MIKE Zero bin\\x64 folder."
    )


sys.path.append(find_mike_zero_x64())
import subprocess as sp
from datetime import datetime

import mikeio
import MShePy as ms
import src.DaisyFunctions as daisy
from src.coupling import (
    CouplingRuntimeContext,
    apply_effective_uz_storage_corrections,
    apply_groupwise_net_leakage_flux,
    apply_nonnegative_sink,
    assign_uniform_scalar_to_cells,
    assign_uniform_scalar_to_groups,
    derive_conservative_theta_bounds,
    interval_depth_to_cell_transfer,
    interval_depth_to_rate_m_per_s,
    net_exchange_to_delta_theta,
    resolve_mshe_timestep_seconds,
)
from src.diagnostics import (
    CouplingDiagnosticRecord,
    VolumeClosureTimeseriesAggregator,
    derive_diagnostics_plot_dir,
    summarize_volume_closure,
    summarize_volume_closure_timeseries,
    write_diagnostics_csv,
    write_diagnostics_summary_csv,
    write_diagnostics_timeseries_csv,
)
from src.diagnostics_plots import write_diagnostics_plots
from src.phase0_diagnostic_spike import extract_theta_bounds, resolve_runtime_param_type
from src.setup_overrides import (
    derive_effective_uz_thickness_from_setup,
    derive_preprocessed_dfs2_path,
    patch_simend_in_place,
    resolve_native_sz_drain_suppression_policy,
    write_preprocessed_runoff_coefficient_override,
    write_saturated_zone_drain_override_setup,
)
from src.spatial_mapping import DEFAULT_SPATIAL_MAPPING

DEFAULT_EFFECTIVE_UZ_THICKNESS_M = 10.0
DEFAULT_RUNOFF_DIAGNOSTICS_OUTPUT = (
    REPO_ROOT / "docs" / "test_cernici_runoff_diagnostics.csv"
)
RUNOFF_BOOKKEEPING_MODE = "virtual_ol_d_snapshot"
DRAIN_BOOKKEEPING_MODE = "virtual_cumulative_drain_depth"
RUNOFF_SIGN_CONVENTION = (
    "positive_daisy_runoff_to_positive_oldr_in_flo_and_negative_storage_sink"
)
MATRIX_PERCOLATION_SIGN_CONVENTION = (
    "positive_daisy_matrix_percolation_minus_native_uz_sz_ex_posup_to_sz_leak_flx"
)
MATRIX_DRAIN_FLOW_SIGN_CONVENTION = "positive_daisy_matrix_drain_to_positive_szdr_in_flo_and_positive_virtual_cumulative_sink"
NATIVE_SZ_DRAIN_SUPPRESSION_SUFFIX = "dr0"
RUNTIME_PARAM_NAMES = (
    "OL_D",
    "P_RATE",
    "OLDR_IN_FLO",
    "SZ_LEAK_FLX",
    "SZ_LEAK_FLO",
    "SZDR_IN_FLO",
    "SZ_SOURCE",
    "UZ_SZ_EX_POSUP",
    "UZ_WC",
)

# # Define blocks as (row_start, row_end, col_start, col_end) with Python slice end-exclusive
# blocks2 = [
#     (74, 77, 95, 96),
#     (73, 77, 96, 97),
#     (71, 77, 97, 98),
#     (66, 76, 98, 99),
#     (65, 76, 99, 100),
#     (64, 76, 100, 101),
#     (63, 76, 101, 102),
#     (63, 77, 102, 108),
#     (62, 78, 108, 110),
#     (61, 78, 110, 113),
#     (60, 79, 113, 116),
#     (59, 80, 116, 119),
#     (58, 81, 119, 120),
#     (58, 69, 120, 121),
#     (79, 81, 120, 121),
#     (57, 58, 121, 122),
#     (79, 81, 121, 122),
#     (79, 80, 122, 123),
# ]


#######################################
# Helper functions
#######################################


def resolve_path(path_value):
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def get_configured_path(cli_value, env_name, default_path, description, required=True):
    if cli_value:
        candidate = resolve_path(cli_value)
        source = "command line"
    else:
        env_value = os.environ.get(env_name)
        if env_value:
            candidate = resolve_path(env_value)
            source = env_name
        elif default_path is not None:
            candidate = default_path.resolve()
            source = "repository default"
        elif required:
            raise FileNotFoundError(
                f"No {description} configured. Use the command line option or set {env_name}."
            )
        else:
            return None, "not set"

    if required and not candidate.exists():
        raise FileNotFoundError(
            f"{description.capitalize()} not found: {candidate}\n"
            f"Use the command line option or set {env_name} in the environment or .env file."
        )

    return candidate, source


def print_configuration(args):
    drain_coupling_enabled = not args.disable_drain_coupling
    native_sz_drain_policy = resolve_native_sz_drain_suppression_policy(
        drain_coupling_enabled=drain_coupling_enabled,
        suppress_native_sz_drain=args.suppress_native_sz_drain,
        keep_native_sz_drain=args.keep_native_sz_drain,
    )

    try:
        setup_path_for_thickness, _ = get_configured_path(
            args.setup,
            "MSHE_SETUP",
            DEFAULT_SETUP,
            "MIKE SHE setup file (.she)",
        )
    except FileNotFoundError:
        setup_path_for_thickness = None

    print(f"Repo root:        {REPO_ROOT}")
    print(f"MIKE_ZERO_X64:    {find_mike_zero_x64()}")
    effective_uz_thickness_m, effective_uz_source = resolve_effective_uz_thickness(
        args.effective_uz_thickness_m,
        setup_path=setup_path_for_thickness,
    )
    print(f"Effective UZ:    {effective_uz_thickness_m:g} m ({effective_uz_source})")
    print(
        f"Runoff coupling: {'disabled' if args.disable_runoff_coupling else 'enabled'}"
    )
    print(
        "Runoff coeffs:   "
        + (
            "zero mapped cells in preprocessed DFS2 (--zero-preprocessed-runoff-coefficients)"
            if args.zero_preprocessed_runoff_coefficients
            else "keep setup/preprocessed coefficients"
        )
    )
    print(
        f"Drain coupling:  {'disabled' if args.disable_drain_coupling else 'enabled'}"
    )
    print("Native SZ drain suppression: " + native_sz_drain_policy["description"])
    diagnostics_output = resolve_diagnostics_output_path(args.diagnostics_output)
    diagnostics_plot_dir = None
    diagnostics_plot_status = "disabled"
    if args.plot_diagnostics is not None:
        if diagnostics_output is None:
            diagnostics_plot_status = (
                "INVALID - --plot-diagnostics requires --diagnostics-output"
            )
        else:
            diagnostics_plot_dir = resolve_diagnostics_plot_dir(
                args.plot_diagnostics,
                diagnostics_output,
            )
            diagnostics_plot_status = str(diagnostics_plot_dir)
    print(
        "Diagnostics:     "
        + (str(diagnostics_output) if diagnostics_output is not None else "disabled")
    )
    print(f"Diag mode:       {args.diagnostics_mode}")
    print(f"Diag plots:      {diagnostics_plot_status}")
    sim_end_dt = parse_sim_end(args.sim_end)
    print(
        f"Sim end:         {sim_end_dt.strftime('%Y-%m-%d')} ({'CLI' if args.sim_end else 'default'})"
    )

    for label, cli_value, env_name, default_path, description in (
        (
            "MSHE setup",
            args.setup,
            "MSHE_SETUP",
            DEFAULT_SETUP,
            "MIKE SHE setup file (.she)",
        ),
        (
            "Daisy output",
            args.daisy_output,
            "DAISY_OUTPUT_CSV",
            DEFAULT_DAISY_OUTPUT,
            "Daisy output CSV",
        ),
    ):
        try:
            path, source = get_configured_path(
                cli_value, env_name, default_path, description
            )
            print(f"{label:16}{path} ({source})")
        except FileNotFoundError as exc:
            print(f"{label:16}MISSING - {exc}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the Cernici MIKE SHE model with Daisy coupling."
    )
    parser.add_argument(
        "--setup",
        help="Path to the MIKE SHE .she setup file. Overrides MSHE_SETUP.",
    )
    parser.add_argument(
        "--daisy-output",
        help="Path to the Daisy output CSV file. Overrides DAISY_OUTPUT_CSV.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print resolved configuration and exit.",
    )
    parser.add_argument(
        "--effective-uz-thickness-m",
        type=float,
        help=(
            "Effective unsaturated-zone thickness used for UZ_WC bookkeeping. "
            "Overrides EFFECTIVE_UZ_THICKNESS_M, any setup-derived thickness, and the built-in default."
        ),
    )
    parser.add_argument(
        "--diagnostics-output",
        help=(
            "Optional CSV path for per-cell coupling diagnostics. "
            "If omitted, diagnostics collection is disabled."
        ),
    )
    parser.add_argument(
        "--diagnostics-mode",
        choices=("detailed", "aggregated"),
        default="detailed",
        help=(
            "Diagnostics storage mode. 'detailed' keeps every cell-step row and is "
            "best for short runs. 'aggregated' stores only per-timestamp/per-variable "
            "closure aggregates so longer runs can safely produce plots without "
            "retaining the full detailed diagnostics table in memory."
        ),
    )
    parser.add_argument(
        "--plot-diagnostics",
        nargs="?",
        const="AUTO",
        metavar="DIR",
        help=(
            "Generate PNG diagnostics plots when --diagnostics-output is enabled. "
            "If DIR is omitted, plots are written to a sibling <diagnostics_stem>_plots directory."
        ),
    )
    parser.add_argument(
        "--disable-runoff-coupling",
        action="store_true",
        help="Disable Phase 1 runoff coupling and keep the current percolation-only behavior.",
    )
    parser.add_argument(
        "--zero-preprocessed-runoff-coefficients",
        action="store_true",
        help=(
            "After preprocessing and before WM initialization, zero the mapped cells "
            "in the preprocessed 'OL-Drainage Runoff Coefficients' DFS2 item. "
            "Experimental stricter Phase 1 runoff-suppression hook."
        ),
    )
    parser.add_argument(
        "--disable-drain-coupling",
        action="store_true",
        help="Disable Phase 3 matrix drain flow coupling and keep SZ drain inflow on the native path.",
    )
    native_sz_drain_policy_group = parser.add_mutually_exclusive_group()
    native_sz_drain_policy_group.add_argument(
        "--suppress-native-sz-drain",
        action="store_true",
        help=(
            "Explicitly request the recommended native SZ drain suppression. "
            "Retained for compatibility; this suppression is now the default when "
            "Phase 3 drain coupling is enabled."
        ),
    )
    native_sz_drain_policy_group.add_argument(
        "--keep-native-sz-drain",
        action="store_true",
        help=(
            "Opt out of the default Phase 3 native SZ drain suppression and keep "
            "the native saturated-zone drain path active. Intended for controlled "
            "comparisons only."
        ),
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        help="Optional maximum number of WM loop iterations to run. Useful for smoke tests.",
    )
    parser.add_argument(
        "--sim-end",
        help=(
            "Stop simulation at this date (ISO format: YYYY-MM-DD). "
            "Overrides the built-in 2020-09-01 cutoff. "
            "Must be within the SIMEND defined in the .she file."
        ),
    )
    return parser.parse_args()


def pp(setup):
    """Run the MIKE She preprocessor.
    As no python interface is available use the executable and run it as an external process.
    """
    # Get the directory where MShePy was loaded from and use PP from the same installation
    mz_dir = os.path.dirname(ms.__file__)
    pp_exe = os.path.join(mz_dir, "MShe_Preprocessor.exe")
    sp.run([pp_exe, setup])


def resolve_python_plugin_dll():
    """Return the most compatible Python runtime DLL for MIKE SHE plugins.

    Prefer the version-specific CPython DLL (for example `python310.dll`) because
    the generic `python3.dll` only exposes the stable ABI and may miss symbols
    required by the MIKE SHE plugin loader.
    """
    py_dir = Path(sys.executable).resolve().parent
    candidates = [
        py_dir / f"python{sys.version_info.major}{sys.version_info.minor}.dll",
        py_dir / f"python{sys.version_info.major}.dll",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Could not find a compatible Python runtime DLL for plugins. "
        f"Checked: {', '.join(str(path) for path in candidates)}"
    )


def resolve_effective_uz_thickness(cli_value, setup_path=None):
    if cli_value is not None:
        value = float(cli_value)
        source = "command line"
    else:
        env_value = os.environ.get("EFFECTIVE_UZ_THICKNESS_M")
        if env_value:
            value = float(env_value)
            source = "EFFECTIVE_UZ_THICKNESS_M"
        else:
            setup_candidates = []
            if setup_path is not None:
                setup_candidates.append(setup_path)
            else:
                configured_setup = os.environ.get("MSHE_SETUP")
                if configured_setup:
                    setup_candidates.append(configured_setup)
                if DEFAULT_SETUP.exists():
                    setup_candidates.append(DEFAULT_SETUP)

            value = DEFAULT_EFFECTIVE_UZ_THICKNESS_M
            source = "default"
            for setup_candidate in setup_candidates:
                try:
                    resolution = derive_effective_uz_thickness_from_setup(
                        setup_candidate
                    )
                except (FileNotFoundError, ValueError):
                    continue

                value = float(resolution.thickness_m)
                source = str(resolution.source)
                break

    if value <= 0:
        raise ValueError(f"effective UZ thickness must be positive, got {value}")

    return value, source


def resolve_diagnostics_output_path(cli_value):
    if not cli_value:
        return None

    return resolve_path(cli_value)


def parse_sim_end(cli_value):
    if cli_value is None:
        return datetime(2020, 9, 1)
    return datetime.strptime(cli_value, "%Y-%m-%d")


def resolve_diagnostics_plot_dir(cli_value, diagnostics_output_path=None):
    if cli_value is None:
        return None

    if diagnostics_output_path is None:
        raise ValueError("--plot-diagnostics requires --diagnostics-output")

    if cli_value == "AUTO":
        return derive_diagnostics_plot_dir(diagnostics_output_path)

    return resolve_path(cli_value)


def prepare_execution_setup(
    setup_path,
    *,
    drain_coupling_enabled,
    suppress_native_sz_drain,
    keep_native_sz_drain,
):
    resolved_setup_path = Path(setup_path).resolve()
    native_sz_drain_policy = resolve_native_sz_drain_suppression_policy(
        drain_coupling_enabled=drain_coupling_enabled,
        suppress_native_sz_drain=suppress_native_sz_drain,
        keep_native_sz_drain=keep_native_sz_drain,
    )
    if not native_sz_drain_policy["enabled"]:
        return resolved_setup_path, None, native_sz_drain_policy

    derived_setup_path, override_metadata = write_saturated_zone_drain_override_setup(
        resolved_setup_path,
        drain_code_fixed_value=0.0,
        suffix=NATIVE_SZ_DRAIN_SUPPRESSION_SUFFIX,
    )
    return (
        derived_setup_path,
        {
            **override_metadata,
            "policy_source": native_sz_drain_policy["source"],
            "policy_description": native_sz_drain_policy["description"],
        },
        native_sz_drain_policy,
    )


def resolve_relevant_runtime_param_types():
    runtime_param_types = {}
    for name in RUNTIME_PARAM_NAMES:
        ptype, _ = resolve_runtime_param_type(ms, name)
        runtime_param_types[name] = int(ptype)

    return runtime_param_types


def initialize_virtual_runoff_bookkeeping(runtime_param_types):
    bookkeeping_values = {}
    source_description = "zeros"

    ol_d_ptype = runtime_param_types.get("OL_D")
    if ol_d_ptype is not None:
        try:
            _, _, ol_d_snapshot = ms.wm.getValues(ol_d_ptype)
            source_description = "OL_D read-only snapshot"
            for info in DEFAULT_SPATIAL_MAPPING.iter_cell_mappings():
                bookkeeping_values[(info.row, info.col)] = float(
                    ol_d_snapshot[info.row][info.col]
                )
        except Exception as exc:
            source_description = f"zeros (OL_D read failed: {type(exc).__name__})"

    if not bookkeeping_values:
        for info in DEFAULT_SPATIAL_MAPPING.iter_cell_mappings():
            bookkeeping_values[(info.row, info.col)] = 0.0

    return {
        "mode": RUNOFF_BOOKKEEPING_MODE,
        "source": source_description,
        "values": bookkeeping_values,
    }


def initialize_virtual_drain_bookkeeping():
    bookkeeping_values = {
        (info.row, info.col): 0.0
        for info in DEFAULT_SPATIAL_MAPPING.iter_drained_cell_mappings()
    }

    return {
        "mode": DRAIN_BOOKKEEPING_MODE,
        "source": "zeros cumulative drain extraction ledger",
        "values": bookkeeping_values,
    }


def read_observed_overland_depth(runtime_param_types):
    ol_d_ptype = runtime_param_types.get("OL_D")
    if ol_d_ptype is None:
        return None, None

    try:
        _, end_time, ol_d_snapshot = ms.wm.getValues(ol_d_ptype)
    except Exception:
        return None, None

    return end_time, ol_d_snapshot


def _grid_metrics():
    origin_x, origin_y = ms.wm.gridCellToCoord(0, 0)
    east_x, _ = ms.wm.gridCellToCoord(1, 0)
    _, north_y = ms.wm.gridCellToCoord(0, 1)
    cell_dx = east_x - origin_x
    cell_dy = north_y - origin_y
    return cell_dx, cell_dy, cell_dx * cell_dy


def build_runtime_context(
    setup_path,
    dt_hours,
    effective_uz_thickness_m,
    effective_uz_thickness_source="default",
):
    theta_bound_report = extract_theta_bounds(Path(setup_path).resolve().parent)
    theta_residual_values = tuple(theta_bound_report.get("theta_r_values", []))
    theta_saturated_values = tuple(theta_bound_report.get("theta_s_values", []))
    theta_residual, theta_saturated = derive_conservative_theta_bounds(
        theta_residual_values,
        theta_saturated_values,
    )
    cell_dx_m, cell_dy_m, cell_area_m2 = _grid_metrics()

    return CouplingRuntimeContext(
        mshe_dt_seconds=resolve_mshe_timestep_seconds(dt_hours),
        effective_uz_thickness_m=float(effective_uz_thickness_m),
        effective_uz_thickness_source=str(effective_uz_thickness_source),
        cell_area_m2=cell_area_m2,
        theta_residual=theta_residual,
        theta_saturated=theta_saturated,
        coupled_group_count=len(DEFAULT_SPATIAL_MAPPING),
        cell_dx_m=cell_dx_m,
        cell_dy_m=cell_dy_m,
        theta_residual_values=theta_residual_values,
        theta_saturated_values=theta_saturated_values,
        theta_bound_source_files=tuple(theta_bound_report.get("source_files", [])),
        runtime_param_types=tuple(
            sorted(resolve_relevant_runtime_param_types().items())
        ),
    )


def resolve_upcoming_wm_step_seconds(default_dt_seconds=None):
    try:
        raw_next_step = ms.wm.nextTimeStep()
        return resolve_mshe_timestep_seconds(raw_next_step), raw_next_step, None
    except Exception as exc:
        if default_dt_seconds is None:
            raise
        return float(default_dt_seconds), None, exc


def is_end_of_simulation_timestep_error(exc):
    return isinstance(exc, ValueError) and "must be positive" in str(exc)


def enable_plugin(in_path, out_path):
    """Enable using plugins, set the path to the python interpreter and the
    path to this file for plugins - save as copy.
    """
    # Use the same interpreter that is running this script - but we need the dll, not the exe
    py_path = str(resolve_python_plugin_dll())
    plugin_script = str(Path(__file__).resolve())

    pfs = mikeio.PfsDocument(in_path, unique_keywords=False)
    pfs.MIKESHE_FLOWMODEL.SimSpec.ModelComp.Plugins = 1
    pfs.MIKESHE_FLOWMODEL.Plugins.PyResolve = 1
    # Set paths - special syntax for pfs paths using '|'
    pfs.MIKESHE_FLOWMODEL.Plugins.PyPath = f"|{py_path}|"
    pfs.MIKESHE_FLOWMODEL.Plugins.PluginFileList.PluginFile_1.FILE_NAME = (
        f"|{plugin_script}|"  # this file
    )
    pfs.write(out_path)  # save copy

    print(f"Plugin script written to setup: {plugin_script}")
    print(f"Plugin Python DLL written to setup: {py_path}")
    print(f"Plugin-enabled setup saved as: {Path(out_path).resolve()}")


#######################################
# Calculated data
#######################################


def calc_SZ_LEAK_FLX(sz_leak_flx, daisy_rate_m_per_s, UZ_SZ_EX_POSUP_prev):
    ## SZ_LEAK_FLX - Leakage (flow) to SZ [m/s]
    if isinstance(daisy_rate_m_per_s, dict):
        source_rates_by_class = {
            str(key): float(value) for key, value in daisy_rate_m_per_s.items()
        }
    else:
        scalar_rate = float(daisy_rate_m_per_s)
        source_rates_by_class = {
            group.daisy_class: scalar_rate for group in DEFAULT_SPATIAL_MAPPING.groups
        }

    apply_groupwise_net_leakage_flux(
        sz_leak_flx,
        DEFAULT_SPATIAL_MAPPING.groups,
        source_rates_by_class,
        UZ_SZ_EX_POSUP_prev,
    )
    # SZ_LEAK_FLX[74:77,95:96] =  [[Daisy_Value - v for v in row[95:96]] for row in UZ_SZ_EX_POSUP_prev[74:77]]
    # SZ_LEAK_FLX[73:77,96:97] = [[Daisy_Value - v for v in row[96:97]] for row in UZ_SZ_EX_POSUP_prev[73:77]]
    # SZ_LEAK_FLX[71:77,97:98] = [[Daisy_Value - v for v in row[97:98]] for row in UZ_SZ_EX_POSUP_prev[71:77]]
    # SZ_LEAK_FLX[66:76,98:99] = [[Daisy_Value - v for v in row[98:99]] for row in  UZ_SZ_EX_POSUP_prev[66:76]]
    # SZ_LEAK_FLX[65:76,99:100] = [[Daisy_Value - v for v in row[99:100]] for row in UZ_SZ_EX_POSUP_prev[65:76]]
    # SZ_LEAK_FLX[64:76,100:101] = [[Daisy_Value - v for v in row[100:101]] for row in UZ_SZ_EX_POSUP_prev[64:76]]
    # SZ_LEAK_FLX[63:76,101:102] = [[Daisy_Value - v for v in row[101:102]] for row in UZ_SZ_EX_POSUP_prev[63:76]]
    # SZ_LEAK_FLX[63:77,102:108] = [[Daisy_Value - v for v in row[102:108]] for row in UZ_SZ_EX_POSUP_prev[63:77]]
    # SZ_LEAK_FLX[62:78,108:110] = [[Daisy_Value - v for v in row[108:110]] for row in UZ_SZ_EX_POSUP_prev[62:78]]
    # SZ_LEAK_FLX[61:78,110:113] = [[Daisy_Value - v for v in row[110:113]] for row in UZ_SZ_EX_POSUP_prev[61:78]]
    # SZ_LEAK_FLX[60:79,113:116] = [[Daisy_Value - v for v in row[113:116]] for row in UZ_SZ_EX_POSUP_prev[60:79]]
    # SZ_LEAK_FLX[59:80,116:119] = [[Daisy_Value - v for v in row[116:119]] for row in UZ_SZ_EX_POSUP_prev[59:80]]
    # SZ_LEAK_FLX[58:81,119:120] = [[Daisy_Value - v for v in row[119:120]] for row in UZ_SZ_EX_POSUP_prev[58:81]]
    # SZ_LEAK_FLX[58:69,120:121] = [[Daisy_Value - v for v in row[120:121]] for row in UZ_SZ_EX_POSUP_prev[58:69]]
    # SZ_LEAK_FLX[79:81,120:121] = [[Daisy_Value - v for v in row[120:121]] for row in UZ_SZ_EX_POSUP_prev[79:81]]
    # SZ_LEAK_FLX[57:58,121:122] = [[Daisy_Value - v for v in row[121:122]] for row in UZ_SZ_EX_POSUP_prev[57:58]]
    # SZ_LEAK_FLX[79:81,121:122] = [[Daisy_Value - v for v in row[121:122]] for row in UZ_SZ_EX_POSUP_prev[79:81]]
    # SZ_LEAK_FLX[79:80,122:123] = [[Daisy_Value - v for v in row[122:123]] for row in UZ_SZ_EX_POSUP_prev[79:80]]

    return sz_leak_flx


def calc_UZ_WC(
    UZ_WC,
    UZ_WC_prev,
    SZ_LEAK_FLX_data,
    delta_t_seconds=None,
    effective_uz_thickness_m=DEFAULT_EFFECTIVE_UZ_THICKNESS_M,
    theta_residual=None,
    theta_saturated=None,
):
    # ## UZ_WC
    # UZ_WC.value(0.50) #in [%] -water content in unsaturated zone
    # UZ_WC = UZ_WC_prev
    # UZ_WC = UZ_WC_prev

    if delta_t_seconds is None:
        raise ValueError("delta_t_seconds must be provided from the runtime context")

    requested_storage_correction_delta_theta_by_cell = {}

    for group in DEFAULT_SPATIAL_MAPPING.groups:
        r0, r1 = group.row_start, group.row_end
        c0, c1 = group.col_start, group.col_end
        for r in range(r0, r1):
            leak_row = SZ_LEAK_FLX_data[r]

            for c in range(c0, c1):
                requested_storage_correction_delta_theta_by_cell[(r, c)] = (
                    net_exchange_to_delta_theta(
                        leak_row[c],
                        delta_t_seconds,
                        effective_uz_thickness_m,
                    )
                )

    return apply_effective_uz_storage_corrections(
        UZ_WC,
        UZ_WC_prev,
        requested_storage_correction_delta_theta_by_cell,
        lower_bound=theta_residual,
        upper_bound=theta_saturated,
    )


def apply_matrix_percolation_coupling(
    sz_leak_flx,
    uz_wc,
    uz_wc_prev,
    daisy_interval_row,
    runtime_context,
    uz_sz_ex_posup_prev,
    timestamp,
    diagnostics_records=None,
):
    source_depth_mm = float(daisy_interval_row["Matrix percolation"])
    interval_seconds = float(daisy_interval_row["interval_seconds"])
    daisy_rate_m_per_s = interval_depth_to_rate_m_per_s(
        source_depth_mm,
        interval_seconds,
    )
    source_rates_by_class = {
        group.daisy_class: daisy_rate_m_per_s
        for group in DEFAULT_SPATIAL_MAPPING.groups
    }

    sz_leak_flx_data = calc_SZ_LEAK_FLX(
        sz_leak_flx,
        source_rates_by_class,
        uz_sz_ex_posup_prev,
    )
    uz_wc_data, uz_wc_shift_results = calc_UZ_WC(
        uz_wc,
        uz_wc_prev,
        sz_leak_flx_data,
        delta_t_seconds=runtime_context.mshe_dt_seconds,
        effective_uz_thickness_m=runtime_context.effective_uz_thickness_m,
        theta_residual=runtime_context.theta_residual,
        theta_saturated=runtime_context.theta_saturated,
    )

    if diagnostics_records is not None:
        for info in DEFAULT_SPATIAL_MAPPING.iter_cell_mappings():
            native_exchange_m_per_s = float(uz_sz_ex_posup_prev[info.row][info.col])
            daisy_rate_for_cell = source_rates_by_class[info.daisy_class]
            net_correction_m_per_s = daisy_rate_for_cell - native_exchange_m_per_s
            requested_step_depth_m = (
                net_correction_m_per_s * runtime_context.mshe_dt_seconds
            )
            requested_step_volume_m3 = (
                None
                if runtime_context.cell_area_m2 is None
                else requested_step_depth_m * runtime_context.cell_area_m2
            )
            delta_theta = net_exchange_to_delta_theta(
                net_correction_m_per_s,
                runtime_context.mshe_dt_seconds,
                runtime_context.effective_uz_thickness_m,
            )
            bookkeeping_result = uz_wc_shift_results[(info.row, info.col)]
            applied_storage_correction = (
                bookkeeping_result.applied_storage_correction_delta_theta
            )
            residual_storage_correction = (
                bookkeeping_result.residual_storage_correction_delta_theta
            )
            storage_correction_volume_m3 = (
                None
                if (
                    applied_storage_correction is None
                    or runtime_context.cell_area_m2 is None
                )
                else applied_storage_correction
                * runtime_context.effective_uz_thickness_m
                * runtime_context.cell_area_m2
            )
            residual_volume_m3 = (
                None
                if (
                    residual_storage_correction is None
                    or runtime_context.cell_area_m2 is None
                )
                else residual_storage_correction
                * runtime_context.effective_uz_thickness_m
                * runtime_context.cell_area_m2
            )

            diagnostics_records.append(
                CouplingDiagnosticRecord(
                    timestamp=timestamp,
                    variable_name="matrix_percolation",
                    row=info.row,
                    col=info.col,
                    daisy_source_id=info.daisy_class,
                    interval_start_time=daisy_interval_row["interval_start_time"],
                    interval_end_time=daisy_interval_row["interval_end_time"],
                    source_depth_mm=source_depth_mm,
                    interval_seconds=interval_seconds,
                    target_value=net_correction_m_per_s,
                    storage_correction=applied_storage_correction,
                    residual=residual_storage_correction,
                    sign_convention=MATRIX_PERCOLATION_SIGN_CONVENTION,
                    lower_boundary_case=info.lower_boundary_case,
                    metadata={
                        "source_rate_m_per_s": daisy_rate_for_cell,
                        "cell_area_m2": runtime_context.cell_area_m2,
                        "effective_uz_thickness_m": runtime_context.effective_uz_thickness_m,
                        "effective_uz_thickness_source": runtime_context.effective_uz_thickness_source,
                        "wm_step_seconds": runtime_context.mshe_dt_seconds,
                        "wm_step_hours": runtime_context.mshe_dt_seconds / 3600.0,
                        "native_exchange_m_per_s": native_exchange_m_per_s,
                        "target_units": "m/s",
                        "storage_units": "delta_theta",
                        "native_comparison_term": "UZ_SZ_EX_POSUP",
                        "provisional_target": "SZ_LEAK_FLX",
                        "bookkeeping_mode": "effective_uz_wc",
                        "bookkeeping_source": "matrix_percolation_net_exchange",
                        "bookkeeping_semantics": "effective_storage_state_uniform_layer_shift",
                        "bounds_applied": bookkeeping_result.clipped_layer_count > 0,
                        "lower_bound_theta": bookkeeping_result.lower_bound,
                        "upper_bound_theta": bookkeeping_result.upper_bound,
                        "requested_step_depth_m": requested_step_depth_m,
                        "requested_step_volume_m3": requested_step_volume_m3,
                        "target_step_volume_m3": requested_step_volume_m3,
                        "requested_storage_correction_delta_theta": delta_theta,
                        "requested_layer_delta_theta": bookkeeping_result.requested_layer_delta_theta,
                        "applied_storage_correction_delta_theta": applied_storage_correction,
                        "residual_storage_correction_delta_theta": residual_storage_correction,
                        "applied_layer_delta_theta": bookkeeping_result.applied_layer_delta_theta,
                        "residual_layer_delta_theta": bookkeeping_result.residual_layer_delta_theta,
                        "storage_correction_volume_m3": storage_correction_volume_m3,
                        "residual_volume_m3": residual_volume_m3,
                        "bookkeeping_representation": "dataset_native_tuple_cell_layers_assign_uniform_delta",
                        "effective_uz_theta_before": bookkeeping_result.effective_theta_before,
                        "effective_uz_theta_requested_after": bookkeeping_result.effective_theta_requested_after,
                        "effective_uz_theta_after": bookkeeping_result.effective_theta_after,
                        "uz_wc_before_layer_mean": bookkeeping_result.effective_theta_before,
                        "uz_wc_expected_after_layer_mean": bookkeeping_result.effective_theta_requested_after,
                        "uz_wc_candidate_after_layer_mean": bookkeeping_result.effective_theta_after,
                        "uz_wc_layer_count": bookkeeping_result.layer_count,
                        "uz_wc_clipped_layer_count": bookkeeping_result.clipped_layer_count,
                    },
                )
            )

    return daisy_rate_m_per_s, sz_leak_flx_data, uz_wc_data


def apply_runoff_coupling(
    oldr_in_flo,
    daisy_interval_row,
    runtime_context,
    runoff_bookkeeping_state,
    timestamp,
    diagnostics_records=None,
    observed_ol_d_time=None,
    observed_ol_d_snapshot=None,
):
    runoff_transfer = interval_depth_to_cell_transfer(
        depth_mm=float(daisy_interval_row["Runoff"]),
        interval_seconds=float(daisy_interval_row["interval_seconds"]),
        dt_seconds=runtime_context.mshe_dt_seconds,
        cell_area_m2=runtime_context.cell_area_m2,
    )
    assign_uniform_scalar_to_groups(
        oldr_in_flo,
        DEFAULT_SPATIAL_MAPPING.groups,
        runoff_transfer.flow_m3_per_s,
    )

    for info in DEFAULT_SPATIAL_MAPPING.iter_cell_mappings():
        cell_key = (info.row, info.col)
        bookkeeping_before = runoff_bookkeeping_state["values"][cell_key]
        bounded_update = apply_nonnegative_sink(
            bookkeeping_before,
            runoff_transfer.step_depth_m,
        )
        runoff_bookkeeping_state["values"][cell_key] = bounded_update.bounded_value

        if diagnostics_records is None:
            continue

        observed_ol_d_before = None
        if observed_ol_d_snapshot is not None:
            observed_ol_d_before = float(observed_ol_d_snapshot[info.row][info.col])

        storage_correction_volume_m3 = (
            None
            if runtime_context.cell_area_m2 is None
            else (-bounded_update.applied_delta) * runtime_context.cell_area_m2
        )
        residual_volume_m3 = (
            None
            if runtime_context.cell_area_m2 is None
            else abs(float(bounded_update.residual)) * runtime_context.cell_area_m2
        )

        diagnostics_records.append(
            CouplingDiagnosticRecord(
                timestamp=timestamp,
                variable_name="runoff",
                row=info.row,
                col=info.col,
                daisy_source_id=info.daisy_class,
                interval_start_time=daisy_interval_row["interval_start_time"],
                interval_end_time=daisy_interval_row["interval_end_time"],
                source_depth_mm=runoff_transfer.source_depth_mm,
                interval_seconds=runoff_transfer.interval_seconds,
                target_value=runoff_transfer.flow_m3_per_s,
                storage_correction=-bounded_update.applied_delta,
                residual=bounded_update.residual,
                sign_convention=RUNOFF_SIGN_CONVENTION,
                lower_boundary_case=info.lower_boundary_case,
                metadata={
                    "cell_area_m2": runtime_context.cell_area_m2,
                    "effective_uz_thickness_m": runtime_context.effective_uz_thickness_m,
                    "effective_uz_thickness_source": runtime_context.effective_uz_thickness_source,
                    "wm_step_seconds": runtime_context.mshe_dt_seconds,
                    "wm_step_hours": runtime_context.mshe_dt_seconds / 3600.0,
                    "target_units": "m3/s",
                    "storage_units": "m",
                    "bookkeeping_mode": runoff_bookkeeping_state["mode"],
                    "bookkeeping_source": runoff_bookkeeping_state["source"],
                    "bookkeeping_before_m": bookkeeping_before,
                    "bookkeeping_after_m": bounded_update.bounded_value,
                    "requested_step_depth_m": runoff_transfer.step_depth_m,
                    "requested_step_volume_m3": runoff_transfer.step_volume_m3,
                    "step_volume_m3": runoff_transfer.step_volume_m3,
                    "target_step_volume_m3": runoff_transfer.step_volume_m3,
                    "storage_correction_volume_m3": storage_correction_volume_m3,
                    "residual_volume_m3": residual_volume_m3,
                    "observed_ol_d_before_m": observed_ol_d_before,
                    "observed_ol_d_time": (
                        observed_ol_d_time.isoformat()
                        if hasattr(observed_ol_d_time, "isoformat")
                        else None
                    ),
                },
            )
        )

    return runoff_transfer


def apply_matrix_drain_flow_coupling(
    szdr_in_flo,
    daisy_interval_row,
    runtime_context,
    drain_bookkeeping_state,
    timestamp,
    diagnostics_records=None,
):
    drained_cell_infos = tuple(DEFAULT_SPATIAL_MAPPING.iter_drained_cell_mappings())
    if not drained_cell_infos:
        return None

    drain_transfer = interval_depth_to_cell_transfer(
        depth_mm=float(daisy_interval_row["Matrix drain flow"]),
        interval_seconds=float(daisy_interval_row["interval_seconds"]),
        dt_seconds=runtime_context.mshe_dt_seconds,
        cell_area_m2=runtime_context.cell_area_m2,
    )
    assign_uniform_scalar_to_cells(
        szdr_in_flo,
        ((info.row, info.col) for info in drained_cell_infos),
        drain_transfer.flow_m3_per_s,
    )

    for info in drained_cell_infos:
        cell_key = (info.row, info.col)
        bookkeeping_before = float(drain_bookkeeping_state["values"].get(cell_key, 0.0))
        bookkeeping_after = bookkeeping_before + drain_transfer.step_depth_m
        drain_bookkeeping_state["values"][cell_key] = bookkeeping_after

        if diagnostics_records is None:
            continue

        diagnostics_records.append(
            CouplingDiagnosticRecord(
                timestamp=timestamp,
                variable_name="matrix_drain_flow",
                row=info.row,
                col=info.col,
                daisy_source_id=info.daisy_class,
                interval_start_time=daisy_interval_row["interval_start_time"],
                interval_end_time=daisy_interval_row["interval_end_time"],
                source_depth_mm=drain_transfer.source_depth_mm,
                interval_seconds=drain_transfer.interval_seconds,
                target_value=drain_transfer.flow_m3_per_s,
                storage_correction=drain_transfer.step_depth_m,
                residual=0.0,
                sign_convention=MATRIX_DRAIN_FLOW_SIGN_CONVENTION,
                lower_boundary_case=info.lower_boundary_case,
                metadata={
                    "source_rate_m_per_s": drain_transfer.rate_m_per_s,
                    "cell_area_m2": runtime_context.cell_area_m2,
                    "effective_uz_thickness_m": runtime_context.effective_uz_thickness_m,
                    "effective_uz_thickness_source": runtime_context.effective_uz_thickness_source,
                    "wm_step_seconds": runtime_context.mshe_dt_seconds,
                    "wm_step_hours": runtime_context.mshe_dt_seconds / 3600.0,
                    "target_units": "m3/s",
                    "storage_units": "m",
                    "bookkeeping_mode": drain_bookkeeping_state["mode"],
                    "bookkeeping_source": drain_bookkeeping_state["source"],
                    "bookkeeping_before_m": bookkeeping_before,
                    "bookkeeping_after_m": bookkeeping_after,
                    "requested_step_depth_m": drain_transfer.step_depth_m,
                    "requested_step_volume_m3": drain_transfer.step_volume_m3,
                    "step_volume_m3": drain_transfer.step_volume_m3,
                    "target_step_volume_m3": drain_transfer.step_volume_m3,
                    "storage_correction_volume_m3": drain_transfer.step_volume_m3,
                    "residual_volume_m3": 0.0,
                    "target_variable": "SZDR_IN_FLO",
                    "bookkeeping_representation": "virtual_cumulative_extracted_depth",
                },
            )
        )

    return drain_transfer


#######################################
# Plugins
#######################################


def postTimeStep():
    """A MIKE She plugin function. No technical problem to put it in the same file as the code
    calling the MIKE She engine, however in a larger project it might be cleaner to separate it.
    """
    ms.wm.log(
        f"Message from plugin: Time step performed, time now: {ms.wm.currentTime()}"
    )


#######################################
# Demo functions
#######################################


def exectue_time_steps(
    setup,
    daisy_output_file,
    effective_uz_thickness_m,
    effective_uz_thickness_source="default",
    diagnostics_output_path=None,
    diagnostics_plot_dir=None,
    diagnostics_mode="detailed",
    runoff_coupling_enabled=True,
    zero_preprocessed_runoff_coefficients=False,
    drain_coupling_enabled=True,
    suppress_native_sz_drain=False,
    keep_native_sz_drain=False,
    max_steps=None,
    sim_end=None,
):
    """Demo: Run the MIKE She water movement engine by taking time steps via the python API."""
    execution_setup_path, native_sz_drain_override, native_sz_drain_policy = (
        prepare_execution_setup(
            setup,
            drain_coupling_enabled=drain_coupling_enabled,
            suppress_native_sz_drain=suppress_native_sz_drain,
            keep_native_sz_drain=keep_native_sz_drain,
        )
    )
    if native_sz_drain_override is not None:
        print(
            "Native SZ drain suppression setup:\t"
            f"{execution_setup_path} "
            f"({native_sz_drain_override['pfs_path']}.DrainCode.FixedValue -> "
            f"{native_sz_drain_override['modified_drain_code_fixed_value']})"
        )
    else:
        print(f"Native SZ drain suppression:\t{native_sz_drain_policy['description']}")

    p, e = os.path.splitext(str(execution_setup_path))
    setup_plugin = p + "_plugin" + e
    # optional: Enable plugins
    enable_plugin(str(execution_setup_path), setup_plugin)

    if sim_end is not None:
        patch_simend_in_place(setup_plugin, sim_end)
        print(f"SIMEND patched to:\t{sim_end.strftime('%Y-%m-%d')}")

    pp(setup_plugin)
    runoff_coefficient_override_metadata = None
    if runoff_coupling_enabled and zero_preprocessed_runoff_coefficients:
        runoff_coefficients_path, runoff_coefficient_override_metadata = (
            write_preprocessed_runoff_coefficient_override(
                setup_plugin,
                coupled_cells=DEFAULT_SPATIAL_MAPPING.coupled_cells(),
            )
        )
        print(
            "Native OL runoff coefficient override:\t"
            f"{runoff_coefficients_path} "
            f"(changed {runoff_coefficient_override_metadata['changed_cell_count']}"
            f"/{runoff_coefficient_override_metadata['coupled_cell_count']} mapped cells)"
        )

    ms.wm.initialize(setup_plugin)

    performed, dt_hours, first_time = ms.wm.performTimeStep()
    if performed:
        runtime_context = build_runtime_context(
            setup_plugin,
            dt_hours,
            effective_uz_thickness_m=effective_uz_thickness_m,
            effective_uz_thickness_source=effective_uz_thickness_source,
        )
        runtime_param_types = dict(runtime_context.runtime_param_types)
        startTime, endTime, data = ms.wm.getValues(runtime_param_types["P_RATE"])
        # startTime,endTime,PET = ms.wm.getValues(ms.paramTypes.ET_REF_EXC)
        P_RATE = ms.dataset(runtime_param_types["P_RATE"])
        OLDR_IN_FLO = ms.dataset(runtime_param_types["OLDR_IN_FLO"])
        SZ_LEAK_FLX = ms.dataset(runtime_param_types["SZ_LEAK_FLX"])
        SZ_LEAK_FLO = ms.dataset(runtime_param_types["SZ_LEAK_FLO"])
        SZDR_IN_FLO = ms.dataset(runtime_param_types["SZDR_IN_FLO"])
        SZ_SOURCE = ms.dataset(runtime_param_types["SZ_SOURCE"])
        ms.wm.log("Initial time step performed!")
        ms.wm.log(f"  Duration: {dt_hours} h")
        ms.wm.log(f"  New time: {first_time}")
        ms.wm.log(
            "  Coupling context: "
            f"dt={runtime_context.mshe_dt_seconds:.0f} s, "
            f"effective_UZ={runtime_context.effective_uz_thickness_m:.2f} m "
            f"({runtime_context.effective_uz_thickness_source}), "
            f"coupled_groups={runtime_context.coupled_group_count}"
        )
        ms.wm.log(
            "  Grid context: "
            f"dx={runtime_context.cell_dx_m:.2f} m, "
            f"dy={runtime_context.cell_dy_m:.2f} m, "
            f"area={runtime_context.cell_area_m2:.2f} m2"
        )
        ms.wm.log(
            "  Theta bounds: "
            f"theta_r={runtime_context.theta_residual}, "
            f"theta_s={runtime_context.theta_saturated}, "
            f"source_files={len(runtime_context.theta_bound_source_files)}"
        )
        ms.wm.log(
            "  Runtime params: "
            + ", ".join(
                f"{name}={ptype}" for name, ptype in runtime_context.runtime_param_types
            )
        )
        ms.wm.log(
            "  Runoff coupling: "
            + ("enabled" if runoff_coupling_enabled else "disabled")
        )
        if zero_preprocessed_runoff_coefficients:
            if runoff_coefficient_override_metadata is not None:
                ms.wm.log(
                    "  Runoff coeff override: "
                    f"zeroed mapped cells in {derive_preprocessed_dfs2_path(setup_plugin)} "
                    f"(changed {runoff_coefficient_override_metadata['changed_cell_count']}"
                    f"/{runoff_coefficient_override_metadata['coupled_cell_count']})"
                )
            else:
                ms.wm.log(
                    "  Runoff coeff override: requested but inactive because runoff coupling is disabled"
                )
        ms.wm.log(
            "  Drain coupling: " + ("enabled" if drain_coupling_enabled else "disabled")
        )
        ms.wm.log(
            f"  Native SZ drain suppression: {native_sz_drain_policy['description']}"
        )
        if native_sz_drain_override is not None:
            ms.wm.log(
                "  Native SZ drain override setup: "
                f"{execution_setup_path} "
                f"({native_sz_drain_override['pfs_path']}.DrainCode.FixedValue = "
                f"{native_sz_drain_override['modified_drain_code_fixed_value']})"
            )
        startTime, currentTime, UZ_SZ_EX_POSUP_prev = ms.wm.getValues(
            runtime_param_types["UZ_SZ_EX_POSUP"]
        )
        startTime, currentTime, UZ_WC_prev = ms.wm.getValues(
            runtime_param_types["UZ_WC"]
        )
        startTime, currentTime, UZ_WC = ms.wm.getValues(runtime_param_types["UZ_WC"])
    else:
        ms.wm.log("Failed to execute time step via python")
        return

    #### Get Daisy result ###
    daisy_df = daisy.readDaisyOutput(daisy_output_file)
    daisy.requireDaisyColumn(daisy_df, "Matrix percolation")
    if runoff_coupling_enabled:
        daisy.requireDaisyColumn(daisy_df, "Runoff")

    diagnostics_records = None
    if diagnostics_output_path is not None:
        if diagnostics_mode == "aggregated":
            diagnostics_records = VolumeClosureTimeseriesAggregator()
        else:
            diagnostics_records = []
    runoff_bookkeeping_state = initialize_virtual_runoff_bookkeeping(
        runtime_param_types
    )
    drain_bookkeeping_state = initialize_virtual_drain_bookkeeping()
    next_step_fallback_logged = False
    last_logged_step_seconds = None
    drained_cell_count = len(drain_bookkeeping_state["values"])
    drain_coupling_active = drain_coupling_enabled and drained_cell_count > 0
    if runoff_coupling_enabled:
        ms.wm.log(
            "  Runoff bookkeeping fallback: "
            f"{runoff_bookkeeping_state['mode']} ({runoff_bookkeeping_state['source']})"
        )
    if drain_coupling_active:
        daisy.requireDaisyColumn(daisy_df, "Matrix drain flow")
        ms.wm.log(f"  Drain scope: {drained_cell_count} drained coupled cells")
        ms.wm.log(
            "  Drain bookkeeping fallback: "
            f"{drain_bookkeeping_state['mode']} ({drain_bookkeeping_state['source']})"
        )
    elif drain_coupling_enabled:
        ms.wm.log(
            "  Drain scope: no drained coupled cells mapped; drain coupling inactive"
        )

    # ## SZDR_IN_FLO
    # SZDR_IN_FLO[:,70:] = 2.0
    # ms.wm.setValues(SZDR_IN_FLO)

    # run ONE time step at the time
    NumberOfTimeSteps = int(max_steps) if max_steps is not None else 5000
    sim_end_dt = sim_end if sim_end is not None else datetime(2020, 9, 1)
    doNextTimeStep = True
    p = 0
    while doNextTimeStep:
        # for p in range(NumberOfTimeSteps):
        if p >= NumberOfTimeSteps:
            break

        Mshe_Tstep = ms.wm.currentTime()
        if ms.wm.currentTime() < sim_end_dt:
            if p % 1000 == 0:
                ms.wm.log(f"Requesting to run time step: {p}")

            (
                current_step_seconds,
                raw_next_step,
                next_step_resolution_error,
            ) = resolve_upcoming_wm_step_seconds(
                default_dt_seconds=runtime_context.mshe_dt_seconds
            )

            if (
                next_step_resolution_error is not None
                and is_end_of_simulation_timestep_error(next_step_resolution_error)
            ):
                ms.wm.log(
                    "  Reached configured simulation end; stopping the python WM loop before requesting another step."
                )
                break

            current_runtime_context = replace(
                runtime_context,
                mshe_dt_seconds=current_step_seconds,
            )

            if next_step_resolution_error is not None:
                if not next_step_fallback_logged:
                    ms.wm.log(
                        "  Warning: could not resolve upcoming WM step duration from "
                        f"nextTimeStep(); falling back to {current_step_seconds:.0f} s "
                        f"({type(next_step_resolution_error).__name__}: {next_step_resolution_error})"
                    )
                    next_step_fallback_logged = True
            elif (
                last_logged_step_seconds is None
                or abs(current_step_seconds - last_logged_step_seconds) > 1.0e-9
            ):
                ms.wm.log(
                    "  Upcoming WM step duration: "
                    f"{current_step_seconds:.0f} s (nextTimeStep={raw_next_step})"
                )
                last_logged_step_seconds = current_step_seconds

            # ms.wm.setValues(SZ_LEAK_FLO)
            # Get values from Daisy
            # daisyValue = daisy.findValueInDaisyResult(daisy_df, pd.to_datetime("2024-08-15 00:00"), "Precipitation")
            # daisyValue_Runoff = daisy.findValueInDaisyResult(daisy_df, Mshe_Tstep, "Runoff")
            daisy_interval_row = daisy.findIntervalRowInDaisyResult(
                daisy_df, Mshe_Tstep
            )
            if runoff_coupling_enabled:
                observed_ol_d_time, observed_ol_d_snapshot = (
                    read_observed_overland_depth(runtime_param_types)
                )
                runoff_transfer = apply_runoff_coupling(
                    OLDR_IN_FLO,
                    daisy_interval_row,
                    current_runtime_context,
                    runoff_bookkeeping_state,
                    Mshe_Tstep,
                    diagnostics_records=diagnostics_records,
                    observed_ol_d_time=observed_ol_d_time,
                    observed_ol_d_snapshot=observed_ol_d_snapshot,
                )
                ms.wm.setValues(OLDR_IN_FLO)
            else:
                runoff_transfer = None

            if drain_coupling_active:
                drain_transfer = apply_matrix_drain_flow_coupling(
                    SZDR_IN_FLO,
                    daisy_interval_row,
                    current_runtime_context,
                    drain_bookkeeping_state,
                    Mshe_Tstep,
                    diagnostics_records=diagnostics_records,
                )
                ms.wm.setValues(SZDR_IN_FLO)
            else:
                drain_transfer = None

            daisyValue_MatrixPercolation = daisy_interval_row["Matrix percolation"]
            (
                daisy_rate_matrix_percolation,
                SZ_LEAK_FLX_data,
                UZ_WC_data,
            ) = apply_matrix_percolation_coupling(
                SZ_LEAK_FLX,
                UZ_WC,
                UZ_WC_prev,
                daisy_interval_row,
                current_runtime_context,
                UZ_SZ_EX_POSUP_prev,
                Mshe_Tstep,
                diagnostics_records=diagnostics_records,
            )
            # daisyValue_MatrixDrainFlow = daisy.findValueInDaisyResult(daisy_df, Mshe_Tstep, "Matrix drain flow")
            if p % 100 == 0:
                print(
                    "Daisy MatrixPerco:\t"
                    + Mshe_Tstep.strftime("%Y-%m-%d %H:%M:%S")
                    + "\t"
                    + str(daisyValue_MatrixPercolation)
                    + " mm over "
                    + str(daisy_interval_row["interval_seconds"])
                    + " s -> "
                    + str(daisy_rate_matrix_percolation)
                    + " m/s"
                )
                if runoff_transfer is not None:
                    print(
                        "Daisy Runoff:\t"
                        + Mshe_Tstep.strftime("%Y-%m-%d %H:%M:%S")
                        + "\t"
                        + str(runoff_transfer.source_depth_mm)
                        + " mm -> "
                        + str(runoff_transfer.flow_m3_per_s)
                        + " m3/s per coupled cell"
                    )
                if drain_transfer is not None:
                    print(
                        "Daisy MatrixDrain:\t"
                        + Mshe_Tstep.strftime("%Y-%m-%d %H:%M:%S")
                        + "\t"
                        + str(drain_transfer.source_depth_mm)
                        + " mm -> "
                        + str(drain_transfer.flow_m3_per_s)
                        + " m3/s per drained cell"
                    )

            # SZ_LEAK_FLX_data[:,89:] = -22.22
            ms.wm.setValues(SZ_LEAK_FLX_data)
            ms.wm.setValues(UZ_WC_data)

            # ms.wm.setValues(SZ_SOURCE)
            # ms.wm.setValues(SZDR_IN_FLO)

            if ms.wm.currentTime() < datetime(2020, 9, 1):  # datetime(2021, 10, 17):
                # Mshe_Tstep = ms.wm.currentTime()
                if p % 100 == 0:
                    print(
                        str(p)
                        + ":"
                        + str(NumberOfTimeSteps)
                        + ":\t"
                        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        + ":\t"
                        + Mshe_Tstep.strftime("%Y-%m-%d %H:%M:%S")
                    )

            step_performed, step_dt_hours, step_time = ms.wm.performTimeStep()
            if not step_performed:
                ms.wm.log("Failed to execute a MIKE SHE time step via python")
                break

            actual_step_seconds = resolve_mshe_timestep_seconds(step_dt_hours)
            if (
                abs(actual_step_seconds - current_runtime_context.mshe_dt_seconds)
                > 1.0e-9
            ):
                ms.wm.log(
                    "  Warning: nextTimeStep prediction mismatch; "
                    f"predicted {current_runtime_context.mshe_dt_seconds:.0f} s but "
                    f"performTimeStep returned {actual_step_seconds:.0f} s at {step_time}"
                )
            startTime, currentTime, UZ_SZ_EX_POSUP_prev = ms.wm.getValues(
                runtime_param_types["UZ_SZ_EX_POSUP"]
            )
            startTime, currentTime, UZ_WC_prev = ms.wm.getValues(
                runtime_param_types["UZ_WC"]
            )
            p = p + 1
        else:
            break

    print("Simulation Completed:\t" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if diagnostics_output_path is not None and diagnostics_records is not None:
        if diagnostics_mode == "aggregated":
            diagnostics_timeseries = diagnostics_records.to_dataframe()
            diagnostics_path = write_diagnostics_csv(
                diagnostics_timeseries,
                diagnostics_output_path,
            )
            diagnostics_summary = diagnostics_records.summarize()
            diagnostics_summary_path = write_diagnostics_summary_csv(
                diagnostics_summary,
                diagnostics_path,
            )
            print(f"Aggregated diagnostics written to:\t{diagnostics_path}")
            print(f"Diagnostics summary written to:\t{diagnostics_summary_path}")
            if diagnostics_plot_dir is not None:
                plot_paths = write_diagnostics_plots(
                    diagnostics_timeseries,
                    diagnostics_path,
                    output_dir=diagnostics_plot_dir,
                )
                print(f"Diagnostics plots written to:\t{diagnostics_plot_dir}")
                for plot_path in plot_paths:
                    print(f"Diagnostics plot:\t{plot_path}")
        else:
            diagnostics_path = write_diagnostics_csv(
                diagnostics_records,
                diagnostics_output_path,
            )
            diagnostics_summary = summarize_volume_closure(diagnostics_records)
            diagnostics_summary_path = write_diagnostics_summary_csv(
                diagnostics_summary,
                diagnostics_path,
            )
            print(f"Diagnostics written to:\t{diagnostics_path}")
            print(f"Diagnostics summary written to:\t{diagnostics_summary_path}")
            if diagnostics_plot_dir is not None:
                diagnostics_timeseries = summarize_volume_closure_timeseries(
                    diagnostics_records
                )
                diagnostics_timeseries_path = write_diagnostics_timeseries_csv(
                    diagnostics_timeseries,
                    diagnostics_path,
                )
                plot_paths = write_diagnostics_plots(
                    diagnostics_timeseries,
                    diagnostics_path,
                    output_dir=diagnostics_plot_dir,
                )
                print(
                    f"Diagnostics timeseries written to:\t{diagnostics_timeseries_path}"
                )
                print(f"Diagnostics plots written to:\t{diagnostics_plot_dir}")
                for plot_path in plot_paths:
                    print(f"Diagnostics plot:\t{plot_path}")
        for _, summary_row in diagnostics_summary.iterrows():
            print(
                "Diagnostics closure summary:\t"
                f"{summary_row['variable_name']}: "
                f"rows={int(summary_row['row_count'])}, "
                f"requested={summary_row['requested_step_volume_m3']:.12g} m3, "
                f"target-storage={summary_row['target_storage_closure_m3']:.12g} m3, "
                f"max|target-storage|={summary_row['max_abs_target_storage_closure_m3']:.12g} m3"
            )
    ms.wm.terminate(True)


if __name__ == "__main__":
    args = parse_args()

    if args.print_config:
        print_configuration(args)
        raise SystemExit(0)

    setup_path, _ = get_configured_path(
        args.setup,
        "MSHE_SETUP",
        DEFAULT_SETUP,
        "MIKE SHE setup file (.she)",
    )
    daisy_output_path, _ = get_configured_path(
        args.daisy_output,
        "DAISY_OUTPUT_CSV",
        DEFAULT_DAISY_OUTPUT,
        "Daisy output CSV",
    )
    effective_uz_thickness_m, effective_uz_source = resolve_effective_uz_thickness(
        args.effective_uz_thickness_m,
        setup_path=setup_path,
    )
    diagnostics_output_path = resolve_diagnostics_output_path(args.diagnostics_output)
    diagnostics_plot_dir = resolve_diagnostics_plot_dir(
        args.plot_diagnostics,
        diagnostics_output_path,
    )

    print("Simulation Started:\t" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(
        f"Effective UZ thickness:\t{effective_uz_thickness_m:g} m ({effective_uz_source})"
    )
    exectue_time_steps(
        str(setup_path),
        str(daisy_output_path),
        effective_uz_thickness_m,
        effective_uz_thickness_source=effective_uz_source,
        diagnostics_output_path=diagnostics_output_path,
        diagnostics_plot_dir=diagnostics_plot_dir,
        diagnostics_mode=args.diagnostics_mode,
        runoff_coupling_enabled=not args.disable_runoff_coupling,
        zero_preprocessed_runoff_coefficients=args.zero_preprocessed_runoff_coefficients,
        drain_coupling_enabled=not args.disable_drain_coupling,
        suppress_native_sz_drain=args.suppress_native_sz_drain,
        keep_native_sz_drain=args.keep_native_sz_drain,
        max_steps=args.max_steps,
        sim_end=datetime.strptime(args.sim_end, "%Y-%m-%d") if args.sim_end else None,
    )
