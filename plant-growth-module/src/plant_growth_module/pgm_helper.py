"""Helper functions and constants for Plant Growth Module processing."""

import warnings
import numpy as np
import mikeio
import pandas as pd

from . import forcing_repository as _forcing_repository

load_data_downloader_catalog = _forcing_repository.load_data_downloader_catalog
load_pgm_forcing_library = _forcing_repository.load_pgm_forcing_library
build_forcing_download_plan = _forcing_repository.build_forcing_download_plan
get_data_downloader_classes = _forcing_repository.get_data_downloader_classes
download_forcing_dfs2_series = _forcing_repository.download_forcing_dfs2_series

# Column name variants for land use mapping
VAL_COLS = ["CODE", "VALUE"]
CLASS_COLS = ["CLASS", "SPECIESID"]
APPLY_COLS = ["APPLY", "USE", "ACTIVE"]

# Column name variants for template files
ID_COLS = ["SPECIESID", "SPECIES", "ID", "CLASS"]
VALUE_COLS = ["VALUE", "VAL", "AMOUNT"]
KEY_COLS = ["CONSTANT", "VARIABLE", "KEY", "NAME", "PARAM", "PARAMETER"]
TEMPLATE_COLS = ["TEMPLATE", "SCOPE", "SOURCE"]
TYPE_COLS = ["TYPE", "MAPTYPE", "MAP"]


