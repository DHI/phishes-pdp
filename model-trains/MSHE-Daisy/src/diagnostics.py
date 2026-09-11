from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

DEFAULT_CLOSURE_TOLERANCE_M3 = 1.0e-15
VOLUME_CLOSURE_SUMMARY_COLUMNS = [
    "variable_name",
    "row_count",
    "requested_step_volume_m3",
    "target_step_volume_m3",
    "storage_correction_volume_m3",
    "residual_volume_m3",
    "rows_with_nonzero_residual",
    "max_abs_residual_volume_m3",
    "requested_target_closure_m3",
    "max_abs_requested_target_closure_m3",
    "requested_target_rows_over_tolerance",
    "requested_storage_closure_m3",
    "max_abs_requested_storage_closure_m3",
    "requested_storage_rows_over_tolerance",
    "target_storage_closure_m3",
    "max_abs_target_storage_closure_m3",
    "target_storage_rows_over_tolerance",
]
VOLUME_CLOSURE_TIMESERIES_MIN_COLUMNS = [
    "timestamp",
    "variable_name",
    "row_count",
    "requested_step_volume_m3",
    "target_step_volume_m3",
    "storage_correction_volume_m3",
    "residual_volume_m3",
    "rows_with_nonzero_residual",
    "bounds_applied_rows",
    "max_abs_residual_volume_m3",
    "requested_target_closure_m3",
    "max_abs_requested_target_closure_m3",
    "requested_storage_closure_m3",
    "max_abs_requested_storage_closure_m3",
    "target_storage_closure_m3",
    "max_abs_target_storage_closure_m3",
    "mean_effective_uz_theta_before",
    "mean_effective_uz_theta_requested_after",
    "mean_effective_uz_theta_after",
]
VOLUME_CLOSURE_TIMESERIES_COLUMNS = [
    "timestamp",
    "variable_name",
    "row_count",
    "requested_step_volume_m3",
    "target_step_volume_m3",
    "storage_correction_volume_m3",
    "residual_volume_m3",
    "rows_with_nonzero_residual",
    "bounds_applied_rows",
    "max_abs_residual_volume_m3",
    "requested_target_closure_m3",
    "max_abs_requested_target_closure_m3",
    "requested_target_rows_over_tolerance",
    "requested_storage_closure_m3",
    "max_abs_requested_storage_closure_m3",
    "requested_storage_rows_over_tolerance",
    "target_storage_closure_m3",
    "max_abs_target_storage_closure_m3",
    "target_storage_rows_over_tolerance",
    "mean_effective_uz_theta_before",
    "mean_effective_uz_theta_requested_after",
    "mean_effective_uz_theta_after",
]


@dataclass(frozen=True)
class CouplingDiagnosticRecord:
    timestamp: object
    variable_name: str
    row: int
    col: int
    daisy_source_id: str
    interval_start_time: object | None = None
    interval_end_time: object | None = None
    source_depth_mm: float | None = None
    interval_seconds: float | None = None
    target_value: float | None = None
    storage_correction: float | None = None
    residual: float | None = None
    sign_convention: str | None = None
    lower_boundary_case: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def _record_to_dict(record: CouplingDiagnosticRecord) -> dict[str, object]:
    record_dict = asdict(record)
    record_dict["metadata"] = (
        json.dumps(record_dict["metadata"], sort_keys=True)
        if record_dict["metadata"]
        else None
    )
    return record_dict


def diagnostics_to_dataframe(
    records: Iterable[CouplingDiagnosticRecord],
) -> pd.DataFrame:
    return pd.DataFrame(_record_to_dict(record) for record in records)


def _coerce_diagnostics_dataframe(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
) -> pd.DataFrame:
    if isinstance(records, pd.DataFrame):
        return records.copy()
    return diagnostics_to_dataframe(records)


def _looks_like_volume_closure_timeseries_dataframe(df: pd.DataFrame) -> bool:
    return set(VOLUME_CLOSURE_TIMESERIES_MIN_COLUMNS).issubset(df.columns)


def _coerce_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return float(default)

    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return bool(default)

    try:
        if pd.isna(value):
            return bool(default)
    except TypeError:
        pass

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False

    return bool(value)


def _coerce_volume_closure_timeseries_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=VOLUME_CLOSURE_TIMESERIES_COLUMNS)

    timeseries_df = df.copy()
    defaults = {
        "row_count": 0,
        "requested_step_volume_m3": 0.0,
        "target_step_volume_m3": 0.0,
        "storage_correction_volume_m3": 0.0,
        "residual_volume_m3": 0.0,
        "rows_with_nonzero_residual": 0,
        "bounds_applied_rows": 0,
        "max_abs_residual_volume_m3": 0.0,
        "requested_target_closure_m3": 0.0,
        "max_abs_requested_target_closure_m3": 0.0,
        "requested_target_rows_over_tolerance": 0,
        "requested_storage_closure_m3": 0.0,
        "max_abs_requested_storage_closure_m3": 0.0,
        "requested_storage_rows_over_tolerance": 0,
        "target_storage_closure_m3": 0.0,
        "max_abs_target_storage_closure_m3": 0.0,
        "target_storage_rows_over_tolerance": 0,
        "mean_effective_uz_theta_before": float("nan"),
        "mean_effective_uz_theta_requested_after": float("nan"),
        "mean_effective_uz_theta_after": float("nan"),
    }

    for column_name, default_value in defaults.items():
        if column_name not in timeseries_df.columns:
            timeseries_df[column_name] = default_value

    timeseries_df["timestamp"] = pd.to_datetime(
        timeseries_df["timestamp"],
        errors="coerce",
    )
    return (
        timeseries_df[VOLUME_CLOSURE_TIMESERIES_COLUMNS]
        .sort_values(["timestamp", "variable_name"])
        .reset_index(drop=True)
    )


