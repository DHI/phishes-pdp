# %%
from typing import Dict, List
import imod
import xarray as xr
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import os
from src.generation.create_models_flow import ScenariosFromToml
from src.postprocessing.water_balance import PlotDiff
import numpy as np

class PostprocessModels:
    reference_heads: xr.DataArray
    scenario_heads: xr.DataArray
    heads_difference: xr.DataArray

    def __init__(self, model_results: ScenariosFromToml) -> None:
        self.model_results = model_results
        self.reference_heads = model_results.reference.heads
        self.reference_flow_budgets = model_results.reference.flow_budgets
        self.scenario_heads = model_results.scenario.heads
        self.scenario_flow_budgets = model_results.scenario.flow_budgets
        self.heads_difference = model_results.heads_difference
        self.reference_uzf_flow_budgets = self.model_results.reference.uzf_flow_budgets
        self.scenario_uzf_flow_budgets = self.model_results.scenario.uzf_flow_budgets
        self.reference_uzf_water_content = self.model_results.reference.uzf_water_content
        self.scenario_uzf_water_content = self.model_results.scenario.uzf_water_content
        self.time= model_results.reference.simulation['time_discretization']['time'].to_numpy()

    def _filter_depth_to_layer(self, z, x, y):
        bottom_arr = self.model_results.reference.flow_model['dis']['bottom']
        top_arr1 = self.model_results.reference.flow_model['dis']['top'].assign_coords({'layer': 1})
        top_arr2 = bottom_arr.sel(layer = slice(1,bottom_arr.layer[-2])).assign_coords({'layer':bottom_arr.layer[1:]})
        top_arr = xr.concat([top_arr1,top_arr2], dim = 'layer')
        bottom_arr.sel(layer = slice(2,bottom_arr.layer[-1])).assign_coords({'layer':bottom_arr.layer[1:]})
        top_arr.name = 'top'
        topbot = (imod.select.points_values(bottom_arr , x=x, y=y)
                 .to_dataframe()
                 .reset_index()
                 .rename(columns={"index": "id"})
        ).set_index('id').merge(imod.select.points_values(top_arr , x=x, y=y)
                 .to_dataframe()
                 .reset_index()
                 .rename(columns={"index": "id"})
        ).set_index('id')
        layers = []
        for id in np.unique(topbot.index):
            # always fit to model z domain
            zfit = max(z[id],topbot.loc[id]['bottom'].min() - 0.0001) # maximize bottom last layer
            zfit = min(z[id ],topbot.loc[id]['top'].max())    # minimize top first layer
            layers.append(topbot.loc[id]['layer'][(zfit > topbot.loc[id]['bottom']) & (zfit <= topbot.loc[id]['top'])].item())
        return np.array(layers)
        
    def _get_extend(self) -> tuple[float, float, float, float]:
        xmin = float(self.reference_heads.x[0])
        xmax = float(self.reference_heads.x[-1])
        ymin = float(self.reference_heads.y[-1])
        ymax = float(self.reference_heads.y[0])
        return xmin, xmax, ymin, ymax
    
    def plot_ponding_reservoir_stage(self, path: Path | str, measurements: pd.DataFrame):
        path = Path(path)
        df_ref = self.model_results.log_ponding_reference
        df_sc = self.model_results.log_ponding_scenario
        fig, ax = plt.subplots()
        ax.plot(self.time,df_ref['stage'], label = 'stage ref')
        ax.plot(self.time,df_sc['stage'], label = 'stage scenario')
        ax.scatter(measurements['time'], measurements['measurements'], label="measurements")
        ax.set_ylabel('stage [mNAP]')
        ax.set_xlabel('Time [day')
        ax.legend()
        plt.tight_layout()
        plt.savefig(path / "stage_ponding_reservoir.png")
        plt.close()

    def plot_ponding_reservoir(self, path: Path | str | None = None):
        path = Path(path)
        df_ref = self.model_results.log_ponding_reference
        df_sc = self.model_results.log_ponding_scenario
        fig, ax = plt.subplots(2,2)
        ax[0,0].plot(df_ref['time'],df_ref['volume'],label = 'volume ref', color='orange')
        ax[0,0].plot(df_ref['time'],df_sc['volume'],'--',label = 'volume scenario', color='orange')
        ax[0,0].set_ylabel('volume [m3]')
        ax[0,0].set_xlabel('Time [day')
        ax[0,0].legend()

        ax[0,1].plot(df_ref['time'],df_ref['stage'],label = 'stage ref', color='orange')
        ax[0,1].plot(df_ref['time'],df_sc['stage'], '--', label = 'stage scenario', color='orange')
        ax[0,1].set_ylabel('stage [mNAP]')
        ax[0,1].set_xlabel('Time [day')
        ax[0,1].legend()

        ax[1,0].plot(df_ref['time'],df_ref['volume_excess_out'],label = 'excess runoff out', color = 'orange')
        ax[1,0].plot(df_ref['time'],df_ref['realised_infiltration_out'],label = 'infiltration out', color = 'green')
        ax[1,0].plot(df_ref['time'],df_sc['volume_excess_out'], '--', color = 'orange')
        ax[1,0].plot(df_ref['time'],df_sc['realised_infiltration_out'], '--', color = 'green')
        ax[1,0].set_ylabel('flux [m3/t]')
        ax[1,0].set_xlabel('Time [day')
        ax[1,0].legend()

        ax[1,1].plot(df_ref['time'],df_ref['groundwater_discharge_in'],label = 'groundwater discharge in', color = 'orange')
        ax[1,1].plot(df_ref['time'],df_ref['rejected_infiltration_in'],label = 'rejected infiltration in', color = 'green')
        ax[1,1].plot(df_ref['time'],df_ref['uzf_infiltration_in'],label = 'runon UZF', color = 'blue')
        ax[1,1].plot(df_ref['time'],df_sc['groundwater_discharge_in'],'--', color = 'orange')
        ax[1,1].plot(df_ref['time'],df_sc['rejected_infiltration_in'],'--',  color = 'green')
        ax[1,1].plot(df_ref['time'],df_sc['uzf_infiltration_in'],'--',  color = 'blue')

        ax[1,1].set_ylabel('flux [m3/t]')
        ax[1,1].set_xlabel('Time [day')
        ax[1,1].legend()
        plt.tight_layout()
        plt.savefig(path / "waterbalance_ponding_reservoir.png")
        plt.close()

    def plot_ponding_reservoir_debug(self, path: Path | str | None = None):
        path = Path(path)
        df_ref = self.model_results.log_ponding_reference
        df_sc = self.model_results.log_ponding_scenario
        
        # first ref
        dt = np.diff(df_ref['time'])[0]
        infiltration = self.model_results.reference.uzf_flow_budgets['wadi_1']['infiltration_wadi_1'].sum(dim = ['y', 'x','layer']).to_numpy()
        rej_infiltration = self.model_results.reference.uzf_flow_budgets['wadi_1']['rej-inf_wadi_1'].sum(dim = ['y', 'x','layer']).to_numpy() 
        gwf = self.model_results.reference.uzf_flow_budgets['wadi_1']['gwf_gwf_1'].sum(dim = ['y', 'x','layer']).to_numpy() 
        gwf_discharge = self.model_results.reference.flow_budgets['uzf-gwd_wadi_1'].sum(dim = ['y', 'x','layer']).to_numpy()
        
        fig, ax = plt.subplots(2,2)
        ax[0,0].plot(df_ref['time'], df_ref['realised_infiltration_out'], label = 'infiltration ponding')
        ax[0,0].plot(df_ref['time'], infiltration * dt, '--', label = 'infiltration uzf')
        ax[0,0].plot(df_ref['time'], df_ref['rejected_infiltration_in'], label = 'rej-infiltration ponding')
        ax[0,0].plot(df_ref['time'],  -rej_infiltration * dt, '--', label = 'rej-infiltration uzf')
        ax[0,0].plot(df_ref['time'], df_ref['groundwater_discharge_in'], color = 'blue', label = 'gw-discharge ponding')
        ax[0,0].plot(df_ref['time'],  -gwf_discharge * dt, '--', label = 'gw-discharge uzf')
        ax[0,0].set_ylabel('flux [m3/t]')
        ax[0,0].set_title('reference')
        ax[0,0].legend()

        ax[1,0].plot(df_ref['time'], df_ref['realised_infiltration_out'], label = 'infiltration')
        ax[1,0].plot(df_ref['time'],- gwf * dt, label = 'groundwater recharge')
        ax[1,0].set_ylabel('flux [m3/t]')
        ax[1,0].set_xlabel('Time [day]')
        ax[1,0].legend()

        # than scenario
        dt = np.diff(df_ref['time'])[0]
        infiltration = self.model_results.scenario.uzf_flow_budgets['wadi_1']['infiltration_wadi_1'].sum(dim = ['y', 'x','layer']).to_numpy()
        rej_infiltration = self.model_results.scenario.uzf_flow_budgets['wadi_1']['rej-inf_wadi_1'].sum(dim = ['y', 'x','layer']).to_numpy() 
        gwf = self.model_results.scenario.uzf_flow_budgets['wadi_1']['gwf_gwf_1'].sum(dim = ['y', 'x','layer']).to_numpy() 
        gwf_discharge = self.model_results.scenario.flow_budgets['uzf-gwd_wadi_1'].sum(dim = ['y', 'x','layer']).to_numpy()
 
        ax[0,1].plot(df_sc['time'], df_sc['realised_infiltration_out'], label = 'infiltration ponding')
        ax[0,1].plot(df_sc['time'], infiltration * dt, '--', label = 'infiltration uzf')
        ax[0,1].plot(df_sc['time'], df_sc['rejected_infiltration_in'], label = 'rej-infiltration ponding')
        ax[0,1].plot(df_sc['time'],  -rej_infiltration * dt, '--', label = 'rej-infiltration uzf')
        ax[0,1].plot(df_sc['time'], df_sc['groundwater_discharge_in'], color = 'blue', label = 'gw-discharge ponding')
        ax[0,1].plot(df_sc['time'],  -gwf_discharge * dt, '--', label = 'gw-discharge uzf')
        ax[0,1].set_ylabel('flux [m3/t]')
        ax[0,1].set_title('scenario')
        ax[0,1].legend()

        ax[1,1].plot(df_sc['time'], df_sc['realised_infiltration_out'], label = 'infiltration')
        ax[1,1].plot(df_sc['time'],- gwf * dt, label = 'groundwater recharge')
        ax[1,1].set_ylabel('flux [m3/t]')
        ax[1,1].set_xlabel('Time [day]')
        ax[1,1].legend()

        plt.tight_layout()
        plt.savefig(path / "waterbalance_ponding_DEBUG.png")
        plt.close()


    def plot_evaporation_reduction(
        self, mask: xr.DataArray, package_name: str, path:str | Path
    ) -> None:
        path = Path(path) # force to path
        ok = False
        for name in self.reference_flow_budgets.keys():
            if package_name in name:
                ok = True
                budget_name = name
                break
        if ok:
            area = np.diff(self.model_results.scenario.flow_model[package_name]['rate'].x)[0]**2
            et_act = -(self.reference_flow_budgets[budget_name] / area).where(mask>0).mean(dim = ['layer','y','x']) * 1000
            et_ref = self.model_results.reference.flow_model[package_name]['rate'].where(mask>0).mean(dim = ['layer','y','x']) * 1000
            et_dif = et_ref - et_act
            x = np.arange(et_act.shape[0])
            fig, ax = plt.subplots(2)
            ax[0].plot(x, et_act, label = 'et-act')
            ax[0].plot(x, et_ref[:-1], '--', label = 'et-ref')
            ax[0].set_title('evapotranspiratie reference')
            ax[0].set_ylabel('Flux [mm/day]')
            ax[0].set_xlabel('Time [stress-periods]')
            ax[0].legend()
            ax[1].plot(et_dif, label = 'reduction')
            ax[1].set_ylabel('Flux [mm/day]')
            ax[1].set_xlabel('Time [stress-periods]')
            ax[1].legend()
            plt.savefig(path / 'waterbalance_et_reference.png')
            plt.close()
        else:
            ok1 = False
        ok = False
        for name in self.scenario_flow_budgets.keys():
            if package_name in name:
                ok = True
                budget_name = name
                break
        if ok:
            area = np.diff(self.model_results.scenario.flow_model[package_name]['rate'].x)[0]**2
            et_act = -(self.scenario_flow_budgets[budget_name] / area).where(mask>0).mean(dim = ['layer','y','x']) * 1000
            et_ref = self.model_results.scenario.flow_model[package_name]['rate'].where(mask>0).mean(dim = ['layer','y','x']) * 1000
            et_dif = (et_ref - et_act)
            x = np.arange(et_act.shape[0])
            fig, ax = plt.subplots(2)
            ax[0].plot(x, et_act, label = 'et-act')
            ax[0].plot(x, et_ref[:-1], '--', label = 'et-ref')
            ax[0].set_title('evapotranspiratie scenario')
            ax[0].set_ylabel('Flux [mm/day]')
            # ax[0].set_xlabel('Time [stress-periods]')
            ax[0].legend()
            ax[1].plot(x, et_dif, label = 'reduction')
            ax[1].set_ylabel('Flux [mm/day]')
            ax[1].set_xlabel('Time [stress-periods]')
            ax[1].legend()
            plt.savefig(path / 'waterbalance_et_scenario.png')
            plt.close()
        else:
            ok2=False
        if not ok1 and not ok2:
            raise ValueError(f'package {package_name} does not exist in both models')

    def plot_flow_budgets(
        self, mask:xr.DataArray, path: Path | str | None = None
    ) -> None:
        path = Path(path) # force to path
        plot = PlotDiff(mask, self.reference_flow_budgets, self.scenario_flow_budgets)
        ax1 = plot.budgets1.plot(remove_zero = True)
        ax1.set_title('Waterbalance reference')
        ax1.set_ylabel('Flux [m3/day]')
        ax1.set_xlabel('Time [stress-periods]')
        plt.savefig(path / 'waterbalance_reference.png')
        plt.close()
        
        ax2 = plot.budgets2.plot(remove_zero = True)
        ax2.set_title('Waterbalance scenario')
        ax2.set_ylabel('Flux [m3/day]')
        ax2.set_xlabel('Time [stress-periods]')
        plt.savefig(path / 'waterbalance_scenario.png')
        plt.close()
        
        ax3 = plot.plot(remove_zero = True)
        ax3.set_title('Waterbalance difference')
        ax3.set_ylabel('Flux [m3/day]')
        ax3.set_xlabel('Time [stress-periods]')
        plt.savefig(path / 'waterbalance_difference.png')
        plt.close()

    def plot_uzf_flow_budgets(
        self, uzf_name:str, mask: xr.DataArray = None, path: Path | str | None = None
    ) -> None:
        path = Path(path) # force to path
        plot = PlotDiff(mask, self.reference_uzf_flow_budgets[uzf_name], self.scenario_uzf_flow_budgets[uzf_name])
        ax1 = plot.budgets1.plot(remove_zero = True, boundary_only =True)
        ax1.set_title('Waterbalance reference')
        ax1.set_ylabel('Flux [m3/day]')
        ax1.set_xlabel('Time [stress-periods]')
        plt.savefig(path / 'waterbalance_reference_uzf.png')
        plt.close()
        
        ax2 = plot.budgets2.plot(remove_zero = True, boundary_only =True)
        ax2.set_title('Waterbalance scenario')
        ax2.set_ylabel('Flux [m3/day]')
        ax2.set_xlabel('Time [stress-periods]')
        plt.savefig(path / 'waterbalance_scenario_uzf.png')
        plt.close()
        
        ax3 = plot.plot(remove_zero = True, boundary_only =True)
        ax3.set_title('Waterbalance difference')
        ax3.set_ylabel('Flux [m3/day]')
        ax3.set_xlabel('Time [stress-periods]')
        plt.savefig(path / 'waterbalance_difference_uzf.png')
        plt.close()

    def plot_wadi_delay(self, path: Path, drn_name: str = 'drn_dit-leiding_dr') -> None:
        path = Path(path) # force to path
        df_ref = self.model_results.log_ponding_reference
        df_sc = self.model_results.log_ponding_scenario
        dt = np.diff(df_ref['time'])[0]
        drainage_ref = -self.model_results.reference.flow_budgets[drn_name].sum(dim = ['y', 'x','layer']).to_numpy() * dt
        drainage_sc = -self.model_results.scenario.flow_budgets[drn_name].sum(dim = ['y', 'x','layer']).to_numpy() * dt
        # ref 
        ymax1 = max(df_ref.max(axis = 0)['realised_infiltration_out'],df_sc.max(axis=0)['realised_infiltration_out'])
        ymax2 = max(drainage_ref.max(), drainage_sc.max())
        ymax = max(ymax1,ymax2) * 1.1
        
        fig, ax = plt.subplots(1,2)
        ax[0].plot(df_ref['time'],df_ref['uzf_infiltration_in'], label = 'precipitation', color = 'blue')  # precipitation
        ax[0].plot(df_ref['time'], df_ref['realised_infiltration_out'], label = 'infiltration') # infiltration
        ax[0].plot(df_ref['time'],drainage_ref, label = 'drainage')
        # secenario
        ax[1].plot(df_sc['time'],df_sc['uzf_infiltration_in'], label = 'precipitation', color = 'blue')  # precipitation
        ax[1].plot(df_sc['time'], df_sc['realised_infiltration_out'], label = 'infiltration') # infiltration
        ax[1].plot(df_sc['time'],drainage_sc, label = 'drainage')

        ax[0].set_title('reference')
        ax[1].set_title('scenario')
        ax[0].set_ylabel('Flux [m3/dt]')
        ax[0].set_xlabel('Time [stress-periods]')
        ax[1].set_xlabel('Time [stress-periods]')
        ax[0].set_ylim(0.0,ymax)
        ax[1].set_ylim(0.0,ymax)
        ax[1].legend()
        plt.savefig(path / 'wadi_reduction.png.png')
        plt.close()

    def make_dir(self, path: Path) -> None:
        if not os.path.isdir(path):
            os.mkdir(path)

    def save_heads(self, path: Path):
        path = Path(path)
        extension = path.suffix
        path = path.parent
        dirs = ["reference", "scenario", "difference"]
        for dir in dirs:
            self.make_dir(path / dir)
        if extension == ".idf":
            imod.idf.save(path / "reference" / "heads.idf", self.reference_heads)
            imod.idf.save(path / "scenario" / "heads.idf", self.scenario_heads)
            imod.idf.save(path / "difference" / "heads.idf", self.heads_difference)
        elif extension == ".nc":
            self.reference_heads.to_netcdf(path / "reference" / "heads.nc")
            self.scenario_heads.to_netcdf(path / "reference" / "heads.nc")
            self.heads_difference.to_netcdf(path / "difference" / "heads.nc")
        else:
            raise ValueError("Unsupported output extension,  supported are idf and nc ")

    def plot_uzf_water_content(
        self,
        uzf_name: str,
        measurements: pd.DataFrame,
        selection: List = ["reference", "scenario"],
        path: Path | str | None = None,
    ) -> None:
        path = Path(path)
        xmin, xmax, ymin, ymax = self._get_extend()
        inbounds = (
            (measurements.x < xmax)
            & (measurements.x > xmin)
            & (measurements.y < ymax)
            & (measurements.y > ymin)
        )
        measurements = measurements[inbounds]
        selection = {
            "reference": self.reference_uzf_water_content[uzf_name],
            "scenario": self.scenario_uzf_water_content[uzf_name],
        }
        wc_to_plot = []
        for key, output in selection.items():
            if key in selection:
                x = measurements.groupby("id").max().x
                y = measurements.groupby("id").max().y
                results = (
                    imod.select.points_values(output, x=x, y=y)
                    .to_dataframe()
                    .reset_index()
                    .rename(columns={"index": "id"})
                )
                # select appropriate layers
                z = measurements.groupby("id").max().depth
                layer_to_plot = self._filter_depth_to_layer(z, x, y)                
                nrow, _ = results.shape
                to_plot = np.full(nrow, False)
                for i in range(layer_to_plot.size):
                    mask = (results['id'] == i) & (results['layer'] == layer_to_plot[i])
                    to_plot[mask] = True
                wc_to_plot.append(results.loc[to_plot,:])

        for wc_id, measurements_id in zip(
            range(wc_to_plot[0].id.max() + 1), pd.unique(measurements.id)
        ):
            wc_subset = wc_to_plot[0].id == wc_id
            measurements_subset = measurements.id == measurements_id
            fig, ax = plt.subplots()
            ax.plot(
                wc_to_plot[0]["time"][wc_subset],
                wc_to_plot[0]['WATER-CONTENT'][wc_subset],
                label=list(selection.keys())[0],
            )
            ax.plot(
                wc_to_plot[1]["time"][wc_subset],
                wc_to_plot[1]['WATER-CONTENT'][wc_subset],
                label=list(selection.keys())[1],
            )
            date = measurements.date[measurements_subset]
            if 'measurements' in measurements.columns:
                measurement = measurements.measurements[measurements_subset]
                ax.scatter(date, measurement, label="measurements")
            ax.set_ylabel("water content")
            ax.set_title(measurements_id)
            ax.legend()
            fig.autofmt_xdate()
            if path is None:
                plt.show()
            else:
                self.make_dir(path)
                plt.savefig(path / (measurements_id + "_uzf_water_content.png"))
                plt.close()

    def plot_heads(
        self,
        measurements: pd.DataFrame,
        selection_to_plot: List = ["reference", "scenario"],
        path: Path | str | None = None,
    ) -> None:
        path = Path(path)
        xmin, xmax, ymin, ymax = self._get_extend()
        inbounds = (
            (measurements.x < xmax)
            & (measurements.x > xmin)
            & (measurements.y < ymax)
            & (measurements.y > ymin)
        )
        measurements = measurements[inbounds]
        selection_to_plot = {
            "surface level": self.model_results.reference.flow_model['dis']['top'],
            "reference": self.reference_heads,
            "scenario": self.scenario_heads,
            "difference": self.heads_difference,
        }
        heads_to_plot = []
        for key, output in selection_to_plot.items():
            if key in selection_to_plot:
                x = measurements.groupby("id").max().x
                y = measurements.groupby("id").max().y
                results = (
                    imod.select.points_values(output, x=x, y=y)
                    .to_dataframe()
                    .reset_index()
                    .rename(columns={"index": "id"})
                )
                # select appropriate layers
                z = measurements.groupby("id").max().depth
                layer_to_plot = self._filter_depth_to_layer(z, x, y)                
                nrow, _ = results.shape
                to_plot = np.full(nrow, False)
                if 'layer' in results.columns:
                    for i in range(layer_to_plot.size):
                        mask = (results['id'] == i) & (results['layer'] == layer_to_plot[i])
                        to_plot[mask] = True
                else:
                    to_plot[:] = True
                heads_to_plot.append(results.loc[to_plot,:])

        for heads_id, measurements_id in zip(
            range(heads_to_plot[0].id.max() + 1), pd.unique(measurements.id)
        ):
            heads_subset = heads_to_plot[1].id == heads_id
            measurements_subset = measurements.id == measurements_id
            fig, ax = plt.subplots()
            ax.plot(
                heads_to_plot[1]["time"][heads_subset],
                heads_to_plot[1]["head"][heads_subset],
                label=list(selection_to_plot.keys())[1],
            )
            ax.plot(
                heads_to_plot[2]["time"][heads_subset],
                heads_to_plot[2]["head"][heads_subset],
                label=list(selection_to_plot.keys())[2],
            )
            heads_subset2 = heads_to_plot[0].id == heads_id
            ax.hlines(
                heads_to_plot[0]['top'][heads_subset2],
                heads_to_plot[1]["time"][heads_subset].min(),
                heads_to_plot[1]["time"][heads_subset].max(),
                label = 'surface',
                color='green'
            )
            date = measurements.date[measurements_subset]
            if 'measurements' in measurements.columns:
                measurement = measurements.measurements[measurements_subset]
                ax.scatter(date, measurement, label="measurements")
            ax.set_ylabel("head (m NAP)")
            ax.set_title(measurements_id)
            ax.legend()
            fig.autofmt_xdate()
            if path is None:
                plt.show()
            else:
                self.make_dir(path)
                plt.savefig(path / (measurements_id + "_heads.png"))
                plt.close()