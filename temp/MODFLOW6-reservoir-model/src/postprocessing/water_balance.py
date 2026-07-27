import xarray as xr
import numpy as np
import matplotlib.pyplot as plt 
import pandas as pd
import math
from matplotlib import cm
import imod

def get_bound(face: str, array: np.ndarray) -> np.ndarray:
    bound = np.zeros_like(array)
    _, nrow, ncol = bound.shape
    if "front" in face:
        bound[:, nrow - 1, :] = 1
        bound[:, 0, :] = 1
    elif "right" in face:
        bound[:, :, ncol - 1] = 1
        bound[:, :, 0] = 1
    return bound

def exclude_budget(key:str) -> bool:
    for exclude in ['flow-right-face', 'flow-front-face', 'flow-lower-face', 'npf-qx', 'npf-qy', 'npf-qz', 'npf-sat']:
        if key in exclude:
            return True
    return False

class Waterbalance:
    summed_budgets: dict
    face_masks: dict
    active_domain: xr.DataArray
    budgets: dict

    def __init__(self, active_domain: xr.DataArray, budgets: dict) -> None:
        self.active_domain = xr.where(active_domain > 0, 1, 0)
        self.budgets = budgets
        self.summed_budgets = {}
        self.face_masks = {}

    def compute(self) -> pd.DataFrame:
        if len(self.face_masks) == 0:
            _ = self.get_masks()
        frf_in_mask = self.face_masks["frf"].where(self.active_domain == 0).fillna(0.0)
        frf_out_mask = self.face_masks["frf"].where(self.active_domain == 1).fillna(0.0)
        masked_frf_in = -self.budgets["flow-right-face"] * frf_in_mask # reverse sign
        masked_frf_out = self.budgets["flow-right-face"] * frf_out_mask
        frf_budget = masked_frf_in.sum(dim=['layer', 'y', 'x']).to_numpy() + masked_frf_out.sum(dim=['layer', 'y', 'x']).to_numpy()
        
        fff_in_mask = self.face_masks["fff"].where(self.active_domain == 0).fillna(0.0)
        fff_out_mask = self.face_masks["fff"].where(self.active_domain == 1).fillna(0.0)
        masked_fff_in = -self.budgets["flow-front-face"] * fff_in_mask # reverse sign
        masked_fff_out = self.budgets["flow-front-face"] * fff_out_mask
        fff_budget = masked_fff_in.sum(dim=['layer', 'y', 'x']).to_numpy() + masked_fff_out.sum(dim=['layer', 'y', 'x']).to_numpy()
        flf_budget = (self.budgets["flow-lower-face"] * self.face_masks["flf"]).sum(dim=['layer', 'y', 'x']).to_numpy()

        self.summed_budgets["bounds"] = frf_budget + fff_budget + flf_budget
        for package, budget in self.budgets.items():
            if not exclude_budget(package):
                self.summed_budgets[package] = (budget * self.active_domain).sum(dim=['layer', 'y', 'x']).to_numpy()
        return pd.DataFrame(self.summed_budgets)
    
    def compute_boundary(self) -> pd.DataFrame:
        self.summed_budgets = {}
        for package, budget in self.budgets.items():
            if not exclude_budget(package):
                self.summed_budgets[package] = (budget * self.active_domain).sum(dim=['layer', 'y', 'x']).to_numpy()
        return pd.DataFrame(self.summed_budgets)
            
    def plot(self, boundary_only: bool = False, remove_zero: bool = False, limit: int | None = None) -> plt.axes:
        if len(self.summed_budgets) == 0:
            if boundary_only:
                _ = self.compute_boundary()
            else:
                _ = self.compute()
        first_item = list(self.summed_budgets.keys())[0]
        bounds = self.summed_budgets[first_item]
        time = np.arange(bounds.size)
        if limit is None:
            limit = time.size
        _, ax = plt.subplots()
        pos_bottom = np.zeros_like(bounds)
        neg_bottom = np.zeros_like(bounds)
        colors = cm.rainbow(np.linspace(0, 1, len(self.summed_budgets.keys())))
        i = -1
        for name, budget in self.summed_budgets.items():
            if remove_zero and math.isclose(budget.sum(),0.0):
                pass
            else:
                i +=1
                pos = np.copy(budget)
                pos[budget < 0] = 0
                neg = np.copy(budget)
                neg[budget > 0] = 0
                ax.bar(time[0:limit], pos[0:limit], bottom = pos_bottom[0:limit], label = name, color=colors[i])
                ax.bar(time[0:limit], neg[0:limit], bottom = neg_bottom[0:limit], color=colors[i])
                pos_bottom += pos
                neg_bottom += neg
        ax.legend()
        ax.set_title('Waterbalance')
        ax.set_ylabel('Flux [m3/day]')
        ax.set_xlabel('Time [stress-periods]')
        return ax
        
    def get_masks(self) -> xr.Dataset:
        domain = self.active_domain.to_numpy()
        _, nrow, ncol = domain.shape
        self.face_masks = {}
        self.face_masks["flf"] = self._mask_flf(domain)
        self.face_masks["fff"] = self._mask_fff(domain, np.arange(0, nrow - 1))
        self.face_masks["frf"] = self._mask_frf(domain, np.arange(0, ncol - 1))
        out = self.face_masks
        out['boundary'] = self.active_domain
        return xr.Dataset(out)

    def _mask_flf(self, domain: np.ndarray) -> xr.DataArray:
        # |   | mask_flf = 1
        # | * | mask_flf = 0
        # | * | mask_flf = 1
        # |   | mask_flf = 0
        nlay, nrow, ncol = domain.shape
        active_indices = np.flatnonzero(domain[0 : nlay - 1, :, :] == 1)
        nlcel = nrow * ncol
        flf_indices = np.logical_or(
            np.logical_and(
                domain.ravel()[active_indices] == 1,
                domain.ravel()[active_indices + nlcel] == 0,
            ),
            np.logical_and(
                domain.ravel()[active_indices] == 0,
                domain.ravel()[active_indices + nlcel] == 1,
            ),
        )
        flf = np.zeros_like(domain).ravel()
        flf[active_indices[flf_indices]] = 1
        return self.array(flf.reshape((nlay, nrow, ncol)))

    def _mask_fff(self, domain: np.ndarray, irow: np.ndarray) -> xr.DataArray:
        nlay, nrow, ncol = domain.shape
        front_bound = get_bound("front", domain)
        # active nodes that are not
        active_indices = np.flatnonzero(
            np.logical_and(domain[:, :, :] == 1, front_bound[:, :, :] != 1)
        )
        fff_indices_bot = np.logical_and(
            domain.ravel()[active_indices] == 1,
            domain.ravel()[active_indices + ncol] == 0,
        )
        fff_indices_top = np.logical_and(
            domain.ravel()[active_indices - ncol] == 0,
            domain.ravel()[active_indices] == 1,
        )
        fff = np.zeros_like(domain).ravel()
        fff[active_indices[fff_indices_bot]] = 1
        fff[active_indices[fff_indices_top] - ncol] = 1
        return self.array(fff.reshape((nlay, nrow, ncol)))

    def _mask_frf(self, domain: np.ndarray, icol: np.ndarray) -> xr.DataArray:
        nlay, nrow, ncol = domain.shape
        right_bound = get_bound("right", domain)
        # active nodes that are not
        active_indices = np.flatnonzero(
            np.logical_and(domain[:, :, :] == 1, right_bound[:, :, :] != 1)
        )
        frf_indices_right = np.logical_and(
            domain.ravel()[active_indices] == 1,
            domain.ravel()[active_indices + 1] == 0,
        )
        frf_indices_left = np.logical_and(
            domain.ravel()[active_indices] == 1,
            domain.ravel()[active_indices - 1] == 0,
        )
        frf = np.zeros_like(domain).ravel()
        frf[active_indices[frf_indices_right]] = 1
        frf[active_indices[frf_indices_left] - 1] = 1
        return self.array(frf.reshape((nlay, nrow, ncol)))

    def array(self, array: np.ndarray) -> xr.DataArray:
        return xr.DataArray(
            data=array,
            coords=self.active_domain.coords,
            dims=self.active_domain.dims,
        )