def _resolve_volume_closure_row(
    record: CouplingDiagnosticRecord,
) -> dict[str, object]:
    metadata = dict(record.metadata or {})
    timestamp = pd.to_datetime(record.timestamp, errors="coerce")
    variable_name = str(record.variable_name)

    target_value = _coerce_float(record.target_value)
    storage_correction = _coerce_float(record.storage_correction)
    residual = _coerce_float(record.residual)
    wm_step_seconds = _coerce_float(metadata.get("wm_step_seconds"))
    cell_area_m2 = _coerce_float(metadata.get("cell_area_m2"))
    effective_uz_thickness_m = _coerce_float(metadata.get("effective_uz_thickness_m"))
    target_units = metadata.get("target_units")
    storage_units = metadata.get("storage_units")
    runoff_mask = variable_name == "runoff"

    requested_step_volume_m3 = metadata.get("requested_step_volume_m3")
    if requested_step_volume_m3 is None or pd.isna(requested_step_volume_m3):
        requested_step_volume_m3 = metadata.get("step_volume_m3")
    requested_step_volume_m3 = _coerce_float(requested_step_volume_m3)

    target_step_volume_m3 = metadata.get("target_step_volume_m3")
    if target_step_volume_m3 is None or pd.isna(target_step_volume_m3):
        if target_units == "m3/s":
            target_step_volume_m3 = target_value * wm_step_seconds
        elif target_units == "m/s":
            target_step_volume_m3 = target_value * wm_step_seconds * cell_area_m2
        else:
            target_step_volume_m3 = 0.0
    target_step_volume_m3 = _coerce_float(target_step_volume_m3)

    storage_correction_volume_m3 = metadata.get("storage_correction_volume_m3")
    if storage_correction_volume_m3 is None or pd.isna(storage_correction_volume_m3):
        if storage_units == "m":
            storage_correction_volume_m3 = storage_correction * cell_area_m2
        elif storage_units == "delta_theta":
            storage_correction_volume_m3 = (
                storage_correction * effective_uz_thickness_m * cell_area_m2
            )
        else:
            storage_correction_volume_m3 = 0.0
    storage_correction_volume_m3 = _coerce_float(storage_correction_volume_m3)

    residual_volume_m3 = metadata.get("residual_volume_m3")
    if residual_volume_m3 is None or pd.isna(residual_volume_m3):
        if storage_units == "m" and runoff_mask:
            residual_volume_m3 = abs(residual) * cell_area_m2
        elif storage_units == "m":
            residual_volume_m3 = residual * cell_area_m2
        elif storage_units == "delta_theta":
            residual_volume_m3 = residual * effective_uz_thickness_m * cell_area_m2
        else:
            residual_volume_m3 = 0.0
    residual_volume_m3 = _coerce_float(residual_volume_m3)

    requested_target_closure_m3 = requested_step_volume_m3 - target_step_volume_m3
    requested_storage_closure_m3 = (
        requested_step_volume_m3 - storage_correction_volume_m3 - residual_volume_m3
    )
    target_storage_closure_m3 = (
        target_step_volume_m3 - storage_correction_volume_m3 - residual_volume_m3
    )

    return {
        "timestamp": timestamp,
        "variable_name": variable_name,
        "requested_step_volume_m3": requested_step_volume_m3,
        "target_step_volume_m3": target_step_volume_m3,
        "storage_correction_volume_m3": storage_correction_volume_m3,
        "residual_volume_m3": residual_volume_m3,
        "requested_target_closure_m3": requested_target_closure_m3,
        "requested_storage_closure_m3": requested_storage_closure_m3,
        "target_storage_closure_m3": target_storage_closure_m3,
        "bounds_applied": _coerce_bool(metadata.get("bounds_applied"), False),
        "effective_uz_theta_before": metadata.get("effective_uz_theta_before"),
        "effective_uz_theta_requested_after": metadata.get(
            "effective_uz_theta_requested_after"
        ),
        "effective_uz_theta_after": metadata.get("effective_uz_theta_after"),
    }


