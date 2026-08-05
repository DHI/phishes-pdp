# %%

import numpy as np
from xmipy import XmiWrapper
from typing import Any, Dict
import pandas as pd
from src.simulation.reservoir_simulation import (
    CoupledPonding,
    CoupledSimplePonding,
    make_ponding_characteristics,
)


class Simulation:
    """
    Run all stress periods in a simulation
    """

    array_pointers: dict[str, np.ndarray]
    continue_solve: bool

    def __init__(self, wdir: str, name: str, mf6_binaries: str, continue_solve: bool = False):
        self.modelname = name
        self.mf6 = XmiWrapper(lib_path=mf6_binaries, working_directory=wdir)
        self.mf6.initialize()
        self.max_iter = self.mf6.get_value_ptr("SLN_1/MXITER")[0]
        self.continue_solve = continue_solve
        self.nm_solution_ids = np.arange(1, self.mf6.get_subcomponent_count() + 1)
        
    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        has_converged = self.mf6.solve(sol_id)
        return has_converged

    def update(self, iperiod: float):
        self.mf6.prepare_time_step(0.0)
        self.solve()
        self.mf6.finalize_time_step()
        current_time = self.mf6.get_current_time()
        return current_time

    def solve(self,) -> None:
        for solution_id in self.nm_solution_ids:
            self.solve_solution(solution_id)

    def solve_solution(self, solution_id) -> None:
        # solves per numerical solution
        self.mf6.prepare_solve(solution_id)
        for _ in range(1, self.max_iter + 1):
            has_converged = self.mf6.solve(solution_id)
            if has_converged:
                break
        if not has_converged and not self.continue_solve:
            raise Exception(f"Solution {solution_id} did not converged; simulation aborted")
        self.mf6.finalize_solve(solution_id)

    def get_times(self):
        """Return times"""
        return (
            self.mf6.get_start_time(),
            self.mf6.get_current_time(),
            self.mf6.get_end_time(),
        )

    def run(self, periods):
        iperiod = 0
        _, current_time, end_time = self.get_times()
        while (current_time < end_time) and iperiod < periods:
            # print(f"MF6 starting period {iperiod}")
            current_time = self.update(iperiod)
            iperiod += 1
            print("solving for stress period: " + str(iperiod))
        print(f"Simulation terminated normally for {iperiod} periods")

    def finalize(self):
        self.mf6.finalize()


class CoupledPondingSimulation(Simulation):
    ponding_data: Dict[str, Any]
    log_ponding: Dict[str, list]
    ponding: CoupledPonding | list
    ponding_active: bool

    def __init__(
        self,
        wdir: str,
        name_model: str,
        ponding_data: Dict[str, Any],
        continue_solve: bool = False,
    ):
        super().__init__(wdir, name_model, continue_solve)
        self.raise_on_version_mismatch()
        self.tstart = self.set_coupled_ponding(ponding_data, name_model)
        self.set_log()
        self.ponding_active = False

    def set_log(self) -> None:
        self.log_ponding = {
            "time": [],
            "volume": [],
            "volume_excess_out": [],
            "realised_infiltration_out": [],
            "rejected_infiltration_in": [],
            "groundwater_discharge_in": [],
            "uzf_infiltration_in": [],
            "stage": [],
            "active": [],
        }

    def logging_stages(self) -> None:
        self.log_ponding["stage"].append(self.ponding.stage)

    def logging_volumes(self) -> None:
        self.log_ponding["time"].append(self.mf6.get_current_time())
        self.log_ponding["volume"].append(self.ponding.volume)
        self.log_ponding["volume_excess_out"].append(self.ponding.excess)
        self.log_ponding["realised_infiltration_out"].append(self.ponding.realised)
        self.log_ponding["groundwater_discharge_in"].append(
            self.ponding.groundwater_discharge
        )
        self.log_ponding["rejected_infiltration_in"].append(
            self.ponding.rejected_infiltration
        )
        self.log_ponding["uzf_infiltration_in"].append(self.ponding.uzf_infiltration)
        self.log_ponding["active"].append(self.ponding_active)

    def set_coupled_ponding(self, data: Dict[str, Any], name_model: str) -> float:
        uzf_package = list(data.keys())[0]
        init_stage = data[uzf_package]["initial_stage"]
        self.ponding = CoupledPonding(
            data[uzf_package],
            init_stage,
            self.mf6,
            name_model,
            uzf_package,
        )
        return data[uzf_package]["tstart"]

    def update(self, iperiod: float):
        self.mf6.prepare_time_step(0.0)
        current_time = self.mf6.get_current_time()
        self.logging_stages()
        if iperiod >= self.tstart:
            self.ponding_active = True
            # exchange input infiltration to ponding reservoir
            self.ponding.exchange_input_from_uzf()
            # exchange actual infiltration to uzf-package
            self.ponding.exchange_to_uzf()
        self.solve()
        if iperiod >= self.tstart:
            # exchange gwd + rejected infiltration to ponding reservoir
            self.ponding.exchange_excess_from_uzf()
        self.logging_volumes()
        self.mf6.finalize_time_step()
        self.ponding.finalize_time_step()
        current_time = self.mf6.get_current_time()
        return current_time
        
    def raise_on_version_mismatch(self) -> None:
        lower_bound = "6.5.0"
        actual_version = self.mf6.get_version()

        def parse_version(v: str) -> tuple[int, int, int]:
            match = re.search(r"(\d+)\.(\d+)\.(\d+)", v)
            if not match:
                raise ValueError(f"Could not parse version from: {v!r}")
            major, minor, patch = match.groups()
            return int(major), int(minor), int(patch)

        if parse_version(actual_version) < parse_version(lower_bound):
            raise Exception(
                f"For coupled simulation we need version >= {lower_bound}, actual version is {actual_version}"
            )

def add_substring_in_list(names: list, string: str) -> list:
    out = []
    for name in names:
        out.append(name + string)
    return out


def run_model(periods, wdir: str, name_model: str):
    sim = Simulation(wdir, name_model)
    sim.run(periods)
    sim.finalize()


def run_coupled_model(
    periods,
    wdir: str,
    name_model: str,
    ponding_data: Dict[str, Any],
    mf6_continue: bool,
):
    sim = CoupledPondingSimulation(wdir, name_model, ponding_data, mf6_continue)
    sim.run(periods)
    sim.finalize()
    return pd.DataFrame.from_dict(sim.log_ponding)

