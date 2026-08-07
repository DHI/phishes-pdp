from __future__ import annotations

import argparse
import os
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from src.diagnostics import (
    DEFAULT_CLOSURE_TOLERANCE_M3,
    VOLUME_CLOSURE_TIMESERIES_MIN_COLUMNS,
    CouplingDiagnosticRecord,
    derive_diagnostics_plot_dir,
    summarize_volume_closure_timeseries,
    write_diagnostics_timeseries_csv,
)

VOLUME_TERMS_PLOT_NAME = "volume_terms_by_variable.png"
CLOSURE_TERMS_PLOT_NAME = "closure_terms_by_variable.png"
MATRIX_PERCOLATION_EFFECTIVE_STATE_PLOT_NAME = "matrix_percolation_effective_state.png"

_VARIABLE_LABELS = {
    "runoff": "Runoff → OLDR_IN_FLO",
    "matrix_percolation": "Matrix Percolation → SZ_LEAK_FLX",
    "drain": "Matrix Drain Flow → SZDR_IN_FLO",
}


def _import_pyplot():
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    return plt


def _coerce_timeseries_dataframe(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
    closure_tolerance_m3: float,
) -> pd.DataFrame:
    if isinstance(records, pd.DataFrame) and set(
        VOLUME_CLOSURE_TIMESERIES_MIN_COLUMNS
    ).issubset(records.columns):
        timeseries_df = records.copy()
    else:
        timeseries_df = summarize_volume_closure_timeseries(
            records,
            closure_tolerance_m3=closure_tolerance_m3,
        )

    if timeseries_df.empty:
        return timeseries_df

    timeseries_df["timestamp"] = pd.to_datetime(
        timeseries_df["timestamp"],
        errors="coerce",
    )
    return timeseries_df.sort_values(["timestamp", "variable_name"]).reset_index(
        drop=True
    )


def _variables_for_plots(timeseries_df: pd.DataFrame) -> list[str]:
    variables = [
        str(variable_name)
        for variable_name in timeseries_df["variable_name"].dropna().unique().tolist()
        if str(variable_name) != "TOTAL"
    ]
    return variables or ["TOTAL"]


