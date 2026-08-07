from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass

import src.blocks as legacy_blocks


@dataclass(frozen=True)
class CoupledCellGroup:
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    daisy_class: str = "default"
    drained: bool = False
    lower_boundary_case: str | None = None

    def iter_cells(self) -> Iterator[tuple[int, int]]:
        for row in range(self.row_start, self.row_end):
            for col in range(self.col_start, self.col_end):
                yield row, col


@dataclass(frozen=True)
class CellMappingInfo:
    row: int
    col: int
    daisy_class: str
    drained: bool
    lower_boundary_case: str | None
    group_index: int


class SpatialMapping:
    def __init__(
        self,
        groups: Iterable[CoupledCellGroup],
        cell_metadata_by_cell: (
            Mapping[tuple[int, int], Mapping[str, object]] | None
        ) = None,
    ):
        self.groups = tuple(groups)
        self._cell_lookup = self._build_cell_lookup(
            self.groups,
            cell_metadata_by_cell=cell_metadata_by_cell,
        )

    @staticmethod
    def _build_cell_lookup(
        groups: tuple[CoupledCellGroup, ...],
        cell_metadata_by_cell: (
            Mapping[tuple[int, int], Mapping[str, object]] | None
        ) = None,
    ) -> dict[tuple[int, int], CellMappingInfo]:
        lookup: dict[tuple[int, int], CellMappingInfo] = {}
        cell_overrides = {} if cell_metadata_by_cell is None else cell_metadata_by_cell

        for group_index, group in enumerate(groups):
            for row, col in group.iter_cells():
                cell_key = (row, col)
                if cell_key in lookup:
                    raise ValueError(
                        f"Cell {cell_key} is assigned by multiple coupling groups"
                    )

                cell_metadata = cell_overrides.get(cell_key, {})

                resolved_daisy_class = cell_metadata.get(
                    "daisy_class", group.daisy_class
                )
                if resolved_daisy_class is None:
                    resolved_daisy_class = group.daisy_class

                resolved_drained = cell_metadata.get("drained", group.drained)
                if resolved_drained is None:
                    resolved_drained = group.drained

                resolved_lower_boundary_case = cell_metadata.get(
                    "lower_boundary_case", group.lower_boundary_case
                )

                lookup[cell_key] = CellMappingInfo(
                    row=row,
                    col=col,
                    daisy_class=str(resolved_daisy_class),
                    drained=bool(resolved_drained),
                    lower_boundary_case=resolved_lower_boundary_case,
                    group_index=group_index,
                )

        unknown_cells = set(cell_overrides).difference(lookup)
        if unknown_cells:
            unknown_cell = min(unknown_cells)
            raise ValueError(
                f"Cell metadata override refers to an uncoupled cell {unknown_cell}"
            )

        return lookup

    @classmethod
    def from_block_slices(
        cls,
        block_slices: Iterable[tuple[int, int, int, int]],
        daisy_class: str = "default",
        drained: bool = False,
        lower_boundary_case: str | None = None,
        group_metadata_by_index: Mapping[int, Mapping[str, object]] | None = None,
        cell_metadata_by_cell: (
            Mapping[tuple[int, int], Mapping[str, object]] | None
        ) = None,
    ) -> SpatialMapping:
        metadata_lookup = (
            {} if group_metadata_by_index is None else group_metadata_by_index
        )

        def _resolve_group(
            group_index: int,
            row_start: int,
            row_end: int,
            col_start: int,
            col_end: int,
        ) -> CoupledCellGroup:
            group_metadata = metadata_lookup.get(group_index, {})

            resolved_daisy_class = group_metadata.get("daisy_class", daisy_class)
            if resolved_daisy_class is None:
                resolved_daisy_class = daisy_class

            resolved_drained = group_metadata.get("drained", drained)
            if resolved_drained is None:
                resolved_drained = drained

            resolved_lower_boundary_case = group_metadata.get(
                "lower_boundary_case", lower_boundary_case
            )

            return CoupledCellGroup(
                row_start=row_start,
                row_end=row_end,
                col_start=col_start,
                col_end=col_end,
                daisy_class=str(resolved_daisy_class),
                drained=bool(resolved_drained),
                lower_boundary_case=resolved_lower_boundary_case,
            )

        return cls(
            (
                _resolve_group(group_index, row_start, row_end, col_start, col_end)
                for group_index, (row_start, row_end, col_start, col_end) in enumerate(
                    block_slices
                )
            ),
            cell_metadata_by_cell=cell_metadata_by_cell,
        )

    def __len__(self) -> int:
        return len(self.groups)

    def iter_cell_mappings(self) -> Iterator[CellMappingInfo]:
        return iter(self._cell_lookup.values())

    def iter_drained_cell_mappings(self) -> Iterator[CellMappingInfo]:
        return (info for info in self._cell_lookup.values() if info.drained)

    def iter_groups(self, drained: bool | None = None) -> Iterator[CoupledCellGroup]:
        for group in self.groups:
            if drained is None or group.drained is drained:
                yield group

    def drained_groups(self) -> tuple[CoupledCellGroup, ...]:
        return tuple(self.iter_groups(drained=True))

    def coupled_cells(self) -> tuple[tuple[int, int], ...]:
        return tuple(self._cell_lookup.keys())

    def lookup(self, row: int, col: int) -> CellMappingInfo | None:
        return self._cell_lookup.get((row, col))

    def is_coupled(self, row: int, col: int) -> bool:
        return (row, col) in self._cell_lookup

    def is_drained(self, row: int, col: int) -> bool:
        info = self.lookup(row, col)
        return bool(info and info.drained)

    def daisy_source_for_cell(self, row: int, col: int) -> str | None:
        info = self.lookup(row, col)
        return None if info is None else info.daisy_class

    def lower_boundary_case_for_cell(self, row: int, col: int) -> str | None:
        info = self.lookup(row, col)
        return None if info is None else info.lower_boundary_case