@dataclass
class _VolumeClosureTimeseriesAccumulator:
    timestamp: object
    variable_name: str
    row_count: int = 0
    requested_step_volume_m3: float = 0.0
    target_step_volume_m3: float = 0.0
    storage_correction_volume_m3: float = 0.0
    residual_volume_m3: float = 0.0
    rows_with_nonzero_residual: int = 0
    bounds_applied_rows: int = 0
    max_abs_residual_volume_m3: float = 0.0
    requested_target_closure_m3: float = 0.0
    max_abs_requested_target_closure_m3: float = 0.0
    requested_target_rows_over_tolerance: int = 0
    requested_storage_closure_m3: float = 0.0
    max_abs_requested_storage_closure_m3: float = 0.0
    requested_storage_rows_over_tolerance: int = 0
    target_storage_closure_m3: float = 0.0
    max_abs_target_storage_closure_m3: float = 0.0
    target_storage_rows_over_tolerance: int = 0
    _effective_uz_theta_before_sum: float = 0.0
    _effective_uz_theta_before_count: int = 0
    _effective_uz_theta_requested_after_sum: float = 0.0
    _effective_uz_theta_requested_after_count: int = 0
    _effective_uz_theta_after_sum: float = 0.0
    _effective_uz_theta_after_count: int = 0

    def add_row(self, row: dict[str, object], closure_tolerance_m3: float) -> None:
        residual_volume_m3 = _coerce_float(row["residual_volume_m3"])
        requested_target_closure_m3 = _coerce_float(row["requested_target_closure_m3"])
        requested_storage_closure_m3 = _coerce_float(
            row["requested_storage_closure_m3"]
        )
        target_storage_closure_m3 = _coerce_float(row["target_storage_closure_m3"])

        self.row_count += 1
        self.requested_step_volume_m3 += _coerce_float(row["requested_step_volume_m3"])
        self.target_step_volume_m3 += _coerce_float(row["target_step_volume_m3"])
        self.storage_correction_volume_m3 += _coerce_float(
            row["storage_correction_volume_m3"]
        )
        self.residual_volume_m3 += residual_volume_m3
        self.rows_with_nonzero_residual += int(
            abs(residual_volume_m3) > closure_tolerance_m3
        )
        self.bounds_applied_rows += int(_coerce_bool(row["bounds_applied"], False))
        self.max_abs_residual_volume_m3 = max(
            self.max_abs_residual_volume_m3,
            abs(residual_volume_m3),
        )
        self.requested_target_closure_m3 += requested_target_closure_m3
        self.max_abs_requested_target_closure_m3 = max(
            self.max_abs_requested_target_closure_m3,
            abs(requested_target_closure_m3),
        )
        self.requested_target_rows_over_tolerance += int(
            abs(requested_target_closure_m3) > closure_tolerance_m3
        )
        self.requested_storage_closure_m3 += requested_storage_closure_m3
        self.max_abs_requested_storage_closure_m3 = max(
            self.max_abs_requested_storage_closure_m3,
            abs(requested_storage_closure_m3),
        )
        self.requested_storage_rows_over_tolerance += int(
            abs(requested_storage_closure_m3) > closure_tolerance_m3
        )
        self.target_storage_closure_m3 += target_storage_closure_m3
        self.max_abs_target_storage_closure_m3 = max(
            self.max_abs_target_storage_closure_m3,
            abs(target_storage_closure_m3),
        )
        self.target_storage_rows_over_tolerance += int(
            abs(target_storage_closure_m3) > closure_tolerance_m3
        )

        for column_name, sum_attr, count_attr in (
            (
                "effective_uz_theta_before",
                "_effective_uz_theta_before_sum",
                "_effective_uz_theta_before_count",
            ),
            (
                "effective_uz_theta_requested_after",
                "_effective_uz_theta_requested_after_sum",
                "_effective_uz_theta_requested_after_count",
            ),
            (
                "effective_uz_theta_after",
                "_effective_uz_theta_after_sum",
                "_effective_uz_theta_after_count",
            ),
        ):
            value = row.get(column_name)
            if value is None:
                continue
            try:
                if pd.isna(value):
                    continue
            except TypeError:
                pass
            setattr(self, sum_attr, getattr(self, sum_attr) + float(value))
            setattr(self, count_attr, getattr(self, count_attr) + 1)

    def to_row(self) -> dict[str, object]:
        def _mean(total: float, count: int) -> float:
            return float("nan") if count == 0 else float(total / count)

        return {
            "timestamp": self.timestamp,
            "variable_name": self.variable_name,
            "row_count": self.row_count,
            "requested_step_volume_m3": self.requested_step_volume_m3,
            "target_step_volume_m3": self.target_step_volume_m3,
            "storage_correction_volume_m3": self.storage_correction_volume_m3,
            "residual_volume_m3": self.residual_volume_m3,
            "rows_with_nonzero_residual": self.rows_with_nonzero_residual,
            "bounds_applied_rows": self.bounds_applied_rows,
            "max_abs_residual_volume_m3": self.max_abs_residual_volume_m3,
            "requested_target_closure_m3": self.requested_target_closure_m3,
            "max_abs_requested_target_closure_m3": self.max_abs_requested_target_closure_m3,
            "requested_target_rows_over_tolerance": self.requested_target_rows_over_tolerance,
            "requested_storage_closure_m3": self.requested_storage_closure_m3,
            "max_abs_requested_storage_closure_m3": self.max_abs_requested_storage_closure_m3,
            "requested_storage_rows_over_tolerance": self.requested_storage_rows_over_tolerance,
            "target_storage_closure_m3": self.target_storage_closure_m3,
            "max_abs_target_storage_closure_m3": self.max_abs_target_storage_closure_m3,
            "target_storage_rows_over_tolerance": self.target_storage_rows_over_tolerance,
            "mean_effective_uz_theta_before": _mean(
                self._effective_uz_theta_before_sum,
                self._effective_uz_theta_before_count,
            ),
            "mean_effective_uz_theta_requested_after": _mean(
                self._effective_uz_theta_requested_after_sum,
                self._effective_uz_theta_requested_after_count,
            ),
            "mean_effective_uz_theta_after": _mean(
                self._effective_uz_theta_after_sum,
                self._effective_uz_theta_after_count,
            ),
        }


