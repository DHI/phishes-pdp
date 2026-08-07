from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

SATURATED_ZONE_DRAIN_PFS_PATH = "MIKESHE_FLOWMODEL.SaturatedZone.Drainage[1]"
SIMULATION_PERIOD_PFS_PATH = "MIKESHE_FLOWMODEL.SimSpec.SimulationPeriod"
NATIVE_SZ_DRAIN_POLICY_DRAIN_COUPLING_DISABLED = "drain_coupling_disabled"
NATIVE_SZ_DRAIN_POLICY_EXPLICIT_REQUEST = "explicit_request"
NATIVE_SZ_DRAIN_POLICY_EXPLICIT_OPT_OUT = "explicit_opt_out"
NATIVE_SZ_DRAIN_POLICY_DEFAULT = "default_phase3_policy"
EFFECTIVE_UZ_THICKNESS_SOURCE_SETUP_LAYER_DEPTH = "setup UZSoilProfiles layer depth"
EFFECTIVE_UZ_THICKNESS_SOURCE_SETUP_DISCRETIZATION = (
    "setup UZSoilProfiles discretization"
)
EFFECTIVE_UZ_THICKNESS_SOURCE_SETUP_LAYER_AND_DISCRETIZATION = (
    "setup UZSoilProfiles layer depth/discretization"
)
PREPROCESSED_RESULT_FILES_DIR_SUFFIX = " - Result Files"
PREPROCESSED_DFS2_SUFFIX = "_PreProcessed.DFS2"
PREPROCESSED_RUNOFF_COEFFICIENT_ITEM_NAME = "OL-Drainage Runoff Coefficients"


@dataclass(frozen=True)
class EffectiveUzThicknessResolution:
    thickness_m: float
    source: str
    profile_count: int
    layer_bottom_depths_m: tuple[float, ...] = ()
    discretization_total_depths_m: tuple[float, ...] = ()


def resolve_native_sz_drain_suppression_policy(
    *,
    drain_coupling_enabled: bool,
    suppress_native_sz_drain: bool = False,
    keep_native_sz_drain: bool = False,
) -> dict[str, Any]:
    if suppress_native_sz_drain and keep_native_sz_drain:
        raise ValueError(
            "Conflicting native SZ drain policy flags: cannot both suppress and keep the native SZ drain path."
        )

    if not drain_coupling_enabled:
        return {
            "enabled": False,
            "source": NATIVE_SZ_DRAIN_POLICY_DRAIN_COUPLING_DISABLED,
            "description": "inactive because Phase 3 drain coupling is disabled",
        }

    if keep_native_sz_drain:
        return {
            "enabled": False,
            "source": NATIVE_SZ_DRAIN_POLICY_EXPLICIT_OPT_OUT,
            "description": "disabled by explicit opt-out (--keep-native-sz-drain)",
        }

    if suppress_native_sz_drain:
        return {
            "enabled": True,
            "source": NATIVE_SZ_DRAIN_POLICY_EXPLICIT_REQUEST,
            "description": "enabled by explicit request (--suppress-native-sz-drain)",
        }

    return {
        "enabled": True,
        "source": NATIVE_SZ_DRAIN_POLICY_DEFAULT,
        "description": "enabled by default Phase 3 policy when drain coupling is active",
    }


def build_derived_setup_path(setup_path: str | Path, suffix: str) -> Path:
    resolved_setup_path = Path(setup_path).expanduser().resolve()
    cleaned_suffix = str(suffix).strip()
    if not cleaned_suffix:
        raise ValueError("suffix must not be empty")

    stem_suffix = (
        cleaned_suffix if cleaned_suffix.startswith("_") else f"_{cleaned_suffix}"
    )
    return resolved_setup_path.with_name(
        f"{resolved_setup_path.stem}{stem_suffix}{resolved_setup_path.suffix}"
    )


def derive_preprocessed_result_files_dir(setup_path: str | Path) -> Path:
    resolved_setup_path = Path(setup_path).expanduser().resolve()
    return resolved_setup_path.with_name(
        resolved_setup_path.name + PREPROCESSED_RESULT_FILES_DIR_SUFFIX
    )


def derive_preprocessed_dfs2_path(setup_path: str | Path) -> Path:
    resolved_setup_path = Path(setup_path).expanduser().resolve()
    return derive_preprocessed_result_files_dir(resolved_setup_path) / (
        resolved_setup_path.stem + PREPROCESSED_DFS2_SUFFIX
    )


