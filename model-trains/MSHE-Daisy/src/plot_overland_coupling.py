from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import matplotlib.pyplot as plt
import mikeio
from matplotlib.colors import ListedColormap, LogNorm, Normalize
from matplotlib.patches import Rectangle
from src.spatial_mapping import DEFAULT_SPATIAL_MAPPING, CoupledCellGroup

DEFAULT_PLUGIN_SETUP = (
    REPO_ROOT
    / "data"
    / "Cernici_060126_Test02_2"
    / "Cernici16_Ben_v100_DAISYinput_plugin.she"
)
DEFAULT_ITEM_NAME = "depth of overland water"
DEFAULT_PADDING_CELLS = 5
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "investigations" / "phase1"


@dataclass(frozen=True)
class GridWindow:
    row_start: int
    row_end: int
    col_start: int
    col_end: int

    @property
    def height(self) -> int:
        return self.row_end - self.row_start

    @property
    def width(self) -> int:
        return self.col_end - self.col_start


@dataclass(frozen=True)
class OverlandPlotSelection:
    overland_dfs2_path: Path
    item_index: int
    item_name: str
    time_index: int
    time_label: str
    window: GridWindow


@dataclass(frozen=True)
class CrossRunTimeSelection:
    primary_indices: tuple[int, ...]
    secondary_indices: tuple[int, ...]
    time_labels: tuple[str, ...]


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def derive_overland_result_path(setup_path: str | Path) -> Path:
    resolved_setup_path = resolve_path(setup_path)
    return (
        resolved_setup_path.with_name(resolved_setup_path.name + " - Result Files")
        / f"{resolved_setup_path.stem}_overland.dfs2"
    )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    slug = slug.strip("_")
    return slug or "plot"


def resolve_time_index(n_timesteps: int, requested_index: int) -> int:
    if n_timesteps < 1:
        raise ValueError("The overland DFS2 file does not contain any timesteps.")

    resolved_index = int(requested_index)
    if resolved_index < 0:
        resolved_index += n_timesteps

    if resolved_index < 0 or resolved_index >= n_timesteps:
        raise IndexError(
            f"Requested time index {requested_index} is outside the available range 0..{n_timesteps - 1}."
        )

    return resolved_index


def resolve_time_selectors(
    times: Sequence[object],
    requested_selectors: Sequence[str],
) -> tuple[int, ...]:
    available_times = tuple(times)
    if not requested_selectors:
        raise ValueError("At least one time selector is required.")

    resolved_indices: list[int] = []
    for selector in requested_selectors:
        normalized_selector = str(selector).strip()
        if not normalized_selector:
            continue

        if re.fullmatch(r"[+-]?\d+", normalized_selector):
            resolved_indices.append(
                resolve_time_index(len(available_times), int(normalized_selector))
            )
            continue

        selector_key = normalized_selector.lower()
        matched_index: int | None = None
        for time_index, time_value in enumerate(available_times):
            candidate_keys = {str(time_value).strip().lower()}

            isoformat = getattr(time_value, "isoformat", None)
            if callable(isoformat):
                candidate_keys.add(str(isoformat()).strip().lower())

            strftime = getattr(time_value, "strftime", None)
            if callable(strftime):
                candidate_keys.add(strftime("%Y-%m-%d").lower())
                candidate_keys.add(strftime("%Y-%m-%d %H:%M:%S").lower())

            if selector_key in candidate_keys:
                matched_index = time_index
                break

        if matched_index is None:
            raise ValueError(
                f"Could not resolve time selector '{selector}'. Available range is "
                f"{available_times[0]} .. {available_times[-1]}."
            )

        resolved_indices.append(matched_index)

    if not resolved_indices:
        raise ValueError("At least one non-empty time selector is required.")

    return tuple(resolved_indices)


