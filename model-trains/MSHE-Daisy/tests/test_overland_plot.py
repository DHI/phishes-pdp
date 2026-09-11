import unittest
from datetime import datetime

import numpy as np
from src.plot_overland_coupling import (
    CrossRunTimeSelection,
    GridWindow,
    _mask_output_values,
    build_group_mask,
    compute_padded_window,
    resolve_shared_time_selectors,
    resolve_time_index,
    resolve_time_selectors,
    swap_groups_for_display,
)
from src.spatial_mapping import CoupledCellGroup


class TestOverlandPlotHelpers(unittest.TestCase):
    def test_build_group_mask_marks_coupled_cells(self):
        groups = (
            CoupledCellGroup(row_start=1, row_end=2, col_start=2, col_end=4),
            CoupledCellGroup(row_start=3, row_end=5, col_start=0, col_end=1),
        )

        mask = build_group_mask(groups, ny=6, nx=5)

        self.assertEqual(mask.shape, (6, 5))
        self.assertTrue(mask[1, 2])
        self.assertTrue(mask[1, 3])
        self.assertTrue(mask[3, 0])
        self.assertTrue(mask[4, 0])
        self.assertFalse(mask[0, 0])
        self.assertEqual(int(np.count_nonzero(mask)), 4)

    def test_compute_padded_window_clips_to_domain(self):
        groups = (
            CoupledCellGroup(row_start=1, row_end=2, col_start=2, col_end=4),
            CoupledCellGroup(row_start=3, row_end=5, col_start=0, col_end=1),
        )

        window = compute_padded_window(groups, ny=5, nx=4, padding_cells=2)

        self.assertEqual(
            window,
            GridWindow(row_start=0, row_end=5, col_start=0, col_end=4),
        )

    def test_swap_groups_for_display_swaps_row_and_col_ranges(self):
        groups = (
            CoupledCellGroup(row_start=10, row_end=12, col_start=20, col_end=23),
            CoupledCellGroup(row_start=14, row_end=15, col_start=25, col_end=27),
        )

        swapped = swap_groups_for_display(groups)

        self.assertEqual(
            swapped,
            (
                CoupledCellGroup(
                    row_start=20,
                    row_end=23,
                    col_start=10,
                    col_end=12,
                ),
                CoupledCellGroup(
                    row_start=25,
                    row_end=27,
                    col_start=14,
                    col_end=15,
                ),
            ),
        )

    def test_resolve_time_index_supports_negative_values(self):
        self.assertEqual(resolve_time_index(4, -1), 3)
        self.assertEqual(resolve_time_index(4, -4), 0)
        self.assertEqual(resolve_time_index(4, 2), 2)

        with self.assertRaises(IndexError):
            resolve_time_index(4, 4)

    def test_resolve_time_selectors_accepts_indices_and_iso_dates(self):
        times = (
            datetime(2020, 8, 1, 0, 0, 0),
            datetime(2020, 8, 2, 0, 0, 0),
            datetime(2020, 8, 3, 0, 0, 0),
            datetime(2020, 8, 4, 0, 0, 0),
        )

        resolved = resolve_time_selectors(
            times, ["2020-08-02", "-1", "2020-08-01 00:00:00"]
        )

        self.assertEqual(resolved, (1, 3, 0))

    def test_resolve_time_selectors_raises_for_unknown_label(self):
        times = (
            datetime(2020, 8, 1, 0, 0, 0),
            datetime(2020, 8, 2, 0, 0, 0),
        )

        with self.assertRaises(ValueError):
            resolve_time_selectors(times, ["2020-08-03"])

    def test_mask_output_values_masks_zero_only_arrays(self):
        masked = _mask_output_values(np.zeros((2, 3), dtype=float))

        self.assertEqual(int(np.ma.count(masked)), 0)

    def test_mask_output_values_masks_nonpositive_when_field_is_positive_only(self):
        data = np.array([[0.0, 1.0], [2.0, 0.0]], dtype=float)

        masked = _mask_output_values(data)

        self.assertTrue(bool(masked.mask[0, 0]))
        self.assertTrue(bool(masked.mask[1, 1]))
        self.assertFalse(bool(masked.mask[0, 1]))
        self.assertFalse(bool(masked.mask[1, 0]))

    def test_resolve_shared_time_selectors_matches_same_dates_across_runs(self):
        primary_times = (
            datetime(2020, 8, 1, 0, 0, 0),
            datetime(2020, 8, 2, 0, 0, 0),
            datetime(2020, 8, 3, 0, 0, 0),
            datetime(2020, 8, 4, 0, 0, 0),
        )
        secondary_times = (
            datetime(2019, 1, 1, 0, 0, 0),
            datetime(2020, 8, 1, 0, 0, 0),
            datetime(2020, 8, 2, 0, 0, 0),
            datetime(2020, 8, 3, 0, 0, 0),
            datetime(2020, 8, 4, 0, 0, 0),
            datetime(2020, 9, 1, 0, 0, 0),
        )

        resolved = resolve_shared_time_selectors(
            primary_times, secondary_times, ["-1", "2020-08-02"]
        )

        self.assertEqual(
            resolved,
            CrossRunTimeSelection(
                primary_indices=(3, 1),
                secondary_indices=(4, 2),
                time_labels=("2020-08-04 00:00:00", "2020-08-02 00:00:00"),
            ),
        )

    def test_resolve_shared_time_selectors_raises_when_secondary_lacks_date(self):
        primary_times = (
            datetime(2020, 8, 1, 0, 0, 0),
            datetime(2020, 8, 2, 0, 0, 0),
        )
        secondary_times = (datetime(2020, 8, 1, 0, 0, 0),)

        with self.assertRaises(ValueError):
            resolve_shared_time_selectors(
                primary_times, secondary_times, ["2020-08-02"]
            )


if __name__ == "__main__":
    unittest.main()
