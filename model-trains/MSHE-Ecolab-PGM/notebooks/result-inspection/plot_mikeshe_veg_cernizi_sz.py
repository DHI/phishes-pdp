# -*- coding: utf-8 -*-
"""
Created on Mon Nov 10 14:39:19 2025

@author: kadr
"""

from pathlib import Path

import mikeio
import matplotlib.pyplot as plt

# from matplotlib.colors import Colormap
# from matplotlib.colors import LinearSegmentedColormap
# from matplotlib import colors
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend comment out if you want to see plots
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

i_data = Path(r"Cernici16_Ben_v101_WM_AD_ECOLabv15.she - Result Files")
i_res = i_data.joinpath("png")

files = [f.name for f in i_data.iterdir() if ".dfs3" in f.name]
# files3D=['WmWqBox_5x6_KADR_v10_UZ_SZ_WQ_3DUZ.dfs3', 'WmWqBox_5x6_KADR_v10_UZ_SZ_3DUZ.dfs3']#,'WmWqBox_5x6_KADR_v9_UZ_SZ_WQ_3DSZ.dfs3']
# files2D=['WmWqBox_5x6_KADR_v10_UZ_SZ_ET_UzCells.dfs2']

no_uz_layer = 24
max_layer = no_uz_layer - 1
loc_x, loc_y = 100, 100

# %% EXTRAXT DFS0 LAYER BY LAYER
layers = list(range(0, no_uz_layer))

special_vars = (
    "UZ soil temperature",
    "unsaturated zone flow",
    "water content in unsaturated zone",
    "root water uptake",
    "head elevation in saturated zone",
    "groundwater flow in x-direction",
    "groundwater flow in y-direction",
    "groundwater flux in z-direction",
    "External sources to SZ",
    "SZ soil temperature",
)


# files3D=['WmWqBox_5x6_KADR_v10_UZ_SZ_WQ_3DUZ.dfs3', 'WmWqBox_5x6_KADR_v10_UZ_SZ_3DSZ.dfs3']
for f in files:
    if "WQ" in f and "3DUZ" in f:
        res = "WQ"
        zone = "UZ"
    elif "WQ" not in f and "flow" in f:
        res = "WM"
        zone = "flow"
    elif "WQ" in f and "3DSZ" in f:
        res = "WQ"
        zone = "SZ"
    elif "WQ" not in f and "3DSZ." in f:
        res = "WM"
        zone = "3DSZ"
    elif "WQ" not in f and "3DUZ." in f:
        res = "WM"
        zone = "3DUZ"

    print(f)
    print(res, "   ", zone)
    dfs_h = mikeio.open(i_data.joinpath(f))

    # for layer_idx in list(range(0,dfs_h.geometry.nz)):
    for layer_idx in list(reversed(range(0, dfs_h.geometry.nz))):
        print(layer_idx)
        df = pd.DataFrame()
        for i in dfs_h.items:
            # print(i.name)

            dfs_i = mikeio.read(i_data.joinpath(f), items=i.name, layers=layer_idx)
            # print(i.name)
            # break
            if any(x in i.name for x in special_vars):
                var = i.name

            else:
                # var=i.name.split(", ")[1]
                var = i.name.split(", ")[1] if ", " in i.name else i.name

            # df_=dfs_i.sel(x=dfs_i.geometry.x[-1]/2, y=dfs_i.geometry.y[-1]/2).to_dataframe()
            # Find middle of domain
            xmid = 0.5 * (dfs_i.geometry.x[0] + dfs_i.geometry.x[-1])
            ymid = 0.5 * (dfs_i.geometry.y[0] + dfs_i.geometry.y[-1])

            ix = int(np.argmin(np.abs(dfs_i.geometry.x - xmid)))
            iy = int(np.argmin(np.abs(dfs_i.geometry.y - ymid)))

            # df_ = dfs_i.isel(x=ix).isel(y=iy).to_dataframe()
            df_ = dfs_i.isel(x=loc_x, y=loc_y).to_dataframe()
            df_.columns = [var]
            df = pd.concat([df, df_], axis=1)

        dfs0_png = i_res.joinpath("dfs0", res)
        dfs0_png.mkdir(parents=True, exist_ok=True)

        mikeio.from_pandas(df, items=dfs_h.items).to_dfs(
            dfs0_png.joinpath(f"Layer_{layer_idx}_{zone}.dfs0")
        )