def resolve_shared_time_selectors(
    primary_times: Sequence[object],
    secondary_times: Sequence[object],
    requested_selectors: Sequence[str],
    nearest: bool = False,
) -> CrossRunTimeSelection:
    primary_time_tuple = tuple(primary_times)
    secondary_time_tuple = tuple(secondary_times)
    primary_indices = resolve_time_selectors(primary_time_tuple, requested_selectors)

    secondary_lookup: dict[str, int] = {}
    for secondary_index, secondary_time in enumerate(secondary_time_tuple):
        secondary_lookup[str(secondary_time)] = secondary_index

    secondary_arr = np.array(secondary_time_tuple, dtype="datetime64[ns]")

    secondary_indices: list[int] = []
    time_labels: list[str] = []
    for primary_index in primary_indices:
        time_label = str(primary_time_tuple[primary_index])
        if time_label in secondary_lookup:
            secondary_indices.append(secondary_lookup[time_label])
        elif nearest:
            t = np.datetime64(primary_time_tuple[primary_index], "ns")  # type: ignore[call-overload]
            nearest_idx = int(np.argmin(np.abs(secondary_arr - t)))
            secondary_indices.append(nearest_idx)
        else:
            raise ValueError(
                f"Time '{time_label}' exists in the primary run but not in the comparison run."
            )
        time_labels.append(time_label)

    return CrossRunTimeSelection(
        primary_indices=tuple(primary_indices),
        secondary_indices=tuple(secondary_indices),
        time_labels=tuple(time_labels),
    )


def resolve_item_index(
    item_names: Iterable[str], requested_name: str
) -> tuple[int, str]:
    available_names = tuple(str(name) for name in item_names)
    try:
        item_index = available_names.index(requested_name)
        return item_index, available_names[item_index]
    except ValueError:
        normalized_requested = requested_name.strip().lower()
        for item_index, item_name in enumerate(available_names):
            if item_name.strip().lower() == normalized_requested:
                return item_index, item_name

    raise ValueError(
        f"Could not find overland item '{requested_name}'. Available items: {available_names}"
    )


def build_group_mask(
    groups: Iterable[CoupledCellGroup],
    ny: int,
    nx: int,
) -> np.ndarray:
    mask = np.zeros((ny, nx), dtype=bool)
    for group in groups:
        mask[group.row_start : group.row_end, group.col_start : group.col_end] = True
    return mask


def compute_padded_window(
    groups: Iterable[CoupledCellGroup],
    ny: int,
    nx: int,
    padding_cells: int,
) -> GridWindow:
    group_tuple = tuple(groups)
    if not group_tuple:
        raise ValueError("At least one coupled-cell group is required.")

    padding = max(0, int(padding_cells))
    row_start = max(0, min(group.row_start for group in group_tuple) - padding)
    row_end = min(ny, max(group.row_end for group in group_tuple) + padding)
    col_start = max(0, min(group.col_start for group in group_tuple) - padding)
    col_end = min(nx, max(group.col_end for group in group_tuple) + padding)

    return GridWindow(
        row_start=row_start,
        row_end=row_end,
        col_start=col_start,
        col_end=col_end,
    )


def swap_groups_for_display(
    groups: Iterable[CoupledCellGroup],
) -> tuple[CoupledCellGroup, ...]:
    """Swap the coupled footprint axes for plotting only.

    The MIKE SHE runtime coupling uses the legacy block selection in a different
    axis convention than the saved DFS2 overland outputs. The data itself is read
    natively and should not be transposed here; only the block overlay is swapped
    so it lands on the correct cells in the 2D result plots.
    """

    group_tuple = tuple(groups)
    if not group_tuple:
        return ()

    swapped_groups = []
    for group in group_tuple:
        swapped_groups.append(
            CoupledCellGroup(
                row_start=group.col_start,
                row_end=group.col_end,
                col_start=group.row_start,
                col_end=group.row_end,
                daisy_class=group.daisy_class,
                drained=group.drained,
                lower_boundary_case=group.lower_boundary_case,
            )
        )

    return tuple(swapped_groups)


