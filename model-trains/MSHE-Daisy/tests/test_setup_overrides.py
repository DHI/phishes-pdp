import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from src.setup_overrides import (
    PREPROCESSED_RUNOFF_COEFFICIENT_ITEM_NAME,
    build_derived_setup_path,
    derive_preprocessed_dfs2_path,
    resolve_native_sz_drain_suppression_policy,
    write_preprocessed_runoff_coefficient_override,
    write_saturated_zone_drain_override_setup,
    write_simulation_period_override_setup,
)


class _FakePfsDocument:
    instances = []

    def __init__(self, path, unique_keywords=False):
        self.path = path
        self.unique_keywords = unique_keywords
        self.drainage_section = SimpleNamespace(
            DrainageOption=2,
            DrainCode=SimpleNamespace(FixedValue=1.0, Type=7),
        )
        self.simulation_period = SimpleNamespace(
            SIMSTART=(2020, 8, 1, 0, 0),
            SIMEND=(2020, 9, 1, 0, 0),
        )
        self.MIKESHE_FLOWMODEL = SimpleNamespace(
            SaturatedZone=SimpleNamespace(Drainage={1: self.drainage_section}),
            SimSpec=SimpleNamespace(SimulationPeriod=self.simulation_period),
        )
        self.written_path = None
        type(self).instances.append(self)

    def write(self, path):
        self.written_path = path


class _FakeDfsItem:
    def __init__(self, name, values):
        self.name = name
        self.values = values


class _FakeDfsDataset:
    last_written_path = None
    last_written_dataset = None

    def __init__(self, items):
        self._items = list(items)
        self.items = tuple(SimpleNamespace(name=item.name) for item in self._items)

    def __getitem__(self, index):
        return self._items[index]

    def copy(self):
        return _FakeDfsDataset(
            _FakeDfsItem(item.name, np.array(item.values, copy=True))
            for item in self._items
        )

    def to_dfs(self, path):
        type(self).last_written_path = path
        type(self).last_written_dataset = self


