"""Native forcing-generator helpers used by the orchestration notebook."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import mikeio
import numpy as np
import pandas as pd
import yaml


def to_abs_path(module_root: Path, path_value: Path | str) -> Path:
    p = Path(path_value)
    if p.is_absolute():
        return p.resolve()
    return module_root.joinpath(p).resolve()


# A forcing's series are written as `inputs:` in the YAML; internally they keep the
# same name as the top-level key so the rest of the module speaks one vocabulary.
FORCING_KEY_ALIASES = {"inputs": "timeseries_inputs"}

# Fields a forcing must have — set on the forcing itself or inherited from
# ``defaults:`` — before it can be generated.
REQUIRED_FORCING_FIELDS = ("grid_code_dfs2", "output_grid", "eum_type", "eum_unit")


def _validate_timeseries_entries(entries: Any, context: str) -> list[dict[str, Any]]:
    """Validate a list of per-grid-code timeseries entries and return it."""
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise ValueError(f"'timeseries_inputs' in {context} must be a list of entries.")

    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(
                f"Timeseries entry {i} in {context} must be a mapping, got {type(entry).__name__}."
            )
        if "grid_code" not in entry or "path" not in entry:
            raise ValueError(
                f"Timeseries entry {i} in {context} must define both 'grid_code' and 'path'."
            )

    return entries


def _apply_key_aliases(entry: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``entry`` with alias keys renamed to canonical names."""
    out: dict[str, Any] = {}
    for key, value in entry.items():
        out[FORCING_KEY_ALIASES.get(str(key), str(key))] = value
    return out


def _safe_filename(name: str) -> str:
    """Turn a forcing name into a filename-safe stem."""
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in str(name).strip())
    return cleaned.strip("_") or "forcing"


def _normalize_forcing(
    entry: dict[str, Any],
    defaults: dict[str, Any],
    index: int,
    context: str,
) -> dict[str, Any]:
    """Merge one raw forcing entry with the config defaults into a canonical dict."""
    if not isinstance(entry, dict):
        raise ValueError(
            f"Forcing entry {index} in {context} must be a mapping, got {type(entry).__name__}."
        )

    merged = {**_apply_key_aliases(defaults), **_apply_key_aliases(entry)}

    name = str(merged.get("name") or f"forcing_{index + 1}")
    output_dir = merged.get("output_dir")
    output_grid = merged.get("output_grid")
    if output_grid is None:
        # Each forcing gets its own output file by default, so a config does not
        # have to spell one out per entry.
        output_grid = f"{_safe_filename(name)}.dfs2"
    if output_dir:
        output_path = Path(str(output_grid))
        if not output_path.is_absolute():
            output_grid = Path(str(output_dir)).joinpath(output_path)

    forcing: dict[str, Any] = {
        "name": name,
        "grid_code_dfs2": merged.get("grid_code_dfs2"),
        "output_grid": output_grid,
        "item_name": merged.get("item_name") or name,
        "eum_type": merged.get("eum_type"),
        "eum_unit": merged.get("eum_unit"),
        "timeseries_inputs": _validate_timeseries_entries(
            merged.get("timeseries_inputs"), f"{context} (forcing '{name}')"
        ),
    }
    return forcing