def _window_extent(geometry, window: GridWindow) -> tuple[float, float, float, float]:
    x = np.asarray(geometry.x, dtype=float)
    y = np.asarray(geometry.y, dtype=float)
    dx = float(getattr(geometry, "dx", np.diff(x).mean() if len(x) > 1 else 1.0))
    dy = float(getattr(geometry, "dy", np.diff(y).mean() if len(y) > 1 else 1.0))
    return (
        float(x[window.col_start] - dx / 2.0),
        float(x[window.col_end - 1] + dx / 2.0),
        float(y[window.row_start] - dy / 2.0),
        float(y[window.row_end - 1] + dy / 2.0),
    )


def _data_norm(data: np.ndarray) -> Normalize | LogNorm | None:
    finite_values = data[np.isfinite(data)]
    if finite_values.size == 0:
        return None

    if np.any(finite_values < 0.0):
        return None

    finite_positive = finite_values[finite_values > 0.0]
    if finite_positive.size == 0:
        return None

    vmin = float(finite_positive.min())
    vmax = float(finite_positive.max())
    if vmax <= vmin:
        return Normalize(vmin=0.0, vmax=max(vmax, 1.0))

    if vmin > 0.0 and (vmax / vmin) >= 100.0:
        return LogNorm(vmin=vmin, vmax=vmax)

    return Normalize(vmin=vmin, vmax=vmax)


def _mask_output_values(data: np.ndarray) -> np.ma.MaskedArray:
    masked_output = np.ma.masked_invalid(np.asarray(data, dtype=float))
    finite_values = masked_output.compressed()
    if finite_values.size == 0:
        return masked_output

    has_positive = bool(np.any(finite_values > 0.0))
    has_negative = bool(np.any(finite_values < 0.0))

    if has_positive and not has_negative:
        masked_output = np.ma.masked_less_equal(masked_output, 0.0)
    elif not has_positive and not has_negative:
        masked_output = np.ma.masked_equal(masked_output, 0.0)

    return masked_output


def add_group_outlines(
    ax,
    groups: Iterable[CoupledCellGroup],
    geometry,
    color: str,
    linewidth: float = 1.0,
) -> None:
    x = np.asarray(geometry.x, dtype=float)
    y = np.asarray(geometry.y, dtype=float)
    dx = float(getattr(geometry, "dx", np.diff(x).mean() if len(x) > 1 else 1.0))
    dy = float(getattr(geometry, "dy", np.diff(y).mean() if len(y) > 1 else 1.0))

    for group in groups:
        x0 = float(x[group.col_start] - dx / 2.0)
        y0 = float(y[group.row_start] - dy / 2.0)
        width = float((group.col_end - group.col_start) * dx)
        height = float((group.row_end - group.row_start) * dy)
        ax.add_patch(
            Rectangle(
                (x0, y0),
                width,
                height,
                fill=False,
                edgecolor=color,
                linewidth=linewidth,
                alpha=0.95,
            )
        )


def plot_overland_coupling_map(
    *,
    values_2d: np.ndarray,
    geometry,
    groups: Iterable[CoupledCellGroup],
    time_label: str,
    item_name: str,
    output_path: str | Path,
    padding_cells: int,
    window: GridWindow,
) -> Path:
    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    group_tuple = tuple(groups)
    mask = build_group_mask(
        group_tuple,
        values_2d.shape[0],
        values_2d.shape[1],
    )
    mask_crop = mask[
        window.row_start : window.row_end,
        window.col_start : window.col_end,
    ]
    data_crop = np.asarray(
        values_2d[
            window.row_start : window.row_end,
            window.col_start : window.col_end,
        ],
        dtype=float,
    )
    extent = _window_extent(geometry, window)

    block_cmap = ListedColormap(["#f2f2f2", "#1f78b4"])
    output_cmap = plt.get_cmap("viridis").copy()
    output_cmap.set_bad("#f3f3f3")

    masked_output = _mask_output_values(data_crop)
    norm = _data_norm(np.asarray(masked_output.filled(np.nan), dtype=float))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)

    axes[0].imshow(
        mask_crop.astype(int),
        origin="lower",
        extent=extent,
        interpolation="nearest",
        cmap=block_cmap,
        vmin=0,
        vmax=1,
        aspect="equal",
    )
    add_group_outlines(
        axes[0],
        group_tuple,
        geometry,
        color="#202020",
        linewidth=0.8,
    )
    axes[0].set_title("Coupled block footprint")

    image = axes[1].imshow(
        masked_output,
        origin="lower",
        extent=extent,
        interpolation="nearest",
        cmap=output_cmap,
        norm=norm,
        aspect="equal",
    )
    add_group_outlines(
        axes[1],
        group_tuple,
        geometry,
        color="white",
        linewidth=0.8,
    )
    axes[1].set_title(f"{item_name}\n{time_label}")

    for ax in axes:
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")

    fig.suptitle(
        "Coupled cells with padded local overland output view "
        f"(padding = {padding_cells} cells; rows {window.row_start}:{window.row_end}, "
        f"cols {window.col_start}:{window.col_end})"
    )
    fig.colorbar(image, ax=axes[1], label=item_name, shrink=0.9)

    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_file


