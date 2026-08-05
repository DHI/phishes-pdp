# PHISHES model trains: inputs and outputs

Coupling field-scale process models with watershed-scale flow and transport models

Each implemented model train is a self-contained project in its own folder, with its own
`pyproject.toml`, environment, tests and notebooks. All of them consume data pulled by the shared
[data-download-tool](../data-download-tool/README.md).

| # | Model train | Folder | Documentation | Implementation status |
| --- | --- | --- | --- | --- |
| 1 | MIKE SHE–Daisy | [MSHE-Daisy/](MSHE-Daisy/) | [README](MSHE-Daisy/README.md) | Not implemented yet |
| 2 | MIKE SHE–MIKE ECO Lab Plant Growth Module | [MSHE-Ecolab-PGM/](MSHE-Ecolab-PGM/) | [README](MSHE-Ecolab-PGM/README.md) | **Implemented** |
| 3 | MODFLOW 6–UZF–Reservoir with Daisy extension | — | [described below](#3-urban-watersheds-modflow-6uzfreservoir-model-with-daisy-extension) | Not implemented yet |
| 4 | 1D HYDRUS–PHREEQC–MODFLOW-2005–MT3D | [HYDRUS-PHREEQC-MODFLOW2005-MT3D/](HYDRUS-PHREEQC-MODFLOW2005-MT3D/) | [README](HYDRUS-PHREEQC-MODFLOW2005-MT3D/README.md) | Not implemented yet |

`MSHE-Ecolab-PGM/` was previously `plant-growth-module/` at the repository root. The move was path-only —
the `plant_growth_module` Python package, its distribution name and all imports are unchanged.

The sections below describe each train scientifically: inputs, the coupling, the data exchanged
between components, and outputs.

## 1. Small agricultural watersheds: MIKE SHE–Daisy

### Inputs
Climate data; soil profiles; land use map; soil type map; catchment characteristics; agricultural management scenarios such as tillage, fertilisation, crop rotation and irrigation.

### Model train
Daisy simulates detailed soil–plant–atmosphere processes at representative field profiles. Daisy outputs are transferred one-way to MIKE SHE, where they substitute MIKE SHE unsaturated-zone calculations in matching agricultural areas. MIKE SHE represents catchment-scale overland flow, saturated zone processes and channel routing.

### Data exchanged
Runoff; matrix percolation; matrix drain flow; nitrogen, Bentazone, N-Methyl-Bentazone and carbon concentrations in runoff, percolation and soil drain components.

### Outputs
- At field scale: soil conditions, plant growth, nutrient and contaminant leaching, carbon sequestration.
- At catchment scale: water balance, soil conditions, nutrient and contaminant leaching.

## 2. Large agricultural watersheds: MIKE SHE–MIKE ECO Lab Plant Growth Module

### Inputs
MIKE SHE water movement and water quality variables; environmental forcings including solar radiation, temperature, precipitation and soil water content; plant groups or crop types; soil and catchment characteristics; nutrient inputs and management scenarios.

### Model train
MIKE SHE provides hydrological and water-quality transport. MIKE ECO Lab provides the Plant Growth Module, which dynamically simulates plant growth, nutrient uptake, carbon and nitrogen dynamics, and feedbacks to MIKE SHE through state variables such as LAI, root depth and nutrient concentrations.

### Data exchanged
MIKE SHE passes constants, forcings and existing state-variable values to MIKE ECO Lab. MIKE ECO Lab updates state variables and returns modified concentrations and plant-growth variables to MIKE SHE.

### Outputs
Water balance indicators; actual evapotranspiration; soil moisture; runoff; infiltration; percolation; drain flow; crop yield; above-ground and below-ground residues; total soil organic carbon; nitrogen fixation; plant nitrogen uptake; denitrification losses; nitrate and ammonium leaching.

## 3. Urban watersheds: MODFLOW 6–UZF–Reservoir model with Daisy extension

### Inputs
Hydrogeological properties; stratigraphy; hydraulic conductivity; storage parameters; soil hydraulic properties; elevation; land use; precipitation; run-on; contaminant concentrations; transport parameters such as dispersivity, effective porosity, initial concentrations and reaction parameters.

### Model train
MODFLOW 6 simulates saturated groundwater flow and groundwater transport. The UZF and UZT packages simulate unsaturated-zone flow and transport. An external reservoir water-balance model computes ponding, inundation and infiltration, and exchanges data online with MODFLOW 6 through the API. Daisy is proposed as an offline extension to represent soil–plant–atmosphere and biogeochemical processes not explicitly represented in MODFLOW 6.

### Data exchanged
- From reservoir model to MODFLOW 6: infiltration rates for inundated nodes.
- From MODFLOW 6 to reservoir model: precipitation plus run-on, groundwater discharge, rejected infiltration, infiltration rates, groundwater heads, discharge fluxes and solute mass fluxes.

### Outputs
Ponding levels; inundation areas; soil moisture dynamics; groundwater levels; unsaturated-zone flow; saturated groundwater flow; solute transport; contaminant movement through vadose zone and groundwater; hydrological soil-function indicators.

## 4. Contaminated sites: 1D HYDRUS–PHREEQC–MODFLOW-2005–MT3D

### Inputs
Representative soil profiles; effective precipitation; evapotranspiration; recharge; soil and soil-water concentrations; groundwater concentrations; partitioning coefficients; hydraulic conductivity; porosity; geological structure; climate records; site monitoring data; remediation-scenario parameters.

### Model train
1D HYDRUS simulates vertical unsaturated water flow. PHREEQC simulates geochemical speciation and reactive transport. Outputs from 1D HYDRUS–PHREEQC are transferred one-way as boundary conditions to MODFLOW-2005 and MT3D. MODFLOW simulates three-dimensional groundwater flow and MT3D simulates contaminant migration in groundwater.

### Data exchanged
Vertical water fluxes; leaching rates; solute concentrations at the bottom boundary of the unsaturated zone; time-series recharge and contaminant boundary conditions for the saturated-zone model.

### Outputs
Soil moisture; contaminant mass; PFAS or arsenic transport; soluble or available contaminant concentrations; groundwater plume evolution; pollution buffering indicators; water storage and fluxes; carbon and nitrogen cycle indicators; remediation-strategy performance.