def _plot_volume_terms(timeseries_df: pd.DataFrame, output_path: Path) -> Path:
    plt = _import_pyplot()
    variables = _variables_for_plots(timeseries_df)
    fig, axes = plt.subplots(
        len(variables),
        1,
        figsize=(12, max(3.5, 3.5 * len(variables))),
        sharex=True,
    )
    if len(variables) == 1:
        axes = [axes]

    term_specs = [
        ("requested_step_volume_m3", "DAISY requested"),
        ("target_step_volume_m3", "Applied to MIKE SHE"),
        ("storage_correction_volume_m3", "UZ storage correction"),
        ("residual_volume_m3", "Residual (error)"),
    ]

    for axis, variable_name in zip(axes, variables):
        subset = timeseries_df.loc[
            timeseries_df["variable_name"].astype(str) == variable_name
        ].sort_values("timestamp")
        for column_name, label in term_specs:
            axis.plot(
                subset["timestamp"],
                subset[column_name],
                marker="o",
                linewidth=1.5,
                markersize=3.0,
                label=label,
            )
        axis.axhline(0.0, color="black", linewidth=0.8, alpha=0.4)
        axis.set_ylabel("Volume (m³)")
        section_label = _VARIABLE_LABELS.get(variable_name, variable_name)
        axis.set_title(f"{section_label} — per-timestep volumes")
        axis.grid(True, alpha=0.3)

    axes[0].legend(loc="best")
    axes[-1].set_xlabel("timestamp")
    fig.autofmt_xdate()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_closure_terms(timeseries_df: pd.DataFrame, output_path: Path) -> Path:
    plt = _import_pyplot()
    variables = _variables_for_plots(timeseries_df)
    fig, axes = plt.subplots(
        len(variables),
        1,
        figsize=(12, max(3.5, 3.5 * len(variables))),
        sharex=True,
    )
    if len(variables) == 1:
        axes = [axes]

    term_specs = [
        ("requested_target_closure_m3", "DAISY − Applied (should be ~0)"),
        ("requested_storage_closure_m3", "DAISY − UZ correction"),
        ("target_storage_closure_m3", "Applied − UZ correction"),
    ]

    for axis, variable_name in zip(axes, variables):
        subset = timeseries_df.loc[
            timeseries_df["variable_name"].astype(str) == variable_name
        ].sort_values("timestamp")
        for column_name, label in term_specs:
            axis.plot(
                subset["timestamp"],
                subset[column_name],
                marker="o",
                linewidth=1.5,
                markersize=3.0,
                label=label,
            )
        axis.axhline(0.0, color="black", linewidth=0.8, alpha=0.4)
        axis.set_ylabel("Closure gap (m³)")
        section_label = _VARIABLE_LABELS.get(variable_name, variable_name)
        axis.set_title(f"{section_label} — volume closure gaps (ideal: all zero)")
        axis.grid(True, alpha=0.3)

    axes[0].legend(loc="best")
    axes[-1].set_xlabel("timestamp")
    fig.autofmt_xdate()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _plot_matrix_percolation_effective_state(
    timeseries_df: pd.DataFrame,
    output_path: Path,
) -> Path | None:
    subset = timeseries_df.loc[
        timeseries_df["variable_name"].astype(str) == "matrix_percolation"
    ].sort_values("timestamp")
    if subset.empty:
        return None

    effective_columns = [
        "mean_effective_uz_theta_before",
        "mean_effective_uz_theta_requested_after",
        "mean_effective_uz_theta_after",
    ]
    if not any(subset[column_name].notna().any() for column_name in effective_columns):
        return None

    plt = _import_pyplot()
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    axes[0].plot(
        subset["timestamp"],
        subset["mean_effective_uz_theta_before"],
        marker="o",
        linewidth=1.5,
        markersize=3.0,
        label="θ before coupling",
    )
    axes[0].plot(
        subset["timestamp"],
        subset["mean_effective_uz_theta_requested_after"],
        marker="o",
        linewidth=1.5,
        markersize=3.0,
        label="θ requested after coupling",
    )
    axes[0].plot(
        subset["timestamp"],
        subset["mean_effective_uz_theta_after"],
        marker="o",
        linewidth=1.5,
        markersize=3.0,
        label="θ after bound clamping",
    )
    axes[0].set_ylabel("Mean UZ water content (θ)")
    axes[0].set_title(
        "Matrix Percolation — mean UZ water content before/after coupling"
    )
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    axes[1].plot(
        subset["timestamp"],
        subset["bounds_applied_rows"],
        marker="o",
        linewidth=1.5,
        markersize=3.0,
        label="cells where θ bounds applied",
    )
    axes[1].plot(
        subset["timestamp"],
        subset["rows_with_nonzero_residual"],
        marker="o",
        linewidth=1.5,
        markersize=3.0,
        label="cells with nonzero residual",
    )
    axes[1].set_ylabel("Number of cells")
    axes[1].set_title(
        "Matrix Percolation — cells hitting θ bounds / cells with residual volume"
    )
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")
    axes[1].set_xlabel("timestamp")

    fig.autofmt_xdate()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def write_diagnostics_plots(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
    diagnostics_output_file: str | Path,
    output_dir: str | Path | None = None,
    closure_tolerance_m3: float = DEFAULT_CLOSURE_TOLERANCE_M3,
) -> list[Path]:
    timeseries_df = _coerce_timeseries_dataframe(records, closure_tolerance_m3)
    if timeseries_df.empty:
        return []

    plot_dir = (
        Path(output_dir)
        if output_dir is not None
        else derive_diagnostics_plot_dir(diagnostics_output_file)
    )
    plot_dir.mkdir(parents=True, exist_ok=True)

    plot_paths = [
        _plot_volume_terms(timeseries_df, plot_dir / VOLUME_TERMS_PLOT_NAME),
        _plot_closure_terms(timeseries_df, plot_dir / CLOSURE_TERMS_PLOT_NAME),
    ]
    matrix_plot_path = _plot_matrix_percolation_effective_state(
        timeseries_df,
        plot_dir / MATRIX_PERCOLATION_EFFECTIVE_STATE_PLOT_NAME,
    )
    if matrix_plot_path is not None:
        plot_paths.append(matrix_plot_path)

    return plot_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Phase 5-style diagnostics plots from an existing diagnostics CSV.",
    )
    parser.add_argument(
        "--diagnostics-csv",
        required=True,
        help="Path to a detailed diagnostics CSV written by src.Test_Cernici.",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Optional directory for generated PNG plots. Defaults to a sibling "
            "<diagnostics_stem>_plots directory."
        ),
    )
    parser.add_argument(
        "--closure-tolerance-m3",
        type=float,
        default=DEFAULT_CLOSURE_TOLERANCE_M3,
        help="Closure tolerance used for derived residual/flag summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    diagnostics_csv_path = Path(args.diagnostics_csv).resolve()
    diagnostics_df = pd.read_csv(diagnostics_csv_path)
    timeseries_df = _coerce_timeseries_dataframe(
        diagnostics_df,
        float(args.closure_tolerance_m3),
    )
    if set(VOLUME_CLOSURE_TIMESERIES_MIN_COLUMNS).issubset(diagnostics_df.columns):
        timeseries_path = diagnostics_csv_path
    else:
        timeseries_path = write_diagnostics_timeseries_csv(
            timeseries_df,
            diagnostics_csv_path,
            closure_tolerance_m3=float(args.closure_tolerance_m3),
        )
    plot_paths = write_diagnostics_plots(
        timeseries_df,
        diagnostics_csv_path,
        output_dir=args.output_dir,
        closure_tolerance_m3=float(args.closure_tolerance_m3),
    )

    print(f"Diagnostics timeseries written to: {timeseries_path}")
    if plot_paths:
        print("Diagnostics plots written:")
        for plot_path in plot_paths:
            print(f"- {plot_path}")
    else:
        print("No plots were written because the diagnostics timeseries was empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
