"""Soil-profile setup parsing and DFS2 export helpers."""

from dataclasses import dataclass
from pathlib import Path
import re
import warnings

import mikeio
import numpy as np
import pandas as pd


def _suppress_mikeio_static_timestep_warning() -> None:
    """Suppress expected MikeIO warnings when writing static (single-time) DFS2 maps."""
    warnings.simplefilter("ignore", category=UserWarning)
    warnings.filterwarnings(
        "ignore",
        message=r"Time step is 0\.0 seconds\. This must be a positive number\. Setting to 1 second\.",
        category=UserWarning,
        module=r"mikeio\.dfs\._dfs",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"Time step is 0\.0 seconds",
        category=UserWarning,
        module=r"mikeio\.dfs\._dfs",
    )


@dataclass(frozen=True)
class ProfileProperty:
    """Parsed FC/WP pair for one soil profile."""

    wilting_point: float
    field_capacity: float


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _extract_grid_code(path: Path) -> int:
    stem = path.stem

    # Prefer explicit SoilProf-style naming when available.
    m = re.search(r"soilprof\s*(\d+)", stem, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Fallback for other naming schemes that still carry a profile/grid number.
    for pattern in (
        r"(?:grid|profile|soil)\D*(\d+)",
        r"(?:cell|code)\D*(\d+)",
        r"(?:^|[_\-\s])(\d+)(?:$|[_\-\s])",
    ):
        m = re.search(pattern, stem, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))

    raise ValueError(
        "Could not infer grid code from file name "
        f"'{path.name}'. Include an identifiable number in the filename."
    )


def _normalize_txt_glob_patterns(
    soil_profile_txt_glob: str | None,
) -> list[str]:
    if soil_profile_txt_glob is None:
        return ["*SoilProf*.txt", "*profile*.txt", "*.txt"]

    patterns = [soil_profile_txt_glob] if str(soil_profile_txt_glob).strip() else []

    return patterns or ["*SoilProf*.txt", "*profile*.txt", "*.txt"]


def _find_profile_txt_files(
    results_dir: Path,
    soil_profile_txt_glob: str | None,
) -> tuple[list[Path], list[str]]:
    patterns = _normalize_txt_glob_patterns(soil_profile_txt_glob)

    seen: set[Path] = set()
    txt_files: list[Path] = []
    for pattern in patterns:
        for candidate in sorted(results_dir.glob(pattern)):
            if candidate in seen:
                continue
            seen.add(candidate)
            txt_files.append(candidate)

    txt_files.sort()
    return txt_files, patterns


def _extract_cell_ranges(text: str) -> list[tuple[str, int, int]]:
    """Parse contiguous cell ranges from UZ table-like rows in profile text files."""
    row_pat = re.compile(
        r"^\s*(?P<cell>\d+)\s+[-+]?\d*\.\d+\s+[-+]?\d*\.\d+\s+(?P<soil>\S+)\s*$"
    )

    rows: list[tuple[int, str]] = []
    current_soil: str | None = None

    for line in text.splitlines():
        m = row_pat.match(line)
        if not m:
            continue

        cell = int(m.group("cell"))
        soil_token = m.group("soil").strip()
        if soil_token != "-":
            current_soil = soil_token

        if current_soil:
            rows.append((cell, current_soil))

    if not rows:
        return []

    rows.sort(key=lambda x: x[0])
    ranges: list[tuple[str, int, int]] = []

    start_cell = rows[0][0]
    prev_cell = rows[0][0]
    active_soil = rows[0][1]

    for cell, soil in rows[1:]:
        contiguous = cell == prev_cell + 1
        if soil == active_soil and contiguous:
            prev_cell = cell
            continue

        ranges.append((active_soil, start_cell, prev_cell))
        start_cell = cell
        prev_cell = cell
        active_soil = soil

    ranges.append((active_soil, start_cell, prev_cell))
    return ranges


def _extract_properties_by_section(text: str) -> dict[str, ProfileProperty]:
    props: dict[str, ProfileProperty] = {}
    section_pat = re.compile(r"^\s*Soil name\s*:\s*(?P<soil>[^\r\n]+)", re.IGNORECASE)

    field_pat = re.compile(
        r"^\s*Field\s+Capacity\s+pF,psi\[m\],Th\s*:\s*"
        r"(?P<pf>[-+0-9.eE]+)\s+(?P<psi>[-+0-9.eE]+)\s+(?P<th>[-+0-9.eE]+)",
        re.IGNORECASE,
    )
    wilt_pat = re.compile(
        r"^\s*Wilting\s+Point\s+pF,psi\[m\],Th\s*:\s*"
        r"(?P<pf>[-+0-9.eE]+)\s+(?P<psi>[-+0-9.eE]+)\s+(?P<th>[-+0-9.eE]+)",
        re.IGNORECASE,
    )

    lines = text.splitlines()
    section_starts: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        m = section_pat.match(line)
        if m:
            section_starts.append((idx, m.group("soil").strip()))

    for i, (start_idx, soil_name) in enumerate(section_starts):
        end_idx = (
            section_starts[i + 1][0] if i + 1 < len(section_starts) else len(lines)
        )
        section = lines[start_idx:end_idx]

        wp = None
        fc = None
        for line in section:
            m_fc = field_pat.match(line)
            if m_fc:
                fc = float(m_fc.group("th"))

            m_wp = wilt_pat.match(line)
            if m_wp:
                wp = float(m_wp.group("th"))

        if wp is not None and fc is not None:
            props[_normalize_name(soil_name)] = ProfileProperty(
                wilting_point=float(wp),
                field_capacity=float(fc),
            )

    return props