# State variables source dictionary (to be extended as PGM evolves)
STATE_VARIABLE_SCOPE = {
    "BCa_2D": "landuse",
    "BNa_2D": "landuse",
    "BCb_2D": "landuse",
    "BNb_2D": "landuse",
    "BCc": "landuse",
    "BNc": "landuse",
    "BCs": "landuse",
    "LAI_2D": "landuse",
    "RD_2D": "landuse",
    "SOC": "soilprofile",
    "SON": "soilprofile",
    "NH4": "soilprofile",
    "NO3": "soilprofile",
    "S_NO3": "soilprofile",
    "S_NH4": "soilprofile",
    "S_PWV": "soilprofile",
    "DO": "soilprofile",
    "AO": "soilprofile",
    "LAI": "soilprofile",
    "RD": "soilprofile",
    "BCh_2D": "soilprofile",
}


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
    default_species_values=None,
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
    default_species_values : dict, optional
        Default values by species/class (e.g. filler zeros for classes with Apply=0)
    """
    default_species_values = default_species_values or {}

    # Create output grid initialized with zeros
    output_grid = np.zeros_like(landuse_data, dtype=np.float32)

    # Map each land use code to its corresponding species value
    # Process each code separately to prevent value overwrites
    for code, species in code_to_species.items():
        if species in species_values:
            value = species_values[species]
        elif species in default_species_values:
            value = default_species_values[species]
        else:
            continue

        mask = landuse_data == code
        output_grid[mask] = value

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


def split_lu_mapping_by_apply(lu_df, code_col, class_col, apply_col=None):
    """Create land use mapping and collect classes with Apply=0 for filler values.

    Parameters:
    -----------
    lu_df : pd.DataFrame
        Land use classification dataframe
    code_col : str
        Column name containing numeric grid codes
    class_col : str
        Column name containing class/species names
    apply_col : str, optional
        Column indicating whether PGM applies to this class (1=yes, 0=no)

    Returns:
    --------
    tuple[dict, set]
        code_to_species mapping and set of class names with Apply=0
    """
    code_to_species = dict(zip(lu_df[code_col], lu_df[class_col]))

    if apply_col is None:
        return code_to_species, set()

    apply_values = lu_df[apply_col].fillna(1)
    apply_values = apply_values.astype(str).str.strip().str.lower()
    apply_mask = apply_values.isin(["0", "false", "no", "n"])

    zero_classes = set(lu_df.loc[apply_mask, class_col].dropna().tolist())
    return code_to_species, zero_classes


def load_classification_mappings(lu_template, sp_template, auto_confirm=False):
    """Load and validate land use/soil profile mappings from CSV templates.

    Parameters:
    -----------
    lu_template : Path
        Path to land use classification CSV
    sp_template : Path
        Path to soil profile classification CSV
    auto_confirm : bool, optional
        If True, skip interactive column confirmation

    Returns:
    --------
    tuple[dict, dict, dict]
        code_to_species, zero_fill_values, code_to_soilprofile
    """
    print("\nLoading land use classification...")
    lu_df = pd.read_csv(lu_template)

    code_col = find_col(lu_df, VAL_COLS)
    class_col = find_col(lu_df, CLASS_COLS)
    apply_col = find_col(lu_df, APPLY_COLS)

    if code_col is None or class_col is None:
        raise ValueError(
            "Required columns not found in the land use classification template."
        )

    confirm_payload = {"Code column": code_col, "Class column": class_col}
    if apply_col is not None:
        confirm_payload["Apply column"] = apply_col

    confirmed = confirm_columns(
        confirm_payload,
        auto_confirm=auto_confirm,
        context="Land use classification",
        multi_files=False,
    )
    if not confirmed:
        raise RuntimeError("User cancelled land use mapping")

    code_to_species, zero_fill_classes = split_lu_mapping_by_apply(
        lu_df, code_col, class_col, apply_col
    )
    zero_fill_values = {class_name: 0.0 for class_name in zero_fill_classes}

    print("\nCode to Species mapping:")
    for code, species in code_to_species.items():
        print(f"  {int(code):4d} → {species}")

    if zero_fill_classes:
        print("\nClasses with Apply=0 (forced to 0 in landuse-based maps):")
        for class_name in sorted(zero_fill_classes):
            print(f"  - {class_name}")

    print("\nLoading soil profile classification...")
    sp_df = pd.read_csv(sp_template)
    sp_code_col = find_col(sp_df, VAL_COLS)
    sp_class_col = find_col(sp_df, CLASS_COLS)

    if sp_code_col is None or sp_class_col is None:
        raise ValueError(
            "Required columns not found in the soil profile classification template."
        )

    confirmed = confirm_columns(
        {"Code column": sp_code_col, "Soil profile column": sp_class_col},
        auto_confirm=auto_confirm,
        context="Soil profile classification",
        multi_files=False,
    )
    if not confirmed:
        raise RuntimeError("User cancelled soil profile mapping")

    code_to_soilprofile = dict(zip(sp_df[sp_code_col], sp_df[sp_class_col]))

    print("\nCode to Soil Profile mapping:")
    for code, profile_name in code_to_soilprofile.items():
        print(f"  {int(code):4d} → {profile_name}")

    return code_to_species, zero_fill_values, code_to_soilprofile


def load_spatial_grids(landuse_dfs2, soilprofile_dfs2):
    """Load land use and soil profile dfs2 grids and validate shape compatibility.

    Parameters:
    -----------
    landuse_dfs2 : Path
        Path to land use dfs2 file
    soilprofile_dfs2 : Path
        Path to soil profile dfs2 file

    Returns:
    --------
    tuple
        landuse_ds, landuse_data, soilprofile_ds, soilprofile_data
    """
    print("Loading land use DFS2 file...")
    landuse_ds = mikeio.Dfs2(landuse_dfs2)
    landuse_data = landuse_ds.read()[0].to_numpy()

    print(f"\nLand use grid shape:    {landuse_data.shape}")
    print(f"Unique land use codes:  {np.unique(landuse_data)}")

    print("\nLoading soil profile DFS2 file...")
    soilprofile_ds = mikeio.Dfs2(soilprofile_dfs2)
    soilprofile_data = soilprofile_ds.read()[0].to_numpy()

    print(f"\nSoil profile grid shape:   {soilprofile_data.shape}")
    print(f"Unique soil profile codes: {np.unique(soilprofile_data)}")

    if landuse_data.shape != soilprofile_data.shape:
        raise ValueError("Land use and soil profile grids must have the same shape")

    return landuse_ds, landuse_data, soilprofile_ds, soilprofile_data


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


def _norm(value):
    return str(value).strip().lower()


def _type_is_map(series):
    as_text = series.astype(str).str.strip().str.lower()
    as_num = pd.to_numeric(as_text.str.replace(",", ".", regex=False), errors="coerce")
    return as_num.eq(1) | as_text.isin(["1", "1.0", "true", "yes", "y", "map"])


def process_template_file(
    template_file,
    auto_confirm,
    output_dir,
    landuse_data,
    landuse_ds,
    code_to_species,
    zero_fill_values,
    soilprofile_data,
    soilprofile_ds,
    code_to_soilprofile,
):
    """Process one template CSV file and generate DFS2 maps.

    Parameters:
    -----------
    template_file : Path
        CSV template to process
    auto_confirm : bool
        If True, skip interactive confirmation prompts
    output_dir : Path
        Directory where generated dfs2 files are written
    landuse_data : np.ndarray
        Land use code grid
    landuse_ds : mikeio.Dataset
        Land use dfs2 object used for geometry/metadata
    code_to_species : dict
        Mapping of land use code -> species/class name
    zero_fill_values : dict
        Default values for land use classes (e.g. Apply=0 classes)
    soilprofile_data : np.ndarray
        Soil profile code grid
    soilprofile_ds : mikeio.Dataset
        Soil profile dfs2 object used for geometry/metadata
    code_to_soilprofile : dict
        Mapping of soil profile code -> soil profile name

    Returns:
    --------
    int
        Number of generated maps for this template
    """
    print(f"\n{'=' * 60}")
    print(f"Processing: {template_file.name}")
    print(f"{'=' * 60}")

    df = pd.read_csv(template_file)

    id_col = find_col(df, ID_COLS)
    value_col = find_col(df, VALUE_COLS)
    key_col = find_col(df, KEY_COLS)
    template_col = find_col(df, TEMPLATE_COLS)
    type_col = find_col(df, TYPE_COLS)

    if not all([id_col, value_col, key_col]):
        print(f"\n⚠ Warning: Missing required columns in {template_file.name}")
        print("  Skipping this template.")
        return 0

    confirm_payload = {
        "ID column": id_col,
        "Value column": value_col,
        "Variable column": key_col,
    }
    if template_col is not None:
        confirm_payload["Template column"] = template_col
    if type_col is not None:
        confirm_payload["Type column"] = type_col

    confirmed = confirm_columns(
        confirm_payload,
        auto_confirm=auto_confirm,
        context=template_file.name,
    )
    if not confirmed:
        return 0

    if type_col is not None:
        type_mask = _type_is_map(df[type_col])
        print(f"  Rows with map-enabled type: {int(type_mask.sum())} / {len(df)}")
        df = df[type_mask]

    keep_cols = [id_col, key_col, value_col]
    if template_col is not None:
        keep_cols.append(template_col)

    df = df[keep_cols].dropna(subset=[id_col, key_col, value_col])

    if df.empty:
        print("  No rows to process after filtering. Skipping.")
        return 0

    maps_count = 0

    for key_name in df[key_col].unique():
        subset = df[df[key_col] == key_name]

        scope = STATE_VARIABLE_SCOPE.get(str(key_name).strip())
        if template_col is not None:
            scope_values = (
                subset[template_col]
                .dropna()
                .astype(str)
                .str.strip()
                .str.lower()
                .unique()
            )
            if len(scope_values) > 0:
                scope = scope_values[0]

        if scope is None:
            scope = "landuse"

        id_values = dict(zip(subset[id_col], subset[value_col]))
        id_values_norm = {_norm(k): v for k, v in id_values.items()}

        print(f"\n  Generating map: {key_name} (scope={scope})")

        if scope == "landuse":
            species_values = id_values
            for species, value in species_values.items():
                print(f"    {value:<10} ← {species}")

            output_path = output_dir.joinpath(f"{key_name}.dfs2")
            generate_dfs2_map(
                landuse_data,
                landuse_ds,
                code_to_species,
                species_values,
                output_path,
                key_name,
                default_species_values=zero_fill_values,
            )
            maps_count += 1

        elif scope == "soilprofile":
            profile_values = {}
            for code, profile_name in code_to_soilprofile.items():
                candidates = {_norm(profile_name), _norm(code)}
                try:
                    code_float = float(code)
                    candidates.add(_norm(code_float))
                    if code_float.is_integer():
                        candidates.add(_norm(int(code_float)))
                except (TypeError, ValueError):
                    pass

                for candidate in candidates:
                    if candidate in id_values_norm:
                        profile_values[profile_name] = id_values_norm[candidate]
                        break

            for profile_name, value in profile_values.items():
                print(f"    {value:<10} ← {profile_name}")

            output_path = output_dir.joinpath(f"{key_name}.dfs2")
            generate_dfs2_map(
                soilprofile_data,
                soilprofile_ds,
                code_to_soilprofile,
                profile_values,
                output_path,
                key_name,
            )
            maps_count += 1

        else:
            print(f"    ⚠ Unknown scope '{scope}' for {key_name}; skipping")

    print(f"\n✓ Generated {maps_count} maps from {template_file.name}")
    return maps_count
