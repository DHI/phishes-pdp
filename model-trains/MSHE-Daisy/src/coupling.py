from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CouplingRuntimeContext:
    mshe_dt_seconds: float
    effective_uz_thickness_m: float
    effective_uz_thickness_source: str = "default"
    cell_area_m2: float | None = None
    theta_residual: float | None = None
    theta_saturated: float | None = None
    coupled_group_count: int = 0
    cell_dx_m: float | None = None
    cell_dy_m: float | None = None
    theta_residual_values: tuple[float, ...] = ()
    theta_saturated_values: tuple[float, ...] = ()
    theta_bound_source_files: tuple[str, ...] = ()
    runtime_param_types: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class BoundedUpdateResult:
    previous_value: float
    requested_delta: float
    proposed_value: float
    bounded_value: float
    residual: float
    lower_bound: float
    upper_bound: float

    @property
    def applied_delta(self) -> float:
        return self.bounded_value - self.previous_value


@dataclass(frozen=True)
class IntervalCellTransfer:
    source_depth_mm: float
    interval_seconds: float
    rate_m_per_s: float
    flow_m3_per_s: float
    step_depth_m: float
    step_volume_m3: float


@dataclass(frozen=True)
class BoundedLayerShiftResult:
    previous_values: tuple[float, ...]
    bounded_values: tuple[float, ...]
    requested_delta: float
    lower_bound: float
    upper_bound: float
    layer_results: tuple[BoundedUpdateResult, ...]

    @property
    def layer_count(self) -> int:
        return len(self.layer_results)

    @property
    def clipped_layer_count(self) -> int:
        return sum(
            1 for result in self.layer_results if abs(float(result.residual)) > 1.0e-15
        )

    @property
    def previous_mean(self) -> float | None:
        if not self.previous_values:
            return None
        return sum(self.previous_values) / len(self.previous_values)

    @property
    def bounded_mean(self) -> float | None:
        if not self.bounded_values:
            return None
        return sum(self.bounded_values) / len(self.bounded_values)

    @property
    def requested_after_mean(self) -> float | None:
        previous_mean = self.previous_mean
        if previous_mean is None:
            return None
        return previous_mean + self.requested_delta

    @property
    def applied_mean_delta(self) -> float | None:
        previous_mean = self.previous_mean
        bounded_mean = self.bounded_mean
        if previous_mean is None or bounded_mean is None:
            return None
        return bounded_mean - previous_mean

    @property
    def residual_mean_delta(self) -> float | None:
        applied_mean_delta = self.applied_mean_delta
        if applied_mean_delta is None:
            return None
        return self.requested_delta - applied_mean_delta


@dataclass(frozen=True)
class EffectiveUzCellBookkeepingResult:
    requested_storage_correction_delta_theta: float
    layer_shift: BoundedLayerShiftResult

    @property
    def previous_values(self) -> tuple[float, ...]:
        return self.layer_shift.previous_values

    @property
    def bounded_values(self) -> tuple[float, ...]:
        return self.layer_shift.bounded_values

    @property
    def layer_count(self) -> int:
        return self.layer_shift.layer_count

    @property
    def clipped_layer_count(self) -> int:
        return self.layer_shift.clipped_layer_count

    @property
    def lower_bound(self) -> float:
        return self.layer_shift.lower_bound

    @property
    def upper_bound(self) -> float:
        return self.layer_shift.upper_bound

    @property
    def requested_layer_delta_theta(self) -> float:
        return -float(self.requested_storage_correction_delta_theta)

    @property
    def effective_theta_before(self) -> float | None:
        return self.layer_shift.previous_mean

    @property
    def effective_theta_requested_after(self) -> float | None:
        return self.layer_shift.requested_after_mean

    @property
    def effective_theta_after(self) -> float | None:
        return self.layer_shift.bounded_mean

    @property
    def applied_layer_delta_theta(self) -> float | None:
        return self.layer_shift.applied_mean_delta

    @property
    def residual_layer_delta_theta(self) -> float | None:
        return self.layer_shift.residual_mean_delta

    @property
    def applied_storage_correction_delta_theta(self) -> float | None:
        applied_layer_delta = self.applied_layer_delta_theta
        if applied_layer_delta is None:
            return None
        return -applied_layer_delta

    @property
    def residual_storage_correction_delta_theta(self) -> float | None:
        residual_layer_delta = self.residual_layer_delta_theta
        if residual_layer_delta is None:
            return None
        return -residual_layer_delta


