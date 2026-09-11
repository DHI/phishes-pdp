import tempfile
import textwrap
import unittest
from pathlib import Path

import pandas as pd
from src.coupling import (
    apply_bounded_delta,
    apply_bounded_layer_shift,
    apply_effective_uz_storage_corrections,
    apply_groupwise_net_leakage_flux,
    apply_nonnegative_sink,
    assign_uniform_scalar_to_cells,
    assign_uniform_scalar_to_groups,
    depth_to_volume_m3,
    derive_conservative_theta_bounds,
    interval_depth_to_cell_transfer,
    interval_depth_to_rate_m_per_s,
    net_exchange_to_delta_theta,
    rate_to_flow_m3_per_s,
    resolve_mshe_timestep_hours,
    resolve_mshe_timestep_seconds,
    shift_layer_values,
)
from src.diagnostics import (
    CouplingDiagnosticRecord,
    VolumeClosureTimeseriesAggregator,
    derive_diagnostics_plot_dir,
    derive_diagnostics_timeseries_path,
    diagnostics_to_dataframe,
    summarize_mass_balance,
    summarize_volume_closure,
    summarize_volume_closure_timeseries,
    write_diagnostics_summary_csv,
    write_diagnostics_timeseries_csv,
)
from src.diagnostics_plots import write_diagnostics_plots
from src.setup_overrides import derive_effective_uz_thickness_from_setup
from src.spatial_mapping import CoupledCellGroup, SpatialMapping


class FakeWritableGrid:
    def __init__(self, row_count: int, col_count: int, fill_value: float = 0.0):
        self.values = [
            [float(fill_value) for _ in range(col_count)] for _ in range(row_count)
        ]

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        row_key, col_key = key
        if isinstance(row_key, int) and isinstance(col_key, int):
            self.values[row_key][col_key] = float(value)
            return

        if not isinstance(row_key, slice) or not isinstance(col_key, slice):
            raise TypeError("FakeWritableGrid only supports slice-based assignment")

        row_range = range(*row_key.indices(len(self.values)))
        col_range = range(*col_key.indices(len(self.values[0])))
        try:
            scalar_value = float(value)
        except (TypeError, ValueError):
            scalar_value = None

        if scalar_value is not None:
            for row_index in row_range:
                for col_index in col_range:
                    self.values[row_index][col_index] = scalar_value
            return

        matrix_values = list(value)
        if len(matrix_values) != len(row_range):
            raise ValueError("Assigned matrix row count does not match target slice")

        for row_index, row_values in zip(row_range, matrix_values):
            row_values = list(row_values)
            if len(row_values) != len(col_range):
                raise ValueError(
                    "Assigned matrix column count does not match target slice"
                )
            for col_index, cell_value in zip(col_range, row_values):
                self.values[row_index][col_index] = float(cell_value)


class FakeLayeredGrid:
    def __init__(
        self,
        row_count: int,
        col_count: int,
        fill_values: tuple[float, ...] = (0.0, 0.0),
    ):
        self.values = [
            [tuple(float(value) for value in fill_values) for _ in range(col_count)]
            for _ in range(row_count)
        ]

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        row_key, col_key = key
        if not isinstance(row_key, int) or not isinstance(col_key, int):
            raise TypeError("FakeLayeredGrid only supports cell assignment")

        self.values[row_key][col_key] = tuple(float(item) for item in value)