# %% 3D
print("-----------   Plotting 3D  ------------------")

# 0 → 0.2 with 0.05 increments
part1 = np.arange(0, 0.2 + 0.001, 0.05)  # +0.001 ensures inclusion of 0.2 due to float rounding

# 0.2 → 10 with 0.2 increments
part2 = np.arange(0.2, 5 + 0.001, 0.2)

# Combine, removing the duplicate 0.2
depth = np.unique(np.concatenate((part1, part2)))

depth_sz = np.arange(0, 10 + 0.001, 5)


for f in files:
    print(f)
    dfs_h = mikeio.open(i_data.joinpath(f))
    if "WQ" in f and "3DUZ" in f:
        res = "WQ"
        zone = "UZ"
    elif "WQ" not in f and "flow" in f:
        res = "WM"
        zone = "flow"
    elif "WQ" in f and "3DSZ" in f:
        res = "WQ"
        zone = "SZ"
    elif "WQ" not in f and "3DSZ." in f:
        res = "WM"
        zone = "3DSZ"
    elif "WQ" not in f and "3DUZ." in f:
        res = "WM"
        zone = "3DUZ"

    if zone == "flow" or zone == "SZ" or zone == "3DSZ":
        for i in dfs_h.items:
            print(i.name)
            dfs_i = mikeio.read(i_data.joinpath(f), items=i.name)
            # break
            if any(x in i.name for x in special_vars):
                var = i.name

            else:
                # var=i.name.split(", ")[1]
                var = i.name.split(", ")[1] if ", " in i.name else i.name

            # PLOT PROFILE
            # x=int(dfs_i.geometry.nx/2)
            # y=int(dfs_i.geometry.ny/2)
            # Find middle of domain
            # xmid = 0.5 * (dfs_i.geometry.x[0] + dfs_i.geometry.x[-1])
            # ymid = 0.5 * (dfs_i.geometry.y[0] + dfs_i.geometry.y[-1])

            # ix = int(np.argmin(np.abs(dfs_i.geometry.x - xmid)))
            # iy = int(np.argmin(np.abs(dfs_i.geometry.y - ymid)))

            x = loc_x
            y = loc_y

            z_max = int(dfs_i.geometry.nz)
            da_i = dfs_i[0]
            da = da_i[:, :, y, x]
            data = da.to_numpy().T  # (layers, time)

            # Get actual datetime values
            times = da.time  # mikeio → pandas.DatetimeIndex
            n_layers = data.shape[0]

            # Plot
            fig, ax = plt.subplots(figsize=(10, 6))
            im = ax.imshow(
                data,
                aspect="auto",
                origin="lower",
                extent=[
                    mdates.date2num(times[0]),
                    mdates.date2num(times[-1]),
                    depth_sz[-1],
                    depth_sz[0],
                ],
            )

            # Format x-axis as dates
            ax.xaxis_date()
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            fig.autofmt_xdate(rotation=45)

            # Labels and title
            plt.colorbar(im, ax=ax, label=f"{var}")
            ax.set_xlabel("Time")
            ax.set_ylabel("Depth (m)")
            ax.set_title(f"{var} (y={y}, x={x})")
            filename_out = f"{zone}_{var}.png"

            profile_png = i_res.joinpath("profile", res)
            profile_png.mkdir(parents=True, exist_ok=True)

            plt.tight_layout()
            plt.savefig(profile_png.joinpath(filename_out), dpi=125, bbox_inches="tight")

            plt.close()

            # PLOT TS

            fig = plt.figure(figsize=(10, 6))
            ax = plt.subplot(111)
            da_i[:, z_max - 1, y, x].plot(ax=ax, c="k", label=f"MIKE SHE {z_max}")
            da_i[:, z_max - 2, y, x].plot(ax=ax, c="k", label=f"MIKE SHE {z_max - 1}")

            # ax.plot(df2plot, label='Experimenter result', c='b')
            ax.set_xlabel("Time")
            ax.set_ylabel(f"{var}")
            ax.set_title(f"{var}", fontsize=10)
            ax.legend()

            filename_out = f"{zone}_{res}_{var}.png"

            ts_png = i_res.joinpath("TS")
            ts_png.mkdir(parents=True, exist_ok=True)

            plt.savefig(ts_png.joinpath(filename_out), dpi=125, bbox_inches="tight")

            plt.close()

    else:
        for i in dfs_h.items:
            # print(i.name)
            dfs_i = mikeio.read(i_data.joinpath(f), items=i.name)
            if any(x in i.name for x in special_vars):
                var = i.name
            else:
                # var=i.name.split(", ")[1]
                var = i.name.split(", ")[1] if ", " in i.name else i.name

            # PLOT PROFILE
            # x=int(dfs_i.geometry.nx/2)
            # y=int(dfs_i.geometry.ny/2)
            # Find middle of domain
            # xmid = 0.5 * (dfs_i.geometry.x[0] + dfs_i.geometry.x[-1])
            # ymid = 0.5 * (dfs_i.geometry.y[0] + dfs_i.geometry.y[-1])

            # ix = int(np.argmin(np.abs(dfs_i.geometry.x - xmid)))
            # iy = int(np.argmin(np.abs(dfs_i.geometry.y - ymid)))

            x = loc_x
            y = loc_y

            da_i = dfs_i[0]
            da = da_i[:, :, y, x]
            data = da.to_numpy().T  # (layers, time)

            # Get actual datetime values
            times = da.time  # mikeio → pandas.DatetimeIndex
            n_layers = data.shape[0]

            # Plot
            fig, ax = plt.subplots(figsize=(10, 6))
            im = ax.imshow(
                data,
                aspect="auto",
                origin="lower",
                extent=[mdates.date2num(times[0]), mdates.date2num(times[-1]), depth[-1], depth[0]],
            )

            # Format x-axis as dates
            ax.xaxis_date()
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            fig.autofmt_xdate(rotation=45)

            # Labels and title
            plt.colorbar(im, ax=ax, label=f"{var}")
            ax.set_xlabel("Time")
            ax.set_ylabel("Depth (m)")
            ax.set_title(f"{var} (y=1, x=1)")
            filename_out = f"{zone}_{var}.png"

            profile_png = i_res.joinpath("profile", res)
            profile_png.mkdir(parents=True, exist_ok=True)

            plt.tight_layout()
            plt.savefig(profile_png.joinpath(filename_out), dpi=125, bbox_inches="tight")

            plt.close()

            # PLOT TS

            fig = plt.figure(figsize=(10, 6))
            ax = plt.subplot(111)
            da_i[:, max_layer, y, x].plot(ax=ax, c="k", label=f"MIKE SHE {max_layer}")
            da_i[:, max_layer - 1, y, x].plot(ax=ax, c="b", label=f"MIKE SHE {max_layer - 1}")
            da_i[:, max_layer - 2, y, x].plot(ax=ax, c="g", label=f"MIKE SHE {max_layer - 2}")
            da_i[:, max_layer - 3, y, x].plot(ax=ax, c="r", label=f"MIKE SHE {max_layer - 3}")
            # ax.plot(df2plot, label='Experimenter result', c='b')
            ax.set_xlabel("Time")
            ax.set_ylabel(f"{var}")
            ax.set_title(f"Layer comparison: {var}", fontsize=10)
            ax.legend()

            filename_out = f"{zone}_{res}_{var}.png"

            ts_png = i_res.joinpath("TS")
            ts_png.mkdir(parents=True, exist_ok=True)

            plt.savefig(ts_png.joinpath(filename_out), dpi=125, bbox_inches="tight")

            plt.close()