class VolumeClosureTimeseriesAggregator:
    def __init__(self, closure_tolerance_m3: float = DEFAULT_CLOSURE_TOLERANCE_M3):
        self.closure_tolerance_m3 = float(closure_tolerance_m3)
        self._accumulators: dict[
            tuple[object, str], _VolumeClosureTimeseriesAccumulator
        ] = {}

    def append(self, record: CouplingDiagnosticRecord) -> None:
        self.add_record(record)

    def add_record(self, record: CouplingDiagnosticRecord) -> None:
        row = _resolve_volume_closure_row(record)
        key = (row["timestamp"], str(row["variable_name"]))
        accumulator = self._accumulators.get(key)
        if accumulator is None:
            accumulator = _VolumeClosureTimeseriesAccumulator(
                timestamp=row["timestamp"],
                variable_name=str(row["variable_name"]),
            )
            self._accumulators[key] = accumulator
        accumulator.add_row(row, self.closure_tolerance_m3)

    def extend(self, records: Iterable[CouplingDiagnosticRecord]) -> None:
        for record in records:
            self.add_record(record)

    def to_dataframe(self) -> pd.DataFrame:
        rows = [
            accumulator.to_row()
            for _, accumulator in sorted(
                self._accumulators.items(),
                key=lambda item: (item[0][0], item[0][1]),
            )
        ]
        return _coerce_volume_closure_timeseries_dataframe(pd.DataFrame(rows))

    def summarize(self) -> pd.DataFrame:
        return summarize_volume_closure(
            self.to_dataframe(),
            closure_tolerance_m3=self.closure_tolerance_m3,
        )


def _parse_metadata_json(value: object) -> dict[str, object]:
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        if not value.strip():
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    if pd.isna(value):
        return {}

    return {}


def expand_diagnostics_metadata(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
) -> pd.DataFrame:
    df = _coerce_diagnostics_dataframe(records)
    if df.empty:
        return df

    metadata_series = df.get(
        "metadata",
        pd.Series([None] * len(df), index=df.index, dtype=object),
    ).map(_parse_metadata_json)
    metadata_df = pd.json_normalize(metadata_series)

    return pd.concat(
        [
            df.drop(columns=["metadata"], errors="ignore").reset_index(drop=True),
            metadata_df,
        ],
        axis=1,
    )


def write_diagnostics_csv(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
    output_file: str | Path,
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _coerce_diagnostics_dataframe(records).to_csv(output_path, index=False)
    return output_path


def derive_diagnostics_summary_path(output_file: str | Path) -> Path:
    output_path = Path(output_file)
    return output_path.with_name(f"{output_path.stem}_summary.csv")


def derive_diagnostics_timeseries_path(output_file: str | Path) -> Path:
    output_path = Path(output_file)
    return output_path.with_name(f"{output_path.stem}_timeseries.csv")


def derive_diagnostics_plot_dir(output_file: str | Path) -> Path:
    output_path = Path(output_file)
    return output_path.with_name(f"{output_path.stem}_plots")


def _numeric_series(
    df: pd.DataFrame,
    column_name: str,
    default: float = 0.0,
) -> pd.Series:
    if column_name not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[column_name], errors="coerce").fillna(default)


def _sum_float(series: pd.Series) -> float:
    return float(series.fillna(0.0).sum())


def _max_abs_float(series: pd.Series) -> float:
    series = series.dropna()
    return 0.0 if series.empty else float(series.abs().max())


def _rows_over_tolerance(
    series: pd.Series,
    closure_tolerance_m3: float,
) -> int:
    return int(series.fillna(0.0).abs().gt(float(closure_tolerance_m3)).sum())


