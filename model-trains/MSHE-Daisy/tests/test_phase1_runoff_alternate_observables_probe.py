import tempfile
import unittest
from pathlib import Path

import pandas as pd
from src.investigations.phase1_runoff_alternate_observables_probe import (
    build_observable_response_timeseries_dataframe,
    summarize_alternate_observable_responses,
    write_observable_response_timeseries_csv,
)


class TestPhase1RunoffAlternateObservablesProbe(unittest.TestCase):
    def _observable_state(self, mean, mean_abs=None, sum_value=None, sum_abs=None):
        absolute_mean = abs(mean) if mean_abs is None else float(mean_abs)
        return {
            "mean": float(mean),
            "mean_abs": absolute_mean,
            "sum": float(mean if sum_value is None else sum_value),
            "sum_abs": float(absolute_mean if sum_abs is None else sum_abs),
        }

    def _case_report(
        self,
        oldr_s_means,
        flow_mean_abs_values,
        flow_mean_values=None,
    ):
        if flow_mean_values is None:
            flow_mean_values = [0.0 for _ in flow_mean_abs_values]

        comparison_steps = []
        for index, (oldr_s_mean, flow_mean_abs, flow_mean) in enumerate(
            zip(oldr_s_means, flow_mean_abs_values, flow_mean_values),
            start=1,
        ):
            comparison_steps.append(
                {
                    "comparison_step_index": index,
                    "wm_step_index": index + 1,
                    "time": f"2020-08-01T00:{index:02d}:00",
                    "observables": {
                        "OLDR_S": self._observable_state(oldr_s_mean),
                        "OL_D": self._observable_state(0.0),
                        "OL_FLOW_X": self._observable_state(
                            flow_mean,
                            mean_abs=flow_mean_abs,
                        ),
                    },
                }
            )

        return {
            "observables_available": {
                "OLDR_S": {"param_id": 367, "resolution_method": "runtime_name"},
                "OL_D": {"param_id": 61, "resolution_method": "runtime_name"},
                "OL_FLOW_X": {
                    "param_id": 999,
                    "resolution_method": "runtime_name",
                },
            },
            "comparison_steps": comparison_steps,
        }

    def _probe_report(self, include_preprocessed=True):
        report = {
            "drainage_runoff_variant": {"modified_fixed_value": 0.0},
            "requested_observables": ["OLDR_S", "OL_D", "OL_FLOW_X"],
            "baseline": self._case_report([1.0, 1.0], [0.10, 0.10]),
            "injected": self._case_report([1.2, 1.4], [0.20, 0.25]),
            "baseline_dr0": self._case_report([1.0, 1.0], [0.05, 0.05]),
            "injected_dr0": self._case_report([1.2, 1.4], [0.10, 0.12]),
            "baseline_preprocessed_zeroed": None,
            "injected_preprocessed_zeroed": None,
        }

        if include_preprocessed:
            report["baseline_preprocessed_zeroed"] = self._case_report(
                [1.0, 1.0],
                [0.08, 0.08],
            )
            report["injected_preprocessed_zeroed"] = self._case_report(
                [1.2, 1.4],
                [0.16, 0.18],
            )

        return report

    def test_response_timeseries_uses_mean_abs_for_signed_flow(self):
        response_df = build_observable_response_timeseries_dataframe(
            self._probe_report(include_preprocessed=False)
        )

        flow_rows = response_df.loc[
            (response_df["variant_key"] == "default")
            & (response_df["observable_name"] == "OL_FLOW_X")
            & (response_df["metric_name"] == "mean_abs")
        ]
        self.assertEqual(len(flow_rows), 2)
        self.assertAlmostEqual(flow_rows.iloc[0]["difference_value"], 0.10)

        mean_rows = response_df.loc[
            (response_df["variant_key"] == "default")
            & (response_df["observable_name"] == "OL_FLOW_X")
            & (response_df["metric_name"] == "mean")
        ]
        self.assertAlmostEqual(mean_rows.iloc[0]["difference_value"], 0.0)

    def test_summary_identifies_alternate_suppression_discriminator(self):
        summary = summarize_alternate_observable_responses(
            self._probe_report(include_preprocessed=True),
            response_metric="mean_abs",
        )

        self.assertEqual(
            summary["responding_reference_observables_default"], ["OLDR_S"]
        )
        self.assertEqual(
            summary["responding_alternate_observables_default"], ["OL_FLOW_X"]
        )
        self.assertIn("OL_FLOW_X", summary["dr0_setup_effect_alternate_observables"])
        self.assertIn(
            "OL_FLOW_X",
            summary["preprocessed_setup_effect_alternate_observables"],
        )
        self.assertEqual(summary["candidate_suppression_discriminators"], ["OL_FLOW_X"])

    def test_csv_artifact_is_written(self):
        report = self._probe_report(include_preprocessed=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir) / "phase1_runoff_alternate_observables_probe.json"
            )
            output_path.write_text("{}", encoding="utf-8")

            csv_path = write_observable_response_timeseries_csv(report, output_path)

            self.assertTrue(csv_path.exists())
            csv_df = pd.read_csv(csv_path)
            self.assertFalse(csv_df.empty)
            self.assertIn("observable_name", csv_df.columns)
            self.assertIn("metric_name", csv_df.columns)
            self.assertIn("difference_value", csv_df.columns)


if __name__ == "__main__":
    unittest.main()