class TestSetupOverrides(unittest.TestCase):
    def setUp(self):
        _FakePfsDocument.instances.clear()
        _FakeDfsDataset.last_written_path = None
        _FakeDfsDataset.last_written_dataset = None

    def test_build_derived_setup_path_appends_suffix(self):
        setup_path = Path(r"C:\temp\example.she")
        derived_path = build_derived_setup_path(setup_path, "dr0")
        self.assertEqual(derived_path.name, "example_dr0.she")

    def test_write_saturated_zone_drain_override_updates_drain_code(self):
        fake_mikeio = types.SimpleNamespace(PfsDocument=_FakePfsDocument)
        setup_path = Path(r"C:\temp\example.she")

        with patch.dict(sys.modules, {"mikeio": fake_mikeio}):
            derived_path, metadata = write_saturated_zone_drain_override_setup(
                setup_path,
                drain_code_fixed_value=0.0,
                suffix="dr0",
            )

        instance = _FakePfsDocument.instances[-1]
        self.assertEqual(derived_path.name, "example_dr0.she")
        self.assertEqual(instance.drainage_section.DrainCode.FixedValue, 0.0)
        self.assertEqual(instance.drainage_section.DrainCode.Type, 0)
        self.assertEqual(metadata["original_drain_code_fixed_value"], 1.0)
        self.assertEqual(metadata["modified_drain_code_fixed_value"], 0.0)
        self.assertEqual(metadata["modified_drain_code_type"], 0)
        self.assertEqual(instance.written_path, str(derived_path))

    def test_write_saturated_zone_drain_override_updates_drainage_option(self):
        fake_mikeio = types.SimpleNamespace(PfsDocument=_FakePfsDocument)
        setup_path = Path(r"C:\temp\example.she")

        with patch.dict(sys.modules, {"mikeio": fake_mikeio}):
            derived_path, metadata = write_saturated_zone_drain_override_setup(
                setup_path,
                drainage_option=0,
                drain_code_fixed_value=0.0,
                suffix="o0c0",
            )

        instance = _FakePfsDocument.instances[-1]
        self.assertEqual(derived_path.name, "example_o0c0.she")
        self.assertEqual(instance.drainage_section.DrainageOption, 0)
        self.assertEqual(metadata["original_drainage_option"], 2)
        self.assertEqual(metadata["modified_drainage_option"], 0)

    def test_write_simulation_period_override_updates_sim_end(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_path = Path(temp_dir) / "example.she"
            setup_path.write_text(
                "\n".join(
                    (
                        "[SimulationPeriod]",
                        "   SIMSTART = 2020, 8, 1, 0, 0",
                        "   SIMEND = 2020, 9, 1, 0, 0",
                        "EndSect  // SimulationPeriod",
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            derived_path, metadata = write_simulation_period_override_setup(
                setup_path,
                sim_end="2020-08-10T05:00:00",
                suffix="10d",
            )

            written_text = derived_path.read_text(encoding="utf-8")

        self.assertEqual(derived_path.name, "example_10d.she")
        self.assertIn("SIMSTART = 2020, 8, 1, 0, 0", written_text)
        self.assertIn("SIMEND = 2020, 8, 10, 5, 0", written_text)
        self.assertEqual(metadata["original_sim_end"], (2020, 9, 1, 0, 0))
        self.assertEqual(metadata["modified_sim_end"], (2020, 8, 10, 5, 0))

    def test_write_simulation_period_override_requires_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_path = Path(temp_dir) / "example.she"
            setup_path.write_text(
                "\n".join(
                    (
                        "[SimulationPeriod]",
                        "   SIMSTART = 2020, 8, 1, 0, 0",
                        "   SIMEND = 2020, 9, 1, 0, 0",
                        "EndSect  // SimulationPeriod",
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                write_simulation_period_override_setup(setup_path)

    def test_derive_preprocessed_dfs2_path_uses_result_files_convention(self):
        setup_path = Path(r"C:\temp\example_plugin.she")

        derived_path = derive_preprocessed_dfs2_path(setup_path)

        self.assertEqual(
            derived_path,
            Path(
                r"C:\temp\example_plugin.she - Result Files\example_plugin_PreProcessed.DFS2"
            ),
        )

    def test_write_preprocessed_runoff_coefficient_override_zeroes_selected_cells(self):
        runoff_values = np.full((1, 4, 4), 0.05, dtype=float)
        runoff_values[0, 0, 0] = 0.10
        fake_dataset = _FakeDfsDataset(
            (
                _FakeDfsItem("other", np.ones((1, 4, 4), dtype=float)),
                _FakeDfsItem(
                    PREPROCESSED_RUNOFF_COEFFICIENT_ITEM_NAME,
                    runoff_values,
                ),
            )
        )

        def _fake_read(path):
            return fake_dataset

        fake_mikeio = types.SimpleNamespace(read=_fake_read)

        with tempfile.TemporaryDirectory() as temp_dir:
            setup_path = Path(temp_dir) / "example_plugin.she"
            setup_path.write_text("dummy", encoding="utf-8")
            result_files_dir = setup_path.with_name(setup_path.name + " - Result Files")
            result_files_dir.mkdir()
            preprocessed_dfs2_path = (
                result_files_dir / "example_plugin_PreProcessed.DFS2"
            )
            preprocessed_dfs2_path.write_text("dummy", encoding="utf-8")

            with patch.dict(sys.modules, {"mikeio": fake_mikeio}):
                written_path, metadata = write_preprocessed_runoff_coefficient_override(
                    setup_path,
                    coupled_cells=((1, 1), (2, 2)),
                )

        self.assertEqual(written_path, preprocessed_dfs2_path.resolve())
        self.assertEqual(
            _FakeDfsDataset.last_written_path, str(preprocessed_dfs2_path.resolve())
        )
        written_dataset = _FakeDfsDataset.last_written_dataset
        self.assertIsNotNone(written_dataset)
        self.assertAlmostEqual(float(written_dataset[1].values[0, 1, 1]), 0.0)
        self.assertAlmostEqual(float(written_dataset[1].values[0, 2, 2]), 0.0)
        self.assertAlmostEqual(float(written_dataset[1].values[0, 0, 0]), 0.10)
        self.assertEqual(
            metadata["item_name"], PREPROCESSED_RUNOFF_COEFFICIENT_ITEM_NAME
        )
        self.assertEqual(metadata["item_index"], 2)
        self.assertEqual(metadata["coupled_cell_count"], 2)
        self.assertEqual(metadata["changed_cell_count"], 2)
        self.assertEqual(metadata["nonzero_before_count"], 2)
        self.assertAlmostEqual(metadata["override_value"], 0.0)

    def test_write_preprocessed_runoff_coefficient_override_requires_expected_item(
        self,
    ):
        fake_dataset = _FakeDfsDataset(
            (_FakeDfsItem("other", np.ones((1, 4, 4), dtype=float)),)
        )

        def _fake_read(path):
            return fake_dataset

        fake_mikeio = types.SimpleNamespace(read=_fake_read)

        with tempfile.TemporaryDirectory() as temp_dir:
            setup_path = Path(temp_dir) / "example_plugin.she"
            setup_path.write_text("dummy", encoding="utf-8")
            result_files_dir = setup_path.with_name(setup_path.name + " - Result Files")
            result_files_dir.mkdir()
            preprocessed_dfs2_path = (
                result_files_dir / "example_plugin_PreProcessed.DFS2"
            )
            preprocessed_dfs2_path.write_text("dummy", encoding="utf-8")

            with patch.dict(sys.modules, {"mikeio": fake_mikeio}):
                with self.assertRaises(ValueError):
                    write_preprocessed_runoff_coefficient_override(
                        setup_path,
                        coupled_cells=((1, 1),),
                    )

    def test_native_sz_drain_policy_defaults_on_with_drain_coupling(self):
        policy = resolve_native_sz_drain_suppression_policy(
            drain_coupling_enabled=True,
        )

        self.assertTrue(policy["enabled"])
        self.assertEqual(policy["source"], "default_phase3_policy")

    def test_native_sz_drain_policy_respects_explicit_opt_out(self):
        policy = resolve_native_sz_drain_suppression_policy(
            drain_coupling_enabled=True,
            keep_native_sz_drain=True,
        )

        self.assertFalse(policy["enabled"])
        self.assertEqual(policy["source"], "explicit_opt_out")

    def test_native_sz_drain_policy_is_inactive_without_drain_coupling(self):
        policy = resolve_native_sz_drain_suppression_policy(
            drain_coupling_enabled=False,
            suppress_native_sz_drain=True,
        )

        self.assertFalse(policy["enabled"])
        self.assertEqual(policy["source"], "drain_coupling_disabled")

    def test_native_sz_drain_policy_rejects_conflicting_flags(self):
        with self.assertRaises(ValueError):
            resolve_native_sz_drain_suppression_policy(
                drain_coupling_enabled=True,
                suppress_native_sz_drain=True,
                keep_native_sz_drain=True,
            )


if __name__ == "__main__":
    unittest.main()