def parse_soil_profile_text(
    path: Path,
    manual_cell_ranges_overrides: dict[int, list[tuple[str, int, int]]] | None = None,
    manual_property_overrides: dict[int, dict[str, tuple[float, float]]] | None = None,
) -> tuple[int, pd.DataFrame]:
    """Parse one PreProcessed_SoilProf*.txt file to one row per cell index."""
    manual_cell_ranges_overrides = manual_cell_ranges_overrides or {}
    manual_property_overrides = manual_property_overrides or {}

    grid_code = _extract_grid_code(path)
    text = path.read_text(encoding="utf-8", errors="ignore")

    ranges = _extract_cell_ranges(text)
    if grid_code in manual_cell_ranges_overrides:
        ranges = manual_cell_ranges_overrides[grid_code]

    if not ranges:
        preview = "\n".join(text.splitlines()[:80])
        raise ValueError(
            f"No soil-profile cell ranges found in {path.name}.\n"
            "Add entries in manual_cell_ranges_overrides.\n"
            f"Preview:\n{preview}"
        )

    properties = _extract_properties_by_section(text)

    if grid_code in manual_property_overrides:
        for soil, (wp, fc) in manual_property_overrides[grid_code].items():
            properties[_normalize_name(soil)] = ProfileProperty(
                wilting_point=float(wp),
                field_capacity=float(fc),
            )

    soil_names = sorted({soil for soil, _, _ in ranges})
    missing = [soil for soil in soil_names if _normalize_name(soil) not in properties]
    if missing:
        print(
            f"[WARN] {path.name}: no parsed properties for {missing}. "
            "Use manual_property_overrides if needed."
        )

    rows = []
    for soil, start, end in ranges:
        p = properties.get(_normalize_name(soil))
        wp = np.nan if p is None else p.wilting_point
        fc = np.nan if p is None else p.field_capacity

        for cell in range(start, end + 1):
            rows.append(
                {
                    "cell_index": int(cell),
                    "soil_name": soil,
                    "wilting_point": float(wp),
                    "field_capacity": float(fc),
                }
            )

    df = (
        pd.DataFrame(rows)
        .drop_duplicates()
        .sort_values(["cell_index", "soil_name"])
        .reset_index(drop=True)
    )

    by_cell = df.groupby("cell_index", as_index=False).agg(
        soil_name_nunique=("soil_name", "nunique"),
        wp_nunique=("wilting_point", lambda s: s.dropna().nunique()),
        fc_nunique=("field_capacity", lambda s: s.dropna().nunique()),
    )
    bad = by_cell[
        (by_cell["soil_name_nunique"] > 1)
        | (by_cell["wp_nunique"] > 1)
        | (by_cell["fc_nunique"] > 1)
    ]
    if not bad.empty:
        raise ValueError(
            f"{path.name}: inconsistent per-cell mapping detected for cells "
            f"{bad['cell_index'].tolist()}"
        )

    df = (
        df.sort_values(["cell_index", "soil_name"])
        .drop_duplicates(subset=["cell_index"], keep="first")
        .reset_index(drop=True)
    )
    return grid_code, df


def parse_soil_profile_texts(
    results_dir: Path,
    soil_profile_txt_glob: str | None,
    profile_table_csv_path: Path,
    manual_cell_ranges_overrides: dict[int, list[tuple[str, int, int]]] | None = None,
    manual_property_overrides: dict[int, dict[str, tuple[float, float]]] | None = None,
) -> tuple[dict[int, pd.DataFrame], pd.DataFrame, int]:
    """Parse all profile text files and persist profile_table CSV."""
    txt_files, patterns = _find_profile_txt_files(results_dir, soil_profile_txt_glob)
    if not txt_files:
        raise FileNotFoundError(
            f"No profile text files found in {results_dir}. Tried patterns: {patterns}"
        )

    parsed_by_grid: dict[int, pd.DataFrame] = {}
    rows = []

    for txt_file in txt_files:
        grid_code, df = parse_soil_profile_text(
            txt_file,
            manual_cell_ranges_overrides=manual_cell_ranges_overrides,
            manual_property_overrides=manual_property_overrides,
        )
        parsed_by_grid[grid_code] = df.set_index("cell_index").sort_index()

        tmp = df.copy()
        tmp["grid_code"] = grid_code
        rows.append(tmp)
        print(f"[OK] Parsed grid code {grid_code}: {txt_file.name}")

    profile_table = pd.concat(rows, ignore_index=True)
    profile_table = profile_table.sort_values(["grid_code", "cell_index"]).reset_index(
        drop=True
    )
    max_cell_index = int(profile_table["cell_index"].max())

    profile_table.to_csv(profile_table_csv_path, index=False)
    return parsed_by_grid, profile_table, max_cell_index