class TestCouplingHelpers(unittest.TestCase):
    def test_interval_depth_to_rate_uses_actual_interval_seconds(self):
        interval_seconds = 31 * 24 * 60 * 60
        rate = interval_depth_to_rate_m_per_s(31.0, interval_seconds)

        self.assertAlmostEqual(rate, 0.031 / interval_seconds)
        self.assertAlmostEqual(rate_to_flow_m3_per_s(rate, 100.0), 100.0 * rate)

    def test_nonnegative_sink_clips_and_tracks_signed_residual(self):
        result = apply_nonnegative_sink(current_value=0.005, sink_amount=0.008)

        self.assertAlmostEqual(result.bounded_value, 0.0)
        self.assertAlmostEqual(result.applied_delta, -0.005)
        self.assertAlmostEqual(result.residual, -0.003)

    def test_bounded_delta_clips_upper_bound(self):
        result = apply_bounded_delta(
            current_value=0.20, delta=0.10, lower_bound=0.0, upper_bound=0.25
        )

        self.assertAlmostEqual(result.bounded_value, 0.25)
        self.assertAlmostEqual(result.applied_delta, 0.05)
        self.assertAlmostEqual(result.residual, 0.05)

    def test_net_exchange_to_delta_theta(self):
        delta_theta = net_exchange_to_delta_theta(1.0e-7, 24 * 60 * 60, 10.0)
        self.assertAlmostEqual(delta_theta, 0.000864)

    def test_interval_depth_to_cell_transfer(self):
        transfer = interval_depth_to_cell_transfer(
            depth_mm=12.5,
            interval_seconds=25 * 60 * 60,
            dt_seconds=0.5 * 60 * 60,
            cell_area_m2=256.0,
        )

        self.assertAlmostEqual(transfer.rate_m_per_s, 0.0125 / (25 * 60 * 60))
        self.assertAlmostEqual(
            transfer.flow_m3_per_s,
            transfer.rate_m_per_s * 256.0,
        )
        self.assertAlmostEqual(
            transfer.step_depth_m,
            transfer.rate_m_per_s * (0.5 * 60 * 60),
        )
        self.assertAlmostEqual(
            transfer.step_volume_m3,
            transfer.step_depth_m * 256.0,
        )

    def test_resolve_mshe_timestep_hours_accepts_scalar(self):
        self.assertAlmostEqual(resolve_mshe_timestep_hours(0.25), 0.25)
        self.assertAlmostEqual(resolve_mshe_timestep_seconds(0.25), 900.0)

    def test_resolve_mshe_timestep_hours_uses_smallest_tuple_value(self):
        self.assertAlmostEqual(
            resolve_mshe_timestep_hours((0.2, 0.15, 0.3)),
            0.15,
        )
        self.assertAlmostEqual(
            resolve_mshe_timestep_seconds((0.2, 0.15, 0.3)),
            540.0,
        )

    def test_runoff_group_assignment_only_updates_coupled_cells(self):
        grid = FakeWritableGrid(row_count=5, col_count=5, fill_value=0.0)
        groups = (
            CoupledCellGroup(row_start=1, row_end=3, col_start=2, col_end=4),
            CoupledCellGroup(row_start=4, row_end=5, col_start=0, col_end=1),
        )

        assign_uniform_scalar_to_groups(grid, groups, 0.125)

        coupled_cells = {
            (1, 2),
            (1, 3),
            (2, 2),
            (2, 3),
            (4, 0),
        }

        for row_index in range(5):
            for col_index in range(5):
                expected = 0.125 if (row_index, col_index) in coupled_cells else 0.0
                self.assertAlmostEqual(grid[row_index][col_index], expected)

    def test_cell_assignment_only_updates_selected_cells(self):
        grid = FakeWritableGrid(row_count=4, col_count=4, fill_value=0.0)

        assign_uniform_scalar_to_cells(grid, [(0, 1), (2, 3), (3, 0)], 0.375)

        selected_cells = {(0, 1), (2, 3), (3, 0)}
        for row_index in range(4):
            for col_index in range(4):
                expected = 0.375 if (row_index, col_index) in selected_cells else 0.0
                self.assertAlmostEqual(grid[row_index][col_index], expected)

    def test_groupwise_net_leakage_flux_uses_group_class_and_native_grid(self):
        grid = FakeWritableGrid(row_count=4, col_count=5, fill_value=-999.0)
        native_exchange_grid = [
            [0.0, 0.0, 0.10, 0.20, 0.0],
            [0.0, 0.0, 0.30, 0.40, 0.0],
            [0.05, 0.15, 0.0, 0.0, 0.0],
            [0.25, 0.35, 0.0, 0.0, 0.0],
        ]
        groups = (
            CoupledCellGroup(
                row_start=0,
                row_end=2,
                col_start=2,
                col_end=4,
                daisy_class="class-a",
            ),
            CoupledCellGroup(
                row_start=2,
                row_end=4,
                col_start=0,
                col_end=2,
                daisy_class="class-b",
            ),
        )

        apply_groupwise_net_leakage_flux(
            grid,
            groups,
            {"class-a": 1.0, "class-b": 2.0},
            native_exchange_grid,
        )

        expected_coupled = {
            (0, 2): 0.90,
            (0, 3): 0.80,
            (1, 2): 0.70,
            (1, 3): 0.60,
            (2, 0): 1.95,
            (2, 1): 1.85,
            (3, 0): 1.75,
            (3, 1): 1.65,
        }

        for row_index in range(4):
            for col_index in range(5):
                expected = expected_coupled.get((row_index, col_index), -999.0)
                self.assertAlmostEqual(grid[row_index][col_index], expected)

    def test_groupwise_net_leakage_flux_requires_rate_for_each_class(self):
        grid = FakeWritableGrid(row_count=2, col_count=2, fill_value=0.0)
        groups = (
            CoupledCellGroup(
                row_start=0,
                row_end=1,
                col_start=0,
                col_end=1,
                daisy_class="class-a",
            ),
            CoupledCellGroup(
                row_start=1,
                row_end=2,
                col_start=1,
                col_end=2,
                daisy_class="class-b",
            ),
        )

        with self.assertRaises(KeyError):
            apply_groupwise_net_leakage_flux(
                grid,
                groups,
                {"class-a": 1.0},
                [[0.0, 0.0], [0.0, 0.0]],
            )

    def test_runoff_transfer_matches_storage_change_without_clipping(self):
        dt_seconds = 6 * 60 * 60
        cell_area_m2 = 256.0
        transfer = interval_depth_to_cell_transfer(
            depth_mm=18.0,
            interval_seconds=30 * 24 * 60 * 60,
            dt_seconds=dt_seconds,
            cell_area_m2=cell_area_m2,
        )

        bookkeeping_result = apply_nonnegative_sink(
            current_value=0.50,
            sink_amount=transfer.step_depth_m,
        )

        self.assertAlmostEqual(-bookkeeping_result.applied_delta, transfer.step_depth_m)
        self.assertAlmostEqual(bookkeeping_result.residual, 0.0)
        self.assertAlmostEqual(
            transfer.flow_m3_per_s * dt_seconds,
            transfer.step_volume_m3,
        )
        self.assertAlmostEqual(
            depth_to_volume_m3(-bookkeeping_result.applied_delta, cell_area_m2),
            transfer.step_volume_m3,
        )

    def test_runoff_storage_clipping_preserves_requested_sink_magnitude(self):
        dt_seconds = 12 * 60 * 60
        cell_area_m2 = 256.0
        transfer = interval_depth_to_cell_transfer(
            depth_mm=25.0,
            interval_seconds=30 * 24 * 60 * 60,
            dt_seconds=dt_seconds,
            cell_area_m2=cell_area_m2,
        )

        bookkeeping_result = apply_nonnegative_sink(
            current_value=0.0001,
            sink_amount=transfer.step_depth_m,
        )

        self.assertAlmostEqual(bookkeeping_result.bounded_value, 0.0)
        self.assertAlmostEqual(
            (-bookkeeping_result.applied_delta) + abs(bookkeeping_result.residual),
            transfer.step_depth_m,
        )
        self.assertAlmostEqual(
            depth_to_volume_m3(-bookkeeping_result.applied_delta, cell_area_m2)
            + depth_to_volume_m3(abs(bookkeeping_result.residual), cell_area_m2),
            transfer.step_volume_m3,
        )

    def test_conservative_theta_bounds_use_most_restrictive_values(self):
        theta_residual, theta_saturated = derive_conservative_theta_bounds(
            [0.03, 0.08, 0.05],
            [0.46, 0.42, 0.48],
        )

        self.assertAlmostEqual(theta_residual, 0.08)
        self.assertAlmostEqual(theta_saturated, 0.42)

    def test_shift_layer_values_applies_signed_delta_uniformly(self):
        shifted = shift_layer_values([0.40, 0.35, 0.30], -0.01)

        self.assertEqual(len(shifted), 3)
        self.assertAlmostEqual(shifted[0], 0.39)
        self.assertAlmostEqual(shifted[1], 0.34)
        self.assertAlmostEqual(shifted[2], 0.29)

    def test_shift_layer_values_converts_values_to_float(self):
        shifted = shift_layer_values((1, 2, 3), 0.5)

        self.assertEqual(shifted, [1.5, 2.5, 3.5])

    def test_bounded_layer_shift_without_clipping(self):
        result = apply_bounded_layer_shift([0.30, 0.40], -0.05, 0.10, 0.50)

        self.assertEqual(len(result.bounded_values), 2)
        self.assertAlmostEqual(result.bounded_values[0], 0.25)
        self.assertAlmostEqual(result.bounded_values[1], 0.35)
        self.assertEqual(result.clipped_layer_count, 0)
        self.assertAlmostEqual(result.previous_mean, 0.35)
        self.assertAlmostEqual(result.requested_after_mean, 0.30)
        self.assertAlmostEqual(result.bounded_mean, 0.30)
        self.assertAlmostEqual(result.applied_mean_delta, -0.05)
        self.assertAlmostEqual(result.residual_mean_delta, 0.0)

    def test_bounded_layer_shift_tracks_clipping_residual(self):
        result = apply_bounded_layer_shift([0.03, 0.06], -0.04, 0.02, 0.50)

        self.assertEqual(len(result.bounded_values), 2)
        self.assertAlmostEqual(result.bounded_values[0], 0.02)
        self.assertAlmostEqual(result.bounded_values[1], 0.02)
        self.assertEqual(result.clipped_layer_count, 1)
        self.assertAlmostEqual(result.previous_mean, 0.045)
        self.assertAlmostEqual(result.requested_after_mean, 0.005)
        self.assertAlmostEqual(result.bounded_mean, 0.02)
        self.assertAlmostEqual(result.applied_mean_delta, -0.025)
        self.assertAlmostEqual(result.residual_mean_delta, -0.015)

    def test_bounded_layer_shift_does_not_snap_existing_upper_violation(self):
        result = apply_bounded_layer_shift([0.45], -0.01, 0.01, 0.38)

        self.assertAlmostEqual(result.bounded_values[0], 0.44)
        self.assertEqual(result.clipped_layer_count, 0)
        self.assertAlmostEqual(result.applied_mean_delta, -0.01)
        self.assertAlmostEqual(result.residual_mean_delta, 0.0)

    def test_effective_uz_storage_corrections_shift_layers_and_report_effective_state(
        self,
    ):
        dataset = FakeLayeredGrid(row_count=1, col_count=2, fill_values=(0.0, 0.0))
        previous_grid = [[(0.30, 0.40), (0.25, 0.45)]]

        updated_dataset, bookkeeping_results = apply_effective_uz_storage_corrections(
            dataset,
            previous_grid,
            {(0, 0): 0.05, (0, 1): -0.02},
            lower_bound=0.10,
            upper_bound=0.50,
        )

        sink_result = bookkeeping_results[(0, 0)]
        source_result = bookkeeping_results[(0, 1)]

        self.assertAlmostEqual(updated_dataset[0][0][0], 0.25)
        self.assertAlmostEqual(updated_dataset[0][0][1], 0.35)
        self.assertAlmostEqual(updated_dataset[0][1][0], 0.27)
        self.assertAlmostEqual(updated_dataset[0][1][1], 0.47)
        self.assertAlmostEqual(sink_result.requested_layer_delta_theta, -0.05)
        self.assertAlmostEqual(sink_result.effective_theta_before, 0.35)
        self.assertAlmostEqual(sink_result.effective_theta_requested_after, 0.30)
        self.assertAlmostEqual(sink_result.effective_theta_after, 0.30)
        self.assertAlmostEqual(
            sink_result.applied_storage_correction_delta_theta,
            0.05,
        )
        self.assertAlmostEqual(
            sink_result.residual_storage_correction_delta_theta,
            0.0,
        )
        self.assertAlmostEqual(source_result.requested_layer_delta_theta, 0.02)
        self.assertAlmostEqual(
            source_result.applied_storage_correction_delta_theta,
            -0.02,
        )

    def test_effective_uz_storage_corrections_track_clipped_residual(self):
        dataset = FakeLayeredGrid(row_count=1, col_count=1, fill_values=(0.0, 0.0))
        previous_grid = [[(0.03, 0.06)]]

        _, bookkeeping_results = apply_effective_uz_storage_corrections(
            dataset,
            previous_grid,
            {(0, 0): 0.04},
            lower_bound=0.02,
            upper_bound=0.50,
        )

        result = bookkeeping_results[(0, 0)]

        self.assertEqual(result.bounded_values, (0.02, 0.02))
        self.assertEqual(result.clipped_layer_count, 1)
        self.assertAlmostEqual(result.effective_theta_before, 0.045)
        self.assertAlmostEqual(result.effective_theta_requested_after, 0.005)
        self.assertAlmostEqual(result.effective_theta_after, 0.02)
        self.assertAlmostEqual(
            result.applied_storage_correction_delta_theta,
            0.025,
        )
        self.assertAlmostEqual(
            result.residual_storage_correction_delta_theta,
            0.015,
        )