def _mean_or_nan(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    return float("nan") if series.empty else float(series.mean())


def _enrich_volume_closure_dataframe(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
) -> pd.DataFrame:
    df = expand_diagnostics_metadata(records)
    if df.empty:
        return df

    target_value = _numeric_series(df, "target_value")
    storage_correction = _numeric_series(df, "storage_correction")
    residual = _numeric_series(df, "residual")
    wm_step_seconds = _numeric_series(df, "wm_step_seconds")
    cell_area_m2 = _numeric_series(df, "cell_area_m2")
    effective_uz_thickness_m = _numeric_series(df, "effective_uz_thickness_m")

    target_units = (
        df["target_units"]
        if "target_units" in df.columns
        else pd.Series([None] * len(df), index=df.index, dtype=object)
    )
    storage_units = (
        df["storage_units"]
        if "storage_units" in df.columns
        else pd.Series([None] * len(df), index=df.index, dtype=object)
    )
    runoff_mask = (
        df["variable_name"].eq("runoff")
        if "variable_name" in df.columns
        else pd.Series(False, index=df.index)
    )

    requested_step_volume_m3 = _numeric_series(
        df,
        "requested_step_volume_m3",
        default=float("nan"),
    )
    unresolved_requested = requested_step_volume_m3.isna()
    requested_step_volume_m3.loc[unresolved_requested] = _numeric_series(
        df.loc[unresolved_requested],
        "step_volume_m3",
        default=0.0,
    )
    requested_step_volume_m3 = requested_step_volume_m3.fillna(0.0)

    target_step_volume_m3 = _numeric_series(
        df,
        "target_step_volume_m3",
        default=float("nan"),
    )
    unresolved_target = target_step_volume_m3.isna()
    target_step_volume_m3.loc[unresolved_target & target_units.eq("m3/s")] = (
        target_value.loc[unresolved_target & target_units.eq("m3/s")]
        * wm_step_seconds.loc[unresolved_target & target_units.eq("m3/s")]
    )
    target_step_volume_m3.loc[unresolved_target & target_units.eq("m/s")] = (
        target_value.loc[unresolved_target & target_units.eq("m/s")]
        * wm_step_seconds.loc[unresolved_target & target_units.eq("m/s")]
        * cell_area_m2.loc[unresolved_target & target_units.eq("m/s")]
    )
    target_step_volume_m3 = target_step_volume_m3.fillna(0.0)

    storage_correction_volume_m3 = _numeric_series(
        df,
        "storage_correction_volume_m3",
        default=float("nan"),
    )
    unresolved_storage = storage_correction_volume_m3.isna()
    storage_correction_volume_m3.loc[unresolved_storage & storage_units.eq("m")] = (
        storage_correction.loc[unresolved_storage & storage_units.eq("m")]
        * cell_area_m2.loc[unresolved_storage & storage_units.eq("m")]
    )
    storage_correction_volume_m3.loc[
        unresolved_storage & storage_units.eq("delta_theta")
    ] = (
        storage_correction.loc[unresolved_storage & storage_units.eq("delta_theta")]
        * effective_uz_thickness_m.loc[
            unresolved_storage & storage_units.eq("delta_theta")
        ]
        * cell_area_m2.loc[unresolved_storage & storage_units.eq("delta_theta")]
    )
    storage_correction_volume_m3 = storage_correction_volume_m3.fillna(0.0)

    residual_volume_m3 = _numeric_series(
        df,
        "residual_volume_m3",
        default=float("nan"),
    )
    unresolved_residual = residual_volume_m3.isna()
    residual_volume_m3.loc[
        unresolved_residual & storage_units.eq("m") & runoff_mask
    ] = (
        residual.loc[unresolved_residual & storage_units.eq("m") & runoff_mask].abs()
        * cell_area_m2.loc[unresolved_residual & storage_units.eq("m") & runoff_mask]
    )
    residual_volume_m3.loc[
        unresolved_residual & storage_units.eq("m") & ~runoff_mask
    ] = (
        residual.loc[unresolved_residual & storage_units.eq("m") & ~runoff_mask]
        * cell_area_m2.loc[unresolved_residual & storage_units.eq("m") & ~runoff_mask]
    )
    residual_volume_m3.loc[unresolved_residual & storage_units.eq("delta_theta")] = (
        residual.loc[unresolved_residual & storage_units.eq("delta_theta")]
        * effective_uz_thickness_m.loc[
            unresolved_residual & storage_units.eq("delta_theta")
        ]
        * cell_area_m2.loc[unresolved_residual & storage_units.eq("delta_theta")]
    )
    residual_volume_m3 = residual_volume_m3.fillna(0.0)

    requested_target_closure_m3 = requested_step_volume_m3 - target_step_volume_m3
    requested_storage_closure_m3 = (
        requested_step_volume_m3 - storage_correction_volume_m3 - residual_volume_m3
    )
    target_storage_closure_m3 = (
        target_step_volume_m3 - storage_correction_volume_m3 - residual_volume_m3
    )

    enriched = df.copy()
    enriched["requested_step_volume_m3"] = requested_step_volume_m3
    enriched["target_step_volume_m3"] = target_step_volume_m3
    enriched["storage_correction_volume_m3"] = storage_correction_volume_m3
    enriched["residual_volume_m3"] = residual_volume_m3
    enriched["requested_target_closure_m3"] = requested_target_closure_m3
    enriched["requested_storage_closure_m3"] = requested_storage_closure_m3
    enriched["target_storage_closure_m3"] = target_storage_closure_m3
    enriched["bounds_applied"] = (
        enriched["bounds_applied"].map(
            lambda value: bool(value) if pd.notna(value) else False
        )
        if "bounds_applied" in enriched.columns
        else pd.Series(False, index=enriched.index, dtype=bool)
    )
    enriched["effective_uz_theta_before"] = _numeric_series(
        enriched,
        "effective_uz_theta_before",
        default=float("nan"),
    )
    enriched["effective_uz_theta_requested_after"] = _numeric_series(
        enriched,
        "effective_uz_theta_requested_after",
        default=float("nan"),
    )
    enriched["effective_uz_theta_after"] = _numeric_series(
        enriched,
        "effective_uz_theta_after",
        default=float("nan"),
    )

    return enriched


def summarize_mass_balance(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
) -> pd.DataFrame:
    df = _coerce_diagnostics_dataframe(records)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "variable_name",
                "source_depth_mm",
                "target_value",
                "storage_correction",
                "residual",
            ]
        )

    numeric_columns = [
        "source_depth_mm",
        "target_value",
        "storage_correction",
        "residual",
    ]
    for column_name in numeric_columns:
        df[column_name] = pd.to_numeric(df[column_name], errors="coerce").fillna(0.0)

    return (
        df.groupby("variable_name", dropna=False)[numeric_columns].sum().reset_index()
    )