def load_forcing_configs(module_root: Path, config_path: Path | str) -> list[dict[str, Any]]:
    """Load every forcing setup defined in a YAML config file.

    ``timeseries_inputs:`` is a mapping of forcing name to that forcing's settings,
    optionally preceded by a ``defaults:`` mapping whose keys are inherited by every
    forcing that does not override them::

        defaults:
          grid_code_dfs2: sample_data/.../GridCode5.dfs2
          output_dir: output_data/pgm_forcing_generator/forcing_generator
          eum_type: Concentration
          eum_unit: kg_per_meter_pow_3
        timeseries_inputs:
          var1:
            output_grid: var1.dfs2
            item_name: Seed Application Rate
            inputs:
              - grid_code: 1
                path: ...

    Per forcing: ``grid_code_dfs2``, ``output_grid`` (default: ``<name>.dfs2``,
    joined onto ``output_dir`` when relative), ``item_name`` (default: the forcing
    name), ``eum_type``, ``eum_unit`` and ``inputs``. A forcing written as a plain
    list of timeseries entries takes every output setting from ``defaults:``.
    """
    cfg_path = to_abs_path(module_root, config_path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Forcing config file not found: {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or not isinstance(data.get("timeseries_inputs"), dict):
        raise ValueError(
            f"{cfg_path} must define 'timeseries_inputs:' as a mapping of forcing name to "
            "that forcing's settings, e.g.\n"
            "  timeseries_inputs:\n"
            "    var1:\n"
            "      output_grid: var1.dfs2\n"
            "      inputs:\n"
            "        - grid_code: 1\n"
            "          path: series.dfs0"
        )

    defaults = data.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ValueError(f"'defaults' in {cfg_path} must be a mapping.")

    raw_forcings: list[dict[str, Any]] = []
    for name, value in data["timeseries_inputs"].items():
        entry = dict(value) if isinstance(value, dict) else {"inputs": value}
        entry.setdefault("name", name)
        raw_forcings.append(entry)

    if not raw_forcings:
        raise ValueError(f"No forcings defined in {cfg_path}.")

    return [
        _normalize_forcing(entry, defaults, i, str(cfg_path))
        for i, entry in enumerate(raw_forcings)
    ]


def resolve_forcing(forcing: dict[str, Any]) -> dict[str, Any]:
    """Check a forcing carries every field needed to generate it."""
    missing = [key for key in REQUIRED_FORCING_FIELDS if forcing.get(key) in (None, "")]
    if missing:
        raise ValueError(
            f"Forcing '{forcing.get('name')}' is missing required field(s): {', '.join(missing)}. "
            "Set them on the forcing or under 'defaults:' in the YAML config."
        )

    return dict(forcing)


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


def resolve_source(ts_path: Path, entry: dict[str, Any]) -> str:
    """Return the reader to use for a timeseries entry: 'csv' or 'dfs0'."""
    source = str(entry.get("source", "")).strip().lower()

    if ts_path.suffix.lower() == ".csv":
        return "csv"
    return source or "dfs0"


def read_timeseries_input(module_root: Path, entry: dict[str, Any]) -> pd.Series:
    ts_path = to_abs_path(module_root, entry["path"])
    source = resolve_source(ts_path, entry)

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

    if not ts_by_code:
        raise ValueError(
            "No timeseries inputs provided; at least one grid code must have a series."
        )

    # Grid codes present in the grid DFS2 but without a provided timeseries are
    # not an error: they are filled with a constant 0 across all timesteps.
    missing_codes = [code for code in unique_codes if code not in ts_by_code]

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

    for code in missing_codes:
        output[:, grid_codes == code] = 0.0

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
        "zero_filled_grid_codes": missing_codes,
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
                "source": resolve_source(ts_path, entry),
                "item": entry.get("item", None),
                "path": str(ts_path),
                "path_exists": ts_path.exists(),
            }
        )
    return rows


def build_forcing_rows(
    module_root: Path,
    forcings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve every forcing and report its paths, item metadata and input status."""
    rows: list[dict[str, Any]] = []
    for forcing in forcings:
        row: dict[str, Any] = {"name": forcing.get("name"), "error": None}
        try:
            resolved = resolve_forcing(forcing)
        except ValueError as exc:
            row["error"] = str(exc)
            rows.append(row)
            continue

        grid_path = to_abs_path(module_root, resolved["grid_code_dfs2"])
        output_path = to_abs_path(module_root, resolved["output_grid"])
        input_rows = build_input_rows(module_root, resolved["timeseries_inputs"])

        row.update(
            {
                "grid_code_dfs2": str(grid_path),
                "grid_code_dfs2_exists": grid_path.exists(),
                "output_grid": str(output_path),
                "output_parent_exists": output_path.parent.exists(),
                "item_name": resolved["item_name"],
                "eum_type": resolved["eum_type"],
                "eum_unit": resolved["eum_unit"],
                "n_timeseries_inputs": len(input_rows),
                "missing_timeseries_inputs": [
                    r["path"] for r in input_rows if not r["path_exists"]
                ],
                "timeseries_inputs": input_rows,
            }
        )
        rows.append(row)

    return rows


def run_forcing_setups(
    module_root: Path,
    forcings: list[dict[str, Any]],
    continue_on_error: bool = False,
) -> list[dict[str, Any]]:
    """Generate every forcing in ``forcings``, one DFS2 output per entry.

    Each result carries the forcing ``name`` plus ``status`` (``"ok"`` or
    ``"failed"``). With ``continue_on_error=True`` a failing forcing is recorded
    with its ``error`` message and the remaining forcings still run.
    """
    if not forcings:
        raise ValueError("No forcings to run.")

    results: list[dict[str, Any]] = []
    for forcing in forcings:
        name = forcing.get("name")
        try:
            resolved = resolve_forcing(forcing)
            result = run_native_setup(
                module_root=module_root,
                grid_code_dfs2=resolved["grid_code_dfs2"],
                timeseries_inputs=resolved["timeseries_inputs"],
                output_grid=resolved["output_grid"],
                output_item_name=resolved["item_name"],
                output_eum_type=resolved["eum_type"],
                output_eum_unit=resolved["eum_unit"],
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            results.append({"name": name, "status": "failed", "error": str(exc)})
            continue

        results.append({"name": name, "status": "ok", "error": None, **result})

    return results


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