class TestSpatialMapping(unittest.TestCase):
    def test_spatial_mapping_answers_cell_queries(self):
        mapping = SpatialMapping(
            [
                CoupledCellGroup(
                    row_start=1,
                    row_end=3,
                    col_start=2,
                    col_end=4,
                    daisy_class="agriculture-a",
                    drained=True,
                    lower_boundary_case="drain",
                )
            ]
        )

        self.assertTrue(mapping.is_coupled(1, 2))
        self.assertTrue(mapping.is_drained(2, 3))
        self.assertEqual(mapping.daisy_source_for_cell(2, 3), "agriculture-a")
        self.assertEqual(mapping.lower_boundary_case_for_cell(2, 3), "drain")
        self.assertIsNone(mapping.lookup(9, 9))

    def test_spatial_mapping_exposes_drained_group_and_cell_iterators(self):
        mapping = SpatialMapping(
            [
                CoupledCellGroup(
                    row_start=0,
                    row_end=1,
                    col_start=0,
                    col_end=2,
                    daisy_class="undrained-a",
                    drained=False,
                ),
                CoupledCellGroup(
                    row_start=1,
                    row_end=3,
                    col_start=1,
                    col_end=2,
                    daisy_class="drained-b",
                    drained=True,
                    lower_boundary_case="matrix_drain",
                ),
            ]
        )

        drained_groups = mapping.drained_groups()
        drained_cells = {
            (info.row, info.col) for info in mapping.iter_drained_cell_mappings()
        }

        self.assertEqual(len(drained_groups), 1)
        self.assertEqual(drained_groups[0].daisy_class, "drained-b")
        self.assertEqual(drained_cells, {(1, 1), (2, 1)})

    def test_from_block_slices_supports_per_group_metadata_overrides(self):
        mapping = SpatialMapping.from_block_slices(
            [(0, 1, 0, 1), (1, 2, 1, 2)],
            daisy_class="default-class",
            drained=False,
            group_metadata_by_index={
                1: {
                    "daisy_class": "drained-class",
                    "drained": True,
                    "lower_boundary_case": "tile_drain",
                }
            },
        )

        self.assertFalse(mapping.is_drained(0, 0))
        self.assertEqual(mapping.daisy_source_for_cell(0, 0), "default-class")
        self.assertTrue(mapping.is_drained(1, 1))
        self.assertEqual(mapping.daisy_source_for_cell(1, 1), "drained-class")
        self.assertEqual(mapping.lower_boundary_case_for_cell(1, 1), "tile_drain")

    def test_from_block_slices_supports_partial_cell_metadata_overrides(self):
        mapping = SpatialMapping.from_block_slices(
            [(0, 1, 0, 3)],
            drained=False,
            cell_metadata_by_cell={
                (0, 1): {"drained": True, "lower_boundary_case": "sz_drain"},
                (0, 2): {"daisy_class": "drained-class", "drained": True},
            },
        )

        drained_cells = {
            (info.row, info.col) for info in mapping.iter_drained_cell_mappings()
        }

        self.assertFalse(mapping.is_drained(0, 0))
        self.assertTrue(mapping.is_drained(0, 1))
        self.assertTrue(mapping.is_drained(0, 2))
        self.assertEqual(mapping.lower_boundary_case_for_cell(0, 1), "sz_drain")
        self.assertEqual(mapping.daisy_source_for_cell(0, 2), "drained-class")
        self.assertEqual(drained_cells, {(0, 1), (0, 2)})

    def test_cell_metadata_overrides_must_target_coupled_cells(self):
        with self.assertRaises(ValueError):
            SpatialMapping.from_block_slices(
                [(0, 1, 0, 1)],
                cell_metadata_by_cell={(5, 5): {"drained": True}},
            )


