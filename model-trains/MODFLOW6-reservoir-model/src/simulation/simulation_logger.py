"""
simulation_logger.py
Collects per-timestep diagnostics during a coupled Daisy–MODFLOW6 simulation.
"""
import numpy as np


class SimulationLogger:
    """Accumulates per-timestep diagnostics. Passed into CoupledSimulation."""

    def __init__(self):
        self.gw_sent_cm: list[float] = []        # GWL sent to Daisy each step [cm]
        self.rch_layer_depth: list[float] = []   # depth [cm] of h0 layer used for recharge
        self.runoff_mm: list[float] = []         # surface runoff [mm/day]
        self.sy_initial: list[float] = []        # Sy initial guess (Δθ-based) per day
        self.sy_deficit: list[float] = []        # Sy from θ_sat - θ at fringe (state-based)
        self.sy_numerator: list[float] = []      # Sy numerator (Δθ·Δz)
        self.sy_denominator: list[float] = []    # Sy denominator (Δz_h0)
        self.sy_static_step: list[bool] = []     # True when static Sy fallback was used
        self.sy_method: list[str] = []           # "dθ/dzh0" or "dθ/dz_fringe" or "default"
        self.sy_perturbation: list[float] = []  # Sy estimated by C++ head-perturbation method
        # Per-layer profiles (each entry is a 1-D array over soil layers)
        self.h_profiles:     list = []   # pressure head [cm]
        self.theta_profiles: list = []   # volumetric water content [-]
        self.fringe_masks:   list = []   # bool array: C(h) fringe mask
        self.zh0_cm:         list = []   # WT depth [cm, positive downward]
        self.q0_cm:          list = []   # depth of q0 interface [cm]
        # Per-species concentration profiles (each entry is a 1-D array over soil layers)
        self.conc_profiles:  dict[str, list] = {}   # species → list of arrays [g/cm³]

    def log_concentration(self, conc_dict: dict):
        """Append one timestep of per-layer Daisy concentrations. Call after log_step."""
        for species, arr in conc_dict.items():
            if species not in self.conc_profiles:
                self.conc_profiles[species] = []
            self.conc_profiles[species].append(np.array(arr) if arr is not None else None)

    def log_step(
        self,
        gw_cm: float,
        layer_depth: float,
        runoff_mm: float,
        sy_est: float,
        h_profile=None,
        theta_profile=None,
        fringe_mask=None,
        zh0_cm: float = None,
        q0_cm: float = None,
    ):
        self.gw_sent_cm.append(gw_cm)
        self.rch_layer_depth.append(layer_depth)
        self.runoff_mm.append(runoff_mm)
        self.sy_initial.append(sy_est)
        self.sy_numerator.append(None)
        self.sy_denominator.append(None)
        self.sy_static_step.append(False)
        self.h_profiles.append(np.array(h_profile) if h_profile is not None else None)
        self.theta_profiles.append(np.array(theta_profile) if theta_profile is not None else None)
        self.fringe_masks.append(np.array(fringe_mask) if fringe_mask is not None else None)
        self.zh0_cm.append(zh0_cm)
        self.q0_cm.append(q0_cm)