def write_preprocessed_runoff_coefficient_override(
    setup_path: str | Path,
    *,
    coupled_cells: Iterable[tuple[int, int]],
    item_name: str = PREPROCESSED_RUNOFF_COEFFICIENT_ITEM_NAME,
    override_value: float = 0.0,
) -> tuple[Path, dict[str, Any]]:
    import mikeio

    resolved_setup_path = Path(setup_path).expanduser().resolve()
    preprocessed_dfs2_path = derive_preprocessed_dfs2_path(resolved_setup_path)
    if not preprocessed_dfs2_path.exists():
        raise FileNotFoundError(
            "Could not find the preprocessed DFS2 file for the active setup: "
            f"{preprocessed_dfs2_path}"
        )

    dataset = mikeio.read(str(preprocessed_dfs2_path))
    item_names = tuple(str(item.name) for item in dataset.items)

    try:
        item_index = item_names.index(str(item_name))
    except ValueError as exc:
        raise ValueError(
            f"Could not find DFS2 item '{item_name}' in {preprocessed_dfs2_path}. "
            f"Available items: {item_names}"
        ) from exc

    modified_dataset = dataset.copy()
    runoff_coefficients = modified_dataset[item_index].values
    if runoff_coefficients.ndim not in (2, 3):
        raise ValueError(
            "Expected a 2D or 3D DFS2 runoff-coefficient array, got shape "
            f"{tuple(runoff_coefficients.shape)}"
        )

    resolved_cells = tuple((int(row), int(col)) for row, col in coupled_cells)
    override_scalar = float(override_value)
    original_values: list[float] = []
    changed_cell_count = 0

    for row, col in resolved_cells:
        if runoff_coefficients.ndim == 3:
            previous_values = tuple(
                float(value) for value in runoff_coefficients[:, row, col]
            )
            original_values.append(
                previous_values[0] if previous_values else override_scalar
            )
            if any(
                abs(previous_value - override_scalar) > 1.0e-15
                for previous_value in previous_values
            ):
                changed_cell_count += 1
            runoff_coefficients[:, row, col] = override_scalar
        else:
            previous_value = float(runoff_coefficients[row, col])
            original_values.append(previous_value)
            if abs(previous_value - override_scalar) > 1.0e-15:
                changed_cell_count += 1
            runoff_coefficients[row, col] = override_scalar

    modified_dataset.to_dfs(str(preprocessed_dfs2_path))

    return preprocessed_dfs2_path.resolve(), {
        "setup_path": str(resolved_setup_path),
        "dfs2_path": str(preprocessed_dfs2_path.resolve()),
        "item_name": str(item_name),
        "item_index": int(item_index + 1),
        "override_value": override_scalar,
        "coupled_cell_count": len(resolved_cells),
        "changed_cell_count": int(changed_cell_count),
        "nonzero_before_count": sum(
            1 for original_value in original_values if abs(original_value) > 1.0e-15
        ),
        "min_original_value": min(original_values) if original_values else None,
        "max_original_value": max(original_values) if original_values else None,
    }


def write_saturated_zone_drain_override_setup(
    setup_path: str | Path,
    *,
    drainage_option: int | None = None,
    drain_code_fixed_value: float | None = None,
    suffix: str = "dr0",
) -> tuple[Path, dict[str, Any]]:
    if drainage_option is None and drain_code_fixed_value is None:
        raise ValueError("At least one saturated-zone drain override must be provided.")

    import mikeio

    resolved_setup_path = Path(setup_path).expanduser().resolve()
    derived_setup_path = build_derived_setup_path(resolved_setup_path, suffix)
    pfs = mikeio.PfsDocument(str(resolved_setup_path), unique_keywords=False)
    drainage_section = pfs.MIKESHE_FLOWMODEL.SaturatedZone.Drainage[1]

    original_drainage_option = int(drainage_section.DrainageOption)
    original_drain_code_fixed_value = float(drainage_section.DrainCode.FixedValue)
    original_drain_code_type = int(drainage_section.DrainCode.Type)

    if drainage_option is not None:
        drainage_section.DrainageOption = int(drainage_option)

    if drain_code_fixed_value is not None:
        drainage_section.DrainCode.FixedValue = float(drain_code_fixed_value)
        drainage_section.DrainCode.Type = 0

    pfs.write(str(derived_setup_path))
    return derived_setup_path.resolve(), {
        "pfs_path": SATURATED_ZONE_DRAIN_PFS_PATH,
        "original_drainage_option": original_drainage_option,
        "original_drain_code_fixed_value": original_drain_code_fixed_value,
        "original_drain_code_type": original_drain_code_type,
        "modified_drainage_option": (
            int(drainage_option) if drainage_option is not None else None
        ),
        "modified_drain_code_fixed_value": (
            float(drain_code_fixed_value)
            if drain_code_fixed_value is not None
            else None
        ),
        "modified_drain_code_type": 0 if drain_code_fixed_value is not None else None,
    }