def plot_overland_timestep_comparison(
    *,
    values_by_time: Sequence[np.ndarray],
    geometry,
    groups: Iterable[CoupledCellGroup],
    time_labels: Sequence[str],
    item_name: str,
    output_path: str | Path,
    padding_cells: int,
    window: GridWindow,
) -> Path:
    if len(values_by_time) != len(time_labels):
        raise ValueError("values_by_time and time_labels must have the same length.")

    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    group_tuple = tuple(groups)
    extent = _window_extent(geometry, window)
    output_cmap = plt.get_cmap("viridis").copy()
    output_cmap.set_bad("#f3f3f3")

    masked_outputs = []
    for values_2d in values_by_time:
        data_crop = np.asarray(
            values_2d[
                window.row_start : window.row_end,
                window.col_start : window.col_end,
            ],
            dtype=float,
        )
        masked_outputs.append(_mask_output_values(data_crop))

    norm = _data_norm(
        np.concatenate(
            [
                np.asarray(masked_output.filled(np.nan), dtype=float).ravel()
                for masked_output in masked_outputs
            ]
        )
    )

    n_panels = len(masked_outputs)
    fig_width = max(6.0, 4.4 * n_panels)
    fig, axes = plt.subplots(
        1,
        n_panels,
        figsize=(fig_width, 5.8),
        constrained_layout=True,
    )
    axes_array = np.atleast_1d(axes).ravel()

    image = None
    for ax, masked_output, time_label in zip(axes_array, masked_outputs, time_labels):
        image = ax.imshow(
            masked_output,
            origin="lower",
            extent=extent,
            interpolation="nearest",
            cmap=output_cmap,
            norm=norm,
            aspect="equal",
        )
        add_group_outlines(
            ax,
            group_tuple,
            geometry,
            color="white",
            linewidth=0.8,
        )
        ax.set_title(str(time_label))
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")

    fig.suptitle(
        f"{item_name} across selected timesteps "
        f"(padding = {padding_cells} cells; rows {window.row_start}:{window.row_end}, "
        f"cols {window.col_start}:{window.col_end})"
    )
    if image is not None:
        fig.colorbar(image, ax=list(axes_array), label=item_name, shrink=0.9)

    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_file


