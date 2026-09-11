# Coupling between Hydrus-1D and MODFLOW6

This folder contains scripts performing the coupling of Hydrus-1D model (Šimůnek and Van Genuchten, 2008) with MODFLOW6 model (Hughes et al., 2017), effectively coupling soil columns with an aquifer.

This is the first version that performs a one-way coupling transferring the recharge between the bottom soil layer and the aquifer only layer.

## Installation

This folder does not contain the executable files and the DLLS for the two models. The missing files should be placed as follows in this folder:

```text
hydrus-1d+modflow6
├── modflow
│   ├── libmf6.dll
│   └── mf6.exe
├── H1D_CALC.EXE
├── PCP_BASE.DLL
├── PCP_FEM2.DLL
├── PCP_MESH.DLL
├── PCPINFOR.SYS
└── ROSETTA.DLL
```

The files *H1D_CALC.EXE*, *PCP_BASE.DLL*, *PCP_FEM2.DLL*, *PCP_MESH.DLL*, *PCPINFOR.SYS*, and *ROSETTA.DLL* are to be downloaded from https://www.pc-progress.com/en/Default.aspx?hydrus-1d.

The files *libmf6.dll* and *mf6.exe* are to be downloaded from https://code.usgs.gov/modflow61/modflow6/-/releases (ZIP archive *mf#.#.#_win64.zip*) (Langevin et al., 2026).

## Usage

The main script to run is *main_coupled_models.py*. This will run the HYDRUS-1D model then the MODFLOW6 model.

## Acknowledments

This coupling has been created by Luca Guillaumot, Thibault Hallouin, and Nicolas Devau (French Geological Survey, BRGM).

This work is part of the EU-funded PHISHES project https://www.phishes-project.eu/.

## References

Hughes, J.D., Langevin, C.D., and Banta, E.R., 2017, Documentation for the MODFLOW 6 framework: U.S. Geological Survey Techniques and Methods, book 6, chap. A57, 40 p., https://doi.org/10.3133/tm6A57.

Langevin, C.D., Hughes, J.D., Provost, A.M., Russcher, M.J., Morway, E.D., Reno, M.J., Bonelli, W.P., Niswonger, R.G., Panday, S., Titus, S., Merrick, D, and Banta, E.R., 2026, MODFLOW 6 Modular Hydrologic Model version 6.7.0: U.S. Geological Survey Software Release, 6 February 2026, https://doi.org/10.5066/P1IJAXDZ

Šimůnek, J. and van Genuchten, M.T. (2008), Modeling Nonequilibrium Flow and Transport Processes Using HYDRUS. Vadose Zone Journal, 7: 782-797. https://doi.org/10.2136/vzj2007.0074
