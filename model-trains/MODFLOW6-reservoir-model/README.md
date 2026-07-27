# PHISHES

This model train is a Python-based groundwater flow and solute transport modelling framework built on top of iMOD and MODFLOW 6. It generates, runs, and post-processes groundwater flow and transport simulations from TOML configuration files.

## Project structure

```text
src/
  generation/         # Model construction (flow and transport)
  postprocessing/     # Post-processing and water balance analysis
  simulation/         # Simulation runners (MF6 and reservoir)

workflows/
  wadi/               # Urban runoff / wadi drainage scenario
  vegetation/         # Vegetation evapotranspiration scenario
```

## Workflows

Each workflow folder contains:

- A TOML configuration file that defines model inputs such as discretisation, properties, boundary conditions, and transport parameters.
- A Python script that reads the configuration, builds the model with `ModelFromToml`, runs the simulation, and analyses the results.

### Wadi scenario

Simulates rapid surface-water drainage through a wadi channel, including ponding, groundwater flow, and solute transport.

```sh
cd workflows/wadi
python scenario_wadi.py
```

### Vegetation scenario

Simulates longer-term groundwater dynamics driven by recharge, evapotranspiration, and drainage/infiltration through ditches and sewers.

```sh
cd workflows/vegetation
python scenario_vegetation.py
```

## Getting started

### Prerequisites

- [pixi](https://pixi.sh) for environment management.
- MODFLOW 6 binaries.

### Install the environment

```sh
pixi install
```

### MODFLOW 6 binaries

MODFLOW 6 executables are not distributed with PHISHES.

Download the desired release from the official MODFLOW 6 GitHub releases page and specify the binary location in the model TOML configuration:

```toml
mf6_binaries = "c:\\src\\modflow6_release\\mf6.7.0_win64\\mf6.7.0_win64\\bin"
```

### Daisy binaries

Daisy BMI binaries are currently installed as `.pyd` files in the Python environment. Installation is handled through Pixi tasks.

In the future, Daisy binaries should be downloaded directly from:

- Official Daisy GitHub releases.
- A maintained project-specific fork.

## Run a workflow

Navigate to the workflow directory and run the scenario script:

```sh
cd workflows/wadi
python scenario_wadi.py
```

Set `run = True` inside the script to build and run the model, or `run = False` to load existing results.

## Configuration

Model scenarios are configured through TOML files.

Key sections include:

- `[model]` – Model name and type.
- `[model.discretisation]` – Spatial extent, layer definition, simulation period, and time step.
- `[model.transport]` – Porosity, dispersivity, retardation, decay, and species.
- `[model.properties]` – Hydraulic conductivity, storage, and optional spatial refinement.
- `[model.boundary_conditions]` – Initial conditions, recharge, drainage/infiltration, and evapotranspiration.

## Daisy coupling

> **Under development**
>
> Daisy-MODFLOW 6 coupling functionality is currently under active development and is **not included in the public repository**.

Documentation, installation instructions, and examples for Daisy coupling will be added once the functionality becomes publicly available.

## Dependencies

Key packages managed through `pixi.toml`:

- `imod` — iMOD Python interface to MODFLOW 6
- `xarray`, `numpy`, `scipy` — array and numerical operations
- `geopandas`, `fiona`, `rasterio` — spatial data handling
- `openpyxl` — reading Excel-based input data
- `xmipy` — BMI/XMI coupling interface