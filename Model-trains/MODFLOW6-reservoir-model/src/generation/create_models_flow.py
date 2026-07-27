# %%
from typing import Dict, List, Callable
import imod
import xarray as xr
import geopandas as gpd
import numpy as np
import pandas as pd
from pathlib import Path
from shapely.geometry import LineString, Polygon
from scipy.ndimage import binary_dilation
from src.simulation.reservoir_simulation import make_ponding_characteristics
from src.simulation.mf6_uzf_simulation import run_coupled_model
from src.generation.create_models_transport import TransportModel

gpd.options.io_engine = "fiona"

class ValidArray:
    def __init__(self, target: xr.DataArray) -> None:
        self.target = target

    def array(self, array: xr.DataArray, mask=None) -> xr.DataArray:
        if mask is None:
            return self.order_dims(array.where(self.target > 0).astype(array.dtype))
        else:
            uit = self.order_dims(array.where(self.target > 0))
            return uit.where(mask.notnull()).astype(array.dtype)

    def order_dims(self, array: xr.DataArray) -> xr.DataArray:
        if not "time" in array.dims:
            if "segment" in array.dims:
                return array.transpose("segment", "layer", "y", "x")
            else:
                return array.transpose("layer", "y", "x")
        else:
            if "segment" in array.dims:
                return array.transpose("segment", "time", "layer", "y", "x")
            else:
                return array.transpose("time", "layer", "y", "x")


