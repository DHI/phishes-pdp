import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import src.DaisyFunctions as daisy

SAMPLE_DAISY_OUTPUT = """dlf-0.0 -- Field water (defined in 'log-std.dai').

VERSION: 7.0.13
LOGFILE: Monthly_FWater.csv
RUN: Wed Aug 20 10:20:52 2025

year\tmonth\tmday\thour\tRunoff\tMatrix percolation\tMatrix drain flow
				mm\tmm\tmm
2020\t1\t1\t0\t0.0\t1.0\t0.25
2020\t2\t1\t0\t2.5\t1.5\t0.5
2020\t3\t1\t0\t3.5\t2.5\t0.75
"""


class TestDaisyFunctions(unittest.TestCase):
    def _write_sample(self, directory: str) -> Path:
        sample_path = Path(directory) / "Monthly_FWater.csv"
        sample_path.write_text(SAMPLE_DAISY_OUTPUT, encoding="utf-8")
        return sample_path

    def test_read_daisy_output_skips_units_row(self):
        with TemporaryDirectory() as directory:
            sample_path = self._write_sample(directory)
            df = daisy.readDaisyOutput(sample_path)

        self.assertEqual(len(df), 3)
        self.assertEqual(df.iloc[0]["Runoff"], 0.0)
        self.assertIsInstance(df.index, pd.DatetimeIndex)

    def test_interval_metadata_uses_actual_timestamp_differences(self):
        with TemporaryDirectory() as directory:
            sample_path = self._write_sample(directory)
            df = daisy.readDaisyOutput(sample_path)

        interval_df = daisy.addIntervalMetadata(df)
        self.assertTrue(pd.isna(interval_df.iloc[0]["interval_seconds"]))
        self.assertEqual(interval_df.iloc[1]["interval_seconds"], 31 * 24 * 60 * 60)
        self.assertEqual(interval_df.iloc[2]["interval_seconds"], 29 * 24 * 60 * 60)

    def test_interval_value_lookup_uses_end_of_interval_assumption(self):
        with TemporaryDirectory() as directory:
            sample_path = self._write_sample(directory)
            df = daisy.readDaisyOutput(sample_path)

        target_time = pd.Timestamp("2020-02-15 00:00")
        self.assertEqual(
            daisy.findIntervalValueInDaisyResult(df, target_time, "Runoff"),
            3.5,
        )
        self.assertAlmostEqual(
            daisy.findIntervalRateInDaisyResult(df, target_time, "Runoff"),
            0.0035 / (29 * 24 * 60 * 60),
        )

    def test_interval_lookup_supports_matrix_drain_flow_column(self):
        with TemporaryDirectory() as directory:
            sample_path = self._write_sample(directory)
            df = daisy.readDaisyOutput(sample_path)

        target_time = pd.Timestamp("2020-02-15 00:00")
        self.assertEqual(
            daisy.findIntervalValueInDaisyResult(df, target_time, "Matrix drain flow"),
            0.75,
        )
        self.assertAlmostEqual(
            daisy.findIntervalRateInDaisyResult(df, target_time, "Matrix drain flow"),
            0.00075 / (29 * 24 * 60 * 60),
        )

    def test_legacy_interpolation_helper_still_available(self):
        df = pd.DataFrame(
            {"Surface water": [0.0, 10.0]},
            index=pd.to_datetime(["2020-01-01 00:00", "2020-01-03 00:00"]),
        )

        interpolated = daisy.findValueInDaisyResult(
            df,
            pd.Timestamp("2020-01-02 00:00"),
            "Surface water",
        )

        self.assertEqual(interpolated, 5.0)

    def test_require_daisy_column_raises_clear_error_for_missing_column(self):
        df = pd.DataFrame(
            {"Runoff": [1.0]},
            index=pd.to_datetime(["2020-01-01 00:00"]),
        )

        with self.assertRaises(KeyError) as exc:
            daisy.requireDaisyColumn(df, "Matrix percolation")

        self.assertIn("Matrix percolation", str(exc.exception))
        self.assertIn("Runoff", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
