# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Repository-level GitHub workflows (CI, security scanning, notebook linting, branch protection)
- Branch protection documentation and CODEOWNERS
- Pull request template and issue templates
- Dependabot configuration for pip and GitHub Actions
- SECURITY.md with vulnerability reporting guidance
- CONTRIBUTING.md with development workflow
- LICENSE (MIT)
- CITATION.cff for academic referencing
- CODE_OF_CONDUCT.md

### Changed

- Renamed `Task1 Plant_Growth_Module` to `PlantGrowthModule`
- Renamed `Task2` to `DataDownloadTool`
- Restructured each module: dedicated `.md` technical docs, updated READMEs, renamed notebooks
- Aligned Python version requirement to >=3.10 across all configs

### Fixed

- Workflow and Dependabot paths updated to match renamed folders
- Removed stray merge conflict marker from .gitignore
- Corrected outdated file references in documentation

## [1.0.0] - 2026-02-09

### Added

- Data Download Tool: Azure-based dataset discovery, catchment clipping, DFS2/NetCDF/Zarr export
- Plant Growth Module: DFS2 map generation for ECO Lab / MIKE SHE
- Jupyter notebook workflows for both modules
