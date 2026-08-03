# MIKE SHE - Daisy

The purpose of this model train coupling MIKE SHE - Daisy is to upscale simulations from field scale
to large scale, enabling a user to simulate dynamic mass balance calculation in the soil-water profile
as well as a 3D spatial distribution of soil contamination at watershed scale. In this coupling structure,
Daisy is used for detailed simulation of the effects of changed agricultural practices
(tillage, fertilizing, crop rotation, etc.) on the soil health and the leakage of nutrients and pesticides.
The simulation will be made for selected representative soil profiles.

To incorporate the interaction with groundwater and streams it will be linked with the groundwater
component of MIKE SHE. Results from Daisy substitute those from MIKE SHE’s unsaturated zone
(UZ) flow component in parts of the catchment. DAISY outputs are used to prescribe all fluxes that
MIKE SHE would otherwise calculate internally in the UZ.
MIKE SHE retains its overland, saturated zone, and river/channel routing modules, as well as
unsaturated zone processes where the substitution has not taken place.
The coupling is one-way: Daisy drives MIKE SHE with water and energy fluxes, while MIKE SHE
does not feed back into Daisy. The Daisy-MIKE SHE coupling consists of the following components:
spatial mapping, temporal mapping, and a Quality Control (QC) calculation. Figure 4 shows the
coupling process steps. The spatial mapping step takes place in the beginning, whereas the temporal
mapping step is continuous based on the MIKE SHE UZ time step. The user, in addition to defining user defined settings for the coupling, must supply both models and results, a land use map and a
soil type map.
