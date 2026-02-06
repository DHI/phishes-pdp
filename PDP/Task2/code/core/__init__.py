"""
PHISHES Digital Platform - Core Module

This package contains the core functionality for the PDP system.
"""

from .utils import build_dataset_path, open_dataset_any, cleanup_existing_dataset
from .folder_structure import create_pdp_folders, PDPFolderStructure
from .downloader import PDPDataDownloader

__all__ = [
    "build_dataset_path",
    "open_dataset_any",
    "cleanup_existing_dataset",
    "create_pdp_folders",
    "PDPFolderStructure",
    "PDPDataDownloader",
]