class ModelFromToml:
    config: Dict
    simulation: imod.mf6.Modflow6Simulation
    flow_model: imod.mf6.GroundwaterFlowModel
    valid: ValidArray
    time: pd.date_range
    heads: xr.DataArray
    flow_budgets: xr.Dataset
    wadi_characteristics: Dict
    gwd_stage: bool
    mf6_continue: bool
    uzf_water_content: dict
    uzf_flow_budgets: dict

    def __init__(self, config: Dict) -> None:
        self.config = config["model"]
        self.simulation = imod.mf6.Modflow6Simulation(self.config["name"])
        self.flow_model = imod.mf6.GroundwaterFlowModel(newton=True)
        self._set_simulation_time()
        self._set_packages()
        self.simulation["GWF_1"] = self.flow_model
        self.transport_model = TransportModel(self.flow_model, self.config)
        self.simulation["GWT_1"] = self.transport_model.transport_model
        self._solvers(['GWF_1','GWT_1'])

    def _set_packages(self) -> None:
        self._oc()
        self._dis()
        self._npf()
        self._sto()
        self._ic()
        self._rch()
        self._rivs_drns()
        self._chd()
        self._evts()
        self._wadi()
        self._olf()

    def run(self, path: Path | str) -> None:
        path = make_path(path)
        self.print_log("wsim")
        self.simulation.write(path, binary=False, validate=True)
        self.print_log("rsim")
        self.simulation.run(mf6path=make_path(self.config["mf6_binaries"]) / "mf6.exe")
        self.print_log("rh")
        self.heads = self.get_heads()
        self.print_log("rb")
        self.flow_budgets = self.get_model_flow_budgets()
        self.print_log("rb_uzf")
        self.uzf_flow_budgets = self.get_uzf_flow_budgets(path)
        self.print_log("rwc_uzf")
        self.uzf_water_content = self.get_uzf_water_content(path)
        self.print_log("rc")
        self.model_concentrations = self.get_model_concentration()
        
    def run_coupled(self, path: Path | str) -> pd.DataFrame:
        path = make_path(path)
        if not hasattr(self, 'wadi_characteristics'):
            raise ValueError("No input was found for coupled run ...")
        self.print_log("wsim")
        self.simulation.write(path, binary=False, validate=True)
        self.transport_model.write_uzt(path)
        self.print_log("rsimc")
        log_ponding = run_coupled_model(
            1e10, str(path), "GWF_1", self.wadi_characteristics, make_path(self.config["mf6_binaries"]) / "libmf6.dll", self.mf6_continue,
        )
        self.print_log("rh")
        self.heads = self.get_heads()
        self.print_log("rb")
        self.flow_budgets = self.get_model_flow_budgets()
        self.print_log("rb_uzf")
        self.uzf_flow_budgets = self.get_uzf_flow_budgets(path)
        self.print_log("rwc_uzf")
        self.uzf_water_content = self.get_uzf_water_content(path)
        self.print_log("rc")
        self.model_concentrations = self.get_model_concentration()
        return log_ponding

    def print_log(self, logtype: str) -> None:
        LOG = {
            "wsim": "writing simulation: " + self.simulation.name,
            "rsim": "running simulation: " + self.simulation.name,
            "rsimc": "running coupled simulation: " + self.simulation.name,
            "rh": "reading heads output for: " + self.simulation.name,
            "rb": "reading model budgets output for: " + self.simulation.name,
            "rb_uzf": "reading uzf budgets output for: " + self.simulation.name,
            "rwc_uzf": "reading uzf water content output for: " + self.simulation.name,
            "rc": "reading model concentrations: " + self.simulation.name,
        }
        if logtype in LOG.keys():
            print(LOG[logtype])

    def _set_simulation_time(self) -> None:
        start = self.config["discretisation"]["start_date"]
        end = self.config["discretisation"]["end_date"]
        freq = str(self.config["discretisation"]["dt"]) + "D"
        time = pd.date_range(start=start, end=end, freq=freq)
        self.simulation.time_discretization(times=time)
        self.time = time

    def _oc(self) -> None:
        self.flow_model["oc"] = imod.mf6.OutputControl(save_head="all", save_budget="all")

    def _solvers(self,names:list) -> None:
        for name in names:
            if 'GWT' in name:
                self.simulation[f"solver_{name}"] = imod.mf6.SolutionPresetComplex(modelnames=[name])
                self.simulation[f"solver_{name}"]["outer_dvclose"] = 1.0
                self.simulation[f"solver_{name}"]["inner_dvclose"] = 1.0
                self.simulation[f"solver_{name}"]["inner_rclose"] = 1.0
                self.simulation[f"solver_{name}"]["outer_maximum"] = 1000
                self.simulation[f"solver_{name}"]["inner_maximum"] = 1000
            else:
                self.simulation[f"solver_{name}"] = imod.mf6.SolutionPresetComplex(modelnames=[name])
                self.mf6_continue = self.config["solver"]["continue"]
                self.simulation[f"solver_{name}"]["outer_dvclose"] = 0.001
                self.simulation[f"solver_{name}"]["inner_dvclose"] = 0.001
                self.simulation[f"solver_{name}"]["inner_rclose"] = 0.001
                self.simulation[f"solver_{name}"]["outer_maximum"] = 1000
                self.simulation[f"solver_{name}"]["inner_maximum"] = 1000

    def _dis(self) -> None:
        xmin, xmax, ymin, ymax = self._get_extent()
        top = xr.open_dataarray(self.config["discretisation"]["top"]).sel(
            y=slice(ymax, ymin), x=slice(xmin, xmax), drop=True
        )
        bottom_values = np.cumsum(
            np.array(self.config["discretisation"]["layer_thickness"])
        )
        bottom = top - layered_array_like(bottom_values, top)
        # 1 for active, -1 for vertical pass true cells
        # TODO: active nodes clippen op polygon?
        idomain = xr.ones_like(top)
        top_stacked = top.assign_coords(layer=0)
        top_stacked = xr.concat(
            [top_stacked, bottom.sel(layer=np.arange(bottom.layer.size - 1) + 1)],
            dim="layer",
        )
        top_stacked = top_stacked.assign_coords(layer=np.arange(bottom.layer.size) + 1)
        thickness = (top_stacked - bottom).transpose("layer", "y", "x")
        idomain = xr.where(thickness <= 0.0, -1, idomain).astype(dtype=np.int32)
        self.valid = ValidArray(idomain)
        self.flow_model["dis"] = imod.mf6.StructuredDiscretization(
            top=top,
            bottom=self.valid.array(bottom),
            idomain=self.valid.array(idomain),
        )

    def _get_extent(self) -> tuple[float, float, float, float]:
        if "shape" in self.config["discretisation"]["extent"]:
            path = self.config["discretisation"]["extent"]["shape"]
            bounds = (gpd.read_file(path).to_crs("EPSG:28992")).bounds
        else:
            bounds = self.config["discretisation"]["extent"]
        return (
            float(bounds["minx"]),
            float(bounds["maxx"]),
            float(bounds["miny"]),
            float(bounds["maxy"]),
        )

    def _ic(self) -> None:
        self.flow_model["ic"] = imod.mf6.InitialConditions(
            start=layered_array_like(
                self.config["boundary_conditions"]["initial_conditions"],
                self.flow_model["dis"]["top"],
            )
        )

    def _npf(self) -> None:
        k = self._get_parameters_array(self.config["properties"], "kh")
        k33 = self._get_parameters_array(self.config["properties"], "kv")
        icelltype = layered_array_like(
            self.config["properties"]["celltype"], self.flow_model["dis"]["idomain"]
        )
        self.flow_model["npf"] = imod.mf6.NodePropertyFlow(
            icelltype=self.valid.array(icelltype),
            k=self.valid.array(k),
            k33=self.valid.array(k33),
            save_flows=True,
            save_saturation=True,
            save_specific_discharge=True,
        )

    def _get_parameters_array(self, input: Dict, label: str) -> xr.DataArray:
        bottom = self.flow_model["dis"]["bottom"]
        # broadcast initial values
        k = layered_array_like(input[label], self.flow_model["dis"]["top"])
        # then add optional refinements
        if "refinement" in input:
            if label in input["refinement"]:
                for layer_label, shape_path in input["refinement"][label].items():
                    layer = int(layer_label.strip("layer_"))
                    rasterized = rasterize_polygon_column(
                        shape_path, label, bottom.sel(layer=layer)
                    )
                    rasterized = xr.where(
                        rasterized.notnull(), rasterized, k.sel(layer=layer)
                    )
                    k = xr.where(k.layer == layer, rasterized, k)
        return k

    def _sto(self) -> None:
        specific_storage = layered_array_like(
            self.config["properties"]["specific_storage"], self.flow_model["dis"]["top"]
        )
        if "wadi" in self.config["boundary_conditions"]:
            saturated_theta = layered_array_like(
                self.config["boundary_conditions"]["wadi"]["saturated_theta"],
                self.flow_model["dis"]["top"],
            )
            risidual_theta = layered_array_like(
                self.config["boundary_conditions"]["wadi"]["residual_theta"],
                self.flow_model["dis"]["top"],
            )
            specific_yield = saturated_theta - risidual_theta
        else:
            specific_yield = layered_array_like(
                self.config["properties"]["specific_yield"], self.flow_model["dis"]["top"]
            )
        celltype = layered_array_like(
            self.config["properties"]["celltype"], self.flow_model["dis"]["idomain"]
        )
        if self.config["properties"]["initial_steady-state_timestep"]:
            ntime = len(self.time)
            transient = xr.DataArray(
                data=np.array([False] + [True] * (ntime - 1)),
                coords={"time": self.time},
                dims=["time"],
            )
        else:
            transient = True
        self.flow_model["sto"] = imod.mf6.SpecificStorage(
            specific_storage=self.valid.array(specific_storage),
            specific_yield=self.valid.array(specific_yield),
            convertible=self.valid.array(celltype),
            transient=transient,
            save_flows=True,
        )

    def _rch(self) -> None:
        if not "recharge" in self.config["boundary_conditions"] or "wadi" in self.config["boundary_conditions"]:
            return
        if "recharge_date_format" in self.config["boundary_conditions"]:
            recharge, _ = self._get_rates_4d(date_format=self.config["boundary_conditions"]["recharge_date_format"])
            concentration = self._get_concentration_4d(date_format=self.config["boundary_conditions"]["recharge_date_format"])
        else:
            recharge, _ = self._get_rates_4d()
            concentration = self._get_concentration_4d()
        recharge_active = recharge.where(recharge.layer == self._top_active_layer()).sel(time = slice(self.time[0],self.time[-1]))
        self.flow_model["rch"] = imod.mf6.Recharge(
            rate=recharge_active, 
            save_flows=True, 
            concentration=concentration.where(recharge_active.notnull())
        )

    def _olf(self) -> None:
        if "wadi" in self.config["boundary_conditions"]:
            # in this case, runoff is dealt with in uzf-omgeving package. 
            return
        dxy = np.diff(self.flow_model["dis"]['idomain'].x)[0]
        elevation = self.flow_model["dis"]['top'].expand_dims(dim = {'layer': np.array([1])})
        self.flow_model["olf"] = imod.mf6.Drainage(
            elevation=elevation,
            conductance=xr.full_like(elevation, dxy / 0.1),
            save_flows=True,
            concentration=(species_array('species1', 0.0) * xr.ones_like(elevation)).where(elevation.notnull())
        )

    def _wadi(self) -> None:
        if not "wadi" in self.config["boundary_conditions"]:
            return
        if "start_date" not in self.config["boundary_conditions"]["wadi"]:
            tstart = 0.0
        else:
            time = self.config["boundary_conditions"]["wadi"]["start_date"]
            stime_wadi = pd.to_datetime(time)
            tstart = np.flatnonzero(stime_wadi > self.time)[-1]
        self.gwd_stage = self.config["boundary_conditions"]["wadi"]["gwd_stage"]
        target_grid = self.flow_model["dis"]["top"]
        wadi_mask = xr.ones_like(
            self.flow_model["dis"]["bottom"]
        ) * rasterize_polygon_column(
            self.config["boundary_conditions"]["wadi"]["location"],
            column_grid="wadi_index",
            grid=target_grid,
        )
        runoff_mask = rasterize_polygon_column(
            self.config["boundary_conditions"]["wadi"]["runoff"],
            column_grid="wadi_index",
            grid=target_grid,
        )
        self.wadi_characteristics = {}
        n = np.unique(wadi_mask)
        nwadi = n[np.isfinite(n)]
        wadi_shape = gpd.read_file(
            self.config["boundary_conditions"]["wadi"]["location"]
        )
        # uzf-instance per wadi
        for n, wadi in enumerate(nwadi):
            ar_mask_recharge = wadi_mask.where(wadi_mask == wadi)
            df_mask_recharge = wadi_shape["wadi_index"] == wadi
            # optional runoff to wadi
            ar_mask_runoff = runoff_mask.where(wadi_mask == wadi)
            dz = wadi_shape["dz"][df_mask_recharge].item()
            zmax = wadi_shape["zmax"][df_mask_recharge].item()
            inf_rate = wadi_shape["inf_rate"].item()
            c_bottom = wadi_shape["c_bottom"].item()
            self._uzf("wadi_" + str(int(wadi)), ar_mask_recharge, ar_mask_runoff)
            self.wadi_characteristics[
                "wadi_" + str(int(wadi))
            ] = make_ponding_characteristics(
                self.flow_model["dis"]["top"],
                ar_mask_recharge.isel(layer=0, drop=True),
                dz,
                zmax,
            )
            self.wadi_characteristics["wadi_" + str(int(wadi))][
                "initial_stage"
            ] = self.config["boundary_conditions"]["wadi"]["initial_stage"][n]
            self.wadi_characteristics["wadi_" + str(int(wadi))]["inf_rate"] = inf_rate
            self.wadi_characteristics["wadi_" + str(int(wadi))]["c_bottom"] = c_bottom
            self.wadi_characteristics["wadi_" + str(int(wadi))]["tstart"] = tstart

        self._uzf(
            "omgeving",
            xr.ones_like(self.flow_model["npf"]["k33"]).where(np.isnan(wadi_mask)),
        )

    def _uzf(
        self,
        name: str,
        mask: xr.DataArray | None = None,
        runoff_mask: xr.DataArray | None = None,
    ) -> None:
        surface_depression_depth = self._get_parameters_array(
            self.config["boundary_conditions"]["wadi"], "surface_depression_depth"
        )
        kv_sat = self.flow_model["npf"]["k33"]
        theta_res = self._get_parameters_array(
            self.config["boundary_conditions"]["wadi"], "residual_theta"
        )
        theta_sat = self._get_parameters_array(
            self.config["boundary_conditions"]["wadi"], "saturated_theta"
        )
        theta_init = self._get_parameters_array(
            self.config["boundary_conditions"]["wadi"], "initial_theta"
        )
        epsilon = self._get_parameters_array(
            self.config["boundary_conditions"]["wadi"], "epsilon"
        )

        # top active node for land-nodes
        landflag = xr.ones_like(kv_sat, dtype=np.int32).where(
            kv_sat.layer == self._top_active_layer(), other=0
        )
        # dummy array with zeros
        infiltration_rate = (
            xr.zeros_like(kv_sat)
            .expand_dims({"time": [self.time[0]]})
            .where(landflag == 1)
        )
        if "recharge" in self.config["boundary_conditions"]:
            if "recharge_date_format" in self.config["boundary_conditions"]:
                recharge, runoff = self._get_rates_4d(date_format=self.config["boundary_conditions"]["recharge_date_format"])
            else:
                recharge, runoff = self._get_rates_4d()
            infiltration_rate = self.valid.array(recharge.where(landflag == 1), mask).sel(time = slice(self.time[0],self.time[-1]))
            if runoff_mask is not None:
                runoff_mask = runoff_mask==1
                # add runoff that could be defined outside the defined masked area (runoff from surrounding area)
                n_surface_cell_wadi = (landflag == 1).where(mask==1).sum()
                summed_runoff = runoff.where(runoff_mask).sum(dim=['y','x','layer'])
                infiltration_rate = infiltration_rate + (summed_runoff / n_surface_cell_wadi)
        simulate_groundwater_seepage = True
        if self.gwd_stage:
            simulate_groundwater_seepage = False
        self.flow_model[name] = imod.mf6.UnsaturatedZoneFlow(
            surface_depression_depth=self.valid.array(surface_depression_depth, mask),
            kv_sat=self.valid.array(kv_sat, mask),
            theta_res=self.valid.array(theta_res, mask),
            theta_sat=self.valid.array(theta_sat, mask),
            theta_init=self.valid.array(theta_init, mask),
            epsilon=self.valid.array(epsilon, mask),
            infiltration_rate=self.valid.array(infiltration_rate, mask),
            simulate_groundwater_seepage=simulate_groundwater_seepage,  # see drn-package below
            save_flows=True,
            budgetcsv_fileout="GWF_1/budgets_sum_uzf_" + name + ".csv",
            budget_fileout="GWF_1/budgets_uzf_" + name + ".cbc",
            water_content_file="GWF_1/budgets_uzf_" + name + ".wc",
            nwavesets= 60,
        )
        self.flow_model[name].dataset["landflag"] = landflag.where(np.isfinite(mask))
        if self.gwd_stage:
            # Create drainage package for surface runoff (gwd). We don’t use the gwd functionality of UZF-package
            # since this can’t be updated with the waterlevels of the ponding reservoir.
            mask = mask.isel(layer=0, drop=True).expand_dims(
                dim={"layer": np.array([1])}
            )
            top = self.flow_model["dis"]["top"].expand_dims(dim={"layer": np.array([1])})
            k = kv_sat.isel(layer=0, drop=True).expand_dims(
                dim={"layer": np.array([1])}
            )
            conductance = k * top.dx * -top.dy
            self.flow_model[name + "_gwd"] = imod.mf6.Drainage(
                elevation=self.valid.array(top, mask),
                conductance=self.valid.array(conductance, mask),
                save_flows=True,
            )

    def _get_rates_4d(self, date_format: str | None = None) -> xr.DataArray:
        nlay = self.config["discretisation"]["nlayers"]
        fraction_unpaved = xr.open_dataarray(
            self.config["boundary_conditions"]["fraction_unpaved"]
        ).expand_dims({"layer": np.arange(nlay) + 1})
        if date_format is None:
            df = pd.read_excel(self.config["boundary_conditions"]["recharge"], index_col=0)  
        else:  
            df = pd.read_excel(self.config["boundary_conditions"]["recharge"])  
            df['time'] = pd.to_datetime(df['time'], format = date_format)
            df = df.set_index('time')
        recharge_mm = df["precipitation"].to_xarray() * fraction_unpaved
        runoff_mm = df["precipitation"].to_xarray() * (1 - fraction_unpaved)
        return recharge_mm.where(recharge_mm.layer == 1) * 0.001, runoff_mm.where(runoff_mm.layer == 1) * 0.001

    def _rivs_drns(self) -> None:
        if not "drainage_infiltration" in self.config["boundary_conditions"]:
            return
        for sys in self.config["boundary_conditions"]["drainage_infiltration"]:
            self._riv_drn(sys)

    def _riv_drn(self, input: Dict[str, str]) -> None:
        name_system = input["name"]
        shape = gpd.read_file(input["shape"]).to_crs("EPSG:28992")
        if isinstance(shape.geometry[0], LineString):
            file = input["shape"].strip(".shp") + "_buffered.shp"
            # buffer line
            buffered_line = shape
            buffered_line.geometry = buffered_line.geometry.buffer(shape["width"] / 2)
            buffered_line.to_file(file, crs = "EPSG:28992")
            (
                stage,
                conductance_riv,
                conductance_drn,
                bottom,
            ) = self.riv_drn_arrays_from_lines(file)
        elif isinstance(shape.geometry[0], Polygon):
            (
                stage,
                conductance_riv,
                conductance_drn,
                bottom,
            ) = self.riv_drn_arrays_from_polygons(input["shape"])
        else:
            check = type(shape.geometry[0])
            raise TypeError(
                f"Error; expected Polygon or LineString format, received {check}"
            )
        # broadcast to right layer based on bottom level
        active = self._active_layer(bottom)
        stage = (stage * xr.ones_like(self.flow_model["dis"]["top"])).where(active)
        conductance_riv = (
            conductance_riv * xr.ones_like(self.flow_model["dis"]["top"])
        ).where(active)
        conductance_drn = (
            conductance_drn * xr.ones_like(self.flow_model["dis"]["top"])
        ).where(active)
        bottom = (bottom * xr.ones_like(self.flow_model["dis"]["top"])).where(active)
        if conductance_drn.notnull().any():
            concentration = self._concentration(input, self.valid.array(conductance_drn, stage))
            # assign drainage conductance if infiltration factor < 1
            # if infiltration factor == 1, all conductance is in riv-package
            self.flow_model[name_system + "_dr"] = imod.mf6.Drainage(
                elevation=self.valid.array(stage),
                conductance=self.valid.array(conductance_drn, stage),
                save_flows=True,
                concentration=concentration,
            )
        elif conductance_riv.notnull().any():
            concentration = self._concentration(input, self.valid.array(conductance_riv, stage))
            # assign infiltration if infiltration factor > 0
            # if infiltration factor == 0, all conductance is in drn-package
            self.flow_model[name_system + "_inf"] = imod.mf6.River(
                stage=self.valid.array(stage),
                conductance=self.valid.array(conductance_riv, stage),
                bottom_elevation=self.valid.array(bottom, stage),
                save_flows=True,
                concentration=concentration,
            )
        else:
            raise ValueError(f"check input of boundary condition {name_system}. No valid paramaterisation was derived!")

    def _chd(self) -> None:
        if not "constant_head" in self.config["boundary_conditions"]:
            return
        bottom = self.flow_model["dis"]["bottom"]
        # get boundary cells
        idomain = self.flow_model["dis"]["idomain"].sel(layer=1, drop=True)
        boundary_grid = xr.zeros_like(idomain).where(idomain == 1)
        boundary_grid.values = binary_dilation(
            boundary_grid.astype(dtype=np.int32), border_value=1
        )
        boundary_grid = boundary_grid.expand_dims(dim={"layer": bottom.layer})
        # get constants per defined layer and broadcast to 3D-array
        constants = []
        for layer in bottom.layer:
            label = "layer_" + str(int(layer))
            if label in self.config["boundary_conditions"]["constant_head"]:
                value = self.config["boundary_conditions"]["constant_head"][label]
                constants.append(value)
            else:
                constants.append(np.nan)
        chd = layered_array_like(constants, bottom).where(boundary_grid == 1)
        # for Newton formulation; take max of chd and layer bottom
        chd = xr.where(chd < bottom, bottom, chd)
        # optional concentrations
        concentration = None
        if "constant_concentration" in self.config["boundary_conditions"]:
            constants = []
            for layer in bottom.layer:
                label = "layer_" + str(int(layer))
                if label in self.config["boundary_conditions"]["constant_concentration"]:
                    value = self.config["boundary_conditions"]["constant_concentration"][label]
                    constants.append(value)
                else:
                    constants.append(np.nan)
            concentration = layered_array_like(constants, bottom).where(boundary_grid == 1)
            species = self.config["boundary_conditions"]["constant_concentration"]["species"]
            concentration = species_array(species, concentration)
        self.flow_model["chd"] = imod.mf6.ConstantHead(
            head=self.valid.array(chd),
            save_flows=True,
            concentration=concentration,
        )

    def _evts(self) -> None:
        if not "evapotranspiration" in self.config["boundary_conditions"]:
            return
        if isinstance(self.config["boundary_conditions"]["evapotranspiration"], list):
            for sys in self.config["boundary_conditions"]["evapotranspiration"]:
                date_format = None
                if "maximum_rate_date_format" in sys:
                    date_format = sys["maximum_rate_date_format"]
                self.config["boundary_conditions"]["evapotranspiration"]
                self._evt(sys, date_format)
        else:
            sys = self.config["boundary_conditions"]["evapotranspiration"]
            date_format = None
            if 'maximum_rate_date_format' in sys:
                    date_format = sys["maximum_rate_date_format"]
            self._evt(self.config["boundary_conditions"]["evapotranspiration"], date_format)

    def _evt(self, input: Dict[str, str], date_format: str | None = None) -> None:
        bot = self.flow_model["dis"]["bottom"].sel(layer=1)
        top = self.flow_model["dis"]["top"].expand_dims({"layer": np.array([1])})
        if date_format is None:
            df = pd.read_excel(input["maximum_rate"], index_col=0)  
        else:  
            df = pd.read_excel(input["maximum_rate"])  
            df['time'] = pd.to_datetime(df['time'], format = date_format)
            df = df.set_index('time')
        df.index = df.index.round("H")
        maximum_rate_constants = df["evapotranspiration"].to_xarray().sel(time = slice(self.time[0],self.time[-1]))
        maximum_rate = maximum_rate_constants * xr.ones_like(top) 
        maximum_rate = maximum_rate * 0.001 # conversion mm/d -> m/d
        root_depth = rasterize_polygon_column(input["vegetation"], "root_depth", bot)
        segment_rate = rasterize_polygon_columns(
            input["vegetation"], "seg_q", bot, "segment"
        ).expand_dims({"layer": np.array([1])})
        segement_depths = rasterize_polygon_columns(
            input["vegetation"], "seg_d", bot, "segment"
        ).expand_dims({"layer": np.array([1])})
        nseg = int(segement_depths.segment.values[-1])
        proportion_rate = segment_rate / maximum_rate
        proportion_depth = segement_depths / segement_depths.sel(
            segment=nseg, drop=True
        )
        proportion_rate = xr.where(proportion_rate >= 1, 0.9999, proportion_rate)
        proportion_depth = xr.where(proportion_depth >= 1, 0.9999, proportion_depth)
        # concentration = None
        # for name in df.columns:
        #     if 'concentration' in name:
        #         concentration= df[name].to_xarray().sel(time = slice(self.time[0],self.time[-1])) * xr.ones_like(top) 
        #         concentration = self.valid.array(concentration, root_depth)
        #         concentration = species_array(name, concentration)
        self.flow_model[input["name"]] = imod.mf6.Evapotranspiration(
            surface=self.valid.array(top - root_depth, root_depth),
            rate=self.valid.array(maximum_rate, root_depth),
            depth=self.valid.array(
                segement_depths.sel(segment=nseg, drop=True), root_depth
            ),
            proportion_rate=self.valid.array(proportion_rate, root_depth),
            proportion_depth=self.valid.array(proportion_depth, root_depth),
            save_flows=True,
            # concentration = concentration,
        )
        # log for postprocessing
        self.segment_rate = segment_rate
        self.segment_depth = segement_depths
        self.top = top

    def _concentration(self, input:dict, mask: xr.DataArray):
        concentration = None
        for name in input.keys():
            if 'concentration' in name:
                ic = input[name]
                if isinstance(ic, str):
                    if 'xlsx' in ic:
                       concentration = self._get_concentration_4d().where(mask.notnull())
                    elif 'nc' in ic:
                        concentration = xr.open_dataarray(ic).where(mask.notnull())
                else:
                    concentration = (species_array(name, ic) * xr.ones_like(mask)).where(mask.notnull())
        return concentration

    def riv_drn_arrays_from_lines(
        self, file: str
    ) -> [xr.DataArray, xr.DataArray, xr.DataArray, xr.DataArray, xr.DataArray]:
        stage = self.rasterize_line_column(file, "stage")
        if stage.isnull().all():
            raise Exception(
                "provided shape does not match current model domain; check for correct id"
            )
        inf_factor = self.rasterize_line_column(file, "inf_factor")
        area = self.rasterize_line_column(
            file, "area"
        )
        resistance = self.rasterize_line_column(file, "c_drain")
        conductance =  area / resistance
        conductance_riv = conductance * inf_factor
        conductance_drn = conductance * (1 - inf_factor)
        bottom = self.rasterize_line_column(file, "bottom")
        return (
            stage,
            conductance_riv.where(conductance_riv > 0.0),
            conductance_drn.where(conductance_drn > 0.0),
            bottom,
        )

    def riv_drn_arrays_from_polygons(
        self, file: str
    ) -> [xr.DataArray, xr.DataArray, xr.DataArray, xr.DataArray, xr.DataArray]:
        top = self.flow_model["dis"]["top"]
        stage = rasterize_polygon_column(file, "stage", top)
        if stage.isnull().all():
            raise Exception(
                "provided shape does not match current model domain; check for correct id"
            )
        inf_factor = rasterize_polygon_column(file, "inf_factor", top)
        area = top.dx * -top.dy
        conductance = area / rasterize_polygon_column(file, "c_drain", top)
        conductance_riv = conductance * inf_factor
        conductance_drn = conductance * (1 - inf_factor)
        bottom = rasterize_polygon_column(file, "bottom", top)
        return (
            stage,
            conductance_riv.where(conductance_riv > 0.0),
            conductance_drn.where(conductance_drn > 0.0),
            bottom,
        )
    
    def _get_concentration_4d(self, date_format: str | None = None, label: str = "concentration") -> xr.DataArray:
        mask = xr.ones_like(self.flow_model['dis']['bottom'], dtype = np.float64)
        df = pd.read_excel(self.config["boundary_conditions"]["recharge"])  
        labels = []
        for column in df.columns:
            if label in column:
                labels.append(column)
        if date_format is None:
            df = df.set_index(df.columns[0])
        else:  
            df['time'] = pd.to_datetime(df['time'], format = date_format)
            df = df.set_index('time')
        concentration = (df[labels[0]].to_xarray() * mask).sel(time = slice(self.time[0], self.time[-1]))
        return species_array(labels[0].split('_')[-1],concentration)

    def rasterize_line_column(self, file: str, column_grid: str) -> xr.DataArray:
        like = xr.full_like(self.flow_model["dis"]["top"], fill_value=np.nan)
        column = column_grid
        if column_grid.lower() == "area":
            column = "id"
        celltable = imod.prepare.celltable(
            file, column=column, resolution=0.1, like=like, dtype = np.float64
        )
        if 'id' in celltable.columns:
            celltable.id = 1.0
        raster = imod.prepare.rasterize_celltable(
            celltable, column=column, like=like
        )
        return raster

    def _top_active_layer(self) -> xr.DataArray:
        # Gets top active layer
        active = self.flow_model["dis"]["idomain"] > 0
        ones = xr.ones_like(active)
        return (ones * ones.layer).where(active).idxmin(dim="layer")

    def _active_layer(self, bottom_elevation: xr.DataArray) -> xr.DataArray:
        active = self.flow_model["dis"]["idomain"] > 0
        dis_bottom = self.flow_model["dis"]["bottom"].where(active)
        dis_top = self.flow_model["dis"]["top"].assign_coords(layer=0)
        dis_top = xr.concat(
            [dis_top, dis_bottom.sel(layer=np.arange(dis_bottom.layer.size - 1) + 1)],
            dim="layer",
        )
        dis_top = dis_top.assign_coords(
            layer=np.arange(dis_bottom.layer.size) + 1
        ).where(active)
        # correct for riv_bottom > dis_bottom of layer 1
        bottom_elevation = xr.where(
            bottom_elevation > dis_bottom.sel(layer=1),
            dis_bottom.sel(layer=1),
            bottom_elevation,
        )
        return xr.where(
            (bottom_elevation <= dis_top) & (bottom_elevation >= dis_bottom),
            True,
            False,
        )

    def get_heads(self) -> xr.DataArray:
        heads = self.simulation.open_head()
        time_min = pd.to_datetime(self.config["discretisation"]["start_date"])
        timedelta = pd.to_timedelta(heads["time"], "D")
        return heads.assign_coords(time=time_min + timedelta)

    def get_model_flow_budgets(self) -> dict | None:
        cbc = self.simulation.open_flow_budget()
        out = {}
        if cbc == {}:
            print("No flow budgets were saved for simulation!")
            return None
        time_min = pd.to_datetime(self.config["discretisation"]["start_date"])
        for key in cbc.keys():
            timedelta = pd.to_timedelta(cbc[key]["time"], "D")
            out[key] = cbc[key].assign_coords(time=time_min + timedelta)
            # cbc[key]['time'] = time
            # out[key] = cbc[key]
        return out

    def get_uzf_flow_budgets(self, model_path=Path | str) -> dict | None:
        model_path = make_path(model_path)
        out = {}
        grb_file = self.simulation._get_grb_path("GWF_1")
        for name, package in self.simulation["GWF_1"].items():
            if isinstance(package, imod.mf6.UnsaturatedZoneFlow):
                print("uzf-budgets: " + name)
                file = "budgets_uzf_" + name + ".cbc"
                cbc_file = model_path / "GWF_1" / file
                out[name] = imod.mf6.open_cbc(cbc_file, grb_file)
                # assign time coord to all variables
                time = self.simulation["time_discretization"]["time"]
                for variable in out[name].keys():
                    out[name][variable]["time"] = time
        return out

    def get_uzf_water_content(self, model_path=Path | str) -> dict | None:
        out = {}
        grb_file = self.simulation._get_grb_path("GWF_1")
        time_min = pd.to_datetime(self.config["discretisation"]["start_date"])
        for name, package in self.simulation["GWF_1"].items():
            if isinstance(package, imod.mf6.UnsaturatedZoneFlow):
                kv_sat = package["kv_sat"]
                nlay, nrow, ncol = kv_sat.shape
                indices = np.arange(nlay * nrow * ncol)[
                    kv_sat.notnull().to_numpy().flatten()
                ]
                print("uzf-budgets: " + name)
                file = "budgets_uzf_" + name + ".wc"
                wc_file = Path(model_path) / "GWF_1" / file
                out[name] = imod.mf6.open_dvs(wc_file, grb_file, indices)
                # assign time coord to all variables
                timedelta = pd.to_timedelta(out[name]["time"], "D")
                out[name] = out[name].assign_coords(time=time_min + timedelta)
        return out
    
    def get_model_concentration(self,):
        return self.simulation.open_concentration(['GWT_1'], simulation_start_time=self.time[0])
    
    def get_uzf_concentration(self,):
        return self.transport_model.get_uzt_water_concentration(self.simulation)


