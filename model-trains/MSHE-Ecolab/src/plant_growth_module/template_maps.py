"""Template-driven map generation helpers (landuse and soilprofile scopes)."""

import pandas as pd

from .common_utils import confirm_columns, find_col, generate_dfs2_map

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


def split_lu_mapping_by_apply(lu_df, code_col, class_col, apply_col=None):
    """Create LU mapping and collect Apply=0 classes for forced zero-fill."""
    code_to_species = dict(zip(lu_df[code_col], lu_df[class_col]))

    if apply_col is None:
        return code_to_species, set()

    apply_values = lu_df[apply_col].fillna(1)
    apply_values = apply_values.astype(str).str.strip().str.lower()
    apply_mask = apply_values.isin(["0", "false", "no", "n"])

    zero_classes = set(lu_df.loc[apply_mask, class_col].dropna().tolist())
    return code_to_species, zero_classes


def load_classification_mappings(lu_template, sp_template, auto_confirm=False):
    """Load and validate land use/soil profile mappings from CSV templates."""
    print("\nLoading land use classification...")
    lu_df = pd.read_csv(lu_template)

    code_col = find_col(lu_df, VAL_COLS)
    class_col = find_col(lu_df, CLASS_COLS)
    apply_col = find_col(lu_df, APPLY_COLS)

    if code_col is None or class_col is None:
        raise ValueError("Required columns not found in the land use classification template.")

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
        raise ValueError("Required columns not found in the soil profile classification template.")

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
    """Load land use and soil profile grids and validate shape compatibility."""
    import mikeio
    import numpy as np

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
    """Validate input paths and create output directory if missing."""
    errors = []

    print("=" * 70)
    print("VALIDATING PATHS")
    print("=" * 70)

    if not landuse_dfs2.exists():
        errors.append(f"❌ Land use DFS2 not found: {landuse_dfs2}")
    else:
        print(f"✓ Land use DFS2:  {landuse_dfs2.name}")

    if not lu_template.exists():
        errors.append(f"❌ LU template not found: {lu_template}")
    else:
        print(f"✓ LU template:    {lu_template.name}")

    for i, tpl_path in enumerate(template_files, 1):
        if not tpl_path.exists():
            errors.append(f"❌ Template file not found: {tpl_path}")
        else:
            print(f"✓ Template {i}:     {tpl_path.name}")

    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created output: {output_dir}")
    else:
        print(f"✓ Output dir:     {output_dir}")

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
    """Process one template CSV file and generate DFS2 maps."""
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
                subset[template_col].dropna().astype(str).str.strip().str.lower().unique()
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
