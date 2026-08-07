from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import matplotlib.pyplot as plt
import mikeio
from src.plot_overland_coupling import (
    GridWindow,
    _data_norm,
    _mask_output_values,
    add_group_outlines,
    compute_padded_window,
    resolve_item_index,
    resolve_path,
    resolve_shared_time_selectors,
    resolve_time_selectors,
    slugify,
    swap_groups_for_display,
)
from src.spatial_mapping import DEFAULT_SPATIAL_MAPPING, CoupledCellGroup

DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "investigations" / "phase1"
DEFAULT_ITEM_NAME = "groundwater flux in z-direction"
DEFAULT_PADDING_CELLS = 5

_LONGSIM_RESULT_SUFFIX = " - Result Files - LongSim"
_RESULT_FILES_SUFFIX = " - Result Files"


def derive_3dsz_result_path(
    setup_path: str | Path, stem_suffix: str = "3DSZflow"
) -> Path:
    resolved = resolve_path(setup_path)
    result_dir = resolved.with_name(resolved.name + _RESULT_FILES_SUFFIX)
    return result_dir / f"{resolved.stem}_{stem_suffix}.dfs3"


def derive_longsim_3dsz_result_path(
    setup_path: str | Path, stem_suffix: str = "3DSZflow"
) -> Path:
    resolved = resolve_path(setup_path)
    longsim_dir = resolved.with_name(resolved.name + _LONGSIM_RESULT_SUFFIX)
    return longsim_dir / f"{resolved.stem}_{stem_suffix}.dfs3"


def resolve_layer_indices(
    n_layers: int, requested: Sequence[int] | None
) -> tuple[int, ...]:
    if not requested:
        return tuple(range(n_layers))
    resolved: list[int] = []
    for idx in requested:
        layer = int(idx)
        if layer < 0:
            layer += n_layers
        if layer < 0 or layer >= n_layers:
            raise IndexError(f"Layer index {idx} out of range 0..{n_layers - 1}.")
        resolved.append(layer)
    return tuple(resolved)


def _layer_label(layer_index: int, geometry) -> str:
    z = getattr(geometry, "z", None)
    if z is not None:
        z_arr = np.asarray(z, dtype=float)
        if layer_index < len(z_arr):
            return f"Layer {layer_index} (z={z_arr[layer_index]:.2f} m)"
    return f"Layer {layer_index}"


def plot_3dsz_layers_single_run(
    *,
    values_4d: np.ndarray,
    geometry,
    groups: Iterable[CoupledCellGroup],
    time_label: str,
    item_name: str,
    layer_indices: Sequence[int],
    output_path: str | Path,
    padding_cells: int,
    window: GridWindow,
) -> Path:
    """One figure: each row is a layer, single column = values at that layer."""
    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    group_tuple = tuple(groups)
    extent = _window_extent_3d(geometry, window)
    output_cmap = plt.get_cmap("viridis").copy()
    output_cmap.set_bad("#f3f3f3")

    layer_crops: list[np.ma.MaskedArray] = []
    for li in layer_indices:
        data_2d = np.asarray(values_4d[li], dtype=float)
        crop = data_2d[
            window.row_start : window.row_end,
            window.col_start : window.col_end,
        ]
        layer_crops.append(_mask_output_values(crop))

    all_data = np.concatenate(
        [np.asarray(c.filled(np.nan), dtype=float).ravel() for c in layer_crops]
    )
    norm = _data_norm(all_data)

    n_layers = len(layer_indices)
    fig_height = max(4.0, 3.5 * n_layers)
    fig, axes = plt.subplots(
        n_layers, 1, figsize=(6.0, fig_height), constrained_layout=True, squeeze=False
    )

    image = None
    for row, (li, crop) in enumerate(zip(layer_indices, layer_crops)):
        ax = axes[row, 0]
        image = ax.imshow(
            crop,
            origin="lower",
            extent=extent,
            interpolation="nearest",
            cmap=output_cmap,
            norm=norm,
            aspect="equal",
        )
        add_group_outlines(ax, group_tuple, geometry, color="white", linewidth=0.8)
        ax.set_title(_layer_label(li, geometry))
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")

    fig.suptitle(f"{item_name}\n{time_label}")
    if image is not None:
        fig.colorbar(image, ax=axes.ravel().tolist(), label=item_name, shrink=0.8)

    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_file


