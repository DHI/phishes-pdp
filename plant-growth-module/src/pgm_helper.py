"""Helper functions and constants for Plant Growth Module processing."""

import warnings
import numpy as np
import mikeio

# Column name variants for land use mapping
VAL_COLS = ["CODE", "VALUE"]
CLASS_COLS = ["CLASS", "SPECIESID"]

# Column name variants for template files
ID_COLS = ["SPECIESID", "SPECIES", "ID", "CLASS"]
VALUE_COLS = ["VALUE", "VAL", "AMOUNT"]
KEY_COLS = ["CONSTANT", "VARIABLE", "KEY", "NAME", "PARAM", "PARAMETER"]


def find_col(df, cols):
    """Find first matching column name (case-insensitive).

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame to search columns in
    cols : list of str
        List of column name variants to match

    Returns:
    --------
    str or None
        Name of first matching column, or None if not found
    """
    for col in df.columns:
        if any(col.lower() == c.lower() for c in cols):
            return col
    return None


def confirm_columns(column_dict, auto_confirm=False, context="", multi_files=True):
    """Prompt user to confirm detected columns before proceeding.

    Parameters:
    -----------
    column_dict : dict
        Dictionary mapping column descriptions to detected column names
        Example: {"Code column": "CODE", "Class column": "CLASS"}
    auto_confirm : bool, optional
        If True, automatically proceed without user input (default: False)
    context : str, optional
        Additional context to display (e.g., file name being processed)

    Returns:
    --------
    bool
        True if user confirmed or auto_confirm is enabled, False otherwise

    Raises:
    -------
    RuntimeError
        If user input is 'exit' (for critical confirmations)
    """
    # Display detected columns
    print(f"\n📋 DETECTED COLUMNS in {context}:")

    for label, col_name in column_dict.items():
        print(f"  {label:25s}: {col_name}")

    # Check for auto-confirm mode
    if auto_confirm:
        print("\n✓ AUTO_CONFIRM enabled - proceeding automatically...")
        return True

    # Prompt user for confirmation
    print("\n" + "=" * 60)
    print("⏸  CONFIRM COLUMNS:")
    print("   'yes' or 'y' = Continue with these columns")
    print("   'no'  or 'n' = " + ("Skip this file" if multi_files else "Cancel"))
    print("=" * 60)
    user_input = input(">>> ").strip().lower()

    if user_input in ["yes", "y"]:
        print("\n✓ Proceeding with column mapping...")
        return True
    elif user_input in ["no", "n"]:
        if multi_files:
            print(f"⏭  Skipping{' ' + context if context else ''}...")
            return False
        else:
            print("❌ Operation cancelled by user.")
            raise RuntimeError("User cancelled operation")
    else:
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
):
    """Generate a DFS2 map by mapping species values to land use codes.

    Parameters:
    -----------
    landuse_data : np.ndarray
        Land use grid data (codes)
    landuse_ds : mikeio.Dataset
        Original land use dataset (for geometry/metadata)
    code_to_species : dict
        Dictionary mapping land use codes to species names
    species_values : dict
        Dictionary mapping speciesID to value
    output_path : Path
        Output file path for the DFS2
    variable_name : str
        Name of the variable/constant
    """
    # Create output grid initialized with zeros
    output_grid = np.zeros_like(landuse_data, dtype=np.float32)

    # Map each land use code to its corresponding species value
    # Process each code separately to prevent value overwrites
    for code, species in code_to_species.items():
        if species in species_values:
            mask = landuse_data == code
            output_grid[mask] = species_values[species]

    # Create DFS2 with same geometry as input
    # Expand dimensions to match mikeio's expected shape (time, y, x)
    output_grid_3d = np.expand_dims(output_grid, axis=0)

    # Create DataArray with proper metadata
    da = mikeio.DataArray(
        data=output_grid_3d,
        time=landuse_ds.time,
        geometry=landuse_ds.geometry,
        item=mikeio.ItemInfo(variable_name),
    )

    # Write to DFS2 (suppress time step warning for static maps)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Time step is 0.0 seconds")
        da.to_dfs(output_path)
    print(f"  📁 Created: {output_path.name}")


def validate_paths(landuse_dfs2, lu_template, template_files, output_dir):
    """Validate all input paths and create output directory if needed.

    Parameters:
    -----------
    landuse_dfs2 : Path
        Path to land use DFS2 file
    lu_template : Path
        Path to land use classification CSV
    template_files : list of Path
        List of template CSV file paths
    output_dir : Path
        Path to output directory

    Returns:
    --------
    list
        List of error messages (empty if all valid)
    """
    errors = []

    print("=" * 70)
    print("VALIDATING PATHS")
    print("=" * 70)

    # Check land use DFS2
    if not landuse_dfs2.exists():
        errors.append(f"❌ Land use DFS2 not found: {landuse_dfs2}")
    else:
        print(f"✓ Land use DFS2:  {landuse_dfs2.name}")

    # Check LU template
    if not lu_template.exists():
        errors.append(f"❌ LU template not found: {lu_template}")
    else:
        print(f"✓ LU template:    {lu_template.name}")

    # Check template files
    for i, tpl_path in enumerate(template_files, 1):
        if not tpl_path.exists():
            errors.append(f"❌ Template file not found: {tpl_path}")
        else:
            print(f"✓ Template {i}:     {tpl_path.name}")

    # Create output directory if needed
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created output: {output_dir}")
    else:
        print(f"✓ Output dir:     {output_dir}")

    # Report errors or success
    if errors:
        print("\n" + "=" * 70)
        print("VALIDATION FAILED")
        print("=" * 70)
        for error in errors:
            print(error)
        return errors

    print("\n" + "=" * 70)
    print("✓ ALL PATHS VALID - Ready to process")
    print("=" * 70 + "\n")

    return []
