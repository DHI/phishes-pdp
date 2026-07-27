# %%
import numpy as np
from typing import Any, Dict
import xarray as xr
import math
from xmipy import XmiWrapper
import imod


def make_ponding_characteristics(
    dem: xr.DataArray, ponding_mask: xr.DataArray, dz: np.float64, zmax: np.float64
) -> Dict[str, np.ndarray]:
    # create area array
    area = xr.zeros_like(dem, dtype=np.float64)
    nx = dem.x.values.size
    ny = dem.y.values.size
    area.values = np.column_stack(
        [np.array([dem.dx.item()] * ny)] * nx
    ) * np.column_stack([np.array([np.absolute(dem.dy.item())] * ny)] * nx)

    # compute volumes per stage
    zmin = dem.where(ponding_mask.notnull()).min().item()
    nz = math.ceil((zmax - zmin) / dz)
    stages = xr.DataArray(
        data=np.array([dz] * nz),
        coords={
            "z": zmin + (np.arange(nz) * dz),
        },
        dims=["z"],
    )
    volumes = (stages * area).where(dem.where(ponding_mask.notnull()) < stages.z)
    volumes_per_stage = volumes.sum(dim=["y", "x"]).cumsum(dim="z")
    stage = volumes.z

    # get active ponding nodes
    ponding_mask = np.where(ponding_mask.notnull(), 1, 0)
    active = np.flatnonzero(ponding_mask)
    active_2d = np.nonzero(ponding_mask)

    return {
        "stage": stage.values,
        "volume": volumes_per_stage.values,
        "top_nodes": dem.values.ravel()[active],
        "2d_index": active_2d,
    }


def get_river_drain_flux(
    package_hcof: np.ndarray,
    package_rhs: np.ndarray,
    package_nodelist: np.ndarray,
    solution_head: np.ndarray,
) -> np.ndarray[np.float64]:
    """
    Returns the calculated river or DRN fluxes of MF6. In MF6 the RIV boundary condition is added to the solution in the following matter:

    RHS = -cond*(hriv-rivbot)
    HCOF = -cond

    if head < bot then HCOF = 0

    for the DRN package:

    RHS = -f * cond * bot
    HCOF = -f * cond

    Where f is the 'drainage scaling factor' when using the option 'auxdepthname'.


    The MF6 solutions has the form of:

    A * X = Q

    Therefore, the flux contributions of RIV and DRN can be calculated by:

    Flux = HCOF * X - RHS

    When this function is called before initialisation of a new timestep (t), the
    calculated flux is of timestep t-1. If function is called before initialisation
    of the first timestep, the calculated flux will be zero.

    Parameters
    ----------
    package_rhs: NDArray[np.float64]
        rhs of package
    package_rhs: NDArray[np.float64]
        hcof of package: NDArray[np.float64]
    package_nodelist: NDArray[np.float64]
        package nodelist with indices to relate to solution
    solution_head: NDArray[np.float64]
        solution head

    Returns
    -------
    NDArray[np.float64]
        flux (array size = nr of river nodes)
        sign is positive for infiltration
    """

    subset_head = solution_head[package_nodelist - 1]
    return package_hcof * subset_head - package_rhs


