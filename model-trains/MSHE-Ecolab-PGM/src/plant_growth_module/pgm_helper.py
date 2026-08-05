"""Backwards-compatible facade for legacy imports.

This module re-exports helpers from focused modules:
- common_utils.py
- template_maps.py
- soil_profile_setup.py
"""

from .common_utils import confirm_columns, find_col, generate_dfs2_map
from .initial_condition_updater import (
    backup_she,
    build_species_item_index,
    split_dfs3_to_layers,
    update_initial_conditions,
)
from .forcing_repository import (
    build_forcing_download_plan,
    download_forcing_dfs2_series,
    get_data_downloader_classes,
    load_data_downloader_catalog,
    load_pgm_forcing_library,
)
from .soil_profile_setup import (
    ProfileProperty,
    build_soil_profile_summary,
    generate_soil_property_dfs2_outputs,
    parse_soil_profile_text,
    parse_soil_profile_texts,
)
from .template_maps import (
    APPLY_COLS,
    CLASS_COLS,
    ID_COLS,
    KEY_COLS,
    STATE_VARIABLE_SCOPE,
    TEMPLATE_COLS,
    TYPE_COLS,
    VAL_COLS,
    VALUE_COLS,
    load_classification_mappings,
    load_spatial_grids,
    process_template_file,
    split_lu_mapping_by_apply,
    validate_paths,
)

__all__ = [
    "APPLY_COLS",
    "CLASS_COLS",
    "ID_COLS",
    "KEY_COLS",
    "STATE_VARIABLE_SCOPE",
    "TEMPLATE_COLS",
    "TYPE_COLS",
    "VAL_COLS",
    "VALUE_COLS",
    "ProfileProperty",
    "backup_she",
    "build_soil_profile_summary",
    "build_species_item_index",
    "confirm_columns",
    "find_col",
    "generate_dfs2_map",
    "split_dfs3_to_layers",
    "update_initial_conditions",
    "build_forcing_download_plan",
    "download_forcing_dfs2_series",
    "get_data_downloader_classes",
    "load_data_downloader_catalog",
    "load_pgm_forcing_library",
    "generate_soil_property_dfs2_outputs",
    "load_classification_mappings",
    "load_spatial_grids",
    "parse_soil_profile_text",
    "parse_soil_profile_texts",
    "process_template_file",
    "split_lu_mapping_by_apply",
    "validate_paths",
]