def _normalize_pfs_datetime_components(
    value: datetime | date | str | Iterable[int],
) -> tuple[int, int, int, int, int]:
    if isinstance(value, datetime):
        return (
            int(value.year),
            int(value.month),
            int(value.day),
            int(value.hour),
            int(value.minute),
        )

    if isinstance(value, date):
        return (
            int(value.year),
            int(value.month),
            int(value.day),
            0,
            0,
        )

    if isinstance(value, str):
        normalized_text = value.strip()
        if not normalized_text:
            raise ValueError("simulation-period datetime strings must not be empty")

        if "," in normalized_text:
            comma_components = tuple(
                int(component.strip())
                for component in normalized_text.split(",")
                if component.strip()
            )
            if len(comma_components) == 3:
                return comma_components + (0, 0)
            if len(comma_components) == 5:
                return comma_components
            raise ValueError(
                "simulation-period datetime strings in MIKE SHE format must have 3 or 5 comma-separated integers"
            )

        if normalized_text.endswith(("Z", "z")):
            normalized_text = normalized_text[:-1]

        parse_candidates = [normalized_text]
        if "T" not in normalized_text and " " not in normalized_text:
            parse_candidates.append(f"{normalized_text}T00:00:00")

        parsed_value = None
        for parse_candidate in parse_candidates:
            try:
                parsed_value = datetime.fromisoformat(parse_candidate)
                break
            except ValueError:
                continue

        if parsed_value is None:
            raise ValueError(
                "Could not parse simulation-period datetime string "
                f"'{value}'. Expected ISO-like forms such as 2020-08-10 or 2020-08-10T05:00:00."
            )

        return _normalize_pfs_datetime_components(parsed_value)

    try:
        components = tuple(int(component) for component in value)
    except TypeError as exc:
        raise TypeError(
            "simulation-period values must be datetime/date objects, ISO-like strings, or iterables of ints"
        ) from exc

    if len(components) == 3:
        return components + (0, 0)

    if len(components) == 5:
        return components

    raise ValueError(
        "simulation-period values must have 3 components (Y, M, D) or 5 components (Y, M, D, h, m)"
    )


def _format_pfs_datetime_components(
    components: Iterable[int],
) -> str:
    return ", ".join(str(int(component)) for component in components)


def write_simulation_period_override_setup(
    setup_path: str | Path,
    *,
    sim_start: datetime | date | str | Iterable[int] | None = None,
    sim_end: datetime | date | str | Iterable[int] | None = None,
    suffix: str = "simperiod",
) -> tuple[Path, dict[str, Any]]:
    if sim_start is None and sim_end is None:
        raise ValueError("At least one simulation-period override must be provided.")

    resolved_setup_path = Path(setup_path).expanduser().resolve()
    derived_setup_path = build_derived_setup_path(resolved_setup_path, suffix)

    raw_text = resolved_setup_path.read_text(encoding="utf-8", errors="ignore")
    newline = "\r\n" if "\r\n" in raw_text else "\n"
    lines = raw_text.splitlines()

    in_simulation_period = False
    found_simulation_period = False
    original_sim_start = None
    original_sim_end = None

    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if stripped_line == "[SimulationPeriod]":
            in_simulation_period = True
            found_simulation_period = True
            continue

        if in_simulation_period and stripped_line.startswith("EndSect"):
            in_simulation_period = False
            continue

        if not in_simulation_period or "=" not in stripped_line:
            continue

        key, raw_value = stripped_line.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if key == "SIMSTART":
            original_sim_start = _normalize_pfs_datetime_components(raw_value)
            if sim_start is not None:
                modified_sim_start = _normalize_pfs_datetime_components(sim_start)
                indent = line[: len(line) - len(line.lstrip())]
                lines[index] = (
                    f"{indent}SIMSTART = "
                    f"{_format_pfs_datetime_components(modified_sim_start)}"
                )
        elif key == "SIMEND":
            original_sim_end = _normalize_pfs_datetime_components(raw_value)
            if sim_end is not None:
                modified_sim_end = _normalize_pfs_datetime_components(sim_end)
                indent = line[: len(line) - len(line.lstrip())]
                lines[index] = (
                    f"{indent}SIMEND = "
                    f"{_format_pfs_datetime_components(modified_sim_end)}"
                )

    if not found_simulation_period:
        raise ValueError(
            "Could not find a [SimulationPeriod] section in the MIKE SHE setup."
        )
    if original_sim_start is None:
        raise ValueError(
            "Could not find SIMSTART inside the [SimulationPeriod] section."
        )
    if original_sim_end is None:
        raise ValueError("Could not find SIMEND inside the [SimulationPeriod] section.")

    modified_sim_start = (
        _normalize_pfs_datetime_components(sim_start)
        if sim_start is not None
        else original_sim_start
    )
    modified_sim_end = (
        _normalize_pfs_datetime_components(sim_end)
        if sim_end is not None
        else original_sim_end
    )

    derived_setup_path.write_text(
        newline.join(lines) + newline,
        encoding="utf-8",
    )
    return derived_setup_path.resolve(), {
        "pfs_path": SIMULATION_PERIOD_PFS_PATH,
        "original_sim_start": original_sim_start,
        "original_sim_end": original_sim_end,
        "modified_sim_start": modified_sim_start,
        "modified_sim_end": modified_sim_end,
    }