class TestDiagnostics(unittest.TestCase):
    def test_diagnostics_schema_and_summary(self):
        records = [
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 00:00"),
                variable_name="runoff",
                row=1,
                col=2,
                daisy_source_id="agriculture-a",
                source_depth_mm=2.5,
                interval_seconds=31 * 24 * 60 * 60,
                target_value=1.2,
                storage_correction=1.2,
                residual=0.0,
                sign_convention="positive_out_of_daisy",
                metadata={"note": "unit-test"},
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-03-01 00:00"),
                variable_name="runoff",
                row=1,
                col=3,
                daisy_source_id="agriculture-a",
                source_depth_mm=3.5,
                interval_seconds=29 * 24 * 60 * 60,
                target_value=1.8,
                storage_correction=1.8,
                residual=0.1,
            ),
        ]

        df = diagnostics_to_dataframe(records)
        self.assertIn("metadata", df.columns)
        self.assertEqual(len(df), 2)

        summary = summarize_mass_balance(records)
        runoff_row = summary.loc[summary["variable_name"] == "runoff"].iloc[0]
        self.assertAlmostEqual(runoff_row["source_depth_mm"], 6.0)
        self.assertAlmostEqual(runoff_row["target_value"], 3.0)
        self.assertAlmostEqual(runoff_row["storage_correction"], 3.0)
        self.assertAlmostEqual(runoff_row["residual"], 0.1)

    def test_volume_closure_summary_uses_metadata_volume_fields(self):
        records = [
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 00:00"),
                variable_name="runoff",
                row=1,
                col=2,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 1.2,
                    "target_step_volume_m3": 1.2,
                    "storage_correction_volume_m3": 1.0,
                    "residual_volume_m3": 0.2,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 01:00"),
                variable_name="runoff",
                row=1,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.8,
                    "target_step_volume_m3": 0.8,
                    "storage_correction_volume_m3": 0.6,
                    "residual_volume_m3": 0.19,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 02:00"),
                variable_name="matrix_percolation",
                row=2,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": -0.5,
                    "target_step_volume_m3": -0.5,
                    "storage_correction_volume_m3": -0.45,
                    "residual_volume_m3": -0.05,
                },
            ),
        ]

        summary = summarize_volume_closure(records, closure_tolerance_m3=1.0e-15)

        runoff_row = summary.loc[summary["variable_name"] == "runoff"].iloc[0]
        total_row = summary.loc[summary["variable_name"] == "TOTAL"].iloc[0]

        self.assertEqual(int(runoff_row["row_count"]), 2)
        self.assertAlmostEqual(runoff_row["requested_step_volume_m3"], 2.0)
        self.assertAlmostEqual(runoff_row["target_step_volume_m3"], 2.0)
        self.assertAlmostEqual(runoff_row["storage_correction_volume_m3"], 1.6)
        self.assertAlmostEqual(runoff_row["residual_volume_m3"], 0.39)
        self.assertEqual(int(runoff_row["rows_with_nonzero_residual"]), 2)
        self.assertAlmostEqual(runoff_row["requested_target_closure_m3"], 0.0)
        self.assertAlmostEqual(runoff_row["requested_storage_closure_m3"], 0.01)
        self.assertAlmostEqual(runoff_row["target_storage_closure_m3"], 0.01)
        self.assertAlmostEqual(
            runoff_row["max_abs_target_storage_closure_m3"],
            0.01,
        )
        self.assertEqual(int(runoff_row["target_storage_rows_over_tolerance"]), 1)

        self.assertEqual(int(total_row["row_count"]), 3)
        self.assertAlmostEqual(total_row["requested_step_volume_m3"], 1.5)
        self.assertAlmostEqual(total_row["target_storage_closure_m3"], 0.01)
        self.assertEqual(int(total_row["target_storage_rows_over_tolerance"]), 1)

    def test_volume_closure_timeseries_tracks_effective_state_and_bounds(self):
        timestamp = pd.Timestamp("2020-02-01 00:00")
        records = [
            CouplingDiagnosticRecord(
                timestamp=timestamp,
                variable_name="matrix_percolation",
                row=1,
                col=2,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.50,
                    "target_step_volume_m3": 0.50,
                    "storage_correction_volume_m3": 0.40,
                    "residual_volume_m3": 0.10,
                    "bounds_applied": True,
                    "effective_uz_theta_before": 0.30,
                    "effective_uz_theta_requested_after": 0.28,
                    "effective_uz_theta_after": 0.29,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=timestamp,
                variable_name="matrix_percolation",
                row=1,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.25,
                    "target_step_volume_m3": 0.25,
                    "storage_correction_volume_m3": 0.20,
                    "residual_volume_m3": 0.05,
                    "bounds_applied": False,
                    "effective_uz_theta_before": 0.35,
                    "effective_uz_theta_requested_after": 0.33,
                    "effective_uz_theta_after": 0.34,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 01:00"),
                variable_name="runoff",
                row=2,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 1.20,
                    "target_step_volume_m3": 1.20,
                    "storage_correction_volume_m3": 1.10,
                    "residual_volume_m3": 0.10,
                },
            ),
        ]

        timeseries = summarize_volume_closure_timeseries(records)

        matrix_row = timeseries.loc[
            timeseries["variable_name"] == "matrix_percolation"
        ].iloc[0]
        runoff_row = timeseries.loc[timeseries["variable_name"] == "runoff"].iloc[0]

        self.assertEqual(int(matrix_row["row_count"]), 2)
        self.assertAlmostEqual(matrix_row["requested_step_volume_m3"], 0.75)
        self.assertAlmostEqual(matrix_row["target_storage_closure_m3"], 0.0)
        self.assertEqual(int(matrix_row["bounds_applied_rows"]), 1)
        self.assertEqual(int(matrix_row["rows_with_nonzero_residual"]), 2)
        self.assertAlmostEqual(matrix_row["mean_effective_uz_theta_before"], 0.325)
        self.assertAlmostEqual(
            matrix_row["mean_effective_uz_theta_requested_after"],
            0.305,
        )
        self.assertAlmostEqual(matrix_row["mean_effective_uz_theta_after"], 0.315)
        self.assertEqual(int(runoff_row["row_count"]), 1)
        self.assertTrue(pd.isna(runoff_row["mean_effective_uz_theta_before"]))

    def test_streaming_volume_closure_aggregator_matches_batch_outputs(self):
        timestamp = pd.Timestamp("2020-02-01 00:00")
        records = [
            CouplingDiagnosticRecord(
                timestamp=timestamp,
                variable_name="matrix_percolation",
                row=1,
                col=2,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.50,
                    "target_step_volume_m3": 0.50,
                    "storage_correction_volume_m3": 0.40,
                    "residual_volume_m3": 0.10,
                    "bounds_applied": True,
                    "effective_uz_theta_before": 0.30,
                    "effective_uz_theta_requested_after": 0.28,
                    "effective_uz_theta_after": 0.29,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=timestamp,
                variable_name="matrix_percolation",
                row=1,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.25,
                    "target_step_volume_m3": 0.25,
                    "storage_correction_volume_m3": 0.20,
                    "residual_volume_m3": 0.05,
                    "bounds_applied": False,
                    "effective_uz_theta_before": 0.35,
                    "effective_uz_theta_requested_after": 0.33,
                    "effective_uz_theta_after": 0.34,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 01:00"),
                variable_name="runoff",
                row=2,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 1.20,
                    "target_step_volume_m3": 1.20,
                    "storage_correction_volume_m3": 1.10,
                    "residual_volume_m3": 0.10,
                },
            ),
        ]

        aggregator = VolumeClosureTimeseriesAggregator()
        aggregator.extend(records)

        expected_timeseries = summarize_volume_closure_timeseries(records)
        expected_summary = summarize_volume_closure(records)

        pd.testing.assert_frame_equal(
            aggregator.to_dataframe().reset_index(drop=True),
            expected_timeseries.reset_index(drop=True),
            check_dtype=False,
        )
        pd.testing.assert_frame_equal(
            aggregator.summarize().reset_index(drop=True),
            expected_summary.reset_index(drop=True),
            check_dtype=False,
        )

    def test_summary_writer_accepts_preaggregated_timeseries_dataframe(self):
        records = [
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 00:00"),
                variable_name="runoff",
                row=1,
                col=2,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 1.20,
                    "target_step_volume_m3": 1.20,
                    "storage_correction_volume_m3": 1.10,
                    "residual_volume_m3": 0.10,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 01:00"),
                variable_name="runoff",
                row=1,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.80,
                    "target_step_volume_m3": 0.80,
                    "storage_correction_volume_m3": 0.75,
                    "residual_volume_m3": 0.05,
                },
            ),
        ]

        timeseries = summarize_volume_closure_timeseries(records)

        with tempfile.TemporaryDirectory() as temp_dir_name:
            diagnostics_output_path = Path(temp_dir_name) / "diagnostics.csv"
            summary_path = write_diagnostics_summary_csv(
                timeseries,
                diagnostics_output_path,
            )
            summary_df = pd.read_csv(summary_path)

            runoff_row = summary_df.loc[summary_df["variable_name"] == "runoff"].iloc[0]
            self.assertAlmostEqual(runoff_row["requested_step_volume_m3"], 2.0)
            self.assertAlmostEqual(runoff_row["target_storage_closure_m3"], 0.0)

    def test_diagnostics_plot_bundle_accepts_preaggregated_timeseries(self):
        records = [
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 00:00"),
                variable_name="matrix_percolation",
                row=1,
                col=2,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.50,
                    "target_step_volume_m3": 0.50,
                    "storage_correction_volume_m3": 0.40,
                    "residual_volume_m3": 0.10,
                    "bounds_applied": True,
                    "effective_uz_theta_before": 0.30,
                    "effective_uz_theta_requested_after": 0.28,
                    "effective_uz_theta_after": 0.29,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 01:00"),
                variable_name="runoff",
                row=2,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 1.20,
                    "target_step_volume_m3": 1.20,
                    "storage_correction_volume_m3": 1.10,
                    "residual_volume_m3": 0.10,
                },
            ),
        ]

        timeseries = summarize_volume_closure_timeseries(records)

        with tempfile.TemporaryDirectory() as temp_dir_name:
            diagnostics_output_path = Path(temp_dir_name) / "diagnostics.csv"
            plot_paths = write_diagnostics_plots(timeseries, diagnostics_output_path)

            self.assertGreaterEqual(len(plot_paths), 2)
            for plot_path in plot_paths:
                self.assertTrue(plot_path.exists())
                self.assertGreater(plot_path.stat().st_size, 0)

    def test_diagnostics_plot_bundle_writes_expected_artifacts(self):
        records = [
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 00:00"),
                variable_name="matrix_percolation",
                row=1,
                col=2,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.50,
                    "target_step_volume_m3": 0.50,
                    "storage_correction_volume_m3": 0.40,
                    "residual_volume_m3": 0.10,
                    "bounds_applied": True,
                    "effective_uz_theta_before": 0.30,
                    "effective_uz_theta_requested_after": 0.28,
                    "effective_uz_theta_after": 0.29,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 01:00"),
                variable_name="matrix_percolation",
                row=1,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 0.25,
                    "target_step_volume_m3": 0.25,
                    "storage_correction_volume_m3": 0.20,
                    "residual_volume_m3": 0.05,
                    "bounds_applied": False,
                    "effective_uz_theta_before": 0.35,
                    "effective_uz_theta_requested_after": 0.33,
                    "effective_uz_theta_after": 0.34,
                },
            ),
            CouplingDiagnosticRecord(
                timestamp=pd.Timestamp("2020-02-01 00:00"),
                variable_name="runoff",
                row=2,
                col=3,
                daisy_source_id="agriculture-a",
                metadata={
                    "requested_step_volume_m3": 1.20,
                    "target_step_volume_m3": 1.20,
                    "storage_correction_volume_m3": 1.10,
                    "residual_volume_m3": 0.10,
                },
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir_name:
            diagnostics_output_path = Path(temp_dir_name) / "diagnostics.csv"
            timeseries_path = write_diagnostics_timeseries_csv(
                records, diagnostics_output_path
            )
            plot_dir = derive_diagnostics_plot_dir(diagnostics_output_path)
            plot_paths = write_diagnostics_plots(records, diagnostics_output_path)

            self.assertEqual(
                timeseries_path,
                derive_diagnostics_timeseries_path(diagnostics_output_path),
            )
            self.assertTrue(timeseries_path.exists())
            self.assertTrue(plot_dir.exists())
            self.assertEqual(len(plot_paths), 3)
            for plot_path in plot_paths:
                self.assertTrue(plot_path.exists())
                self.assertGreater(plot_path.stat().st_size, 0)


class TestSetupThicknessResolution(unittest.TestCase):
    def _write_temp_setup(self, contents: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        setup_path = Path(temp_dir.name) / "test_effective_uz.she"
        setup_path.write_text(textwrap.dedent(contents), encoding="utf-8")
        return setup_path

    def test_repo_setup_derives_ten_meter_effective_uz_thickness(self):
        repo_root = Path(__file__).resolve().parents[1]
        setup_path = (
            repo_root
            / "data"
            / "Cernici_060126_Test02_2"
            / "Cernici16_Ben_v100_DAISYinput.she"
        )

        resolution = derive_effective_uz_thickness_from_setup(setup_path)

        self.assertAlmostEqual(resolution.thickness_m, 10.0)
        self.assertEqual(
            resolution.source,
            "setup UZSoilProfiles layer depth/discretization",
        )
        self.assertGreaterEqual(resolution.profile_count, 1)

    def test_effective_uz_thickness_can_fall_back_to_layer_depths_only(self):
        setup_path = self._write_temp_setup("""
                [Unsatzone]
                    [UZSoilProfiles]
                        [UZSoilProfileProp]
                            ProfileSecNumber = 1
                            GridCode = '1'
                            SoilProfile_ID = '1'
                            [CUZSoilProfilePropLayerListPfs]
                                [UZSoilProfilePropLayerItem1]
                                    Depth = 0.5
                                EndSect  // UZSoilProfilePropLayerItem1
                                [UZSoilProfilePropLayerItem2]
                                    Depth = 6.0
                                EndSect  // UZSoilProfilePropLayerItem2
                            EndSect  // CUZSoilProfilePropLayerListPfs
                        EndSect  // UZSoilProfileProp
                        [UZSoilProfileProp]
                            ProfileSecNumber = 2
                            GridCode = '2'
                            SoilProfile_ID = '2'
                            [CUZSoilProfilePropLayerListPfs]
                                [UZSoilProfilePropLayerItem1]
                                    Depth = 1.0
                                EndSect  // UZSoilProfilePropLayerItem1
                                [UZSoilProfilePropLayerItem2]
                                    Depth = 6.0
                                EndSect  // UZSoilProfilePropLayerItem2
                            EndSect  // CUZSoilProfilePropLayerListPfs
                        EndSect  // UZSoilProfileProp
                    EndSect  // UZSoilProfiles
                EndSect  // Unsatzone
                """)

        resolution = derive_effective_uz_thickness_from_setup(setup_path)

        self.assertAlmostEqual(resolution.thickness_m, 6.0)
        self.assertEqual(
            resolution.source,
            "setup UZSoilProfiles layer depth",
        )

    def test_effective_uz_thickness_rejects_nonuniform_profile_depths(self):
        setup_path = self._write_temp_setup("""
                [Unsatzone]
                    [UZSoilProfiles]
                        [UZSoilProfileProp]
                            ProfileSecNumber = 1
                            GridCode = '1'
                            SoilProfile_ID = '1'
                            [CUZSoilProfilePropLayerListPfs]
                                [UZSoilProfilePropLayerItem1]
                                    Depth = 0.5
                                EndSect  // UZSoilProfilePropLayerItem1
                                [UZSoilProfilePropLayerItem2]
                                    Depth = 8.0
                                EndSect  // UZSoilProfilePropLayerItem2
                            EndSect  // CUZSoilProfilePropLayerListPfs
                            [CUZSoilProfilePropDiscrListPfs]
                                [UZSoilProfilePropDiscr1]
                                    CellHeight = 1.0
                                    NoCells = 8
                                EndSect  // UZSoilProfilePropDiscr1
                            EndSect  // CUZSoilProfilePropDiscrListPfs
                        EndSect  // UZSoilProfileProp
                        [UZSoilProfileProp]
                            ProfileSecNumber = 2
                            GridCode = '2'
                            SoilProfile_ID = '2'
                            [CUZSoilProfilePropLayerListPfs]
                                [UZSoilProfilePropLayerItem1]
                                    Depth = 0.5
                                EndSect  // UZSoilProfilePropLayerItem1
                                [UZSoilProfilePropLayerItem2]
                                    Depth = 10.0
                                EndSect  // UZSoilProfilePropLayerItem2
                            EndSect  // CUZSoilProfilePropLayerListPfs
                            [CUZSoilProfilePropDiscrListPfs]
                                [UZSoilProfilePropDiscr1]
                                    CellHeight = 1.0
                                    NoCells = 10
                                EndSect  // UZSoilProfilePropDiscr1
                            EndSect  // CUZSoilProfilePropDiscrListPfs
                        EndSect  // UZSoilProfileProp
                    EndSect  // UZSoilProfiles
                EndSect  // Unsatzone
                """)

        with self.assertRaises(ValueError):
            derive_effective_uz_thickness_from_setup(setup_path)


if __name__ == "__main__":
    unittest.main()