def plot_3dsz_layers_cross_run(
    *,
    primary_values_4d: np.ndarray,
    secondary_values_4d: np.ndarray,
    geometry,
    groups: Iterable[CoupledCellGroup],
    time_label: str,
    item_name: str,
    primary_label: str,
    secondary_label: str,
    layer_indices: Sequence[int],
    output_path: str | Path,
    padding_cells: int,
    window: GridWindow,
) -> Path:
    """One figure: rows = layers, cols = [primary, secondary]. Shared colour scale."""
    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    group_tuple = tuple(groups)
    extent = _window_extent_3d(geometry, window)
    output_cmap = plt.get_cmap("viridis").copy()
    output_cmap.set_bad("#f3f3f3")

    primary_crops: list[np.ma.MaskedArray] = []
    secondary_crops: list[np.ma.MaskedArray] = []
    for li in layer_indices:
        for crops, values_4d in (
            (primary_crops, primary_values_4d),
            (secondary_crops, secondary_values_4d),
        ):
            data_2d = np.asarray(values_4d[li], dtype=float)
            crop = data_2d[
                window.row_start : window.row_end,
                window.col_start : window.col_end,
            ]
            crops.append(_mask_output_values(crop))

    all_data = np.concatenate(
        [
            np.asarray(c.filled(np.nan), dtype=float).ravel()
            for crops in (primary_crops, secondary_crops)
            for c in crops
        ]
    )
    norm = _data_norm(all_data)

    n_layers = len(layer_indices)
    fig_height = max(5.0, 3.5 * n_layers)
    fig, axes = plt.subplots(
        n_layers,
        2,
        figsize=(10.0, fig_height),
        constrained_layout=True,
        sharex=True,
        sharey=True,
        squeeze=False,
    )

    image = None
    col_labels = (primary_label, secondary_label)
    for row, li in enumerate(layer_indices):
        for col, (col_label, crop) in enumerate(
            zip(col_labels, (primary_crops[row], secondary_crops[row]))
        ):
            ax = axes[row, col]
            image = ax.imshow(
                crop,
                origin="lower",
                extent=extent,
                interpolation="nearest",
                cmap=output_cmap,
                norm=norm,
                aspect="equal",
            )
            add_group_outlines(ax, group_tuple, geometry, color="white", linewidth=0.8)
            if row == 0:
                ax.set_title(col_label)
            ax.set_xlabel("Easting (m)")
            if col == 0:
                ax.set_ylabel(f"{_layer_label(li, geometry)}\nNorthing (m)")
            else:
                ax.set_ylabel("Northing (m)")

    fig.suptitle(f"{item_name}\n{time_label}")
    if image is not None:
        fig.colorbar(image, ax=axes.ravel().tolist(), label=item_name, shrink=0.8)

    fig.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_file


