import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


import tomli
from src.generation.create_models_flow import ModelFromToml, ScenariosFromToml
from src.postprocessing.postprocess_models import PostprocessModels
import pandas as pd
import imod
import xarray as xr  
import numpy as np
from src.generation.create_models_flow import rasterize_polygon_column
import matplotlib.pyplot as plt

run = True

# leest invoerfile
with open(r"workflows/vegetation/scenario_vegetation.toml", "rb") as f:
    config = tomli.load(f)
if run:
    # maakt een model op basis van de ingelezen invoerfile
    model = ModelFromToml(config=config)
    # draait het model en retourneert de resultaten van het ponding reservoir 
    model.run("simulation_dir/vegetation")
    model_concentrations = model.model_concentrations
    flow_budgets = model.flow_budgets

else:
    ucn_path = "simulation_dir/vegetation/GWT_1/GWT_1.ucn"
    cbc_path = "simulation_dir/vegetation/GWF_1/GWF_1.cbc"
    grb_path = "simulation_dir/vegetation/GWF_1/dis.dis.grb"
    sdate = pd.to_datetime(config['model']['discretisation']['start_date'])
    model_concentrations = imod.mf6.open_conc(ucn_path, grb_path, simulation_start_time=sdate)
    flow_budgets = imod.mf6.open_cbc(cbc_path, grb_path, simulation_start_time=sdate)

concentration_time1 = model_concentrations.sel(layer = 1, x = 95668, y = 432686, method='nearest')
concentration_time2 = model_concentrations.sel(layer = 1, x = 95667, y = 432686, method='nearest')
concentration_time3 = model_concentrations.sel(layer = 1, x = 95671, y = 432680, method='nearest')

flow_time = flow_budgets['riv_dit-riool_inf'].sum(dim = ['layer', 'y', 'x'])

itime = -1
for time in model_concentrations.time:
    itime += 1
    fig, ax = plt.subplot_mosaic(
        """
        ac
        ab
        ab
        """
    )
    model_concentrations.sel(layer = 1, time = time).plot(
        ax = ax['a'],
        yincrease=False, 
        vmin = 0.0, 
        vmax = 0.5,
    )
    ax['a'].axis('equal')
    ax['b'].plot(concentration_time1.time,concentration_time1, color= 'blue')
    ax['b'].plot(concentration_time2.time,concentration_time2, color= 'blue')
    ax['b'].plot(concentration_time3.time,concentration_time3, color= 'blue')
    ax['b'].scatter(concentration_time1.sel(time=time).time, concentration_time1.sel(time=time), color='blue')

    ax['c'].plot(flow_time.time,flow_time, color= 'green')
    ax['c'].scatter(flow_time.sel(time=time).time, flow_time.sel(time=time), color='green')



    plt.tight_layout()
    fig.savefig(f'simulation_dir/vegetation/concentrations_{itime:04d}.png')
