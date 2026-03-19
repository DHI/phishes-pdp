"""Shared utility helpers for Plant Growth Module workflows."""

import warnings

import mikeio
import numpy as np
import pandas as pd


def _suppress_mikeio_static_timestep_warning() -> None:
    """Suppress expected MikeIO warnings when writing static (single-time) DFS2 maps."""
    warnings.simplefilter("ignore", category=UserWarning)
    warnings.filterwarnings(
        "ignore",
        message=r"Time step is 0\.0 seconds\. This must be a positive number\. Setting to 1 second\.",
        category=UserWarning,
        module=r"mikeio\.dfs\._dfs",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"Time step is 0\.0 seconds",
        category=UserWarning,
        module=r"mikeio\.dfs\._dfs",
    )


def find_col(df, cols):
    """Find first matching column name (case-insensitive)."""
    for col in df.columns:
        if any(col.lower() == c.lower() for c in cols):
            return col
    return None


def confirm_columns(column_dict, auto_confirm=False, context="", multi_files=True):
    """Prompt user to confirm detected columns before proceeding."""
    print(f"\n📋 DETECTED COLUMNS in {context}:")

    for label, col_name in column_dict.items():
        print(f"  {label:25s}: {col_name}")

    if auto_confirm:
        print("\n✓ AUTO_CONFIRM enabled - proceeding automatically...")
        return True

    print("\n" + "=" * 60)
    print("⏸  CONFIRM COLUMNS:")
    print("   'yes' or 'y' = Continue with these columns")
    print("   'no'  or 'n' = " + ("Skip this file" if multi_files else "Cancel"))
    print("=" * 60)
    user_input = input(">>> ").strip().lower()

    if user_input in ["yes", "y"]:
        print("\n✓ Proceeding with column mapping...")
        return True
    if user_input in ["no", "n"]:
        if multi_files:
            print(f"⏭  Skipping{' ' + context if context else ''}...")
            return False
        print("❌ Operation cancelled by user.")
        raise RuntimeError("User cancelled operation")

    print(
        f"⚠ Invalid input '{user_input}'. Skipping{' ' + context if context else ''}..."
    )
    return False


def generate_dfs2_map(
    landuse_data,
    landuse_ds,
    code_to_species,
    species_values,
    output_path,
    variable_name,
    default_species_values=None,
):
    """Generate a DFS2 map by mapping values to code grid cells."""
    default_species_values = default_species_values or {}

    output_grid = np.zeros_like(landuse_data, dtype=np.float32)

    for code, species in code_to_species.items():
        if species in species_values:
            value = species_values[species]
        elif species in default_species_values:
            value = default_species_values[species]
        else:
            continue

        mask = landuse_data == code
        output_grid[mask] = value

    output_grid_3d = np.expand_dims(output_grid, axis=0)

    da = mikeio.DataArray(
        data=output_grid_3d,
        time=landuse_ds.time,
        geometry=landuse_ds.geometry,
        item=mikeio.ItemInfo(variable_name),
    )

    with warnings.catch_warnings():
        _suppress_mikeio_static_timestep_warning()
        da.to_dfs(output_path)
    print(f"  📁 Created: {output_path.name}")