def plot_overland_cross_run_comparison(
    *,
    primary_values_by_time: Sequence[np.ndarray],
    secondary_values_by_time: Sequence[np.ndarray],
    geometry,
    groups: Iterable[CoupledCellGroup],
    time_labels: Sequence[str],
    item_name: str,
    primary_label: str,
    secondary_label: str,
    output_path: str | Path,
    padding_cells: int,
    window: GridWindow,
) -> Path:
    if len(primary_values_by_time) != len(time_labels):
        raise ValueError(
            "primary_values_by_time and time_labels must have the same length."
        )
    if len(secondary_values_by_time) != len(time_labels):
        raise ValueError(
            "secondary_values_by_time and time_labels must have the same length."
        )

    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    group_tuple = tuple(groups)
    extent = _window_extent(geometry, window)
    output_cmap = plt.get_cmap("viridis").copy()
    output_cmap.set_bad("#f3f3f3")

    cropped_values_by_run: list[list[np.ma.MaskedArray]] = []
    for values_by_time in (primary_values_by_time, secondary_values_by_time):
        masked_outputs_for_run: list[np.ma.MaskedArray] = []
        for values_2d in values_by_time:
            data_crop = np.asarray(
                values_2d[
                    window.row_start : window.row_end,
                    window.col_start : window.col_end,
                ],
                dtype=float,
            )
            masked_outputs_for_run.append(_mask_output_values(data_crop))
        cropped_values_by_run.append(masked_outputs_for_run)

    norm = _data_norm(
        np.concatenate(
            [
                np.asarray(masked_output.filled(np.nan), dtype=float).ravel()
                for masked_outputs_for_run in cropped_values_by_run
                for masked_output in masked_outputs_for_run
            ]
        )
    )

    n_columns = len(time_labels)
    fig_width = max(8.0, 4.1 * n_columns)
    fig, axes = plt.subplots(
        2,
        n_columns,
        figsize=(fig_width, 9.6),
        constrained_layout=True,
        sharex=True,
        sharey=True,
        squeeze=False,
    )

    row_labels = (primary_label, secondary_label)
    image = None
    for row_index, (row_label, masked_outputs_for_run) in enumerate(
        zip(row_labels, cropped_values_by_run)
    ):
        for col_index, (time_label, masked_output) in enumerate(
            zip(time_labels, masked_outputs_for_run)
        ):
            ax = axes[row_index, col_index]
            image = ax.imshow(
                masked_output,
                origin="lower",
                extent=extent,
                interpolation="nearest",
                cmap=output_cmap,
                norm=norm,
                aspect="equal",
            )
            add_group_outlines(
                ax,
                group_tuple,
                geometry,
                color="white",
                linewidth=0.8,
            )
            if row_index == 0:
                ax.set_title(str(time_label))
            ax.set_xlabel("Easting (m)")
            if col_index == 0:
                ax.set_ylabel(f"{row_label}\nNorthing (m)")
            else:
                ax.set_ylabel("Northing (m)")

    fig.suptitle(
        f"{item_name}: short run vs LongSim on matching dates "
        f"(padding = {padding_cells} cells; rows {window.row_start}:{window.row_end}, "
        f"cols {window.col_start}:{window.col_end})"
    )
    if image is not None:
        fig.colorbar(image, ax=axes.ravel().tolist(), label=item_name, shrink=0.9)

    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_file