def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def resolve_mshe_timestep_hours(
    value: float | list[float] | tuple[float, ...],
) -> float:
    if isinstance(value, (list, tuple)):
        candidates = [float(candidate) for candidate in value]
        if not candidates:
            raise ValueError("mshe timestep sequence must not be empty")

        for candidate in candidates:
            _require_positive(candidate, "mshe_timestep_hours")

        return min(candidates)

    resolved_hours = float(value)
    _require_positive(resolved_hours, "mshe_timestep_hours")
    return resolved_hours


def resolve_mshe_timestep_seconds(
    value: float | list[float] | tuple[float, ...],
) -> float:
    return resolve_mshe_timestep_hours(value) * 60.0 * 60.0


def depth_mm_to_m(depth_mm: float) -> float:
    return float(depth_mm) / 1000.0


def derive_conservative_theta_bounds(
    theta_residual_values: list[float] | tuple[float, ...],
    theta_saturated_values: list[float] | tuple[float, ...],
) -> tuple[float | None, float | None]:
    residual_values = tuple(sorted({float(value) for value in theta_residual_values}))
    saturated_values = tuple(sorted({float(value) for value in theta_saturated_values}))

    theta_residual = max(residual_values) if residual_values else None
    theta_saturated = min(saturated_values) if saturated_values else None

    if (
        theta_residual is not None
        and theta_saturated is not None
        and theta_residual > theta_saturated
    ):
        raise ValueError(
            "theta_residual cannot exceed theta_saturated when deriving bounds"
        )

    return theta_residual, theta_saturated


def interval_depth_to_rate_m_per_s(depth_mm: float, interval_seconds: float) -> float:
    _require_positive(float(interval_seconds), "interval_seconds")
    return depth_mm_to_m(depth_mm) / float(interval_seconds)


def interval_depth_to_cell_transfer(
    depth_mm: float,
    interval_seconds: float,
    dt_seconds: float,
    cell_area_m2: float,
) -> IntervalCellTransfer:
    rate_m_per_s = interval_depth_to_rate_m_per_s(depth_mm, interval_seconds)
    step_depth_m = rate_to_step_depth_m(rate_m_per_s, dt_seconds)
    flow_m3_per_s = rate_to_flow_m3_per_s(rate_m_per_s, cell_area_m2)
    return IntervalCellTransfer(
        source_depth_mm=float(depth_mm),
        interval_seconds=float(interval_seconds),
        rate_m_per_s=rate_m_per_s,
        flow_m3_per_s=flow_m3_per_s,
        step_depth_m=step_depth_m,
        step_volume_m3=depth_to_volume_m3(step_depth_m, cell_area_m2),
    )


def assign_uniform_scalar_to_groups(
    dataset: object,
    groups: Iterable[object],
    value: float,
) -> object:
    scalar_value = float(value)

    for group in groups:
        dataset[group.row_start : group.row_end, group.col_start : group.col_end] = (
            scalar_value
        )

    return dataset


def assign_uniform_scalar_to_cells(
    dataset: object,
    cells: Iterable[tuple[int, int]],
    value: float,
) -> object:
    scalar_value = float(value)

    for row, col in cells:
        dataset[row, col] = scalar_value

    return dataset


def apply_groupwise_net_leakage_flux(
    dataset: object,
    groups: Iterable[object],
    source_rates_m_per_s_by_class: Mapping[str, float],
    native_exchange_grid: object,
) -> object:
    for group in groups:
        daisy_class = getattr(group, "daisy_class", "default")
        if daisy_class not in source_rates_m_per_s_by_class:
            raise KeyError(
                "No DAISY source rate configured for coupling group class "
                f"'{daisy_class}'"
            )

        daisy_rate_m_per_s = float(source_rates_m_per_s_by_class[daisy_class])
        r0, r1 = group.row_start, group.row_end
        c0, c1 = group.col_start, group.col_end
        dataset[r0:r1, c0:c1] = [
            [
                daisy_rate_m_per_s - float(native_exchange_grid[row][col])
                for col in range(c0, c1)
            ]
            for row in range(r0, r1)
        ]

    return dataset


def shift_layer_values(values: Iterable[float], delta: float) -> list[float]:
    signed_delta = float(delta)
    return [float(value) + signed_delta for value in values]


