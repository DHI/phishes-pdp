MIKE SHE Exchangeble items

Working note for this repository (2026-05-30):

- This extract is best treated as a product-level catalog of named exchange/output items, not as a guarantee that every listed item is writable in every MIKE SHE setup.
- In this extract, `OL_D` appears in both the exchangeable-input overview and the output-items list.
- `OLDR_IN_FLO` appears in the exchangeable-input overview.
- `OLDR_S` appears in the output-items list.
- In this repository's MIKE Zero 2025 runtime probes, `OLDR_IN_FLO` is solver-visible when written through dataset-native assignment, `OLDR_S` is the reliable responding observable, and `OL_D` still behaves as effectively output-only / non-writable in the current setup.
- Phase 2 leakage implication: this extract lists both `SZ_LEAK_FLX` and `SZ_LEAK_FLO` in the exchangeable-input overview, while `UZ_SZ_EX_POSUP` appears in the output-items list.
- For this repository, that strengthens the current interpretation that `UZ_SZ_EX_POSUP` is the native comparison/output term and that `SZ_LEAK_FLX` / `SZ_LEAK_FLO` are candidate writable correction targets.
- Because DAISY percolation is handled as an interval depth converted to a flux-like rate and `UZ_SZ_EX_POSUP` is also reported in `m/s`, the extract is consistent with keeping `SZ_LEAK_FLX` as the cleaner provisional engineering target.
- This still does **not** fully prove that `SZ_LEAK_FLX` is the final authoritative MIKE SHE target; it remains a provisional choice until confirmed by a controlled exchange test or vendor documentation.


Overview of MIKE SHE items that can be exchanged as input with Python:

Precipitation rate	P_RATE	m/s	2
Air temperature	AIR_TEMP	C	2
Rooting depth	ROOTZONE_WC	m	2
Leaf area index	LAI		2
Crop coefficient	KC		2
reference evapotranspiration	ET_REF_EXC	m/s	2
updated precipitation rate	P_RATE_UPDT	m/s	2
depth of overland water	OL_D	m	2
External sources to Overland (for OpenMI)	OL_SOURCE	m3/s	2
overland water elevation	OL_H	m	2
Inflow (flux) to OL drain	OLDR_IN_FLX	m/s	2
Inflow (flow) to OL drain	OLDR_IN_FLO	m3/s	2
water content in unsaturated zone	UZ_WC		3
head elevation in saturated zone	SZ_HEAD	m	3
SZ horizontal conductivity (for DA- OpenMI)	SZ_K_HOR	m/s	3
SZ vertical conductivity (for DA-OpenMI)	SZ_K_VER	m/s	3
Leakage (flux) to SZ	SZ_LEAK_FLX	m/s	2
Leakage (flow) to SZ	SZ_LEAK_FLO	m3/s	2
Inflow (flux) to SZ drain	SZDR_IN_FLX	m/s	2
Inflow (flow) to SZ drain	SZDR_IN_FLO	m3/s	2
groundwater extraction	SZ_EXTR	m3/s	3
External sources to SZ (for OpenMI)	SZ_SOURCE	m3s	3
pumping from baseflow reservoir	PMP_BASE	m3/s


Output items:
precipitation rate	P_RATE	m/s	2
air temperature	AIR_TEMP	C	2
average water content in the rootzone	ROOT_DPTH		2
rooting depth	ROOTZONE_WC	m	2
leaf area index	LAI		2
crop coefficient	KC		2
reference evapotranspiration	ET_REF_EXC	m/s	2
precipitation rate of next time step	P_RATE_NEXT	m/s	2
updated precipitation rate	P_RATE_UPDT	m/s	2
ETref x Kc	ET_REF_X_KC	m/s	2
actual evapotranspiration	ET_ACT	m/s	2
actual transpiration	TRANSP_ACT	m/s	2
actual soil evaporation	ESOIL_ACT	m/s	2
actual evaporation from interception	EI_ACT	m/s	2
actual evaporation from ponded water	EOL_ACT	m/s	2
canopy interception storage	SI	mm	2
evapotranspiration from SZ	ESZ	m/s	2
snow evaporation	SNOW_ET	m/s	2
depth of overland water	OL_D	m	2
overland flow in x-direction	OL_FLOW_X	m3/s	2
overland flow in y-direction	OL_FLOW_Y	m3/s	2
OL Drain Storage Depth	OLDR_S	m	2
net precipitation rate for AD	P_NET_AD	m/s	2
overland water elevation	OL_H	m	2
infiltration to UZ (negative)	INF	m/s	2
exchange between UZ and SZ (pos.up)	UZ_SZ_EX_POSUP	m/s	2
bypass flow UZ (negative)"	BYP_FLO	m/s	2
total recharge to SZ (pos.down)	RECHARGE_POSDN	m/s	2
total recharge (flow) to SZ (pos.down)	RECH_TOT_FLO	m3/s	2
groundwater levels used by UZ	GW_LVL	m	2
unsaturated zone flow	UZ_FLO	mm/h	3
water content in unsaturated zone	UZ_WC		3
root water uptake	ROOT_UPTK	m/s	3
macropore water content	MP_WC		3
macropore flow	MP_FLO	mm/h	3
exchange from matrix to macropores	MX_MP_EX	mm/h	3
exchange from macropores to matrix	MP_MP_EX	mm/h	3
depth to phreatic surface (negative)	PHR_DP	m	2
elevation of phreatic surface	PHR_ELV	m	2
head elevation in saturated zone	SZ_HEAD	m	3
SZ horizontal conductivity (for DA-OpenMI)	SZ_K_HOR	m/s	3
SZ vertical conductivity (for DA-OpenMI)	SZ_K_VER	m/s	3
seepage flow SZ -overland	SZ_OL_EX	mm/day	2
seepage flow overland - SZ (negative)	OL_SZ_EX	mm/day	2
3D UZ recharge to SZ (negative)	SZ_RE_NEG	mm/day	3
groundwater flux in x-direction	SZ_X_FLO	m3/s	3
groundwater flux in y-direction	SZ_Y_FLO	m3/s	3
groundwater flux in z-direction	SZ_Z_FLO	mm/day	3
groundwater extraction	SZ_EXTR	m3/s	3
SZ exchange flow with river	SZ_RI_EX	m3/s	3
SZ drainage flow from point	SZDR_POINT_FLO	m3/s	3
SZ flow to MOUSE	SZ_MOUSE_FLO	m3/s	3
pumping from baseflow reservoir	PMP_BASE	m3/s
overland to river flow (positive)	OL_RI_POS	m3/s
river to overland flow (negative)	RI_OL_NEG	m3/s
positive baseflow (SZ to river)	SZ_RI_POS	m3/s
negative baseflow (river to SZ)	RI_SZ_NEG	m3/s
exchange from river to SZ	RI_SZ_EX	m3/s
exchange from river to OL	RI_OL_EX	m3/s
river water level	RI_WL	m	2
elevation of ground surface	DEM_Z	m	2