def summarize_volume_closure(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
    closure_tolerance_m3: float = DEFAULT_CLOSURE_TOLERANCE_M3,
) -> pd.DataFrame:
    if isinstance(
        records, pd.DataFrame
    ) and _looks_like_volume_closure_timeseries_dataframe(records):
        timeseries_df = _coerce_volume_closure_timeseries_dataframe(records)
        summary_rows = []
        for variable_name, group_df in timeseries_df.groupby(
            "variable_name", dropna=False
        ):
            summary_rows.append(
                {
                    "variable_name": variable_name,
                    "row_count": int(_sum_float(group_df["row_count"])),
                    "requested_step_volume_m3": _sum_float(
                        group_df["requested_step_volume_m3"]
                    ),
                    "target_step_volume_m3": _sum_float(
                        group_df["target_step_volume_m3"]
                    ),
                    "storage_correction_volume_m3": _sum_float(
                        group_df["storage_correction_volume_m3"]
                    ),
                    "residual_volume_m3": _sum_float(group_df["residual_volume_m3"]),
                    "rows_with_nonzero_residual": int(
                        _sum_float(group_df["rows_with_nonzero_residual"])
                    ),
                    "max_abs_residual_volume_m3": _max_abs_float(
                        group_df["max_abs_residual_volume_m3"]
                    ),
                    "requested_target_closure_m3": _sum_float(
                        group_df["requested_target_closure_m3"]
                    ),
                    "max_abs_requested_target_closure_m3": _max_abs_float(
                        group_df["max_abs_requested_target_closure_m3"]
                    ),
                    "requested_target_rows_over_tolerance": int(
                        _sum_float(group_df["requested_target_rows_over_tolerance"])
                    ),
                    "requested_storage_closure_m3": _sum_float(
                        group_df["requested_storage_closure_m3"]
                    ),
                    "max_abs_requested_storage_closure_m3": _max_abs_float(
                        group_df["max_abs_requested_storage_closure_m3"]
                    ),
                    "requested_storage_rows_over_tolerance": int(
                        _sum_float(group_df["requested_storage_rows_over_tolerance"])
                    ),
                    "target_storage_closure_m3": _sum_float(
                        group_df["target_storage_closure_m3"]
                    ),
                    "max_abs_target_storage_closure_m3": _max_abs_float(
                        group_df["max_abs_target_storage_closure_m3"]
                    ),
                    "target_storage_rows_over_tolerance": int(
                        _sum_float(group_df["target_storage_rows_over_tolerance"])
                    ),
                }
            )

        summary_rows.append(
            {
                "variable_name": "TOTAL",
                "row_count": int(_sum_float(timeseries_df["row_count"])),
                "requested_step_volume_m3": _sum_float(
                    timeseries_df["requested_step_volume_m3"]
                ),
                "target_step_volume_m3": _sum_float(
                    timeseries_df["target_step_volume_m3"]
                ),
                "storage_correction_volume_m3": _sum_float(
                    timeseries_df["storage_correction_volume_m3"]
                ),
                "residual_volume_m3": _sum_float(timeseries_df["residual_volume_m3"]),
                "rows_with_nonzero_residual": int(
                    _sum_float(timeseries_df["rows_with_nonzero_residual"])
                ),
                "max_abs_residual_volume_m3": _max_abs_float(
                    timeseries_df["max_abs_residual_volume_m3"]
                ),
                "requested_target_closure_m3": _sum_float(
                    timeseries_df["requested_target_closure_m3"]
                ),
                "max_abs_requested_target_closure_m3": _max_abs_float(
                    timeseries_df["max_abs_requested_target_closure_m3"]
                ),
                "requested_target_rows_over_tolerance": int(
                    _sum_float(timeseries_df["requested_target_rows_over_tolerance"])
                ),
                "requested_storage_closure_m3": _sum_float(
                    timeseries_df["requested_storage_closure_m3"]
                ),
                "max_abs_requested_storage_closure_m3": _max_abs_float(
                    timeseries_df["max_abs_requested_storage_closure_m3"]
                ),
                "requested_storage_rows_over_tolerance": int(
                    _sum_float(timeseries_df["requested_storage_rows_over_tolerance"])
                ),
                "target_storage_closure_m3": _sum_float(
                    timeseries_df["target_storage_closure_m3"]
                ),
                "max_abs_target_storage_closure_m3": _max_abs_float(
                    timeseries_df["max_abs_target_storage_closure_m3"]
                ),
                "target_storage_rows_over_tolerance": int(
                    _sum_float(timeseries_df["target_storage_rows_over_tolerance"])
                ),
            }
        )

        return pd.DataFrame(summary_rows, columns=VOLUME_CLOSURE_SUMMARY_COLUMNS)

    enriched = _enrich_volume_closure_dataframe(records)
    if enriched.empty:
        return pd.DataFrame(columns=VOLUME_CLOSURE_SUMMARY_COLUMNS)

    summary_rows = []
    for variable_name, group_df in enriched.groupby("variable_name", dropna=False):
        summary_rows.append(
            {
                "variable_name": variable_name,
                "row_count": len(group_df),
                "requested_step_volume_m3": _sum_float(
                    group_df["requested_step_volume_m3"]
                ),
                "target_step_volume_m3": _sum_float(group_df["target_step_volume_m3"]),
                "storage_correction_volume_m3": _sum_float(
                    group_df["storage_correction_volume_m3"]
                ),
                "residual_volume_m3": _sum_float(group_df["residual_volume_m3"]),
                "rows_with_nonzero_residual": _rows_over_tolerance(
                    group_df["residual_volume_m3"],
                    closure_tolerance_m3,
                ),
                "max_abs_residual_volume_m3": _max_abs_float(
                    group_df["residual_volume_m3"]
                ),
                "requested_target_closure_m3": _sum_float(
                    group_df["requested_target_closure_m3"]
                ),
                "max_abs_requested_target_closure_m3": _max_abs_float(
                    group_df["requested_target_closure_m3"]
                ),
                "requested_target_rows_over_tolerance": _rows_over_tolerance(
                    group_df["requested_target_closure_m3"],
                    closure_tolerance_m3,
                ),
                "requested_storage_closure_m3": _sum_float(
                    group_df["requested_storage_closure_m3"]
                ),
                "max_abs_requested_storage_closure_m3": _max_abs_float(
                    group_df["requested_storage_closure_m3"]
                ),
                "requested_storage_rows_over_tolerance": _rows_over_tolerance(
                    group_df["requested_storage_closure_m3"],
                    closure_tolerance_m3,
                ),
                "target_storage_closure_m3": _sum_float(
                    group_df["target_storage_closure_m3"]
                ),
                "max_abs_target_storage_closure_m3": _max_abs_float(
                    group_df["target_storage_closure_m3"]
                ),
                "target_storage_rows_over_tolerance": _rows_over_tolerance(
                    group_df["target_storage_closure_m3"],
                    closure_tolerance_m3,
                ),
            }
        )

    summary_rows.append(
        {
            "variable_name": "TOTAL",
            "row_count": len(enriched),
            "requested_step_volume_m3": _sum_float(
                enriched["requested_step_volume_m3"]
            ),
            "target_step_volume_m3": _sum_float(enriched["target_step_volume_m3"]),
            "storage_correction_volume_m3": _sum_float(
                enriched["storage_correction_volume_m3"]
            ),
            "residual_volume_m3": _sum_float(enriched["residual_volume_m3"]),
            "rows_with_nonzero_residual": _rows_over_tolerance(
                enriched["residual_volume_m3"],
                closure_tolerance_m3,
            ),
            "max_abs_residual_volume_m3": _max_abs_float(
                enriched["residual_volume_m3"]
            ),
            "requested_target_closure_m3": _sum_float(
                enriched["requested_target_closure_m3"]
            ),
            "max_abs_requested_target_closure_m3": _max_abs_float(
                enriched["requested_target_closure_m3"]
            ),
            "requested_target_rows_over_tolerance": _rows_over_tolerance(
                enriched["requested_target_closure_m3"],
                closure_tolerance_m3,
            ),
            "requested_storage_closure_m3": _sum_float(
                enriched["requested_storage_closure_m3"]
            ),
            "max_abs_requested_storage_closure_m3": _max_abs_float(
                enriched["requested_storage_closure_m3"]
            ),
            "requested_storage_rows_over_tolerance": _rows_over_tolerance(
                enriched["requested_storage_closure_m3"],
                closure_tolerance_m3,
            ),
            "target_storage_closure_m3": _sum_float(
                enriched["target_storage_closure_m3"]
            ),
            "max_abs_target_storage_closure_m3": _max_abs_float(
                enriched["target_storage_closure_m3"]
            ),
            "target_storage_rows_over_tolerance": _rows_over_tolerance(
                enriched["target_storage_closure_m3"],
                closure_tolerance_m3,
            ),
        }
    )

    return pd.DataFrame(summary_rows, columns=VOLUME_CLOSURE_SUMMARY_COLUMNS)