class Ponding:
    volume: np.ndarray
    infiltration_index: np.ndarray
    uzf_infiltration_in_saved: np.ndarray
    volume: float
    excess: float

    def __init__(
        self,
        characteristics: dict[str, np.ndarray[Any]],
        init_stage: np.ndarray,
    ):
        self.characteristics = characteristics
        self._set_init_stage(init_stage)
        self._set_volume()
        self._set_infiltration_index()
        self.excess = 0.0
        self.uzf_infiltration = 0.0

    def _set_volume(self) -> None:
        n = self.characteristics["volume"].size - 1
        self.max_volume = self.characteristics["volume"][n]
        self.volume = np.interp(
            self.stage,
            self.characteristics["stage"],
            self.characteristics["volume"],
            left=0.0,
            right=self.max_volume,
        )

    def _set_init_stage(self, stage: np.ndarray) -> None:
        n = self.characteristics["stage"].size - 1
        self.max_stage = self.characteristics["stage"][n]
        self.min_stage = self.characteristics["stage"][0]
        self.stage = stage
        self.stage = min(self.stage, self.max_stage)
        self.stage = max(self.stage, self.min_stage)

    def _set_stage(self) -> None:
        min_stage = self.characteristics["stage"][0]
        self.stage = np.interp(
            self.volume,
            self.characteristics["volume"],
            self.characteristics["stage"],
            left=min_stage,
            right=self.max_stage,
        )
        self._set_infiltration_index()

    def _set_outflux(self, demand_volume: np.ndarray) -> np.ndarray:
        realised_volume = np.sum(demand_volume)
        if realised_volume == 0.0:
            return 0.0
        if realised_volume > self.volume:
            realised_volume = self.volume
        self.volume = self.volume - realised_volume
        self._set_stage()
        return realised_volume / np.sum(demand_volume)

    def _set_influx(self, volume: np.ndarray) -> np.ndarray:
        self.volume += volume
        self.volume = np.maximum(self.volume, 0.0)
        excess  =  max(self.volume - self.max_volume, 0.0)
        self.excess += excess # cumulative for logging purpose
        self.volume = min(self.volume, self.max_volume)
        self._set_stage()
        if volume > 0.0:
            frealised = (volume - excess) / volume
            # self.excess = excess   #+= volume * (1 - frealised)
            return frealised
        else:
            return 0.0

    def _set_infiltration_index(self) -> None:
        """
        sets nodes that could infiltrate since there is water ponding at ground level

        this function assumes row-majour numbering where all top nodes comes before the lower ones
        """
        below_stage = self.characteristics["top_nodes"] < self.stage
        self.infiltration_index = np.arange(below_stage.size)[below_stage]


class SoilInfiltration:
    inf_rate: float
    c_bottom: float

    def __init__(self, inf_rate: float, c_bottom: float, bottom: np.ndarray):
        self.bottom = bottom
        self.inf_rate = inf_rate
        self.c_bottom = c_bottom

    def infiltration_rate(self, stage: float) -> np.ndarray:
        ponding_infiltration = (stage - self.bottom) / self.c_bottom
        return ponding_infiltration + self.inf_rate


