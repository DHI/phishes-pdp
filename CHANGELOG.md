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
- `model-trains/` parent folder to hold one self-contained project per model train
- README stubs for the `MSHE-Daisy` and `HYDRUS-PHREEQC-MODFLOW2005-MT3D` trains
- `.python-version` (3.11) per module, matching CI
- Dedicated agent and skill for the PGM initial condition updater (Workflow D)

### Changed

- Moved `plant-growth-module/` to `model-trains/MSHE-Ecolab-PGM/` (path-only; the
  `plant_growth_module` package, distribution name and imports are unchanged)
- Renamed `Task1 Plant_Growth_Module` to `plant-growth-module`
- Renamed `Task2` to `data-download-tool`
- Restructured each module: dedicated `.md` technical docs, updated READMEs, renamed notebooks
- Aligned Python version requirement to `>=3.10,<3.14` across all configs; the upper bound is
  load-bearing, since a fresh resolve on 3.14 fails building `fiona` from source
- Split CI checks into blocking (lint, tests, file size, secret scan, dependency audit) and advisory
  (format, markdown lint, notebook lint), so formatting never blocks fork contributors
- Pinned `ruff==0.16.0` in both modules and in `.pre-commit-config.yaml`
- CI jobs now resolve dependencies via `uv sync` instead of a hand-maintained list
- Refreshed root and module READMEs plus agent files for the `model-trains/MSHE-Ecolab-PGM` naming
- Root README now points at `model-trains/README.md` as the single model-train index rather than
  linking individual trains, so no train is singled out and the train list lives in one place

### Fixed

- Workflow and Dependabot paths updated to match renamed folders
- Removed stray merge conflict marker from .gitignore
- Corrected outdated file references in documentation

## [1.0.0] - 2026-02-09

### Added

- Data Download Tool: Azure-based dataset discovery, catchment clipping, DFS2/NetCDF/Zarr export
- Plant Growth Module: DFS2 map generation for ECO Lab / MIKE SHE
- Jupyter notebook workflows for both modules