def summarize_volume_closure_timeseries(
    records: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
    closure_tolerance_m3: float = DEFAULT_CLOSURE_TOLERANCE_M3,
) -> pd.DataFrame:
    if isinstance(
        records, pd.DataFrame
    ) and _looks_like_volume_closure_timeseries_dataframe(records):
        return _coerce_volume_closure_timeseries_dataframe(records)

    enriched = _enrich_volume_closure_dataframe(records)
    if enriched.empty:
        return pd.DataFrame(columns=VOLUME_CLOSURE_TIMESERIES_COLUMNS)

    timestamps = pd.to_datetime(enriched.get("timestamp"), errors="coerce")
    enriched = enriched.assign(timestamp=timestamps)

    summary_rows = []
    for (timestamp, variable_name), group_df in enriched.groupby(
        ["timestamp", "variable_name"],
        dropna=False,
    ):
        summary_rows.append(
            {
                "timestamp": timestamp,
                "variable_name": variable_name,
                "row_count": len(group_df),
                "requested_step_volume_m3": _sum_float(
                    group_df["requested_step_volume_m3"]
                ),
                "target_step_volume_m3": _sum_float(group_df["target_step_volume_m3"]),
                "storage_correction_volume_m3": _sum_float(
                    group_df["storage_correction_volume_m3"]
                ),
                "residual_volume_m3": _sum_float(group_df["residual_volume_m3"]),
                "rows_with_nonzero_residual": _rows_over_tolerance(
                    group_df["residual_volume_m3"],
                    closure_tolerance_m3,
                ),
                "bounds_applied_rows": int(group_df["bounds_applied"].sum()),
                "max_abs_residual_volume_m3": _max_abs_float(
                    group_df["residual_volume_m3"]
                ),
                "requested_target_closure_m3": _sum_float(
                    group_df["requested_target_closure_m3"]
                ),
                "max_abs_requested_target_closure_m3": _max_abs_float(
                    group_df["requested_target_closure_m3"]
                ),
                "requested_target_rows_over_tolerance": _rows_over_tolerance(
                    group_df["requested_target_closure_m3"],
                    closure_tolerance_m3,
                ),
                "requested_storage_closure_m3": _sum_float(
                    group_df["requested_storage_closure_m3"]
                ),
                "max_abs_requested_storage_closure_m3": _max_abs_float(
                    group_df["requested_storage_closure_m3"]
                ),
                "requested_storage_rows_over_tolerance": _rows_over_tolerance(
                    group_df["requested_storage_closure_m3"],
                    closure_tolerance_m3,
                ),
                "target_storage_closure_m3": _sum_float(
                    group_df["target_storage_closure_m3"]
                ),
                "max_abs_target_storage_closure_m3": _max_abs_float(
                    group_df["target_storage_closure_m3"]
                ),
                "target_storage_rows_over_tolerance": _rows_over_tolerance(
                    group_df["target_storage_closure_m3"],
                    closure_tolerance_m3,
                ),
                "mean_effective_uz_theta_before": _mean_or_nan(
                    group_df["effective_uz_theta_before"]
                ),
                "mean_effective_uz_theta_requested_after": _mean_or_nan(
                    group_df["effective_uz_theta_requested_after"]
                ),
                "mean_effective_uz_theta_after": _mean_or_nan(
                    group_df["effective_uz_theta_after"]
                ),
            }
        )

    summary_df = pd.DataFrame(summary_rows, columns=VOLUME_CLOSURE_TIMESERIES_COLUMNS)
    if summary_df.empty:
        return summary_df

    return summary_df.sort_values(["timestamp", "variable_name"]).reset_index(drop=True)


