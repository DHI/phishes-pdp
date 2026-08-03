# HYDRUS - PHREEQC - MODFLOW-2005 - MT3D

A 1D HYDRUS–PHREEQC – MODFLOW 2005 – MT3D model train designed for PFAS contaminated sites resulting from AFFF use, as well as for mine tailings enriched in trace metals.

The model train applies one-dimensional flow (1D Hydrus) and reactive transport (PHREEQC) to representative soil profiles which simulate a mass-balance of water and contaminant transport, in turn used as input to a more extensive 3D groundwater flow (MODFLOW) and transport (MT3D) model. This allows for simulation of the fate of contaminants, here PFAS and arsenic, to optimize, assess and compare different soil remediation approaches. These simulations include parameters which directly influence soil function and health, although in this model train a distinction is made between parameterized soil function indicators such as root zone depth, soil retention capacity and porosity and simulated soil function indicators such as soil moisture, permeability/drainage and degree of contamination.

The coupling of the one-dimensional and three-dimensional components is achieved through a staged workflow:
- 1D Hydrus calculates unsaturated water flow using the Richards’ equation.
- PHREEQC processes chemical speciation and mass balance reactions under transient moisture and redox conditions.
- Outputs from 1D HP, including vertical water fluxes, leaching rates, and solute concentrations at the bottom boundary of the unsaturated zone, are exported as time series boundary conditions to the saturated zone model.
- MODFLOW simulates groundwater flow using site-specific hydraulic properties and geological structure.
- MT3D incorporates the transferred solute fluxes, allowing simulation of PFAS migration in three dimensions.