class ScenariosFromToml:
    reference: ModelFromToml
    scenario: ModelFromToml
    heads_difference: xr.DataArray
    log_ponding_reference: Dict
    log_ponding_scenario: Dict

    def __init__(self, config: Dict) -> None:
        self.reference = ModelFromToml(config)
        self.scenario = self._scenario_instance(config)

    def run(self, path: Path | str) -> None:
        path = make_path(path)
        self.reference.run(path / "reference")
        self.scenario.run(path / "scenario")
        self.heads_difference = self.scenario.heads - self.reference.heads

    def run_coupled(self, path: Path | str) -> None:
        path = make_path(path)
        self.log_ponding_reference = self.reference.run_coupled(path / "reference")
        self.log_ponding_scenario = self.scenario.run_coupled(path / "scenario")
        self.heads_difference = self.scenario.heads - self.reference.heads

    def _supported_methods(self, model: ModelFromToml) -> dict[str, list[Callable]]:
        return {
            "initial_conditions": [model._ic],
            "recharge": [model._rch],
            "drainage_infiltration": [model._rivs_drns],
            "constant_head": [model._chd],
            "evapotranspiration": [model._evts],
            "wadi": [model._wadi],
            "properties": [model._npf, model._sto],
        }

    # TODO:

    def _scenario_instance(self, config: Dict) -> ModelFromToml:
        scenario = ModelFromToml(config)
        supported_methods = self._supported_methods(scenario)
        # update config atribute in ModelFromToml instance for scenario model
        if "properties" in config["scenario"].keys():
            scenario.config["properties"] = config["scenario"]["properties"]
            scenario.config["name"] = config["scenario"]['name']
            # update methods based on scenario input
            for method in supported_methods["properties"]:
                method()
        if "boundary_conditions" in config["scenario"].keys():
            scenario.config["boundary_conditions"].update(config["scenario"]["boundary_conditions"])
            scenario.config["name"] = config["scenario"]['name']
            # update methods based on scenario input
            for boundary_type in config["scenario"]["boundary_conditions"].keys():
                if boundary_type not in supported_methods.keys():
                    raise ValueError(
                        f"provided package for scenario is not supported, supported packages are: {list(supported_methods.keys())}"
                    )
                # boundary conditions has a list of size 1.
                supported_methods[boundary_type][0]()
        # update name
        scenario.simulation.name = config["scenario"]["name"]
        return scenario