def build_selection(
    *,
    overland_dfs2_path: str | Path,
    item_name: str,
    time_index: int,
    padding_cells: int,
) -> OverlandPlotSelection:
    resolved_overland_path = resolve_path(overland_dfs2_path)
    if not resolved_overland_path.exists():
        raise FileNotFoundError(
            f"Could not find overland DFS2 file: {resolved_overland_path}"
        )

    dataset = mikeio.open(str(resolved_overland_path))
    resolved_item_index, resolved_item_name = resolve_item_index(
        (item.name for item in dataset.items),
        item_name,
    )
    resolved_time_index = resolve_time_index(dataset.n_timesteps, time_index)
    display_groups = swap_groups_for_display(DEFAULT_SPATIAL_MAPPING.groups)
    window = compute_padded_window(
        display_groups,
        dataset.geometry.ny,
        dataset.geometry.nx,
        padding_cells,
    )

    return OverlandPlotSelection(
        overland_dfs2_path=resolved_overland_path,
        item_index=resolved_item_index,
        item_name=resolved_item_name,
        time_index=resolved_time_index,
        time_label=str(dataset.time[resolved_time_index]),
        window=window,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot the coupled-cell block footprint and a padded crop of a MIKE SHE "
            "overland DFS2 output item."
        )
    )
    parser.add_argument(
        "--setup",
        help=(
            "Optional MIKE SHE setup path. Used only to derive the overland DFS2 path "
            "when --overland-dfs2 is not provided."
        ),
    )
    parser.add_argument(
        "--overland-dfs2",
        help="Explicit path to the MIKE SHE overland DFS2 result file.",
    )
    parser.add_argument(
        "--compare-overland-dfs2",
        help=(
            "Optional second overland DFS2 path. When provided together with "
            "--compare-times, plots the primary run versus the comparison run on the same dates."
        ),
    )
    parser.add_argument(
        "--primary-label",
        default="Short run",
        help="Row label for the primary overland DFS2 when using --compare-overland-dfs2.",
    )
    parser.add_argument(
        "--secondary-label",
        default="LongSim",
        help="Row label for the comparison overland DFS2 when using --compare-overland-dfs2.",
    )
    parser.add_argument(
        "--item",
        default=DEFAULT_ITEM_NAME,
        help="DFS2 item name to plot (default: depth of overland water).",
    )
    parser.add_argument(
        "--time-index",
        type=int,
        default=-1,
        help="Time index to plot. Negative values count from the end (default: -1).",
    )
    parser.add_argument(
        "--compare-times",
        nargs="+",
        help=(
            "Optional time selectors to compare side by side. Each selector can be an "
            "integer index (including negative indices) or an ISO date like 2020-08-04."
        ),
    )
    parser.add_argument(
        "--padding-cells",
        type=int,
        default=DEFAULT_PADDING_CELLS,
        help="Number of extra cells to include around the coupled footprint.",
    )
    parser.add_argument(
        "--output",
        help="Output PNG path. Defaults to docs/investigations/phase1/<item>_overland_blocks.png",
    )
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory for auto-named output PNGs. "
            "Ignored when --output is given. "
            f"Defaults to {DEFAULT_OUTPUT_DIR}."
        ),
    )
    parser.add_argument(
        "--list-items",
        action="store_true",
        help="Print available overland DFS2 items and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overland_dfs2_path = (
        resolve_path(args.overland_dfs2)
        if args.overland_dfs2
        else derive_overland_result_path(args.setup or DEFAULT_PLUGIN_SETUP)
    )

    dfs = mikeio.open(str(overland_dfs2_path))
    available_item_names = [item.name for item in dfs.items]
    if args.list_items:
        print("Available overland DFS2 items:")
        for item_name in available_item_names:
            print(f"- {item_name}")
        return 0

    item_index, item_name = resolve_item_index(available_item_names, args.item)
    compare_time_indices = (
        resolve_time_selectors(dfs.time, args.compare_times)
        if args.compare_times
        else ()
    )
    resolved_time_index = resolve_time_index(len(dfs.time), args.time_index)
    dataset = mikeio.read(str(overland_dfs2_path), items=[item_index])
    data_array = dataset[0]
    display_groups = swap_groups_for_display(DEFAULT_SPATIAL_MAPPING.groups)
    window = compute_padded_window(
        display_groups,
        data_array.values.shape[-2],
        data_array.values.shape[-1],
        args.padding_cells,
    )

    if args.compare_overland_dfs2 and not args.compare_times:
        raise ValueError("--compare-overland-dfs2 requires --compare-times.")

    if args.compare_overland_dfs2:
        comparison_overland_path = resolve_path(args.compare_overland_dfs2)
        comparison_dfs = mikeio.open(str(comparison_overland_path))
        comparison_item_index, comparison_item_name = resolve_item_index(
            [item.name for item in comparison_dfs.items],
            args.item,
        )
        if comparison_item_name != item_name:
            raise ValueError(
                f"Resolved comparison item '{comparison_item_name}' does not match primary item '{item_name}'."
            )

        comparison_dataset = mikeio.read(
            str(comparison_overland_path),
            items=[comparison_item_index],
        )
        comparison_data_array = comparison_dataset[0]
        if comparison_data_array.values.shape[-2:] != data_array.values.shape[-2:]:
            raise ValueError(
                "Primary and comparison overland grids must have matching shapes for cross-run comparison."
            )

        shared_time_selection = resolve_shared_time_selectors(
            dfs.time,
            comparison_dfs.time,
            args.compare_times or (),
        )
        primary_values_by_time = [
            np.asarray(data_array.values[time_index], dtype=float)
            for time_index in shared_time_selection.primary_indices
        ]
        secondary_values_by_time = [
            np.asarray(comparison_data_array.values[time_index], dtype=float)
            for time_index in shared_time_selection.secondary_indices
        ]
        _auto_dir = (
            resolve_path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
        )
        output_path = (
            resolve_path(args.output)
            if args.output
            else _auto_dir
            / (
                f"{slugify(item_name)}_short_vs_longsim_compare_"
                f"{slugify(shared_time_selection.time_labels[0])}_to_"
                f"{slugify(shared_time_selection.time_labels[-1])}.png"
            )
        )
        written_path = plot_overland_cross_run_comparison(
            primary_values_by_time=primary_values_by_time,
            secondary_values_by_time=secondary_values_by_time,
            geometry=data_array.geometry,
            groups=display_groups,
            time_labels=shared_time_selection.time_labels,
            item_name=item_name,
            primary_label=args.primary_label,
            secondary_label=args.secondary_label,
            output_path=output_path,
            padding_cells=args.padding_cells,
            window=window,
        )

        print(f"Primary overland DFS2: {overland_dfs2_path}")
        print(f"Comparison overland DFS2: {comparison_overland_path}")
        print(f"Item: {item_name}")
        print("Matched times:")
        for time_label in shared_time_selection.time_labels:
            print(f"- {time_label}")
        print(
            "Window: "
            f"rows {window.row_start}:{window.row_end}, cols {window.col_start}:{window.col_end}"
        )
        print(f"Cross-run comparison plot written to: {written_path}")
        return 0

    if compare_time_indices:
        time_labels = [str(dfs.time[time_index]) for time_index in compare_time_indices]
        values_by_time = [
            np.asarray(data_array.values[time_index], dtype=float)
            for time_index in compare_time_indices
        ]
        _auto_dir = (
            resolve_path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
        )
        output_path = (
            resolve_path(args.output)
            if args.output
            else _auto_dir
            / (
                f"{slugify(item_name)}_overland_compare_"
                f"t{compare_time_indices[0]}_to_t{compare_time_indices[-1]}.png"
            )
        )
        written_path = plot_overland_timestep_comparison(
            values_by_time=values_by_time,
            geometry=data_array.geometry,
            groups=display_groups,
            time_labels=time_labels,
            item_name=item_name,
            output_path=output_path,
            padding_cells=args.padding_cells,
            window=window,
        )

        print(f"Overland DFS2: {overland_dfs2_path}")
        print(f"Item: {item_name}")
        print("Times:")
        for time_label in time_labels:
            print(f"- {time_label}")
        print(
            "Window: "
            f"rows {window.row_start}:{window.row_end}, cols {window.col_start}:{window.col_end}"
        )
        print(f"Comparison plot written to: {written_path}")
        return 0

    values_2d = np.asarray(data_array.values[resolved_time_index], dtype=float)

    _auto_dir = resolve_path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    output_path = (
        resolve_path(args.output)
        if args.output
        else _auto_dir
        / f"{slugify(item_name)}_overland_blocks_t{resolved_time_index}.png"
    )
    written_path = plot_overland_coupling_map(
        values_2d=values_2d,
        geometry=data_array.geometry,
        groups=display_groups,
        time_label=str(dataset.time[resolved_time_index]),
        item_name=item_name,
        output_path=output_path,
        padding_cells=args.padding_cells,
        window=window,
    )

    print(f"Overland DFS2: {overland_dfs2_path}")
    print(f"Item: {item_name}")
    print(f"Time: {dfs.time[resolved_time_index]}")
    print(
        "Window: "
        f"rows {window.row_start}:{window.row_end}, cols {window.col_start}:{window.col_end}"
    )
    print(f"Plot written to: {written_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
