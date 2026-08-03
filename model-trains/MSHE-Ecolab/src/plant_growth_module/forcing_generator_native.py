"""Native forcing-generator helpers used by the orchestration notebook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mikeio
import numpy as np
import pandas as pd


def to_abs_path(module_root: Path, path_value: Path | str) -> Path:
    p = Path(path_value)
    if p.is_absolute():
        return p.resolve()
    return module_root.joinpath(p).resolve()


def normalize_daily_if_needed(series: pd.Series) -> pd.Series:
    if len(series.index) < 2:
        return series.sort_index()

    idx = pd.to_datetime(series.index).sort_values()
    delta_hours = idx.to_series().diff().dropna().dt.total_seconds() / 3600.0

    if delta_hours.empty:
        return series.sort_index()

    near_daily_share = ((delta_hours >= 23.0) & (delta_hours <= 25.0)).mean()
    if near_daily_share >= 0.8:
        s = series.copy()
        s.index = pd.to_datetime(s.index).normalize()
        return s.groupby(level=0).last().sort_index()

    return series.sort_index()


def read_timeseries_input(module_root: Path, entry: dict[str, Any]) -> pd.Series:
    ts_path = to_abs_path(module_root, entry["path"])
    source = str(entry.get("source", "")).strip().lower()

    if ts_path.suffix.lower() == ".csv":
        source = "csv"
    elif not source:
        source = "dfs0"

    if source == "dfs0":
        ds = mikeio.read(ts_path)
        item_1_based = int(entry.get("item", 1))
        if item_1_based < 1 or item_1_based > len(ds):
            raise ValueError(
                f"Invalid DFS0 item index {item_1_based} for {ts_path}. File has {len(ds)} item(s)."
            )
        da = ds[item_1_based - 1]
        values = np.asarray(da.to_numpy()).astype(float).reshape(-1)
        index = pd.to_datetime(pd.DatetimeIndex(da.time)).tz_localize(None)
        series = pd.Series(values, index=index)
    elif source == "csv":
        df = pd.read_csv(ts_path)
        time_col = entry.get("time_col", "time")
        value_col = entry.get("value_col", "value")
        if time_col not in df.columns or value_col not in df.columns:
            raise ValueError(f"CSV {ts_path} must contain columns '{time_col}' and '{value_col}'.")

        index = pd.to_datetime(df[time_col], errors="coerce").dt.tz_localize(None)
        if index.isna().any():
            raise ValueError(f"CSV {ts_path} has invalid timestamps in column '{time_col}'.")

        values = pd.to_numeric(df[value_col], errors="coerce")
        if values.isna().any():
            raise ValueError(f"CSV {ts_path} has non-numeric values in column '{value_col}'.")

        series = pd.Series(values.to_numpy(dtype=float), index=index)
    else:
        raise ValueError(f"Unsupported source '{source}' for {ts_path}. Use 'dfs0' or 'csv'.")

    if series.empty:
        raise ValueError(f"Timeseries input is empty: {ts_path}")

    series = series[~series.index.duplicated(keep="last")].sort_index()
    return normalize_daily_if_needed(series)


def resolve_item_info(name: str, eum_type_name: str, eum_unit_name: str) -> mikeio.ItemInfo:
    try:
        eum_type = getattr(mikeio.EUMType, eum_type_name)
    except AttributeError as exc:
        raise ValueError(f"Unknown EUMType '{eum_type_name}'.") from exc

    try:
        eum_unit = getattr(mikeio.EUMUnit, eum_unit_name)
    except AttributeError as exc:
        raise ValueError(f"Unknown EUMUnit '{eum_unit_name}'.") from exc

    return mikeio.ItemInfo(name, itemtype=eum_type, unit=eum_unit)


def run_native_setup(
    module_root: Path,
    grid_code_dfs2: Path | str,
    timeseries_inputs: list[dict[str, Any]],
    output_grid: Path | str,
    output_item_name: str,
    output_eum_type: str,
    output_eum_unit: str,
) -> dict[str, Any]:
    grid_path = to_abs_path(module_root, grid_code_dfs2)

    grid_ds = mikeio.read(grid_path)
    grid_da = grid_ds[0]
    grid_data = np.asarray(grid_da.to_numpy())
    if grid_data.ndim == 3:
        grid_codes = grid_data[0].astype(np.int32)
    elif grid_data.ndim == 2:
        grid_codes = grid_data.astype(np.int32)
    else:
        raise ValueError(f"Unexpected grid dimensions for {grid_path}: {grid_data.shape}")

    unique_codes = sorted(int(code) for code in np.unique(grid_codes))

    ts_by_code: dict[int, pd.Series] = {}
    for entry in timeseries_inputs:
        code = int(entry["grid_code"])
        if code in ts_by_code:
            raise ValueError(f"Duplicate timeseries mapping for grid code {code}.")
        ts_by_code[code] = read_timeseries_input(module_root, entry)

    missing_codes = [code for code in unique_codes if code not in ts_by_code]
    if missing_codes:
        raise ValueError(f"Missing timeseries for grid code(s) {missing_codes}.")

    common_index = sorted({ts for series in ts_by_code.values() for ts in series.index})
    common_index = pd.DatetimeIndex(common_index)

    aligned_by_code: dict[int, pd.Series] = {}
    for code, series in ts_by_code.items():
        aligned = series.reindex(common_index).bfill().ffill()
        if aligned.isna().any():
            raise ValueError(f"Could not fill all timesteps for grid code {code}.")
        aligned_by_code[code] = aligned

    output = np.full((len(common_index), *grid_codes.shape), np.nan, dtype=np.float32)
    for code, aligned in aligned_by_code.items():
        mask = grid_codes == code
        output[:, mask] = aligned.to_numpy(dtype=np.float32)[:, None]

    output_path = to_abs_path(module_root, output_grid)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    item_info = resolve_item_info(output_item_name, output_eum_type, output_eum_unit)

    da = mikeio.DataArray(
        data=output,
        time=common_index,
        geometry=grid_da.geometry,
        item=item_info,
    )
    da.to_dfs(output_path)

    return {
        "grid_code_dfs2": str(grid_path),
        "output_grid": str(output_path),
        "n_grid_codes": len(unique_codes),
        "n_timesteps": len(common_index),
        "start_time": common_index.min(),
        "end_time": common_index.max(),
    }


def build_input_rows(
    module_root: Path, timeseries_inputs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in timeseries_inputs:
        ts_path = to_abs_path(module_root, entry["path"])
        rows.append(
            {
                "grid_code": int(entry["grid_code"]),
                "source": str(entry.get("source", "dfs0")),
                "item": entry.get("item", None),
                "path": str(ts_path),
                "path_exists": ts_path.exists(),
            }
        )
    return rows


def export_first_dfs0_item_to_csv(
    module_root: Path,
    timeseries_inputs: list[dict[str, Any]],
) -> Path:
    first_dfs0_entry = None
    for entry in timeseries_inputs:
        candidate = to_abs_path(module_root, entry["path"])
        if candidate.suffix.lower().startswith(".dfs"):
            first_dfs0_entry = entry
            break

    if first_dfs0_entry is None:
        first_dfs0_entry = next(
            (
                e
                for e in timeseries_inputs
                if str(e.get("source", "dfs0")).strip().lower() == "dfs0"
                and to_abs_path(module_root, e["path"]).suffix.lower().startswith(".dfs")
            ),
            None,
        )

    if first_dfs0_entry is None:
        raise ValueError("No DFS0 input found in TIMESERIES_INPUTS.")

    dfs0_path = to_abs_path(module_root, first_dfs0_entry["path"])
    ds = mikeio.read(dfs0_path)
    da = ds[0]

    csv_path = dfs0_path.with_name(f"{dfs0_path.stem}_item1.csv")
    export_df = pd.DataFrame(
        {
            "time": pd.to_datetime(pd.DatetimeIndex(da.time)).tz_localize(None),
            "value": np.asarray(da.to_numpy()).reshape(-1),
        }
    )
    export_df.to_csv(csv_path, index=False)
    return csv_path


def eum_matches(type_query: str = "", unit_query: str = "") -> dict[str, Any]:
    def _enum_names(enum_obj: Any) -> list[str]:
        names = []
        for name in dir(enum_obj):
            if name.startswith("_"):
                continue
            try:
                value = getattr(enum_obj, name)
            except (AttributeError, TypeError):
                continue
            if callable(value):
                continue
            names.append(name)
        return sorted(set(names))

    def _norm(text: str) -> str:
        return str(text).strip().lower().replace(" ", "").replace("_", "")

    def _filter_names(names: list[str], query: str) -> list[str]:
        q = _norm(query)
        if not q:
            return names
        return [n for n in names if q in _norm(n)]

    def _compatible_units_for_type(type_name: str) -> list[str]:
        try:
            eum_type = getattr(mikeio.EUMType, type_name)
            units = getattr(eum_type, "units", None)
            if units is None:
                return []
            out = []
            for unit in units:
                if hasattr(unit, "name"):
                    out.append(unit.name)
                else:
                    out.append(str(unit))
            return sorted(set(out))
        except Exception:
            return []

    def _compatible_types_for_unit(unit_name: str, all_types: list[str]) -> list[str]:
        compatible = []
        for type_name in all_types:
            units = _compatible_units_for_type(type_name)
            if any(_norm(unit) == _norm(unit_name) for unit in units):
                compatible.append(type_name)
        return compatible

    all_types = _enum_names(mikeio.EUMType)
    all_units = _enum_names(mikeio.EUMUnit)

    matched_types = _filter_names(all_types, type_query)
    matched_units = _filter_names(all_units, unit_query)

    compatible_units: list[str] = []
    compatible_types: list[str] = []

    if type_query and any(_norm(t) == _norm(type_query) for t in all_types):
        exact_type = next(t for t in all_types if _norm(t) == _norm(type_query))
        compatible_units = _compatible_units_for_type(exact_type)

    if unit_query and any(_norm(u) == _norm(unit_query) for u in all_units):
        exact_unit = next(u for u in all_units if _norm(u) == _norm(unit_query))
        compatible_types = _compatible_types_for_unit(exact_unit, all_types)

    return {
        "matched_types": matched_types,
        "matched_units": matched_units,
        "compatible_units": compatible_units,
        "compatible_types": compatible_types,
    }