class PlotDiff:
    
    budgets1: Waterbalance
    budgets2: Waterbalance
    
    def __init__(self, active_domain: xr.DataArray, budgets1: dict, budgets2: dict) -> None:
        self.budgets1 = Waterbalance(active_domain, budgets1)
        self.budgets2 = Waterbalance(active_domain, budgets2)
        
    def plot(self, boundary_only: bool = False, remove_zero: bool = False, limit: int | None = None) -> plt.axes:
        if len(self.budgets1.summed_budgets | self.budgets2.summed_budgets) == 0:
            if boundary_only:
                _ = self.budgets1.compute_boundary()
                _ = self.budgets2.compute_boundary()
            else:
                _ = self.budgets1.compute()
                _ = self.budgets2.compute()
                
        bounds = self.budgets1.summed_budgets[list(self.budgets1.summed_budgets.keys())[0]][0:limit]
        time = np.arange(bounds.size)
        if limit is None:
            limit = time.size
        _, ax = plt.subplots()
        pos_bottom = np.zeros_like(bounds)
        neg_bottom = np.zeros_like(bounds)
        colors = cm.rainbow(np.linspace(0, 1, len(self.budgets2.summed_budgets.keys())))
        i = -1
        for name2, budget2 in self.budgets2.summed_budgets.items():
            i +=1
            if name2 in self.budgets1.summed_budgets.keys():
                budget1 = self.budgets1.summed_budgets[name2]
                budget = budget2[0:limit] - budget1[0:limit]
            else:
                budget = budget2[0:limit] - 0.0
            pos = np.copy(budget)
            pos[budget < 0] = 0
            neg = np.copy(budget)
            neg[budget > 0] = 0
            if remove_zero and math.isclose(budget.sum(),0.0):
                pass
            else:
                ax.bar(time, pos, bottom = pos_bottom, label = name2, color=colors[i])
                ax.bar(time, neg, bottom = neg_bottom, color=colors[i])
                pos_bottom += pos
                neg_bottom += neg
        ax.legend()
        ax.set_title('Diff waterbalance')
        ax.set_ylabel('DFlux [m3/day]')
        ax.set_xlabel('Time [stress-periods]')
        return ax
    
    def plot_single(self, name1: str, boundary_only: bool = False, remove_zero: bool = False, limit: int | None = None):
        if len(self.budgets1.summed_budgets | self.budgets2.summed_budgets) == 0:
            if boundary_only:
                _ = self.budgets1.compute_boundary()
                _ = self.budgets2.compute_boundary()
            else:
                _ = self.budgets1.compute()
                _ = self.budgets2.compute()
                
        bounds = self.budgets1.summed_budgets[list(self.budgets1.summed_budgets.keys())[0]][0:limit]
        time = np.arange(bounds.size)
        if limit is None:
            limit = time.size
        _, ax = plt.subplots()
        pos_bottom = np.zeros_like(bounds)
        neg_bottom = np.zeros_like(bounds)
        
        budget1 = self.budgets1.summed_budgets[name1]
        budget2 = self.budgets2.summed_budgets[name1]
        budget = budget1[0:limit] - budget2[0:limit]
        pos = np.copy(budget)
        pos[budget < 0] = 0
        neg = np.copy(budget)
        neg[budget > 0] = 0
        ax.bar(time, pos, bottom = pos_bottom, label = name1, color='blue')
        ax.bar(time, neg, bottom = neg_bottom, color='blue')
        ax.legend()
        ax.set_title('Diff waterbalance')
        ax.set_ylabel('DFlux [m3/day]')
        ax.set_xlabel('Time [stress-periods]')
        return ax