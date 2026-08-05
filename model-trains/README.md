# PHISHES model trains: inputs and outputs

Coupling field-scale process models with watershed-scale flow and transport models

A **model train** is a chain of coupled simulation models aimed at one class of soil-health question.
PHISHES has four, each built by a different project partner for a different setting: agricultural
catchments, urban catchments, and contaminated sites.

This page is the overview — what each train does and which one to reach for. Once you have picked one,
its own README has the technical detail: how to install it, what software it needs and how to run it.

| Model train                                  | Delivered by | Folder                                                               | Documentation                                                                           | Implementation status |
| -------------------------------------------- | ------------ | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------- |
| MIKE SHE–Daisy                               | DHI          | [MSHE-Daisy/](MSHE-Daisy/)                                           | [README](MSHE-Daisy/README.md)                                                          | Not implemented yet   |
| MIKE SHE–MIKE ECO Lab Plant Growth Module    | DHI          | [MSHE-Ecolab-PGM/](MSHE-Ecolab-PGM/)                                 | [README](MSHE-Ecolab-PGM/README.md)                                                     | **Implemented**       |
| MODFLOW 6–UZF–Reservoir with Daisy extension | Deltares     | [MODFLOW6-reservoir-model/](MODFLOW6-reservoir-model/)               | [README](MODFLOW6-reservoir-model/README.md)                                            | **Implemented**       |
| 1D HYDRUS–PHREEQC–MODFLOW-2005–MT3D          | BRGM         | [HYDRUS-PHREEQC-MODFLOW2005-MT3D/](HYDRUS-PHREEQC-MODFLOW2005-MT3D/) | [README](HYDRUS-PHREEQC-MODFLOW2005-MT3D/README.md)                                     | **Implemented**       |

**The simulation software itself is not in this repository.** Every train drives external models —
MIKE SHE and MIKE ECO Lab, Daisy, HYDRUS-1D, MODFLOW — which you install separately under their own
licences. The train's README says which ones it needs and where to get them.

## Which train do I need?

| If you are working on… | Use | Available now? |
| --- | --- | --- |
| A **small agricultural catchment**, and you care about how tillage, fertilising, crop rotation or irrigation change soil health and the leaching of nutrients and pesticides | MIKE SHE–Daisy | No — design stage |
| A **large agricultural catchment**, where plant growth, carbon and nitrogen need to respond dynamically to the hydrology rather than being prescribed | MIKE SHE–MIKE ECO Lab Plant Growth Module | **Yes** |
| An **urban catchment**, where ponding and inundation at the surface drive infiltration into the unsaturated zone and groundwater | MODFLOW 6–UZF–Reservoir with Daisy extension | **Yes** |
| A **contaminated site** — PFAS from firefighting foam, or trace metals from mine tailings — where you need contaminant movement from the soil profile into groundwater | 1D HYDRUS–PHREEQC–MODFLOW-2005–MT3D | **Yes** |

## What the available trains do

### MIKE SHE–MIKE ECO Lab Plant Growth Module — DHI

Prepares everything a MIKE SHE + MIKE ECO Lab Plant Growth Module simulation needs, so that plant
growth and nutrient cycling are simulated inside the catchment model instead of being fixed in advance.
It turns land-use and soil-profile maps into the spatial parameter fields the Plant Growth Module reads,
derives the soil water-retention properties each grid cell needs, builds the climate forcing grids, and
can restart a simulation from the water-quality state of a previous run.

Four workflows, each driven by its own Jupyter notebook. Setup, the workflow descriptions and the
notebook index are in its **[README](MSHE-Ecolab-PGM/README.md)**.

### MODFLOW 6–UZF–Reservoir with Daisy extension — Deltares

Simulates an urban catchment where water ponds at the surface before it gets into the ground. A
reservoir water balance tracks ponding and inundation and hands the resulting infiltration to a
MODFLOW 6 model, which carries groundwater flow and solute transport through the unsaturated zone and
the aquifer. You describe a scenario in a TOML file — extent, layers, soil and aquifer properties,
boundary conditions, transport parameters — and the framework builds, runs and post-processes the
simulation for you, water balance included.

Two worked scenarios ship with it: a wadi channel draining urban runoff, and longer-term groundwater
dynamics under vegetation evapotranspiration with ditches and sewers. Built on iMOD Python and managed
with [pixi](https://pixi.sh) rather than uv. Its **[README](MODFLOW6-reservoir-model/README.md)** covers
setup, the TOML configuration and how to run a scenario; note that per that README the Daisy coupling
itself is still under development and not part of the public code.

### 1D HYDRUS–PHREEQC–MODFLOW-2005–MT3D — BRGM

Connects what happens in a soil column to what happens in the aquifer underneath it. HYDRUS-1D
simulates water and solute movement down through the unsaturated soil profile; the resulting recharge
and its solute concentration are then handed to a MODFLOW 6 groundwater flow and transport model, which
is advanced step by step and fed the new values as it goes. The exchange is one-way — from the bottom of
the soil profile into the aquifer — and it lets you follow a contaminant from the surface, through the
vadose zone, into the groundwater plume.

Delivered complete by BRGM and run as Python scripts rather than notebooks. Installation and usage are
in its **[README](HYDRUS-PHREEQC-MODFLOW2005-MT3D/README.md)**; beyond the two models it names, the
scripts need the Python packages `flopy`, `xmipy`, `numpy`, `pandas`, `matplotlib` and `tqdm`.

## Scientific descriptions

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

## Adding a model train

This page is the index of model trains, so it has to be updated in the same change that adds a train or
changes one's status. Four places:

1. The **table at the top** — all five columns, using `—` where there is no folder or README yet.
2. **[Which train do I need?](#which-train-do-i-need)** — one row, phrased as the problem a reader
   arrives with rather than as the model.
3. **[What the available trains do](#what-the-available-trains-do)** — a short subsection, if the train
   is available to use.
4. The train's numbered **[scientific description](#scientific-descriptions)**, and the available-trains
   list in the [root README](../README.md).

Keep it an overview: it exists so a reader can work out which train fits their problem. Installation
steps, dependency lists and command lines belong in the train's own README.
