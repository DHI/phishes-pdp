import tempfile
import unittest
from pathlib import Path

import pandas as pd
from src.investigations.phase1_runoff_double_count_probe import (
    RESPONSE_DIFFERENCE_PLOT_NAME,
    SETUP_EFFECT_PLOT_NAME,
    build_runoff_response_timeseries_dataframe,
    build_runoff_setup_effect_timeseries_dataframe,
    write_runoff_probe_plots,
    write_runoff_response_timeseries_csv,
)


class TestPhase1RunoffDoubleCountProbeArtifacts(unittest.TestCase):
    def _case_report(self, ol_d_means, oldr_s_means):
        comparison_steps = []
        for index, (ol_d_mean, oldr_s_mean) in enumerate(
            zip(ol_d_means, oldr_s_means),
            start=1,
        ):
            comparison_steps.append(
                {
                    "comparison_step_index": index,
                    "wm_step_index": index + 1,
                    "time": f"2020-08-01T00:{index:02d}:00",
                    "ol_d": {"mean": float(ol_d_mean)},
                    "oldr_s": {"mean": float(oldr_s_mean)},
                }
            )

        return {
            "comparison_steps": comparison_steps,
            "after": {
                "ol_d": {"mean": float(ol_d_means[-1])},
                "oldr_s": {"mean": float(oldr_s_means[-1])},
            },
        }

    def _probe_report(self, include_preprocessed=True):
        report = {
            "drainage_runoff_variant": {"modified_fixed_value": 0.0},
            "baseline": self._case_report([1.0, 1.0], [2.0, 2.0]),
            "injected": self._case_report([1.0, 1.1], [2.2, 2.4]),
            "baseline_dr0": self._case_report([0.95, 0.95], [1.9, 1.9]),
            "injected_dr0": self._case_report([0.95, 1.0], [2.1, 2.2]),
            "baseline_preprocessed_zeroed": None,
            "injected_preprocessed_zeroed": None,
        }

        if include_preprocessed:
            report["baseline_preprocessed_zeroed"] = self._case_report(
                [0.9, 0.9],
                [1.8, 1.8],
            )
            report["injected_preprocessed_zeroed"] = self._case_report(
                [0.9, 0.92],
                [1.95, 2.05],
            )

        return report

    def test_response_timeseries_skips_missing_preprocessed_variant(self):
        response_df = build_runoff_response_timeseries_dataframe(
            self._probe_report(include_preprocessed=False)
        )

        self.assertEqual(
            sorted(response_df["variant_key"].unique().tolist()),
            ["default", "dr0"],
        )
        self.assertEqual(len(response_df), 4)
        first_default = response_df.loc[response_df["variant_key"] == "default"].iloc[0]
        self.assertAlmostEqual(first_default["oldr_s_mean_diff"], 0.2)
        self.assertAlmostEqual(first_default["ol_d_mean_diff"], 0.0)

    def test_setup_effect_timeseries_includes_preprocessed_variant(self):
        setup_effect_df = build_runoff_setup_effect_timeseries_dataframe(
            self._probe_report(include_preprocessed=True)
        )

        self.assertEqual(
            sorted(setup_effect_df["variant_key"].unique().tolist()),
            ["dr0", "preprocessed_zeroed"],
        )
        injected_preprocessed = setup_effect_df.loc[
            (setup_effect_df["variant_key"] == "preprocessed_zeroed")
            & (setup_effect_df["comparison_case"] == "injected")
        ].iloc[-1]
        self.assertAlmostEqual(injected_preprocessed["oldr_s_mean_setup_effect"], -0.35)
        self.assertAlmostEqual(injected_preprocessed["ol_d_mean_setup_effect"], -0.18)

    def test_csv_and_plot_artifacts_are_written(self):
        report = self._probe_report(include_preprocessed=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "phase1_runoff_double_count_probe.json"
            output_path.write_text("{}", encoding="utf-8")

            csv_path = write_runoff_response_timeseries_csv(report, output_path)
            plot_paths = write_runoff_probe_plots(report, output_path)

            self.assertTrue(csv_path.exists())
            csv_df = pd.read_csv(csv_path)
            self.assertFalse(csv_df.empty)
            self.assertEqual(len(plot_paths), 2)
            self.assertEqual(
                sorted(path.name for path in plot_paths),
                sorted(
                    [
                        RESPONSE_DIFFERENCE_PLOT_NAME,
                        SETUP_EFFECT_PLOT_NAME,
                    ]
                ),
            )
            for plot_path in plot_paths:
                self.assertTrue(plot_path.exists())
                self.assertGreater(plot_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