def _expand_cell_metadata_blocks(
    block_slices: Iterable[tuple[int, int, int, int]],
    *,
    daisy_class: str | None = None,
    drained: bool | None = None,
    lower_boundary_case: str | None = None,
) -> dict[tuple[int, int], dict[str, object]]:
    metadata_template: dict[str, object] = {}
    if daisy_class is not None:
        metadata_template["daisy_class"] = daisy_class
    if drained is not None:
        metadata_template["drained"] = drained
    if lower_boundary_case is not None:
        metadata_template["lower_boundary_case"] = lower_boundary_case

    cell_metadata: dict[tuple[int, int], dict[str, object]] = {}
    for row_start, row_end, col_start, col_end in block_slices:
        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                cell_metadata[(row, col)] = dict(metadata_template)

    return cell_metadata


DEFAULT_GROUP_METADATA_BY_INDEX: dict[int, dict[str, object]] = {}

# Derived from `data/Cernici_060126_Test02_2/07_SZ/drain_map_Cernici_v1.shp`
# using majority cell-area overlap (>= 50%) against the coupled footprint.
DEFAULT_DRAINED_CELL_BLOCKS: tuple[tuple[int, int, int, int], ...] = (
    (85, 86, 66, 67),
    (85, 86, 95, 105),
    (86, 87, 91, 93),
    (86, 87, 94, 106),
    (87, 88, 95, 106),
    (87, 89, 87, 93),
    (88, 89, 64, 67),
    (88, 89, 72, 74),
    (88, 90, 96, 106),
    (89, 90, 62, 69),
    (89, 90, 71, 78),
    (89, 91, 86, 88),
    (90, 91, 59, 70),
    (90, 91, 71, 82),
    (90, 92, 96, 105),
    (91, 92, 56, 70),
    (91, 92, 71, 89),
    (92, 93, 56, 90),
    (92, 93, 94, 105),
    (93, 94, 55, 91),
    (93, 94, 92, 105),
    (94, 96, 56, 105),
    (96, 97, 57, 105),
    (97, 99, 58, 105),
    (99, 100, 59, 71),
    (99, 100, 74, 104),
    (100, 101, 61, 71),
    (100, 101, 75, 104),
    (101, 102, 63, 71),
    (101, 102, 75, 92),
    (102, 103, 65, 69),
    (102, 103, 74, 80),
    (103, 108, 72, 78),
)

DEFAULT_CELL_METADATA_BY_CELL = _expand_cell_metadata_blocks(
    DEFAULT_DRAINED_CELL_BLOCKS,
    drained=True,
    lower_boundary_case="sz_drain",
)


DEFAULT_SPATIAL_MAPPING = SpatialMapping.from_block_slices(
    legacy_blocks.blocks,
    group_metadata_by_index=DEFAULT_GROUP_METADATA_BY_INDEX,
    cell_metadata_by_cell=DEFAULT_CELL_METADATA_BY_CELL,
)