def _window_extent_3d(
    geometry, window: GridWindow
) -> tuple[float, float, float, float]:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot per-layer 2D slices of a MIKE SHE 3D SZ DFS3 result file, "
            "optionally comparing a short run against a LongSim reference."
        )
    )
    parser.add_argument(
        "--setup",
        help="MIKE SHE setup path. Used to derive both DFS3 paths when explicit paths are not given.",
    )
    parser.add_argument(
        "--dfs3",
        help="Explicit path to the primary DFS3 result file.",
    )
    parser.add_argument(
        "--compare-dfs3",
        help=(
            "Optional second DFS3 path for cross-run comparison. "
            "Defaults to the LongSim result directory when --setup is given."
        ),
    )
    parser.add_argument(
        "--stem-suffix",
        default="3DSZflow",
        help="Filename suffix used to locate DFS3 files from a --setup path (default: 3DSZflow).",
    )
    parser.add_argument(
        "--primary-label",
        default="Short run",
        help="Column label for the primary DFS3.",
    )
    parser.add_argument(
        "--secondary-label",
        default="LongSim",
        help="Column label for the comparison DFS3.",
    )
    parser.add_argument(
        "--item",
        default=None,
        help="DFS3 item name to plot. Defaults to all items in the file.",
    )
    parser.add_argument(
        "--times",
        nargs="+",
        default=None,
        help=(
            "Time selectors: integer indices (negative supported) or ISO dates. "
            "Defaults to first, middle, and last timestep."
        ),
    )
    parser.add_argument(
        "--n-times",
        type=int,
        default=None,
        help=(
            "Auto-select N evenly spaced timesteps from the result file. "
            "Overridden by --times if both are given."
        ),
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        type=int,
        help=(
            "Layer indices to plot (0-based, negative supported). "
            "Defaults to all layers."
        ),
    )
    parser.add_argument(
        "--padding-cells",
        type=int,
        default=DEFAULT_PADDING_CELLS,
        help="Extra cells around the coupled footprint (default: 5).",
    )
    parser.add_argument(
        "--output",
        help="Output PNG path (single-item runs only). Ignored when plotting all items.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            f"Directory for auto-named output PNGs. Defaults to {DEFAULT_OUTPUT_DIR}."
        ),
    )
    parser.add_argument(
        "--list-items",
        action="store_true",
        help="Print available DFS3 items and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.dfs3:
        primary_path = resolve_path(args.dfs3)
    elif args.setup:
        primary_path = derive_3dsz_result_path(args.setup, args.stem_suffix)
    else:
        raise ValueError("Provide --dfs3 or --setup.")

    if not primary_path.exists():
        raise FileNotFoundError(f"Primary DFS3 not found: {primary_path}")

    dfs = mikeio.open(str(primary_path))
    available_item_names = [item.name for item in dfs.items]

    if args.list_items:
        print("Available DFS3 items:")
        for name in available_item_names:
            print(f"  - {name}")
        return 0

    # Determine which items to plot
    if args.item:
        idx, name = resolve_item_index(available_item_names, args.item)
        items_to_plot = [(idx, name)]
    else:
        items_to_plot = list(enumerate(available_item_names))

    # Resolve timestep selectors — default: first, middle, last
    n_steps = dfs.n_timesteps
    if args.times:
        time_indices = resolve_time_selectors(dfs.time, args.times)
    elif args.n_times is not None:
        n = max(1, min(args.n_times, n_steps))
        selectors = [str(round(i * (n_steps - 1) / max(n - 1, 1))) for i in range(n)]
        seen: set[int] = set()
        time_indices = tuple(
            i
            for i in resolve_time_selectors(dfs.time, selectors)
            if not (i in seen or seen.add(i))  # type: ignore[func-returns-value]
        )
    else:
        mid = n_steps // 2
        selectors = ["0", str(mid), str(n_steps - 1)]
        # deduplicate while preserving order (e.g. if n_steps <= 2)
        seen = set()
        time_indices = tuple(
            i
            for i in resolve_time_selectors(dfs.time, selectors)
            if not (i in seen or seen.add(i))  # type: ignore[func-returns-value]
        )

    # Determine comparison path
    compare_path: Path | None = None
    if args.compare_dfs3:
        compare_path = resolve_path(args.compare_dfs3)
    elif args.setup:
        candidate = derive_longsim_3dsz_result_path(args.setup, args.stem_suffix)
        if candidate.exists():
            compare_path = candidate

    compare_dfs = None
    compare_available: list[str] = []
    compare_time_indices: dict[int, int] = {}
    if compare_path is not None:
        if not compare_path.exists():
            raise FileNotFoundError(f"Comparison DFS3 not found: {compare_path}")
        compare_dfs = mikeio.open(str(compare_path))
        compare_available = [item.name for item in compare_dfs.items]
        time_selectors = [str(dfs.time[i]) for i in time_indices]
        shared = resolve_shared_time_selectors(
            dfs.time, compare_dfs.time, time_selectors, nearest=True
        )
        compare_time_indices = dict(
            zip(shared.primary_indices, shared.secondary_indices)
        )

    output_dir = (
        resolve_path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read geometry once from first item at first timestep
    first_dataset = mikeio.read(str(primary_path), items=[items_to_plot[0][0]])
    first_array = first_dataset[0]
    geometry = first_array.geometry
    display_groups = swap_groups_for_display(DEFAULT_SPATIAL_MAPPING.groups)
    sample_shape = first_array.values[time_indices[0]].shape
    window = compute_padded_window(
        display_groups,
        sample_shape[-2],
        sample_shape[-1],
        args.padding_cells,
    )

    written_paths: list[Path] = []
    layers_str: str | None = None

    for item_index, item_name in items_to_plot:
        dataset = mikeio.read(str(primary_path), items=[item_index])
        data_array = dataset[0]

        compare_item_index: int | None = None
        compare_array = None
        if compare_dfs is not None:
            try:
                compare_item_index, _ = resolve_item_index(compare_available, item_name)
            except ValueError:
                compare_item_index = 0
                print(
                    f"  Warning: {item_name!r} not in comparison file; using {compare_available[0]!r}"
                )
            compare_dataset = mikeio.read(str(compare_path), items=[compare_item_index])
            compare_array = compare_dataset[0]

        for time_index in time_indices:
            time_label = str(dfs.time[time_index])
            values_4d = np.asarray(data_array.values[time_index], dtype=float)
            n_layers = values_4d.shape[0]
            layer_indices = resolve_layer_indices(n_layers, args.layers)
            if layers_str is None:
                layers_str = ", ".join(str(li) for li in layer_indices)

            if compare_array is not None:
                compare_time_index = compare_time_indices[time_index]
                secondary_values_4d = np.asarray(
                    compare_array.values[compare_time_index], dtype=float
                )

                if secondary_values_4d.shape != values_4d.shape:
                    print(f"  Skipping {item_name!r} t={time_label}: shape mismatch")
                    continue

                out = (
                    output_dir
                    / f"{slugify(item_name)}_3dsz_crossrun_{slugify(time_label)}.png"
                )
                written = plot_3dsz_layers_cross_run(
                    primary_values_4d=values_4d,
                    secondary_values_4d=secondary_values_4d,
                    geometry=geometry,
                    groups=display_groups,
                    time_label=time_label,
                    item_name=item_name,
                    primary_label=args.primary_label,
                    secondary_label=args.secondary_label,
                    layer_indices=layer_indices,
                    output_path=out,
                    padding_cells=args.padding_cells,
                    window=window,
                )
            else:
                out = (
                    output_dir
                    / f"{slugify(item_name)}_3dsz_layers_{slugify(time_label)}.png"
                )
                written = plot_3dsz_layers_single_run(
                    values_4d=values_4d,
                    geometry=geometry,
                    groups=display_groups,
                    time_label=time_label,
                    item_name=item_name,
                    layer_indices=layer_indices,
                    output_path=out,
                    padding_cells=args.padding_cells,
                    window=window,
                )

            print(f"  [{item_name}] t={time_label} -> {written.name}")
            written_paths.append(written)

    print(f"Primary DFS3: {primary_path}")
    if compare_path is not None:
        print(f"Comparison:   {compare_path}")
    time_labels_str = ", ".join(str(dfs.time[i]) for i in time_indices)
    print(f"Times:        {time_labels_str}")
    print(f"Layers:       {layers_str}")
    print(f"Written:      {len(written_paths)} plots to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