def _coerce_layer_values(values: float | Iterable[float]) -> tuple[float, ...]:
    if isinstance(values, (int, float)):
        return (float(values),)

    try:
        return tuple(float(value) for value in values)
    except TypeError:
        return (float(values),)


def apply_bounded_layer_shift(
    values: float | Iterable[float],
    delta: float,
    lower_bound: float | None = None,
    upper_bound: float | None = None,
) -> BoundedLayerShiftResult:
    bounded_lower = -math.inf if lower_bound is None else float(lower_bound)
    bounded_upper = math.inf if upper_bound is None else float(upper_bound)
    previous_values = _coerce_layer_values(values)
    layer_results = tuple(
        apply_bounded_delta(
            current_value=value,
            delta=delta,
            lower_bound=min(bounded_lower, value),
            upper_bound=max(bounded_upper, value),
        )
        for value in previous_values
    )
    bounded_values = tuple(result.bounded_value for result in layer_results)

    return BoundedLayerShiftResult(
        previous_values=previous_values,
        bounded_values=bounded_values,
        requested_delta=float(delta),
        lower_bound=bounded_lower,
        upper_bound=bounded_upper,
        layer_results=layer_results,
    )


def apply_effective_uz_storage_corrections(
    dataset: object,
    previous_grid: object,
    requested_storage_correction_delta_theta_by_cell: Mapping[tuple[int, int], float],
    lower_bound: float | None = None,
    upper_bound: float | None = None,
) -> tuple[object, dict[tuple[int, int], EffectiveUzCellBookkeepingResult]]:
    bookkeeping_results: dict[tuple[int, int], EffectiveUzCellBookkeepingResult] = {}

    for (
        (
            row,
            col,
        ),
        requested_storage_correction,
    ) in requested_storage_correction_delta_theta_by_cell.items():
        layer_shift = apply_bounded_layer_shift(
            previous_grid[row][col],
            -float(requested_storage_correction),
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        dataset[row, col] = layer_shift.bounded_values
        bookkeeping_results[(row, col)] = EffectiveUzCellBookkeepingResult(
            requested_storage_correction_delta_theta=float(
                requested_storage_correction
            ),
            layer_shift=layer_shift,
        )

    return dataset, bookkeeping_results


def rate_to_flow_m3_per_s(rate_m_per_s: float, cell_area_m2: float) -> float:
    _require_positive(float(cell_area_m2), "cell_area_m2")
    return float(rate_m_per_s) * float(cell_area_m2)


def rate_to_step_depth_m(rate_m_per_s: float, dt_seconds: float) -> float:
    _require_positive(float(dt_seconds), "dt_seconds")
    return float(rate_m_per_s) * float(dt_seconds)


def depth_to_volume_m3(depth_m: float, cell_area_m2: float) -> float:
    _require_positive(float(cell_area_m2), "cell_area_m2")
    return float(depth_m) * float(cell_area_m2)


def net_exchange_to_delta_theta(
    net_rate_m_per_s: float,
    dt_seconds: float,
    effective_uz_thickness_m: float,
) -> float:
    _require_positive(float(effective_uz_thickness_m), "effective_uz_thickness_m")
    return rate_to_step_depth_m(net_rate_m_per_s, dt_seconds) / float(
        effective_uz_thickness_m
    )


def apply_bounded_delta(
    current_value: float,
    delta: float,
    lower_bound: float = -math.inf,
    upper_bound: float = math.inf,
) -> BoundedUpdateResult:
    if lower_bound > upper_bound:
        raise ValueError("lower_bound cannot be greater than upper_bound")

    previous_value = float(current_value)
    requested_delta = float(delta)
    proposed_value = previous_value + requested_delta
    bounded_value = min(max(proposed_value, lower_bound), upper_bound)
    applied_delta = bounded_value - previous_value
    residual = requested_delta - applied_delta

    return BoundedUpdateResult(
        previous_value=previous_value,
        requested_delta=requested_delta,
        proposed_value=proposed_value,
        bounded_value=bounded_value,
        residual=residual,
        lower_bound=float(lower_bound),
        upper_bound=float(upper_bound),
    )


def apply_nonnegative_sink(
    current_value: float, sink_amount: float
) -> BoundedUpdateResult:
    sink_amount = float(sink_amount)
    if sink_amount < 0:
        raise ValueError(f"sink_amount must be non-negative, got {sink_amount}")

    return apply_bounded_delta(current_value, -sink_amount, lower_bound=0.0)