def patch_simend_in_place(setup_path: str | Path, sim_end: datetime) -> None:
    resolved = Path(setup_path).expanduser().resolve()
    raw_text = resolved.read_text(encoding="utf-8", errors="ignore")
    newline = "\r\n" if "\r\n" in raw_text else "\n"
    lines = raw_text.splitlines()
    in_simulation_period = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[SimulationPeriod]":
            in_simulation_period = True
            continue
        if in_simulation_period and stripped.startswith("EndSect"):
            in_simulation_period = False
            continue
        if in_simulation_period and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key == "SIMEND":
                indent = line[: len(line) - len(line.lstrip())]
                components = _normalize_pfs_datetime_components(sim_end)
                lines[i] = (
                    f"{indent}SIMEND = {_format_pfs_datetime_components(components)}"
                )
                break
    resolved.write_text(newline.join(lines) + newline, encoding="utf-8")


def _clean_pfs_value(raw_value: str) -> str:
    value = str(raw_value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'|":
        return value[1:-1]
    return value


def _resolve_uniform_depth(
    values: tuple[float, ...],
    label: str,
    tolerance: float,
) -> float | None:
    if not values:
        return None

    reference = float(values[0])
    for candidate in values[1:]:
        if abs(float(candidate) - reference) > tolerance:
            raise ValueError(f"Non-uniform {label} in MIKE SHE setup: {values}")

    return reference


def _extract_uz_soil_profile_thickness_report(
    setup_path: str | Path,
) -> dict[str, Any]:
    resolved_setup_path = Path(setup_path).expanduser().resolve()
    profiles: list[dict[str, Any]] = []
    section_stack: list[str] = []
    current_profile: dict[str, Any] | None = None
    current_discretization: dict[str, Any] | None = None

    for raw_line in resolved_setup_path.read_text(
        encoding="utf-8", errors="ignore"
    ).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            section_stack.append(section_name)

            if section_name == "UZSoilProfileProp":
                current_profile = {
                    "grid_code": None,
                    "soil_profile_id": None,
                    "layer_depths_m": [],
                    "discretization_items": [],
                }
            elif current_profile is not None and section_name.startswith(
                "UZSoilProfilePropDiscr"
            ):
                current_discretization = {
                    "cell_height_m": None,
                    "no_cells": None,
                }

            continue

        if line.startswith("EndSect"):
            ended_section = section_stack.pop() if section_stack else None

            if (
                ended_section is not None
                and ended_section.startswith("UZSoilProfilePropDiscr")
                and current_profile is not None
                and current_discretization is not None
            ):
                cell_height_m = current_discretization.get("cell_height_m")
                no_cells = current_discretization.get("no_cells")
                if cell_height_m is not None and no_cells is not None:
                    current_profile["discretization_items"].append(
                        (float(cell_height_m), int(no_cells))
                    )
                current_discretization = None
            elif ended_section == "UZSoilProfileProp" and current_profile is not None:
                layer_depths_m = tuple(
                    float(value) for value in current_profile["layer_depths_m"]
                )
                discretization_items = tuple(
                    (float(cell_height_m), int(no_cells))
                    for cell_height_m, no_cells in current_profile[
                        "discretization_items"
                    ]
                )
                profiles.append(
                    {
                        "grid_code": current_profile["grid_code"],
                        "soil_profile_id": current_profile["soil_profile_id"],
                        "layer_depths_m": layer_depths_m,
                        "layer_bottom_depth_m": (
                            max(layer_depths_m) if layer_depths_m else None
                        ),
                        "discretization_items": discretization_items,
                        "discretization_total_depth_m": (
                            sum(
                                float(cell_height_m) * int(no_cells)
                                for cell_height_m, no_cells in discretization_items
                            )
                            if discretization_items
                            else None
                        ),
                    }
                )
                current_profile = None
                current_discretization = None

            continue

        if current_profile is None or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = _clean_pfs_value(raw_value)
        current_section = section_stack[-1] if section_stack else None

        if current_section == "UZSoilProfileProp":
            if key == "GridCode":
                current_profile["grid_code"] = value
            elif key == "SoilProfile_ID":
                current_profile["soil_profile_id"] = value
        elif (
            current_section is not None
            and current_section.startswith("UZSoilProfilePropLayerItem")
            and key == "Depth"
        ):
            current_profile["layer_depths_m"].append(float(value))
        elif (
            current_section is not None
            and current_section.startswith("UZSoilProfilePropDiscr")
            and current_discretization is not None
        ):
            if key == "CellHeight":
                current_discretization["cell_height_m"] = float(value)
            elif key == "NoCells":
                current_discretization["no_cells"] = int(float(value))

    layer_bottom_depths_m = tuple(
        float(profile["layer_bottom_depth_m"])
        for profile in profiles
        if profile["layer_bottom_depth_m"] is not None
    )
    discretization_total_depths_m = tuple(
        float(profile["discretization_total_depth_m"])
        for profile in profiles
        if profile["discretization_total_depth_m"] is not None
    )

    return {
        "setup_path": str(resolved_setup_path),
        "profile_count": len(profiles),
        "profiles": tuple(profiles),
        "layer_bottom_depths_m": layer_bottom_depths_m,
        "discretization_total_depths_m": discretization_total_depths_m,
    }


def derive_effective_uz_thickness_from_setup(
    setup_path: str | Path,
    *,
    tolerance: float = 1.0e-9,
) -> EffectiveUzThicknessResolution:
    report = _extract_uz_soil_profile_thickness_report(setup_path)
    if int(report["profile_count"]) < 1:
        raise ValueError(
            "Could not find any UZSoilProfileProp sections in the MIKE SHE setup."
        )

    layer_bottom_depth_m = _resolve_uniform_depth(
        report["layer_bottom_depths_m"],
        "UZ soil profile layer depths",
        tolerance,
    )
    discretization_total_depth_m = _resolve_uniform_depth(
        report["discretization_total_depths_m"],
        "UZ soil profile discretization totals",
        tolerance,
    )

    if (
        layer_bottom_depth_m is not None
        and discretization_total_depth_m is not None
        and abs(layer_bottom_depth_m - discretization_total_depth_m) > tolerance
    ):
        raise ValueError(
            "UZ soil profile layer depths and discretization totals disagree in the MIKE SHE setup: "
            f"{layer_bottom_depth_m} m vs {discretization_total_depth_m} m"
        )

    if layer_bottom_depth_m is not None and discretization_total_depth_m is not None:
        return EffectiveUzThicknessResolution(
            thickness_m=float(layer_bottom_depth_m),
            source=EFFECTIVE_UZ_THICKNESS_SOURCE_SETUP_LAYER_AND_DISCRETIZATION,
            profile_count=int(report["profile_count"]),
            layer_bottom_depths_m=tuple(report["layer_bottom_depths_m"]),
            discretization_total_depths_m=tuple(
                report["discretization_total_depths_m"]
            ),
        )

    if layer_bottom_depth_m is not None:
        return EffectiveUzThicknessResolution(
            thickness_m=float(layer_bottom_depth_m),
            source=EFFECTIVE_UZ_THICKNESS_SOURCE_SETUP_LAYER_DEPTH,
            profile_count=int(report["profile_count"]),
            layer_bottom_depths_m=tuple(report["layer_bottom_depths_m"]),
            discretization_total_depths_m=tuple(
                report["discretization_total_depths_m"]
            ),
        )

    if discretization_total_depth_m is not None:
        return EffectiveUzThicknessResolution(
            thickness_m=float(discretization_total_depth_m),
            source=EFFECTIVE_UZ_THICKNESS_SOURCE_SETUP_DISCRETIZATION,
            profile_count=int(report["profile_count"]),
            layer_bottom_depths_m=tuple(report["layer_bottom_depths_m"]),
            discretization_total_depths_m=tuple(
                report["discretization_total_depths_m"]
            ),
        )

    raise ValueError(
        "Could not derive an effective UZ thickness from the MIKE SHE setup."
    )
