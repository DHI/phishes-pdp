---
name: daisy-runoff-identically-zero
description: DAISY Runoff column is all zeros in Monthly_FWater.csv — Phase 1 runoff path injects 0 correctly, not broken
metadata:
  type: project
---

DAISY `Runoff` column in `data/Cernici_060126_Test02_2/Monthly_FWater.csv` is identically zero across the entire 12-year series (2012-09 → 2024-09, 145 rows): sum=0.0, min=0.0, max=0.0, zero nonzero entries. Same in any sim window.

Verified 2026-06-08 via `readDaisyOutput`. Matrix percolation (sum 305 mm) and Matrix drain flow (sum 1246 mm) ARE nonzero — all water leaves via those two paths.

**Why:** Phase 1 runoff coupling (`Runoff` → `OLDR_IN_FLO`) showing zero applied volume in diagnostics, and the earlier "non-discriminating observable" probes, are BOTH explained by zero driving input — not a coupling bug. The pipeline injects 0 because DAISY produced 0.

**How to apply:** Do NOT re-investigate the Phase 1 runoff path as broken. To actually exercise it, need a DAISY scenario producing nonzero `Runoff` (storm / saturation-excess event); none exists in this dataset. See [[phase1-runoff-non-discriminating]].
