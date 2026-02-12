"""
PHISHES Digital Platform - Core Module

This package contains the core functionality for the PDP system.
"""

from .utils import build_dataset_path, open_dataset_any, cleanup_existing_dataset
from .folder_structure import create_pdp_folders, PDPFolderStructure

__all__ = [
    "build_dataset_path",
    "open_dataset_any",
    "cleanup_existing_dataset",
    "create_pdp_folders",
    "PDPFolderStructure",
    "PDPDataDownloader",
]


def __getattr__(name):
    if name == "PDPDataDownloader":
        from .downloader import PDPDataDownloader

        return PDPDataDownloader
    raise AttributeError(f"module 'core' has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
