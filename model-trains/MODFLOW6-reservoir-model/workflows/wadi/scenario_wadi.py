import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import tomli
from src.generation.create_models_flow import ScenariosFromToml, ModelFromToml
from src.postprocessing.postprocess_models import PostprocessModels
import pandas as pd
import imod
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import xarray as xr
import rioxarray


def get_uzf_water_content(wc_path: Path | str,grb_path, mask) -> dict | None:
    nlay, nrow, ncol = mask.shape
    indices = np.arange(nlay * nrow * ncol)[mask.notnull().to_numpy().flatten()]
    return imod.mf6.open_dvs(wc_path,grb_path, indices)

run = True

# leest invoerfile
with open(Path(__file__).parent / "scenario_wadi.toml", "rb") as f:
    config = tomli.load(f)

if run:
    # maakt een model op basis van de ingelezen invoerfile
    model = ModelFromToml(config=config)
    # draait het model en retourneert de resultaten van het ponding reservoir 
    log = model.run_coupled("simulation_dir/wadi")
    model_concentrations = model.model_concentrations
    flow_budgets = model.flow_budgets
    flow_budgets_uzf = model.uzf_flow_budgets
    # de resultaten van het pondingreservoir zijn te vinden onder
    log.to_csv('simulation_dir/wadi/ponding_ref.csv', index = False)
    uzf_concentrations = model.get_uzf_concentration()
else:
    ucn_path = "simulation_dir/wadi/GWT_1/GWT_1.ucn"
    cbc_path = "simulation_dir/wadi/GWF_1/GWF_1.cbc"
    cbc_uzf_path = "simulation_dir/wadi/GWF_1/budgets_uzf_wadi_1.cbc"
    grb_path = "simulation_dir/wadi/GWF_1/dis.dis.grb"
    uzf_con_path = "simulation_dir/wadi/GWT_1/concentration_uzt_wadi_1.con"
    sdate = pd.to_datetime(config['model']['discretisation']['start_date'])
    model_concentrations = imod.mf6.open_conc(ucn_path, grb_path, simulation_start_time=sdate)
    flow_budgets = imod.mf6.open_cbc(cbc_path, grb_path, simulation_start_time=sdate)
    flow_budgets_uzf = imod.mf6.open_cbc(cbc_uzf_path, grb_path, simulation_start_time=sdate)
    # uzf_concentrations = get_uzf_water_content(model_path=uzf_con_path)
    mask = flow_budgets['uzf-gwrch_wadi_1'].isel(time = 0, drop=True)
    uzf_concentrations = get_uzf_water_content(uzf_con_path,grb_path, mask).fillna(0.0)

concentration_time1 = model_concentrations.sel(layer = 1, x = 95668, y = 432686, method='nearest')
concentration_time2 = model_concentrations.sel(layer = 1, x = 95667, y = 432686, method='nearest')
concentration_time3 = model_concentrations.sel(layer = 1, x = 95671, y = 432680, method='nearest')

uzf_concentration_time1 = uzf_concentrations['wadi_1'].sel(layer = 1, x = 95668, y = 432686, method='nearest')
uzf_concentration_time2 = uzf_concentrations['wadi_1'].sel(layer = 1, x = 95667, y = 432686, method='nearest')
uzf_concentration_time3 = uzf_concentrations['wadi_1'].sel(layer = 1, x = 95671, y = 432680, method='nearest')

flow_time = -flow_budgets['drn_dit-leiding_dr'].sum(dim = ['layer', 'y', 'x'])
flow_time_gw_recharge = flow_budgets['uzf-gwrch_wadi_1'].sum(dim = ['layer', 'y', 'x'])

flow_time_uzf_inf = flow_budgets_uzf['wadi_1']['infiltration_wadi_1'].sum(dim = ['layer', 'y', 'x'])

itime = -1
for time in model_concentrations.time:
    print(itime, time)
    itime += 1
    fig, ax = plt.subplot_mosaic(
        """
        ac
        ad
        eb
        """
    )
    model_concentrations.sel(layer = 1, time = time).plot(
        ax = ax['a'],
        yincrease=False, 
        vmin = 0.0, 
        vmax = 0.5,
    )
    # uzf_concentrations.sel(time = uzf_concentrations.time[itime]).mean(dim = 'y').plot(
    #     ax = ax['f'],
    #     yincrease=False, 
    #     vmin = 0.0, 
    #     vmax = 0.5,
    # )
    model_concentrations.sel(time = time).max(dim = 'y').plot(
        ax = ax['e'],
        yincrease=False, 
        vmin = 0.0, 
        vmax = 0.5,
    )
    ax['a'].axis('equal')
    ax['d'].plot(uzf_concentration_time1.time, uzf_concentration_time1)
    ax['d'].plot(uzf_concentration_time2.time, uzf_concentration_time2)
    ax['d'].plot(uzf_concentration_time3.time, uzf_concentration_time3)
    ax['d'].scatter(uzf_concentration_time1.isel(time=itime).time, uzf_concentration_time1.isel(time=itime))

    ax['b'].plot(concentration_time1.time,concentration_time1, color= 'blue')
    ax['b'].plot(concentration_time2.time,concentration_time2, color= 'blue')
    ax['b'].plot(concentration_time3.time,concentration_time3, color= 'blue')
    ax['b'].scatter(concentration_time1.isel(time=itime).time, concentration_time1.sel(time=time), color='blue')

    # flow!
    ax['c'].plot(flow_time.time,flow_time, color= 'green')
    ax['c'].plot(flow_time_gw_recharge.time, flow_time_gw_recharge, color='orange')
    ax['c'].plot(flow_time_uzf_inf.time, flow_time_uzf_inf, color='blue')
    ax['c'].scatter(flow_time.sel(time=time).time, flow_time.sel(time=time), color='green')
    ax['c'].set_ylim(0,150)
    
    plt.tight_layout()
    fig.savefig(f'simulation_dir/wadi/concentrations_{itime:04d}.png')

# generate output nc
results = model.heads.to_dataset(name = 'groundwater_levels')
results['unsaturated_water_content'] = model.uzf_water_content["wadi_1"].combine_first(model.uzf_water_content["omgeving"] )
results['saturated_groundwater_concentrations'] = model_concentrations
results['unsaturated_groundwater_concentrations'] = uzf_concentrations["wadi_1"].combine_first(uzf_concentrations["omgeving"] )
results = imod.util.spatial.gdal_compliant_grid(results, crs = "EPSG:28992")
results.time.attrs.update({
    "standard_name": "time",
    "long_name": "time",
    "axis": "T",
})
results.layer.attrs.update({
    "long_name": "model_layer",
    "positive": "down",
    "axis": "Z",
})
results = results.rio.write_crs("EPSG:28992")
results.to_netcdf("model_results.nc")