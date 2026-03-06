# Script Download Feature - Requirements & Design

Version: 1.0
Last Updated: 2026-02-25

## Overview

This document defines the requirements and design guidance for a future **script download** feature in the PHISHES Data Download Tool.

## 1. Objective

Enable users to download processing scripts that can be used with downloaded datasets.

## 2. Current State

- Not implemented in code
- Scripts are currently hosted in the repository but are not exposed via the downloader API

## 3. Design

### 3.1 Script Registry

Define an available scripts list in a YAML catalog (similar to `dataset_catalog.yaml`):

```yaml
scripts:
  preprocessing:
    - name: quality_check.py
      description: QA checks on downloaded datasets
      category: [climate, soils]
      path: src/scripts/quality_check.py
    - name: gap_fill.py
      description: Gap filling for missing values
      category: [climate]
      path: src/scripts/gap_fill.py
  analysis:
    - name: compute_basin_avg.py
      description: Basin-averaged time series
      category: [climate]
      path: src/analysis/timeseries.py
  postprocessing:
    - name: export_to_model.py
      description: Export to model input format
      category: [all]
      path: src/scripts/export_to_model.py
```

### 3.2 API Addition to `PDPDataDownloader`

```python
class PDPDataDownloader:
    # ... existing methods ...

    def list_available_scripts(self) -> Dict:
        """List all available scripts by category."""
        return self.script_catalog

    def download_scripts(
        self,
        script_names: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        output_dir: Optional[Union[str, Path]] = None
    ) -> Dict[str, Path]:
        """
        Download processing scripts.

        Parameters
        ----------
        script_names : list of str, optional
            Specific script names to download. If None, download all.
        categories : list of str, optional
            Filter scripts by category (e.g., 'preprocessing', 'analysis').
        output_dir : str or Path, optional
            Output directory. If None, creates scripts/ subfolder in output_base.

        Returns
        -------
        dict
            Mapping of script_name -> local_path
        """
        pass
```

### 3.3 Notebook Integration

```python
# In notebook after downloading datasets
downloader.download_scripts(categories=['preprocessing', 'analysis'])
# Output: scripts/ folder with copies of all preprocessing/analysis scripts
```

### 3.4 Outputs

- Path: `scripts/` or `scripts/<category>/`
- Contents: Python files, README, requirements.txt for scripts

## 4. Implementation Notes

- Copy scripts from repository to `output_dir`
- Preserve folder structure or flatten to `output_dir`
- Include `requirements.txt` or inline dependency info
- Log downloaded scripts in `download_log.json`

## 5. Out of Scope

- Multi-run comparison management
- Baseline/alternative metadata orchestration
- Project-run family folder orchestration
