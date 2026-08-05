from imod import mf6
from pathlib import Path
import xarray as xr
import pandas as pd
import numpy as np
from imod.mf6.boundary_condition import BoundaryCondition

class TransportModel:
    uzf_package :  dict

    def __init__(self, flow_model, config: dict):
        self.config = config
        self.transport_model = mf6.GroundwaterTransportModel(save_flows=True)
        self.transport_model["dis"] = flow_model["dis"]
        self.add_source_sinks_mixing(flow_model)
        self.transport_model['adv'] = mf6.AdvectionUpstream()
        self.transport_model['dsp'] = mf6.Dispersion(
            diffusion_coefficient= 1.0,
            longitudinal_horizontal=config['transport']['dispersivity'],
            transversal_horizontal1= 1.0,
            xt3d_off=False,  # TODO: gaat dit goed i.c.m. Newton
            xt3d_rhs=False,
        )
        self.transport_model["mst"] = mf6.MobileStorageTransfer(
            porosity=config['transport']['porosity'],
        )
        self.add_ic()
        self.transport_model["oc"] = mf6.OutputControl(
            save_concentration="all", save_budget="last"
            )
        
    def add_ic(self,):
        ic = self.config["boundary_conditions"]['initial_concentrations']
        self.transport_model["ic"] = mf6.InitialConditions(
            start=self._get_concentration(ic),
            )
    
    def add_source_sinks_mixing(self, flow_model):
        # remove uzf for issues within iMOD-python
        self.uzf = {}

        for name in flow_model.keys():
            if isinstance(flow_model[name], mf6.UnsaturatedZoneFlow):
                self.uzf[name]= flow_model[name]  
            elif isinstance(flow_model[name], mf6.Evapotranspiration):
                self.uzf[name]= flow_model[name]
            # elif isinstance(flow_model[name], mf6.Drainage):
            #     self.uzf[name]= flow_model[name]
        for name in self.uzf.keys():
            flow_model.pop(name)
        ok = False
        for package in flow_model.values():
            if isinstance(package, BoundaryCondition) and not isinstance(package, mf6.UnsaturatedZoneFlow) :
                ok = True
                break
        if ok:
            self.transport_model['ssm'] = mf6.SourceSinkMixing.from_flow_model(flow_model, self.config['transport']['species'], save_flows=True)
        for name in self.uzf.keys():
            flow_model[name] = self.uzf[name]


    def write_uzt(self, dir: Path, name: str = 'wadi_1'):
        ntime = self.uzf[name].dataset.time.size
        initial_concentration = self._get_concentration(self.config['boundary_conditions']['wadi']['initial_concentration'])
        concentration = self._get_concentration(self.config['boundary_conditions']['wadi']['concentration'])
        self.write_uzt_package(dir, name, ntime, initial_concentration, concentration)
        self.write_uzt_package(dir, 'omgeving', ntime, 0.0, 0.0)

        ssm_file = dir / 'GWT_1' / 'ssm.ssm'
        if not ssm_file.is_file():
            f = open(ssm_file, "w")
            f.write("begin options \n")
            f.write("   save_flows \n")
            f.write("end options \n")
            f.write("\n")
            f.write("begin sources \n")
            f.write("end sources \n")
            f.close()
            self.update_nam_file(dir, '  ssm6 GWT_1/ssm.ssm ssm \n')


    def write_uzt_package(self, dir: Path, name, ntime, initial_concentration, concentration):
        f = open(dir / 'GWT_1' / f'{name}.uzt', "w")
        f.write("begin options \n")
        f.write("   save_flows \n")
        f.write(f"   concentration fileout GWT_1/concentration_uzt_{name}.con \n")
        f.write(f"   budget fileout GWT_1/budget_uzt_{name}.cbc \n")
        f.write("end options \n")
        f.write("\n")
        f.write("begin packagedata \n")
        nnode = self.uzf[name].dataset['iuzno'].max().item() + 1
        nnode_inf = self.uzf[name].dataset['iuzno'].isel(layer = 0).max().item() + 1
        for inode in range(1,nnode):
            f.write(f"{inode}  {initial_concentration} \n")
        f.write("end packagedata \n")
        f.write("\n")
        for itime in range(1, ntime):
            f.write(f"begin period {itime} \n")
            for inode in range(1, nnode_inf):
                f.write(f"{inode} infiltration {concentration} \n")
            f.write("end period \n")
        f.close()
        self.update_nam_file(dir, f'  uzt6 GWT_1/{name}.uzt  {name} \n')

    def update_nam_file(self, dir, string): 
        # update nam -file
        with open(dir / 'GWT_1' / 'GWT_1.nam', "r") as f:
            lines = f.readlines()
        with open(dir / 'GWT_1' / 'GWT_1.nam', "w") as f:
            for line in lines:
                if 'end packages' in line:
                    f.write(string)
                f.write(line)
        f.close()


    def _get_concentration(self, ic: str | np.float64):
        if isinstance(ic, str):
            if 'xlsx' in ic:
                concentration = self._get_concentration_4d()
            elif 'nc' in ic:
                concentration = xr.open_dataarray(ic)
        else:
            concentration = ic
        return concentration

    def _get_concentration_4d(self, date_format: str | None = None, label: str = "concentration") -> xr.DataArray:
        mask = xr.ones_like(self.transport_model['dis']['bottom'], dtype = np.float64)
        if date_format is None:
            df = pd.read_excel(self.config["boundary_conditions"]["recharge"], index_col=0)  
        else:  
            df = pd.read_excel(self.config["boundary_conditions"]["recharge"])  
            df['time'] = pd.to_datetime(df['time'], format = date_format)
            df = df.set_index('time')
        return df[label].to_xarray() * mask


    def get_uzt_flow_budgets(self,simulation: mf6.simulation, model_path = Path | str) -> dict | None:
        model_path = Path(model_path)
        out = {}
        grb_file = simulation._get_grb_path('GWF_1')
        time_min = pd.to_datetime(self.config["discretisation"]["start_date"])
        for name, package in simulation['GWF_1'].items():
            if isinstance(package, mf6.UnsaturatedZoneFlow):
                print('uzf-budgets: ' + name)
                file = 'budget_' + name.replace('f','t') + '.cbc'
                cbc_file = model_path / 'GWT_1' / file
                out[name] = mf6.open_cbc(cbc_file,grb_file)
                # assign time coord to all variables
                for variable in out[name].keys():
                    timedelta = pd.to_timedelta(out[name][variable]['time'], "D")
                    out[name][variable] = out[name][variable].assign_coords(time=time_min + timedelta)
        return out
    
    def get_uzt_water_concentration(self, simulation: mf6.simulation) -> dict | None:
        out = {}
        grb_file = Path(simulation._get_grb_path('GWF_1'))
        time_min = pd.to_datetime(self.config["discretisation"]["start_date"])
        for name, package in simulation['GWF_1'].items():
            if isinstance(package, mf6.UnsaturatedZoneFlow):
                kv_sat = package['kv_sat']
                nlay, nrow, ncol = kv_sat.shape
                indices = np.arange(nlay * nrow * ncol)[kv_sat.notnull().to_numpy().flatten()]
                print('uzf-water concentration: ' + name)
                file = 'concentration_uzt_' + name + '.con'
                wc_file = grb_file.parents[1] / 'GWT_1' / file
                out[name] = mf6.open_dvs(wc_file,grb_file, indices)
                #assign time coord to all variables
                timedelta = pd.to_timedelta(out[name]['time'], "D")
                out[name] = out[name].assign_coords(time=time_min + timedelta)
        return out