"""
PHISHES Digital Platform - Folder Structure Setup

This module creates the standardized folder structure for PDP data on the user's machine.
The structure is designed to accommodate datasets from Azure storage and future result viewer integration.

Author: DHI A/S
Date: January 2026
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime


class PDPFolderStructure:
    """
    Creates and manages the PHISHES Digital Platform folder structure.

    The folder structure is organized by data type and designed to accommodate
    both input datasets and future model outputs for the result viewer.
    """

    # Default folder structure definition (minimal - data folders created on download)
    FOLDER_STRUCTURE = {"logs": {}}

    def __init__(self, base_path: Optional[Path] = None, custom_structure: Optional[Dict] = None):
        """
        Initialize the folder structure manager.

        Parameters
        ----------
        base_path : str, optional
            Base path for the project. If None, uses current directory.
        custom_structure : dict, optional
            Custom folder structure. If None, uses default structure.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.structure = custom_structure if custom_structure else self.FOLDER_STRUCTURE

    def _create_directory_recursive(self, structure: Dict, parent_path: Path):
        """
        Recursively create directory structure from nested dictionary.

        Parameters
        ----------
        structure : dict
            Nested dictionary representing folder structure.
        parent_path : Path
            Parent directory path.
        """
        for folder_name, substructure in structure.items():
            folder_path = parent_path / folder_name

            # Create directory
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"Created: {folder_path}")

            # Create README if it's a leaf directory
            if not substructure:
                self._create_readme(folder_path, folder_name)

            # Recursively create subdirectories
            if substructure:
                self._create_directory_recursive(substructure, folder_path)

    def _create_readme(self, folder_path: Path, folder_name: str):
        """
        Create a README.md file in each leaf directory.

        Parameters
        ----------
        folder_path : Path
            Path to the directory.
        folder_name : str
            Name of the directory.
        """
        readme_path = folder_path.joinpath("README.md")
        if not readme_path.exists():
            with open(readme_path, "w") as f:
                f.write(f"# {folder_name.replace('_', ' ').title()}\n\n")
                f.write(f"This folder contains {folder_name.replace('_', ' ')} data.\n\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def create_structure(self):
        """
        Create the complete folder structure.

        Returns
        -------
        Path
            Path to the created base directory.
        """
        print(f"Creating PDP folder structure at: {self.base_path}")

        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create main structure
        self._create_directory_recursive(self.structure, self.base_path)

        # Create project metadata file
        self._create_metadata_file()

        print("Folder structure created successfully!")
        return self.base_path

    def _create_metadata_file(self):
        """Create project metadata JSON file."""
        metadata = {
            "project_name": "PHISHES Digital Platform Project",
            "created": datetime.now().isoformat(),
            "structure_version": "1.0",
            "base_path": str(self.base_path.absolute()),
            "description": "PHISHES soil science data and modeling project",
        }

        metadata_path = self.base_path / ".pdp_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def get_dataset_path(self, category: str, subcategory: str) -> Path:
        """
        Get the path for a specific dataset category.

        Parameters
        ----------
        category : str
            Main category (e.g., 'climate', 'soil', 'topography')
        subcategory : str
            Subcategory (e.g., 'temperature', 'properties', 'dem')

        Returns
        -------
        Path
            Full path to the dataset directory.
        """
        return self.base_path.joinpath("data", category, subcategory)

    def list_structure(self) -> List[str]:
        """
        List all directories in the structure.

        Returns
        -------
        list of str
            List of all directory paths relative to base_path.
        """
        dirs = []
        for root, dirnames, _ in os.walk(self.base_path):
            for dirname in dirnames:
                full_path = Path(root).joinpath(dirname)
                rel_path = full_path.relative_to(self.base_path)
                dirs.append(str(rel_path))
        return sorted(dirs)

    def verify_structure(self) -> Dict[str, bool]:
        """
        Verify that all expected directories exist.

        Returns
        -------
        dict
            Dictionary mapping directory paths to existence status.
        """

        def check_recursive(structure: Dict, parent_path: Path) -> Dict[str, bool]:
            results = {}
            for folder_name, substructure in structure.items():
                folder_path = parent_path / folder_name
                results[str(folder_path.relative_to(self.base_path))] = folder_path.exists()

                if substructure:
                    results.update(check_recursive(substructure, folder_path))

            return results

        return check_recursive(self.structure, self.base_path)


def create_pdp_folders(
    base_path: Optional[Path] = None,
    custom_structure: Optional[Dict] = None,
) -> Path:
    """
    Convenience function to create PDP folder structure.

    Parameters
    ----------
    base_path : str, optional
        Base path for the project. If None, uses current directory.
    custom_structure : dict, optional
        Custom folder structure. If None, uses default structure.

    Returns
    -------
    Path
        Path to the created base directory.

    Examples
    --------
    >>> # Create structure in current directory
    >>> create_pdp_folders()

    >>> # Create structure in specific location
    >>> create_pdp_folders(base_path='C:/Users/username/my_phishes_project')
    """
    manager = PDPFolderStructure(base_path=base_path, custom_structure=custom_structure)
    return manager.create_structure()


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Create PHISHES Digital Platform folder structure")
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Base path for the project (default: current directory)",
    )

    args = parser.parse_args()

    print("Creating PHISHES Digital Platform folder structure...")
    base = create_pdp_folders(base_path=args.path)
    print(f"Folder structure created at: {base.absolute()}")
    print("You can now:")
    print("1. Place your catchment shapefile in inputs/catchment/")
    print("2. Run the download script to fetch datasets from Azure")
    print("3. Start your analysis!")