def rasterize_polygon_column(
    file: str, column_grid: str, grid: xr.DataArray
) -> xr.DataArray:
    shape = gpd.read_file(file).to_crs("EPSG:28992")
    return imod.prepare.rasterize(
        shape,
        column=column_grid,
        like=grid,
        fill=np.nan,
    )


def rasterize_polygon_columns(
    file: str, column_grid: str, grid: xr.DataArray, dim: str
) -> xr.DataArray:
    shape = gpd.read_file(file).to_crs("EPSG:28992")
    ncolumns = 0
    for name in shape.keys():
        if column_grid in name:
            ncolumns += 1
    columns_arrays_list = []
    for icolumn in range(1, ncolumns + 1):
        array = imod.prepare.rasterize(
            shape,
            column=column_grid + str(icolumn),
            like=grid,
            fill=np.nan,
        )
        array = array.expand_dims({dim: np.array([icolumn])})
        columns_arrays_list.append(array)
    return xr.concat(columns_arrays_list, dim)


def layered_array_like(data_list: List, like: xr.DataArray) -> xr.DataArray:
    return (
        xr.DataArray(
            data=np.array(data_list),
            coords={
                "layer": np.arange(len(data_list)) + 1,
            },
            dims=["layer"],
        )
        * xr.ones_like(like)
    ).astype(like.dtype)


def make_path(string: Path | str) -> Path:
    if isinstance(string, Path):
        return string
    else:
        return Path(string)

def species_array(label:str, concentration: xr.DataArray | np.float64):
    species = xr.DataArray(
        data = np.array([1]),
        coords = {
                'species': [label.split('_')[-1]],
        },
        dims = ['species']
    )
    return species * concentration