def generate_soil_property_dfs2_outputs(
    preprocessed_dfs2: Path,
    profile_grid_item_hint: str,
    parsed_by_grid: dict[int, pd.DataFrame],
    max_cell_index: int,
    wp_output_dir: Path,
    fc_output_dir: Path,
    output_prefix_wp: str,
    output_prefix_fc: str,
    grid_codes_dfs2_path: Path,
) -> pd.DataFrame:
    """Generate grid_codes and per-cell FC/WP dfs2 outputs."""
    if not preprocessed_dfs2.exists():
        raise FileNotFoundError(f"Preprocessed DFS2 not found: {preprocessed_dfs2}")

    with warnings.catch_warnings():
        _suppress_mikeio_static_timestep_warning()
        preprocessed = mikeio.read(preprocessed_dfs2)
    item_names = [item.name for item in preprocessed.items]

    item_index = 0
    for idx, item_name in enumerate(item_names):
        if profile_grid_item_hint.lower() in item_name.lower():
            item_index = idx
            break

    profile_grid_da = preprocessed[item_index]
    profile_grid = profile_grid_da.to_numpy().squeeze()
    if profile_grid.ndim == 3:
        profile_grid = profile_grid[0]

    unique_grid_codes = sorted(
        int(v) for v in np.unique(profile_grid[~np.isnan(profile_grid)])
    )
    missing_grid_codes = [gc for gc in unique_grid_codes if gc not in parsed_by_grid]
    if missing_grid_codes:
        raise ValueError(
            "Missing parsed profile text for grid codes in DFS2: "
            + ", ".join(map(str, missing_grid_codes))
        )

    time_index = profile_grid_da.time[:1]
    geometry = profile_grid_da.geometry

    with warnings.catch_warnings():
        _suppress_mikeio_static_timestep_warning()
        grid_codes_da = mikeio.DataArray(
            data=np.expand_dims(profile_grid.astype(np.float32), axis=0),
            time=time_index,
            geometry=geometry,
            item=mikeio.ItemInfo("grid_codes"),
        )
        grid_codes_da.to_dfs(grid_codes_dfs2_path)

    written = []
    for cell_idx in range(1, max_cell_index + 1):
        wp_grid = np.full_like(profile_grid, np.nan, dtype=np.float32)
        fc_grid = np.full_like(profile_grid, np.nan, dtype=np.float32)

        for grid_code in unique_grid_codes:
            table = parsed_by_grid[grid_code]
            if cell_idx not in table.index:
                continue

            record = table.loc[cell_idx]
            if isinstance(record, pd.DataFrame):
                raise ValueError(
                    f"Duplicate cell mapping detected for grid_code={grid_code}, cell={cell_idx}"
                )

            mask = profile_grid == grid_code
            wp_grid[mask] = float(record["wilting_point"])
            fc_grid[mask] = float(record["field_capacity"])

        wp_out = wp_output_dir.joinpath(f"{output_prefix_wp}_cell{cell_idx:02d}.dfs2")
        fc_out = fc_output_dir.joinpath(f"{output_prefix_fc}_cell{cell_idx:02d}.dfs2")

        with warnings.catch_warnings():
            _suppress_mikeio_static_timestep_warning()
            wp_da = mikeio.DataArray(
                data=np.expand_dims(wp_grid, axis=0),
                time=time_index,
                geometry=geometry,
                item=mikeio.ItemInfo(f"wilting_point_cell{cell_idx:02d}"),
            )
            fc_da = mikeio.DataArray(
                data=np.expand_dims(fc_grid, axis=0),
                time=time_index,
                geometry=geometry,
                item=mikeio.ItemInfo(f"field_capacity_cell{cell_idx:02d}"),
            )
            wp_da.to_dfs(wp_out)
            fc_da.to_dfs(fc_out)

        written.append(
            {
                "cell_index": cell_idx,
                "wilting_point_dfs2": str(wp_out),
                "field_capacity_dfs2": str(fc_out),
            }
        )

    return pd.DataFrame(written)


def build_soil_profile_summary(
    output_index: pd.DataFrame, summary_csv_path: Path
) -> pd.DataFrame:
    """Build summary table and persist as CSV."""
    summary = output_index.copy()
    summary["wp_exists"] = summary["wilting_point_dfs2"].map(lambda p: Path(p).exists())
    summary["fc_exists"] = summary["field_capacity_dfs2"].map(
        lambda p: Path(p).exists()
    )
    summary.to_csv(summary_csv_path, index=False)
    return summary