def write_diagnostics_summary_csv(
    summary: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
    output_file: str | Path,
    closure_tolerance_m3: float = DEFAULT_CLOSURE_TOLERANCE_M3,
) -> Path:
    if isinstance(summary, pd.DataFrame):
        if _looks_like_volume_closure_timeseries_dataframe(summary):
            summary_df = summarize_volume_closure(summary, closure_tolerance_m3)
        else:
            summary_df = summary.copy()
    else:
        summary_df = summarize_volume_closure(summary, closure_tolerance_m3)

    summary_path = derive_diagnostics_summary_path(output_file)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(summary_path, index=False)
    return summary_path


def write_diagnostics_timeseries_csv(
    summary: Iterable[CouplingDiagnosticRecord] | pd.DataFrame,
    output_file: str | Path,
    closure_tolerance_m3: float = DEFAULT_CLOSURE_TOLERANCE_M3,
) -> Path:
    if isinstance(summary, pd.DataFrame):
        if _looks_like_volume_closure_timeseries_dataframe(summary):
            summary_df = _coerce_volume_closure_timeseries_dataframe(summary)
        else:
            summary_df = summarize_volume_closure_timeseries(
                summary,
                closure_tolerance_m3,
            )
    else:
        summary_df = summarize_volume_closure_timeseries(
            summary,
            closure_tolerance_m3,
        )

    timeseries_path = derive_diagnostics_timeseries_path(output_file)
    timeseries_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(timeseries_path, index=False)
    return timeseries_path