class CoupledPonding(Ponding):
    mf6: XmiWrapper
    uzf_name: str
    uzf_pointers: Dict
    drn_pointers: Dict
    update_pointer: bool
    sinf_saved: np.ndarray
    realised: float
    groundwater_discharge: np.ndarray
    groundwater_discharge_stage: np.ndarray
    rejected_infiltration: np.ndarray
    infiltration_rate_reduction: np.ndarray
    uzf_infiltration: np.ndarray
    soil: SoilInfiltration

    def __init__(
        self,
        characteristics: dict[str, np.ndarray[Any]],
        init_stage: np.ndarray,
        mf6: XmiWrapper,
        model_name: str,
        uzf_name: str,
    ):
        super().__init__(characteristics, init_stage)
        self.mf6 = mf6
        self.uzf_name = uzf_name
        self._get_uzf_pointers(model_name, uzf_name)
        self.infiltration_rate_reduction = np.ones_like(self.uzf_pointers["VKS"])
        self._set_soil_parameters()
        self.realised = 0.0
        self.update_pointer = False
        self.groundwater_discharge = 0.0
        self.rejected_infiltration = 0.0

    def _set_soil_parameters(self) -> None:
        inf_rate = self.characteristics["inf_rate"]
        c_bottom = self.characteristics["c_bottom"]
        bottom = self.uzf_pointers["CELTOP"]
        self.soil = SoilInfiltration(inf_rate, c_bottom, bottom)

    def exchange_excess_from_uzf(self) -> None:
        """exchange volumes from uzf-package to ponding class"""
        top_nodes = self.uzf_pointers["LANDFLAG"] == 1
        self.groundwater_discharge = (
            self.uzf_pointers["GWD"][top_nodes].sum() * self.delt
        )
        _ = self._set_influx(self.groundwater_discharge)
        self.rejected_infiltration = (
            self.uzf_pointers["REJINF"][top_nodes].sum() * self.delt
        )
        _ = self._set_influx(self.rejected_infiltration)

    def exchange_input_from_uzf(self) -> None:
        # new timestep: reset excess 
        self.excess = 0.0
        # all uzf input is moved to ponding reservoir, so infiltration rate is computed using max infiltration rate and resistance
        # SINF_PVAR is an input variable in m/d; convert to volumes per timestep
        # use all uzf nodes, but only first layer nodes should have input
        self.uzf_infiltration = (
            self.uzf_pointers["SINF_PVAR"] * self.uzf_pointers["UZFAREA"]
        ).sum() * self.delt
        _ = self._set_influx(self.uzf_infiltration)
        # the SINF_PVAR pointer will be updated by _set_uzf_realised() and 
        # restored to the input value in finalize_time_step().

    def exchange_to_uzf(self) -> None:
        """exchange volumes from ponding class to uzf-package"""
        if self.volume > 0.0:
            demand = self._get_uzf_demand()
            fraction_realised = self._set_outflux(demand)  # ponding outflux
            if fraction_realised > 0:
                self._set_uzf_realised(demand, fraction_realised)
            else:
                self.realised = 0.0
        else:
            self.realised = 0.0

    def finalize_time_step(self) -> None:
        """resets SINF_PVAR pointer to original values for cases where input values are repeated.
        In that case mf6 does not update the values.
        """
        if self.update_pointer:
            self.uzf_pointers["SINF_PVAR"][:] = self.sinf_saved[:]
            self.update_pointer = False

    def _get_uzf_demand(self) -> None:
        # get UZF-package demand
        uzf_demand = np.copy((self.uzf_pointers["VKS"] - self.uzf_pointers["SINF_PVAR"]))
        condition = uzf_demand < 0
        uzf_demand[condition] = 0.0
        # get WADI demand
        wadi_demand = self.soil.infiltration_rate(self.stage)
        # total demand; maximized at VKS UZF
        demand = np.minimum(uzf_demand, wadi_demand)

        # In the UZF-package the infiltration rate reduces linearly to zero from top – surfdep.
        # We do the same here. This method is limited to stress period level, internally the uzf package does
        # this at outer iteration level.
        dep = (
            self.uzf_pointers["CELTOP"]
            - self.uzf_pointers["solution_head"][self.uzf_pointers["NODELIST"] - 1]
        )
        surfdep = self.uzf_pointers["SURFDEP"]
        np.minimum(
            dep / surfdep, np.ones_like(dep), out=self.infiltration_rate_reduction
        )
        np.maximum(
            self.infiltration_rate_reduction,
            np.zeros_like(dep),
            out=self.infiltration_rate_reduction,
        )
        demand = demand * self.infiltration_rate_reduction
        return demand[self.infiltration_index]

    def _set_uzf_realised(
        self, demand: np.ndarray, fraction_realised: np.float64
    ) -> None:
        if (self.uzf_pointers["LANDFLAG"][self.infiltration_index] != 1).any():
            raise KeyError("found infiltration nodes with incorrect landflag!")
        self.sinf_saved[:] = self.uzf_pointers["SINF_PVAR"][:]
        # SINF_PVAR is in m/d
        self.uzf_pointers["SINF_PVAR"][self.infiltration_index] = (
            (demand) * fraction_realised
        )[:]
        self.update_pointer = True
        # MF6 internally multiplies SINF_PVAR by area to get a volume. For logging purposes we do the same here. SINF is in m3/d, but the actual flux will be in m3/dt
        self.realised = (
            self.uzf_pointers["SINF_PVAR"][self.infiltration_index]
            * self.uzf_pointers["UZFAREA"][self.infiltration_index]
        ).sum() * self.delt
        # update the stage
        self._set_stage()

    def _get_uzf_pointers(self, model_name: str, uzf_name: str) -> None:
        tags = [
            "GWD",
            "REJINF",
            "SINF_PVAR",
            "VKS",
            "UZFAREA",
            "LANDFLAG",
            "NODELIST",
            "CELTOP",
            "SURFDEP",
        ]
        self.uzf_pointers = {}
        for tag in tags:
            mf6_tag = self.mf6.get_var_address(tag, model_name, uzf_name)
            self.uzf_pointers[tag] = self.mf6.get_value_ptr(mf6_tag)
        mf6_tag = self.mf6.get_var_address("X", model_name)
        self.uzf_pointers["solution_head"] = self.mf6.get_value_ptr(mf6_tag)
        self.sinf_saved = np.copy(self.uzf_pointers['SINF'])

    def _set_outflux(self, demand_volume_array: np.ndarray) -> np.ndarray:
        demand_volume = np.sum(demand_volume_array) * self.delt
        realised_volume = demand_volume
        if realised_volume == 0.0:
            return 0.0
        if realised_volume > self.volume:
            realised_volume = self.volume
        self.volume = self.volume - realised_volume
        return realised_volume / demand_volume

    @property
    def delt(self) -> float:
        return self.mf6.get_time_step()

