# DAISY to MIKE SHE coupling detailed implementation plan

## Objective

> Latest runtime-write investigation status (2026-05-30): the Phase 1 MIKE Zero 2025 probes saved in `docs/investigations/phase1/phase1_runtime_write_investigation_2026-05-29.md` now show the same core rule for both scalar runoff fields and layered `UZ_WC`: mutating fetched `grid[row]` lists edits detached Python copies, but dataset-native setters on the live `Dataset` do work. After switching `OLDR_IN_FLO` writes to block assignment (`dataset[r0:r1, c0:c1] = scalar`), both the external `phase1_runoff_double_count_probe` and plugin-timed `phase1_plugin_timed_oldr_in_flo_probe` immediately diverged from baseline in coupled-cell mean `OLDR_S` (from `+0.0102013483` at comparison step 1 to `+0.2649804227` at step 20) while `OL_D` remained flat; this invalidates the earlier “no runoff response” conclusion reached with detached-row scalar writes. The next recommended implementation step is to keep dataset-native scalar writes in the production runoff path, investigate why `OLDR_IN_FLO` affects `OLDR_S` but not `OL_D`, and then return to rewriting `calc_UZ_WC(...)` with dataset-native tuple-cell layered assignment.

Implement DAISY-driven water-movement coupling in a way that is:

1. physically consistent at the MIKE SHE cell scale,
2. traceable cell by cell and time step by time step,
3. mass conservative within defined tolerances, and
4. testable independently for runoff, matrix percolation, matrix drain flow, and effective unsaturated-zone bookkeeping.

The implementation should reuse the current proof-of-concept where it is useful, but it should separate parsing, mapping, conversion, state updates, and diagnostics so each part can be validated on its own.

## What exists today in this repository

### Code baseline

- `src/DaisyFunctions.py`
  - Reads a DAISY output file into a `pandas` DataFrame.
  - Builds a `datetime` index.
  - Currently exposes `findValueInDaisyResult`, which linearly interpolates a selected column at an arbitrary timestamp.
- `src/blocks.py`
  - Holds hard-coded coupled-cell blocks.
  - Represents only a spatial footprint, not a full mapping model with class identifiers, drain subsets, or per-class metadata.
- `src/Test_Cernici.py`
  - Handles MIKE Zero discovery, plugin setup, pre-processing, MIKE SHE initialization, and the main time-step loop.
  - Already loads MIKE SHE datasets such as `OLDR_IN_FLO`, `SZ_LEAK_FLO`, `SZ_LEAK_FLX`, `SZDR_IN_FLO`, and `UZ_WC`.
  - Contains a proof-of-concept for matrix percolation and `UZ_WC` bookkeeping.

### Important repository findings

- `Monthly_FWater.csv` is an interval-based DAISY water-balance log with monthly rows and values in `mm`.
- The current code converts matrix percolation using a hard-coded `30 * 24 * 60 * 60` interval.
- The current code interpolates interval totals in time, which is not appropriate for variables such as runoff, percolation, and drain flow that represent totals over a reporting interval rather than continuous state variables.
- The current `UZ_WC` proof-of-concept subtracts the same `delta` from every layer entry in a cell. That is risky because it can over-apply the intended water-volume correction if `UZ_WC` is layer-resolved.

## Key design decisions to lock before coding

These decisions should be confirmed before implementing the variable-specific tasks.

1. **DAISY interval semantics**
	- Confirm whether each timestamp in `Monthly_FWater.csv` represents the end of the previous reporting interval or the beginning of the next one.
	- Treat runoff, matrix percolation, and matrix drain flow as interval totals, not values to interpolate linearly.

2. **Authoritative MIKE SHE leakage variable**
	- Decide whether the percolation correction should target `SZ_LEAK_FLO` or `SZ_LEAK_FLX`.
	- Confirm the sign convention and units of the comparison term currently read from MIKE SHE, for example `UZ_SZ_EX_POSUP` versus an SZ leakage term.

3. **Spatial mapping model**
	- Decide whether `src/blocks.py` remains a temporary footprint file or is replaced by a richer mapping structure that can identify:
	  - all coupled agricultural cells,
	  - drained coupled cells,
	  - DAISY class or simulation identifier per cell group,
	  - optional lower-boundary case metadata.

4. **UZ bookkeeping representation**
	- Decide how an effective `UZ_WC` correction is represented when MIKE SHE exposes a layered `UZ_WC` structure.
	- Do not blindly apply the same correction to every layer unless that behavior is explicitly justified by the chosen effective-thickness definition.

5. **Storage owner for drain-flow bookkeeping**
	- Decide whether drain extraction will be balanced against `OL_D` or a separate bookkeeping store.
	- The choice must be documented once and then used consistently.

## Recommended file structure for the implementation

The current code can support the work, but the implementation will be easier to test and extend if responsibilities are split more cleanly.

- `src/DaisyFunctions.py`
  - Keep DAISY file parsing here.
  - Extend it with helpers that treat log columns as interval totals.
- `src/blocks.py` or a replacement such as `src/spatial_mapping.py`
  - Store coupled-cell masks, drain masks, and DAISY class metadata.
- `src/coupling.py` (recommended new module)
  - Hold pure functions for unit conversion, per-cell update logic, clipping, and residual handling.
- `src/diagnostics.py` (recommended new module)
  - Hold row builders, aggregation helpers, and output writers for diagnostics.
- `src/Test_Cernici.py`
  - Keep as the orchestration layer for initializing MIKE SHE, stepping the model, calling the coupling functions, and flushing diagnostics.
- `tests/test_daisy_functions.py` (recommended)
  - Validate DAISY parsing and interval handling.
- `tests/test_coupling.py` (recommended)
  - Validate runoff, percolation, drain flow, clipping, and bookkeeping updates using synthetic arrays.

## Phase 0 - Foundation and refactoring

### Goal

Create a shared coupling foundation so each variable can be implemented as a small, testable unit rather than as ad hoc logic inside the MIKE SHE time loop.

### Implementation tasks

1. **Refactor DAISY access away from interpolation of interval totals**
	- Replace `findValueInDaisyResult` for water-balance columns with an interval-aware accessor.
	- For each DAISY record, derive:
	  - `interval_end_time`,
	  - `interval_start_time`,
	  - `interval_seconds`,
	  - source depth in `mm`.
	- Convert interval totals to rates using:
	  - `depth_m = depth_mm / 1000`
	  - `rate_m_per_s = depth_m / interval_seconds`
	- For a MIKE SHE time step, derive the applied amount as:
	  - `step_depth_m = rate_m_per_s * mshe_dt_seconds`
	  - `step_volume_m3 = step_depth_m * cell_area_m2`

2. **Create a single source of truth for spatial scope**
	- Replace the anonymous block list with a mapping structure that can answer:
	  - Is the cell coupled?
	  - Is the cell drained?
	  - Which DAISY class or source series applies?
	- If the current repository only has one DAISY series for all coupled cells, keep that as an initial mode, but make the data structure ready for multiple DAISY classes.

3. **Centralize unit conversion helpers**
	- Add pure functions for:
	  - interval depth to rate,
	  - rate to MIKE SHE flow,
	  - net water depth to `UZ_WC` change,
	  - clipping to physical bounds,
	  - residual calculation.

4. **Centralize diagnostics schema**
	- Define a per-cell, per-time-step diagnostics record with at least:
	  - timestamp,
	  - DAISY simulation or class identifier,
	  - row and column,
	  - variable name,
	  - source depth,
	  - interval seconds,
	  - applied MIKE SHE target value,
	  - storage correction,
	  - residual due to clipping,
	  - selected sign convention metadata.

5. **Prepare MIKE SHE runtime context**
	- In `src/Test_Cernici.py`, gather runtime constants once at startup:
	  - MIKE SHE time-step length,
	  - cell area,
	  - effective UZ thickness,
	  - `theta_residual`,
	  - `theta_saturated` or porosity,
	  - relevant datasets to read/write each step.
	- Remove hard-coded conversion assumptions such as the current fixed 30-day interval.

### Exit criteria

- DAISY interval totals can be queried without time interpolation.
- Coupled-cell scope is available through a structured mapping interface.
- Shared conversion and clipping helpers exist and are covered by unit tests.

### Phase 0 sign-off summary (2026-05-30)

- New artifact:
	- `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`
- Recommended decision:
	- sign off Phase 0 for the **runtime-foundation and API-discovery milestone**;
	- do **not** yet treat this as a stricter final leakage-target authority sign-off.
- Basis recorded in the summary:
	- the runtime probe established a stable isolated setup, cell geometry, runtime parameter IDs, and key read/write behavior;
	- `OL_D` was confirmed readable but not writable, `UZ_WC` writable and layered, `UZ_SZ_EX_POSUP` readable, and both `SZ_LEAK_FLO` / `SZ_LEAK_FLX` writable;
	- the MIKE Zero 2025 leakage-target follow-up supported using `SZ_LEAK_FLX` as the most coherent **provisional** engineering target for later implementation work.
- What remains outside stricter final sign-off:
	- authoritative confirmation of whether `SZ_LEAK_FLO` or `SZ_LEAK_FLX` is the final intended leakage target;
	- final sign-convention lock against `UZ_SZ_EX_POSUP`.
- Follow-up after implementation work:
	- close the authoritative target question through DHI documentation or a runtime setup with measurable output response;
	- then record the final sign convention explicitly.

## Phase 1 - Runoff coupling

### Goal

Route DAISY runoff into MIKE SHE overland drainage inflow in coupled agricultural cells only, with explicit storage correction and no double counting.

### Implementation tasks

1. **Confirm DAISY runoff source column**
	- Read the `Runoff` column from `Monthly_FWater.csv`.
	- Validate the column exists and fail with a clear error if it is missing.

2. **Identify the MIKE SHE runoff target and bookkeeping store**
	- Use `OLDR_IN_FLO` as the target inflow variable.
	- Read `OL_D` as the overland-depth bookkeeping store if available through the API.
	- If `OL_D` is not writable through the API, document the fallback bookkeeping approach before proceeding.

3. **Prevent double counting**
	- Disable or zero the internal MIKE SHE runoff generation for coupled cells.
	- This may require one of two approaches:
	  - pre-configure the setup file so coupled cells do not generate native runoff, or
	  - explicitly zero native runoff terms each step before applying DAISY-driven values.
	- The chosen method must be verified with a short diagnostic run.

4. **Convert interval depth to MIKE SHE flow**
	- For each coupled cell or cell block:
	  - get DAISY runoff depth for the active DAISY interval,
	  - convert to `rate_m_per_s`,
	  - convert to `flow_m3_per_s = rate_m_per_s * cell_area_m2`,
	  - write to `OLDR_IN_FLO`.

5. **Apply storage correction**
	- Convert the same applied runoff amount to a step-depth sink:
	  - `step_depth_m = rate_m_per_s * mshe_dt_seconds`
	- Subtract that amount from `OL_D`.
	- Clip so the resulting depth cannot go below zero.
	- Record any clipped remainder as a residual.

6. **Add diagnostics**
	- Store, per cell and step:
	  - DAISY runoff depth for the source interval,
	  - applied MIKE SHE flow,
	  - `OL_D` before and after,
	  - clipped residual.

### Runoff acceptance criteria

- Coupled cells receive runoff from DAISY only.
- Uncoupled cells are unchanged.
- The runoff flow and overland storage correction represent the same water amount within tolerance.

### Phase 1 closure checklist (status on 2026-06-02)

Done:

- [x] Read and validate the `Runoff` column before applying Phase 1 updates.
- [x] Use `OLDR_IN_FLO` as the production target runoff variable.
- [x] Document the bookkeeping fallback when `OL_D` is not writable in the current setup (`virtual_ol_d_snapshot` in `src/Test_Cernici.py`).
- [x] Convert DAISY interval totals using actual interval seconds and runtime cell area before computing per-cell `OLDR_IN_FLO`.
- [x] Use dataset-native scalar writes for coupled cells only; MIKE Zero 2025 probes now show a solver-visible response through `OLDR_S`.
- [x] Record per-cell runoff diagnostics including source interval depth, interval seconds, applied target flow, bookkeeping before/after, and clipped residual.
- [x] Add dedicated runoff tests covering coupled-only assignment, uncoupled-cell invariance, and source/storage consistency in `tests/test_coupling.py`.
- [x] Accept `virtual_ol_d_snapshot` as the authoritative Phase 1 bookkeeping store for the lighter engineering-routing milestone boundary.
- [x] Lock `OLDR_S` as the accepted Phase 1 response observable for that lighter boundary; the June 2026 alternate-observable follow-up did not identify a better or delayed discriminator.
- [x] Record the lighter-boundary Phase 1 closeout evidence in the published closeout/sign-off notes (`phase1_runoff_closeout_diagnostic_2026-05-30.md`, `phase1_signoff_summary_2026-05-30.md`, and `phase1_runoff_finalization_task_2026-06-01.md`).

Deferred / not yet closed:

- [ ] Prove that native MIKE SHE runoff is disabled or zeroed for coupled cells, so double counting is ruled out in the live setup.
- [ ] Replace the external `virtual_ol_d_snapshot` fallback with a live writable overland-storage correction path if the project later requires stricter in-model Phase 1 closure.
- [ ] Reopen the Phase 1 acceptance observable only if the project later requires a stricter in-model observable that lives directly in corrected `OL_D` rather than `OLDR_S`.

Current deferral note:

- The Phase 1 probes did not identify a runtime-zeroable native runoff control, and forcing `DrRunoffCoefficient = 0.0` did not change the short-run overland metrics that were checked.
- The later mapped-cell preprocessed-coefficient suppression reruns and targeted alternate-observable reruns also did not change that interpretation: `OLDR_S` remained the only responding observable, `OL_D` remained flat, and no suppression-sensitive alternate discriminator emerged.
- Supplemental documentation note: `docs/exchangeble_items.md` lists `OL_D` in both the exchangeable-input overview and the output-items list, while `OLDR_IN_FLO` appears as an exchangeable input and `OLDR_S` as an output item; in this repository, runtime probe behavior still shows `OL_D` acting as effectively output-only / non-writable in the current setup.

### Stricter Phase 1 runoff closeout checklist (status on 2026-05-30)

Use this stricter list if Phase 1 sign-off must satisfy an in-model runoff-closeout standard rather than the lighter engineering-routing milestone described above.

1. **Partial** — Spatial mapping correctly identifies the coupled agricultural cells.
	- `src/spatial_mapping.py` now wraps the legacy block footprint in a structured mapping interface and all current runoff writes are scoped through `DEFAULT_SPATIAL_MAPPING`.
	- The agricultural-cell footprint itself has not yet been re-validated against source GIS or land-use inputs in this phase.

2. **Open** — OL-Drainage runoff coefficients are set to zero in coupled cells.
	- A derived-setup `DrRunoffCoefficient = 0.0` probe and a mapped-cell preprocessed coefficient-zeroing probe were both run through the longer 20-step horizon, but they still did not prove effective suppression in the checked Phase 1 outputs.

3. **Open** — MIKE SHE internal runoff generation is disabled in coupled cells.
	- This remains unresolved until native runoff suppression is demonstrated either by setup configuration or by a runtime control that measurably removes the native contribution.

4. **Done** — DAISY runoff is read from `Monthly_FWater.csv`.
	- `src/Test_Cernici.py` resolves `Monthly_FWater.csv` by default and explicitly validates that the `Runoff` column exists before applying Phase 1 runoff updates.

5. **Done** — DAISY runoff depth is converted to flow using `Q_runoff = D_runoff × A / Δt`.
	- The current runoff path uses the interval-aware helper `interval_depth_to_cell_transfer(...)` to derive rate, per-cell flow, step depth, and step volume from DAISY depth, interval seconds, MIKE SHE time-step length, and runtime cell area.

6. **Done** — Converted DAISY runoff is assigned to `OLDR_IN_FLO`.
	- The production path uses dataset-native scalar assignment through `assign_uniform_scalar_to_groups(...)` and then commits the updated dataset with `ms.wm.setValues(OLDR_IN_FLO)`.

7. **Done** — The equivalent runoff depth is calculated using `Δh_OL = Q_runoff × Δt / A`.
	- The same transfer helper carries this amount as `step_depth_m`, which is then used for the storage-side bookkeeping sink.

8. **Partial** — `OL_D` is updated using `OL_D_new = max(0, OL_D_existing - Δh_OL)`.
	- The current code applies this bounded sink to the external `virtual_ol_d_snapshot` bookkeeping store because live `OL_D` is readable but not writable in the current setup.

9. **Partial** — `OL_D` is never allowed to become negative.
	- Nonnegative clipping is enforced for `virtual_ol_d_snapshot` through `apply_nonnegative_sink(...)`, but the same guarantee is not yet proven for live `OL_D` because live `OL_D` is not currently updated.

10. **Open** — No double counting occurs between DAISY runoff and MIKE SHE runoff generation.
	- This is not yet proven in the live setup because native MIKE SHE runoff suppression has not been demonstrated for the coupled cells.

11. **Partial** — Runoff is included in the post-run water-balance diagnostic.
	- Per-cell runoff diagnostics, bookkeeping deltas, and residual fields are already written and can be summarized; the lighter-boundary closeout diagnostic has been recorded, but the stricter final in-model runoff closeout diagnostic has not been completed.

12. **Open** — Water-balance residuals are checked against the agreed tolerance.
	- Residual fields exist in the diagnostics schema, and the lighter-boundary closeout note records floating-tolerance closure under the accepted external bookkeeping policy, but no stricter in-model tolerance closeout report is recorded yet for Phase 1 runoff.

13. **Open** — UZ and total MIKE SHE water-balance errors are reviewed after coupling.
	- This review step has not yet been formalized or recorded as part of the Phase 1 runoff closeout evidence.

### Latest Phase 1 closeout diagnostic attempt (2026-05-30)

- Candidate closeout artifacts are now saved in:
	- `docs/investigations/phase1/phase1_runoff_closeout_probe_20step.json`
	- `docs/investigations/phase1/phase1_runoff_closeout_diagnostic_nonzero.csv`
	- `docs/investigations/phase1/phase1_runoff_closeout_diagnostic_2026-05-30.md`
- The 20-step comparison probe confirms the current accepted-observable behavior:
	- coupled-cell mean `OLDR_S` diverged from baseline immediately at comparison step `1` and reached `+0.2649804227204137` by step `20`;
	- coupled-cell mean `OL_D` stayed flat;
	- no runtime-zeroable native runoff control was identified in the current setup;
	- forcing `DrRunoffCoefficient = 0.0` still did not alter the checked short-run outputs.
- The one-step production bookkeeping diagnostic using `docs/Monthly_FWater_phase1_smoke.csv` confirms the current accounting identity under `virtual_ol_d_snapshot`:
	- source depth was `62.0 mm`, mapped to `5.925925925925926e-06 m^3/s` per coupled cell;
	- requested runoff volume closed to floating tolerance once explicit clipped residual was included;
	- all `1355` coupled cells clipped against the first-step read-only `OL_D` snapshot, so nearly the full requested sink appeared as residual rather than retained virtual storage.
- Practical implication:
	- these artifacts are strong support for the lighter `virtual_ol_d_snapshot` + `OLDR_S` Phase 1 closure path if that policy is formally accepted;
	- they do not by themselves satisfy the stricter in-model runoff closeout gate, because native runoff suppression, live writable `OL_D` correction, and strict no-double-count proof remain open.

### June 2026 confirmatory follow-up

- Additional confirmatory artifacts now exist in:
	- `docs/investigations/phase1/phase1_runoff_double_count_probe_preprocessed_followup_20step_2026-06-01.json`
	- `docs/investigations/phase1/phase1_runoff_alternate_observables_probe_smoke_2026-06-02.json`
	- `docs/investigations/phase1/phase1_runoff_alternate_observables_probe_20step_2026-06-02.json`
- These later reruns did not change the closure boundary:
	- `OLDR_S` remained the only reproducibly responding observable;
	- `OL_D` remained flat;
	- targeted alternate observables (`INF`, `OL_FLOW_X`, `OL_FLOW_Y`, `OL_SZ_EX`, `SZ_OL_EX`, `RECHARGE_POSDN`) did not reveal a delayed suppression-sensitive signal;
	- neither setup-level `DrRunoffCoefficient = 0` nor mapped-cell preprocessed coefficient zeroing produced a measurable setup-effect signal in the checked Phase 1 outputs.
- Practical consequence:
	- the lighter Phase 1 engineering-routing closure is now better confirmed, not weakened;
	- the stricter in-model runoff closeout still remains a deferred requirement rather than a satisfied one.

### Remaining Phase 1 work only if stricter closure is required

The lighter Phase 1 closure policy is now the documented accepted default:

- `virtual_ol_d_snapshot` is the accepted bookkeeping store for the lighter engineering-routing boundary;
- `OLDR_S` is the accepted response observable for that same boundary;
- native MIKE SHE runoff suppression remains a documented deferred limitation outside the accepted lighter boundary.

So no further work is required to keep Phase 1 closed at the lighter milestone level.

Only reopen Phase 1 if the project later decides that a stricter in-model runoff closeout is mandatory. In that case, the recommended order is:

1. **Reopen native-runoff suppression investigation**
	- Continue only if there is a new setup-level lever, runtime control, or external documentation hypothesis to test.
	- Repeating the current `DrRunoffCoefficient = 0`, preprocessed-zeroed, or targeted alternate-observable reruns without a new hypothesis is not recommended.

2. **Reopen live `OL_D` correction investigation**
	- A stricter sign-off still requires either a writable in-model overland storage path or an explicit project decision to accept the external bookkeeping model permanently.

3. **Regenerate the stricter closeout diagnostic only after a new lever exists**
	- The next strict diagnostic should be rerun only after there is a materially new suppression or in-model storage path to evaluate.

4. **Otherwise leave Phase 1 closed at the accepted lighter boundary and continue with later-phase work**
	- The current evidence package already supports that lighter closure cleanly.

### Phase 1 sign-off summary (2026-05-30)

- New artifact:
	- `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md`
- Recommended decision:
	- sign off Phase 1 for the **lighter runoff engineering-routing milestone**;
	- do **not** yet treat this as a stricter final in-model runoff closeout sign-off.
- Basis recorded in the summary:
	- dataset-native scalar writes to `OLDR_IN_FLO` are solver-visible under MIKE Zero 2025;
	- the production runoff path uses interval-aware conversions, mapped coupled-cell scoping, and dedicated runoff tests;
	- `OLDR_S` is the reproducible response observable;
	- the documented `virtual_ol_d_snapshot` bookkeeping identity closes numerically to floating tolerance when explicit residual is included.
- What remains outside stricter final sign-off:
	- proof of native MIKE SHE runoff suppression in coupled cells;
	- a live writable `OL_D` correction path or an explicit permanent acceptance of the external bookkeeping fallback;
	- a stricter no-double-count argument in the live setup.
- Follow-up after implementation work:
	- keep the `virtual_ol_d_snapshot` + `OLDR_S` closure policy as the accepted lighter Phase 1 boundary;
	- reopen Phase 1 only if stricter native-runoff suppression proof and live writable overland-state correction are later required.

## Phase 2 - Matrix percolation coupling

### Goal

Use DAISY matrix percolation to control the net UZ-to-SZ exchange in coupled agricultural cells while keeping the unsaturated-zone bookkeeping mass conservative.

Supplemental documentation note (2026-05-30):

- `docs/exchangeble_items.md` lists both `SZ_LEAK_FLX` and `SZ_LEAK_FLO` in the exchangeable-input overview, while `UZ_SZ_EX_POSUP` appears in the output-items list.
- Together with the Phase 0 runtime probe, this strengthens the current working interpretation that `UZ_SZ_EX_POSUP` is the native comparison/output term and that `SZ_LEAK_FLX` / `SZ_LEAK_FLO` are writable correction candidates.
- Because the current DAISY percolation path is naturally expressed as a flux-like rate and `UZ_SZ_EX_POSUP` is reported in `m/s`, this documentation clue is consistent with keeping `SZ_LEAK_FLX` as the provisional engineering target.
- It does **not** eliminate the need for a dedicated authoritative-target check; `SZ_LEAK_FLX` remains provisional rather than vendor-confirmed.

Current provisional engineering stance (2026-05-30):

- compare DAISY matrix percolation against `UZ_SZ_EX_POSUP` as the native MIKE SHE comparison/output term;
- implement the writable correction path against `SZ_LEAK_FLX` by default unless stronger evidence later contradicts it;
- treat `SZ_LEAK_FLO` as the cell-area-scaled flow representation of the same physical concept when a flow-form diagnostic or interface is explicitly needed;
- keep the authoritative-target confirmation task open, so this remains an implementation stance rather than a vendor-verified final fact.

### Latest Phase 2 implementation smoke (2026-05-30)

- New implementation status:
	- `src/coupling.py` now contains the mapping-aware helper `apply_groupwise_net_leakage_flux(...)`.
	- `src/Test_Cernici.py` now routes matrix percolation through `apply_matrix_percolation_coupling(...)` and writes per-cell Phase 2 diagnostics.
- New artifacts:
	- `docs/investigations/phase2/phase2_matrix_percolation_smoke.csv`
	- `docs/investigations/phase2/phase2_matrix_percolation_smoke_2026-05-30.md`
- One-step runtime smoke used:
	- `--max-steps 1`
	- runoff coupling disabled to isolate Phase 2
	- `docs/Monthly_FWater_phase1_smoke.csv` as the DAISY input
- Recorded first-step results:
	- DAISY matrix percolation source depth `2.99483 mm` over `2678400.0 s` (`1.1181414277180407e-09 m/s`);
	- `1355` coupled-cell `matrix_percolation` diagnostic rows were written;
	- mean net correction written toward `SZ_LEAK_FLX`: `3.524602980485193e-09 m/s`;
	- mean effective bookkeeping term `delta_theta`: `8.45904715316446e-08`.
- Current implication:
	- the Phase 2 routing path and per-cell diagnostics are now integrated into the real MIKE SHE loop;
	- the diagnostics also show that `uz_wc_expected_after_layer_mean` shifts slightly while `uz_wc_candidate_after_layer_mean` stayed equal to `uz_wc_before_layer_mean` in the sampled rows, so the `UZ_WC` write-back / bookkeeping representation remains the next unresolved implementation item.

### Phase 2 `UZ_WC` setter follow-up (2026-05-30)

- Production `calc_UZ_WC(...)` has now been switched from detached row-copy mutation to dataset-native tuple-cell layered assignment.
- New artifacts:
	- `docs/investigations/phase2/phase2_matrix_percolation_smoke_after_uz_wc_setter.csv`
	- `docs/investigations/phase2/phase2_matrix_percolation_smoke_after_uz_wc_setter_2026-05-30.md`
- Validation status after the change:
	- full unit suite passed (`20` tests);
	- the one-step Phase 2 smoke again completed successfully under MIKE Zero 2025.
- Recorded diagnostics result:
	- all `1355` coupled-cell rows now showed `uz_wc_candidate_after_layer_mean != uz_wc_before_layer_mean`;
	- all `1355` rows also matched `uz_wc_expected_after_layer_mean` within numerical tolerance;
	- the diagnostics metadata now reports `bookkeeping_representation = dataset_native_tuple_cell_layers_assign_uniform_delta`.
- Current implication:
	- the earlier Phase 2 “candidate `UZ_WC` did not move” result was a detached-row write artifact rather than evidence against the effective `delta_theta` bookkeeping formula itself;
	- the production Phase 2 path now uses the same class of dataset-native `UZ_WC` setter already validated in the dedicated runtime-write investigation;
	- the next unresolved work is no longer basic candidate writeability, but bounded/residual-aware `UZ_WC` bookkeeping and any stricter persisted-response production proof the project may still want.

### Phase 2 bounded `UZ_WC` bookkeeping follow-up (2026-05-30)

- Production `calc_UZ_WC(...)` now uses bounded/residual-aware layered bookkeeping through shared helpers in `src/coupling.py`.
- New artifacts:
	- `docs/investigations/phase2/phase2_matrix_percolation_smoke_bounded_uz_wc.csv`
	- `docs/investigations/phase2/phase2_matrix_percolation_smoke_bounded_uz_wc_2026-05-30.md`
- Validation status after the bounded bookkeeping update:
	- full unit suite passed (`23` tests);
	- the one-step Phase 2 smoke again completed successfully under MIKE Zero 2025.
- Recorded diagnostics result:
	- `1355` `matrix_percolation` rows were written;
	- `280` rows applied at least one `UZ_WC` bound clip;
	- total clipped layer count was `6594`;
	- the same `280` rows recorded nonzero residual.
- Important implementation note:
	- the first conservative-bounds attempt incorrectly snapped many cells toward the upper bound because some live `UZ_WC` states already sit above the derived conservative bound;
	- the final implementation therefore uses a directional rule: do not forcibly snap an existing out-of-bounds state back to the conservative bound in one step, but do prevent the requested update from moving that state even further out of bounds.
- Current implication:
	- unclipped cells still match the requested effective `delta_theta` update to floating tolerance;
	- clipped cells now expose their blocked amount explicitly through the residual field;
	- the remaining open questions have shifted from low-level `UZ_WC` write mechanics to higher-level implementation choices such as stricter persisted-response proof and the long-term adequacy of the current equal-shift-per-layer effective representation.

### Phase 2 bounded persisted-response production comparison (2026-05-30)

- New probe entrypoint:
	- `src/investigations/phase2_bounded_persisted_response_probe.py`
- New artifacts:
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe.json`
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_injected_diagnostics.csv`
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_2026-05-30.md`
- Probe design:
	- runs a fresh **baseline** production-style case and a fresh **bounded_phase2** production-style case;
	- uses the repository default Cernici setup, MIKE Zero 2025, and `docs/Monthly_FWater_phase1_smoke.csv`;
	- compares `20` WM steps after the initial warm-up step (`2.3111111111111113 h` total compared duration).
- Recorded result:
	- candidate bounded `UZ_WC` writes were visible before `setValues` on the injected steps;
	- same-time `UZ_WC` readback still stayed flat;
	- later readable `UZ_WC` states diverged from baseline, with:
	  - all-layer first difference at comparison step `2` / WM step `3`;
	  - top-layer first difference at comparison step `8` / WM step `9`;
	  - final all-layer mean diff `-7.908795840450011e-10`;
	  - final top-layer mean diff `-1.9135070750131433e-09`.
	- readable `UZ_SZ_EX_POSUP` did **not** diverge above the probe tolerance (`1e-12`) over the same 20-step horizon; max absolute difference was `2.7872312199636183e-13`.
	- injected diagnostics covered `27100` `matrix_percolation` rows across the 20 compared steps, with `4590` rows applying bounds / residuals and max absolute residual `1.7602737757164715e-06`.
- Important runtime note:
	- `SZ_LEAK_FLX` behaved as an input-only field in this probe path, so the strict persisted comparison now treats readable `UZ_WC` and `UZ_SZ_EX_POSUP` as the relevant persisted observables while still summarizing candidate target writes for `SZ_LEAK_FLX`.
- Current implication:
	- the bounded Phase 2 production path now has a stronger persisted-response proof for readable storage (`UZ_WC`) than the earlier one-step smokes provided;
	- the current validation gap has narrowed to flux-side / longer-horizon proof rather than basic bounded-write persistence.

### Phase 2 longer-horizon + alternate-observable persisted-response follow-up (2026-05-30)

- Probe updates:
	- `src/investigations/phase2_bounded_persisted_response_probe.py` now also tracks readable optional observables `OL_SZ_EX` and `SZ_HEAD` when available;
	- the same probe now emits stderr progress heartbeats during longer runs so multi-step comparisons stay terminal-visible.
- New artifacts:
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_40step.json`
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_40step_injected_diagnostics.csv`
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_40step_2026-05-30.md`
- Probe design:
	- same fresh baseline vs bounded-injected production comparison as the earlier strict probe;
	- extended to `40` compared WM steps after the warm-up step (`8.68888888888889 h`, ending at `2020-08-01T08:45:00`).
- Recorded result:
	- candidate bounded `UZ_WC` writes still moved before `setValues`, while immediate same-time `UZ_WC` readback still stayed flat;
	- readable `UZ_WC` divergence strengthened further, reaching final differences:
	  - all-layer mean `-2.493057743579996e-08`;
	  - top-layer mean `-6.382755690648168e-08`.
	- readable `UZ_SZ_EX_POSUP` now **did** diverge above the `1e-12` probe tolerance on the longer horizon:
	  - first difference at comparison step `31` / WM step `32`;
	  - max absolute difference `5.663911723803456e-12`.
	- alternate observable `SZ_HEAD` also diverged from baseline:
	  - all-layer and top-layer first difference both at comparison step `1` / WM step `2`;
	  - final all-layer mean diff `-2.983685590152163e-06`;
	  - final top-layer mean diff `-4.4690551703752135e-06`.
	- alternate observable `OL_SZ_EX` remained identically flat (`0.0` difference throughout the 40-step window).
	- injected diagnostics covered `54200` rows across the 40 compared steps, with `7007` rows applying bounds / residuals and max absolute residual `1.7602737757164715e-06`.
- Current implication:
	- the bounded Phase 2 production path now has longer-horizon persisted-response evidence in readable storage (`UZ_WC`), delayed readable flux-side output (`UZ_SZ_EX_POSUP`), and alternate groundwater-state output (`SZ_HEAD`);
	- `OL_SZ_EX` is not currently a useful alternate discriminator in this setup;
	- the remaining uncertainty is now more about target authority / engineering representation than about whether the bounded production path persists into later readable model behavior.

### Phase 2 120-step persisted-response follow-up (2026-05-30)

- New artifacts:
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_120step.json`
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_120step_injected_diagnostics.csv`
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_120step_2026-05-30.md`
- Probe design:
	- same bounded production comparison harness as the 20-step and 40-step follow-ups;
	- extended to `120` compared WM steps after the warm-up step (`76.93333333333332 h`, ending at `2020-08-04T05:00:00`).
- Recorded result:
	- candidate bounded `UZ_WC` writes still moved before `setValues`, while immediate same-time `UZ_WC` readback still stayed flat;
	- readable `UZ_WC` divergence remained present and became much larger late in the run:
	  - all-layer first difference still at step `2`, top-layer first difference still at step `8`;
	  - all-layer max absolute difference `0.0023853081884492866` at comparison step `103` / WM step `104`;
	  - top-layer max absolute difference `0.02587496748269702` at the same step;
	  - final all-layer and top-layer differences remained nonzero (`-7.342099960117032e-06` / `-0.0007464062903639879`).
	- readable `UZ_SZ_EX_POSUP` still first diverged at comparison step `31` / WM step `32`, and its longer-horizon max absolute difference grew to `3.122995874984447e-08` at comparison step `103` / WM step `104`.
	- alternate observable `SZ_HEAD` continued to diverge and kept growing through the end of the run:
	  - all-layer max absolute / final difference `0.005820976749760121` at step `120`;
	  - top-layer max absolute / final difference `0.008269983614695775` at step `120`.
	- alternate observable `OL_SZ_EX` still remained identically flat (`0.0` difference throughout the 120-step window).
	- injected diagnostics covered `162600` rows across the 120 compared steps, with `14636` rows applying bounds / residuals and max absolute residual `4.589978395594646e-05`.
- Important interpretation note:
	- the 120-step response is no longer just a tiny accumulated numerical offset; it enters a late nonlinear regime with much larger `UZ_WC` / `UZ_SZ_EX_POSUP` excursions before partially relaxing, while `SZ_HEAD` keeps separating through the final step.
	- deeper inspection of the peak window shows that comparison step `103` (`2020-08-03 07:00:00`) is an `8 min` bridge step inserted after a `52 min` step and immediately before a block of `60 min` hourly steps, so the late crest aligns with a WM cadence transition rather than a steady fixed-step continuation.
	- the same peak window did **not** coincide with the global maxima in bounds/residual activity: the run-wide max requested `delta_theta` (`4.851902652083534e-05`), max residual (`4.589978395594646e-05`), and max bounded-row count (`342`) all occurred earlier around steps `75`-`80`; step `103` / `104` still had active bookkeeping (`78` then `60` bounded rows, with a local max requested `delta_theta` of `3.5412526656755816e-05` at step `104`), but the evidence now points more toward a propagated nonlinear state response than to a one-step clipping artifact.
- Current implication:
	- the bounded Phase 2 production path now has robust persisted-response evidence in readable storage (`UZ_WC`), delayed readable flux-side output (`UZ_SZ_EX_POSUP`), and alternate groundwater-state output (`SZ_HEAD`) over a multi-day WM horizon;
	- `OL_SZ_EX` can likely be deprioritized as a Phase 2 discriminator in this setup;
	- the remaining sign-off question has shifted toward interpreting the longer-horizon nonlinear regime rather than proving basic persistence.

### Phase 2 late-regime window follow-up (2026-05-30)

- New artifacts:
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_120step_peak_window_95_110.csv`
	- `docs/investigations/phase2/phase2_bounded_persisted_response_probe_120step_late_regime_2026-05-30.md`
- Focus:
	- derived a compact stepwise view for comparison steps `95`-`110` by aligning the JSON difference series with the timestamp-keyed injected diagnostics CSV.
- Recorded result:
	- the crest at comparison step `103` maps to `2020-08-03 07:00:00` and occurs after an `8 min` bridge step inserted between a preceding `52 min` step and a new block of `60 min` hourly steps (`104`-`107`);
	- step `103` still had active bookkeeping (`78` bounded rows, `1872` clipped layers), but its max absolute residual was only `1.3003724320418979e-06`;
	- step `104` showed the largest local requested correction magnitude within the `95`-`110` window (`3.5412526656755816e-05` max absolute requested `delta_theta`, `0.001682493593344247` summed absolute requested `delta_theta`) while bounded-row count actually dropped to `60`.
	- the strongest run-wide bookkeeping extremes all occurred earlier around steps `75`-`80`:
	  - max abs requested `delta_theta`: `4.851902652083534e-05` at step `75`;
	  - max summed abs requested `delta_theta`: `0.002249441338878104` at step `78`;
	  - max abs residual `delta_theta`: `4.589978395594646e-05` at step `79`;
	  - max bounded-row count and clipped-layer count: `342` / `8208` at step `80`.
- Current implication:
	- the late `UZ_WC` / `UZ_SZ_EX_POSUP` crest is better interpreted as a propagated nonlinear state response exposed at a WM cadence transition than as a trivial one-step clipping artifact;
	- clipping and bounded bookkeeping remain part of the dynamics, but the late peak no longer looks like the direct signature of the run's strongest same-step residual event.

### Phase 2 sign-off memo (2026-05-30)

- New artifact:
	- `docs/investigations/phase2/phase2_signoff_memo_2026-05-30.md`
	- `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`
- Recommended decision:
	- sign off the current Phase 2 path for the **bounded persisted-response implementation milestone**;
	- do **not** yet treat this as a stricter final Phase 2 physics-authority sign-off.
- Basis recorded in the memo:
	- the real production path executes cleanly in MIKE Zero 2025 and writes per-cell diagnostics;
	- the earlier `UZ_WC` write-path blocker was resolved by dataset-native tuple-cell layered assignment;
	- bounded/residual-aware bookkeeping is active, explicit, and test-backed (`23` tests passed, explicit clipped residuals recorded);
	- persisted readable response now exists across multiple horizons in `UZ_WC`, `UZ_SZ_EX_POSUP`, and `SZ_HEAD`;
	- the late `103` / `104` crest has been investigated enough to show that it aligns with a WM cadence transition rather than simply with the single strongest one-step clipping event.
- Conditions attached to the recommended sign-off:
	- accept `UZ_SZ_EX_POSUP` as the current working native comparison/output term;
	- accept `SZ_LEAK_FLX` as a **provisional** engineering target rather than a vendor-confirmed final authority;
	- accept the bounded effective `UZ_WC` path as an engineering bookkeeping representation rather than a reconstruction of DAISY internal layer physics;
	- accept the longer-horizon nonlinear regime and schedule sensitivity as deferred interpretation topics rather than closed final-physics questions.
- What remains outside this sign-off:
	- authoritative target confirmation,
	- a final long-horizon closure policy/report,
	- and a fully resolved physical interpretation of the late nonlinear regime.
	- the shorter companion summary now provides a copy-ready PR / stakeholder statement for the same decision boundary.

### Cross-phase post-implementation sign-off tracker (2026-05-30)

- New artifact:
	- `docs/signoff_and_followup_index_2026-05-30.md`
	- `docs/post_implementation_signoff_tracker_2026-05-30.md`
	- `docs/final_cross_phase_closeout_matrix_template.md`
- Purpose:
	- provides a single navigation entry point across the implementation plan, phase summaries, tracker, and final closeout template;
	- combines the remaining follow-up items from the Phase 0, Phase 1, and Phase 2 sign-off summaries into one post-implementation tracker.
	- provides a reusable final closeout-matrix template to fill once implementation is otherwise complete.
- Main cross-phase conclusion:
	- the implementation plan is no longer blocked by low-level runtime feasibility;
	- the remaining work after implementation is mostly about which sign-off boundary the project wants to enforce: lighter milestone closure vs stricter final in-model / physics-authority closure.
- Main shared dependency highlighted by the tracker:
	- the authoritative leakage-target question (`SZ_LEAK_FLO` vs `SZ_LEAK_FLX`) and final sign convention against `UZ_SZ_EX_POSUP` remain the main Phase 0 / Phase 2 shared technical follow-up.
- Main Phase 1 decision highlighted by the tracker:
	- after implementation is otherwise complete, the project should explicitly decide whether `virtual_ol_d_snapshot` + `OLDR_S` is the accepted permanent Phase 1 closure policy or whether stricter in-model runoff closure is still required.
- Main Phase 2 decision highlighted by the tracker:
	- after implementation is otherwise complete, the project should explicitly decide whether the current bounded persisted-response milestone boundary is sufficient or whether stricter final sign-off requires long-horizon closure and deeper schedule-sensitive interpretation work.

### Implementation tasks

1. **Confirm the authoritative native MIKE SHE comparison term**
	- Run a short diagnostic step and compare:
	  - `UZ_SZ_EX_POSUP`,
	  - `SZ_LEAK_FLO`,
	  - `SZ_LEAK_FLX`.
	- Determine which variable best represents the native UZ-to-SZ exchange already implied by the model.
	- Lock the sign convention in the code and in the diagnostics output.

2. **Replace the current scalar proof-of-concept with cell-aware net exchange logic**
	- The current `calc_SZ_LEAK_FLX` applies one scalar DAISY value to every coupled cell block.
	- Replace it with logic that operates on each coupled mapping unit and supports future class-specific DAISY inputs.

3. **Compute net leakage correction**
	- For each coupled cell:
	  - compute DAISY percolation rate from interval depth,
	  - read the native MIKE SHE leakage term,
	  - compute `net_correction = daisy_exchange - native_exchange` using the verified sign convention.

4. **Write the correction to the selected MIKE SHE target**
	- Until the authoritative target is conclusively confirmed, use `SZ_LEAK_FLX` as the provisional engineering target for implementation work.
	- Apply the correction to `SZ_LEAK_FLO` or `SZ_LEAK_FLX`, whichever is confirmed to be the correct writable representation.
	- Keep units consistent with the selected variable.

5. **Update `UZ_WC` bookkeeping from the same exchange**
	- Convert the net exchange into an effective change in volumetric water content:
	  - `step_depth_m = net_rate_m_per_s * mshe_dt_seconds`
	  - `delta_theta = step_depth_m / effective_uz_thickness_m`
	- Apply the `UZ_WC` correction using the chosen effective representation.
	- Do not apply the same `delta_theta` to every layer unless that is explicitly validated to conserve the intended volume.

6. **Clip to physical bounds**
	- Constrain the updated `UZ_WC` between residual and saturated values.
	- Record clipped residuals as explicit water-balance terms.

7. **Add diagnostics**
	- Store, per cell and step:
	  - DAISY matrix percolation depth,
	  - DAISY rate,
	  - native MIKE leakage term,
	  - net correction applied,
	  - `UZ_WC` before and after,
	  - clipped residual.

### Matrix percolation acceptance criteria

- The selected leakage correction variable is used with a documented sign convention.
- The applied correction and the `UZ_WC` change represent the same water exchange.
- Water-balance closure remains within tolerance for each coupled cell and for the full domain.

## Phase 3 - Matrix drain flow coupling

### Goal

Route DAISY matrix drain flow into MIKE SHE drain inflow for coupled drained cells only, while keeping bookkeeping consistent and preventing double counting.

### Phase 3 preparation scaffolding (2026-05-30)

- New artifacts:
	- `docs/investigations/phase3/phase3_preparation_2026-05-30.md`
	- `docs/Monthly_FWater_phase3_smoke.csv`
- Code preparation completed:
	- `src/spatial_mapping.py` now supports per-group metadata overrides when building from legacy blocks, plus drained-scope selectors (`drained_groups()`, `iter_drained_cell_mappings()`, `iter_groups(drained=...)`);
	- `tests/test_daisy_functions.py` now covers the `Matrix drain flow` DAISY interval-total column;
	- `tests/test_coupling.py` now covers drained-group selection and per-group metadata overrides in the spatial mapping.
- Validation status:
	- `pixi run python -m unittest discover -s tests -v` passed with `26` tests.
- Important current limitation:
	- historical prep-time limitation: the default production mapping still used an empty drain metadata overlay at this stage; this has since been addressed by the implementation smoke update below.
- Immediate next implementation step:
	- historical next step at that time: define the default drained metadata overlay and then implement the production `Matrix drain flow -> SZDR_IN_FLO` path.

### Latest Phase 3 implementation smoke (2026-05-30)

- New implementation status:
	- `src/spatial_mapping.py` now carries an exact per-cell drained overlay derived from `data/Cernici_060126_Test02_2/07_SZ/drain_map_Cernici_v1.shp` using majority cell-area overlap against the coupled footprint;
	- the encoded default drain scope currently covers `33` drained block slices / `643` drained coupled cells and assigns `lower_boundary_case = sz_drain` to those cells;
	- `src/coupling.py` now provides `assign_uniform_scalar_to_cells(...)` for exact drained-cell writes;
	- `src/Test_Cernici.py` now routes DAISY `Matrix drain flow` into `SZDR_IN_FLO` for mapped drained cells, records `matrix_drain_flow` diagnostics, and supports `--disable-drain-coupling` for isolation.
- New artifacts:
	- `docs/investigations/phase3/phase3_matrix_drain_flow_smoke.csv`
	- `docs/investigations/phase3/phase3_matrix_drain_flow_smoke_2026-05-30.md`
- Validation status after the change:
	- full unit suite passed (`29` tests);
	- one-step MIKE SHE smoke completed successfully with `docs/Monthly_FWater_phase3_smoke.csv`.
- Recorded smoke result:
	- total diagnostic rows: `1998`;
	- `matrix_percolation` rows: `1355`;
	- `matrix_drain_flow` rows: `643`;
	- mean applied `SZDR_IN_FLO` target per drained cell: `1.1799856630824374e-07 m^3/s` for a DAISY source depth of `1.23456 mm` over `2678400.0 s`;
	- all drain rows carried `lower_boundary_case = sz_drain`.
- Current bookkeeping stance:
	- Phase 3 currently uses a provisional external cumulative ledger `virtual_cumulative_drain_depth`; this is an implementation bookkeeping model, not yet a final accepted physical storage owner.
- Important current limitation:
	- the smoke proves production routing and diagnostics, but it does **not** yet prove that native MIKE SHE drain inflow is disabled or zeroed for the drained coupled cells.
- Immediate next implementation step:
	- run a focused native-vs-injected drain double-count probe / setup-override check using the new mapped drained subset and `matrix_drain_flow` diagnostics.

### Phase 3 native-vs-injected drain double-count probe (2026-05-30)

- New probe entrypoint:
	- `src/investigations/phase3_matrix_drain_double_count_probe.py`
- New investigation note:
	- `docs/investigations/phase3/phase3_matrix_drain_double_count_probe_2026-05-30.md`
- Probe scope:
	- compared baseline vs externally injected `SZDR_IN_FLO = 1.0e-5 m^3/s` per drained cell on the `643` mapped drained coupled cells;
	- used solver-visible `SZDR_POINT_FLO` when available and `SZ_HEAD` as the alternate readable groundwater-state observable;
	- tested four setup variants on the isolated no-plugin/no-M1D probe setup:
	  - `default`
	  - `szdr_code0` (`DrainCode.FixedValue = 0`)
	  - `szdr_option0` (`DrainageOption = 0`)
	  - `szdr_option0_code0`
- Recorded findings:
	- `default` kept a nonzero readable native drain baseline (`SZDR_POINT_FLO` remained active), but injected `SZDR_IN_FLO` produced **no detectable divergence** from baseline in either `SZDR_POINT_FLO` or `SZ_HEAD`, even across a `20`-step comparison horizon.
	- `szdr_code0` suppressed the readable native baseline drain signal to `0.0` while keeping `SZDR_IN_FLO` writable and solver-visible; the injected case diverged immediately from baseline and remained separated through `20` steps in both:
	  - `SZDR_POINT_FLO` (final drained-cell mean cell-sum difference `-9.999999747378752e-06 m^3/s`), and
	  - `SZ_HEAD` (final mean differences `+0.003388888393715206 m` all-layer / `+0.0061130172312005016 m` top-layer).
	- `szdr_option0` and `szdr_option0_code0` removed the readable drain output item entirely (`SZDR_POINT_FLO` unavailable) **and** made the external `SZDR_IN_FLO` runtime dataset unavailable, while `SZ_HEAD` stayed identical between baseline and injected cases over the tested `3`-step horizon.
- Current interpretation:
	- the default setup leaves native MIKE SHE saturated-zone drain behavior active, but the external `SZDR_IN_FLO` path is not solver-visible there over the tested horizon;
	- `DrainCode.FixedValue = 0` is the strongest current setup-level suppression candidate because it removes the native readable drain signal while preserving a clean external injected response;
	- `DrainageOption = 0` is too strong for the intended Phase 3 coupling path because it disables the whole drain component, including the external input route.
- Current recommended next implementation step:
	- if Phase 3 is meant to keep DAISY-driven drain routing while avoiding native double counting, treat `MIKESHE_FLOWMODEL.SaturatedZone.Drainage[1].DrainCode.FixedValue = 0` as the leading production/setup override candidate and decide how that override should be enforced in the final workflow.

### Phase 3 production native-SZ-drain suppression support (2026-05-30)

- New helper module:
	- `src/setup_overrides.py`
- Production entrypoint update:
	- `src/Test_Cernici.py` now supports `--suppress-native-sz-drain`
- Shared implementation note:
	- the new production flag writes a derived setup with:
	  - `MIKESHE_FLOWMODEL.SaturatedZone.Drainage[1].DrainCode.FixedValue = 0`
	  before the normal plugin-enabled setup copy and MIKE SHE execution.
- Probe/runtime alignment update:
	- `src/investigations/phase3_matrix_drain_double_count_probe.py` now reuses the same shared saturated-zone drain override writer, so production and probe setup mutation no longer live in separate copy-pasted implementations.
- New validation artifact:
	- `docs/investigations/phase3/phase3_native_sz_drain_suppression_smoke_2026-05-30.md`
- Validation run used:
	- `pixi run python -m src.Test_Cernici --max-steps 1 --disable-runoff-coupling --daisy-output docs/Monthly_FWater_phase3_smoke.csv --diagnostics-output docs/investigations/phase3/phase3_matrix_drain_flow_smoke_suppressed.csv --suppress-native-sz-drain`
- Recorded result:
	- the production-style run completed successfully using derived setup `Cernici16_Ben_v100_DAISYinput_dr0.she`;
	- diagnostics again wrote `1998` rows total, including `643` `matrix_drain_flow` rows for the mapped drained cells;
	- the mean applied `SZDR_IN_FLO` target per drained cell remained `1.1799856630824374e-07 m3/s`, matching the earlier unsuppressed one-step smoke.
- Current implication:
	- the recommended `DrainCode.FixedValue = 0` suppression lever is now available through the real production entrypoint rather than only through ad hoc probe-specific setup edits.
- Remaining decision:
	- the repository still needs an explicit Phase 3 closure policy on whether `--suppress-native-sz-drain` should remain an opt-in production switch or become the default Phase 3 drain-coupling behavior.

### Phase 3 default native-SZ-drain policy (2026-05-30)

- Policy decision now implemented:
	- when Phase 3 drain coupling is enabled, `src/Test_Cernici.py` now suppresses the native saturated-zone drain path by default via a derived setup with:
	  - `MIKESHE_FLOWMODEL.SaturatedZone.Drainage[1].DrainCode.FixedValue = 0`
- CLI behavior after the change:
	- default behavior with drain coupling enabled: suppression is **on**;
	- explicit opt-out for controlled comparisons: `--keep-native-sz-drain`;
	- compatibility flag retained: `--suppress-native-sz-drain` now acts as an explicit confirmation of the default recommended behavior rather than the only activation path.
- New validation artifact:
	- `docs/investigations/phase3/phase3_native_sz_drain_default_policy_2026-05-30.md`
- Validation status after the policy change:
	- full unit suite passed with `36` tests;
	- a one-step production smoke completed successfully **without** `--suppress-native-sz-drain` using:
	  - `pixi run python -m src.Test_Cernici --max-steps 1 --disable-runoff-coupling --daisy-output docs/Monthly_FWater_phase3_smoke.csv --diagnostics-output docs/investigations/phase3/phase3_matrix_drain_flow_smoke_default_policy.csv`
- Recorded default-path smoke result:
	- the run still auto-generated and used derived setup `Cernici16_Ben_v100_DAISYinput_dr0.she`;
	- diagnostics again wrote `1998` rows total, including `643` `matrix_drain_flow` rows for the mapped drained cells;
	- the mean applied `SZDR_IN_FLO` target per drained cell remained `1.1799856630824374e-07 m3/s`, matching the earlier explicit opt-in suppression smoke.
- Current implication:
	- the repository no longer depends on operators remembering a special suppression flag in order to reach the only currently tested solver-visible external drain-routing configuration.
- Remaining limitation:
	- this policy change settles the Phase 3 suppression default, but it does **not** by itself settle the final acceptance status of the external `virtual_cumulative_drain_depth` bookkeeping ledger.

### Phase 3 dynamic WM timestep alignment + closeout diagnostic (2026-05-30)

- Closeout diagnostic follow-up artifact:
	- `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md`
	- `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic.csv`
- Bug discovered during the first 20-step closeout attempt:
	- the production loop was still using the initial warm-up WM step duration for drain/percolation bookkeeping even though the live MIKE SHE WM cadence over the same run varied between `4` and `10` minutes.
- Fix implemented:
	- `src/coupling.py` now exposes `resolve_mshe_timestep_hours(...)` / `resolve_mshe_timestep_seconds(...)`;
	- `src/Test_Cernici.py` now resolves the upcoming live WM step from `ms.wm.nextTimeStep()` before each coupling write, uses that duration for all Phase 1/2/3 transfer bookkeeping, and records `wm_step_seconds` / `wm_step_hours` in diagnostics metadata.
- Validation status after the timestep fix:
	- full unit suite passed with `38` tests.
- Regenerated 20-step Phase 3 closeout run used:
	- `pixi run python -m src.Test_Cernici --max-steps 20 --disable-runoff-coupling --daisy-output docs/Monthly_FWater_phase3_smoke.csv --diagnostics-output docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic.csv`
- Recorded result after the fix:
	- `12860` `matrix_drain_flow` rows were written across `20` WM steps for the mapped `643` drained cells;
	- live WM step deltas over the run ranged from `4` to `10` minutes and the diagnostics now recorded matching `wm_step_seconds` values from `240` to `640` s;
	- requested drain step depth now varied with the live WM cadence (`1.1062365591397849e-07 m` min to `2.9499641577060903e-07 m` max);
	- total requested drain step volume over the diagnostic was `0.6312640100931901 m^3`;
	- explicit residual remained `0.0`;
	- max absolute volume closure was `1.3552527156068805e-20 m^3` with `0` rows above a `1e-15 m^3` threshold;
	- final per-cell cumulative drain bookkeeping depth was `3.834953405017922e-06 m`, matching the per-cell summed requested depth exactly to floating tolerance.
- Current implication:
	- the lighter Phase 3 bookkeeping argument is no longer undermined by a frozen-first-step WM duration assumption; the external drain ledger now follows the live MIKE SHE step cadence used by the production run.

### Phase 3 sign-off summary (2026-05-30)

- New artifact:
	- `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md`
- Recommended decision:
	- sign off the current Phase 3 path for the **lighter matrix-drain engineering-routing milestone**;
	- do **not** yet treat this as a stricter final in-model drain-storage closeout sign-off.
- Basis recorded in the summary:
	- mapped drained-cell routing to `SZDR_IN_FLO` is production-live;
	- the native-vs-injected probe established `DrainCode.FixedValue = 0` as the working suppression lever;
	- production now enforces that suppression by default when drain coupling is enabled;
	- the 20-step closeout diagnostic now closes the documented `virtual_cumulative_drain_depth` bookkeeping identity to floating tolerance while following the live WM cadence.
- What remains outside stricter final sign-off:
	- permanent acceptance of the external `virtual_cumulative_drain_depth` ledger as the final Phase 3 storage owner, or replacement with a stronger in-model storage owner / observable if the project requires that stricter boundary.

### Implementation tasks

1. **Add drain-specific spatial scope**
	- Extend the mapping structure so a cell can be both coupled and flagged as drained.
	- If lower-boundary case information is not available in the current repository, add it as explicit mapping metadata.

2. **Confirm DAISY drain source column**
	- Read `Matrix drain flow` from `Monthly_FWater.csv`.
	- Validate the column exists and is used only for drain-enabled DAISY cases.

3. **Prevent double counting of MIKE SHE drain inflow**
	- Disable or zero native drain inflow in coupled drained cells.
	- Verify by comparing a short run before and after the override.

4. **Convert DAISY interval depth to MIKE SHE drain flow**
	- For each coupled drained cell:
	  - convert DAISY interval depth to rate,
	  - convert rate to flow using cell area,
	  - write the result to `SZDR_IN_FLO`.

5. **Apply explicit storage bookkeeping**
	- Convert the same applied amount to a step-depth sink.
	- Apply it to the chosen bookkeeping store.
	- Clip so storage does not go negative.
	- Record any remainder as a residual.

6. **Add diagnostics**
	- Store, per cell and step:
	  - DAISY matrix drain depth,
	  - applied `SZDR_IN_FLO`,
	  - bookkeeping store before and after,
	  - clipped residual.

### Matrix drain flow acceptance criteria

- Only mapped drained cells are updated.
- Native MIKE SHE drain inflow is not double counted.
- Applied drain flow and storage reduction represent the same water amount within tolerance.

## Current progress snapshot (2026-05-30)

This is the shortest accurate answer to **"where are we now?"**

### Implemented and accepted at the current milestone boundary

- Phase 0 is accepted for the runtime-foundation / API-discovery milestone.
- Phase 1 is accepted for the lighter runoff engineering-routing milestone.
- Phase 2 is accepted for the bounded persisted-response implementation milestone.
- Phase 3 is accepted for the lighter matrix-drain engineering-routing milestone.
- Phase 4 is accepted for the effective unsaturated-zone bookkeeping implementation milestone.
- Phase 5 is accepted for the diagnostics and reporting implementation milestone.
- Standalone handoff note:
	- `docs/current_status_handoff_2026-05-30.md`
- The current published status record lives in:
	- `docs/post_implementation_signoff_tracker_2026-05-30.md`
	- `docs/final_cross_phase_closeout_matrix_2026-06-01.md`
- Earlier-phase closeout decisions are now also recorded in:
	- `docs/followup_decision_record_2026-06-01.md`
- New follow-up recommendation notes now exist for the remaining earlier-phase policy choices:
	- `docs/investigations/phase1/phase1_permanent_policy_recommendation_2026-06-01.md`
	- `docs/phase0_phase2_authority_recommendation_2026-06-01.md`
	- `docs/investigations/phase3/phase3_permanent_policy_recommendation_2026-06-01.md`

### Current code-level state

- `src/Test_Cernici.py` now carries the production coupling path for runoff, matrix percolation, and matrix drain flow using dataset-native writes.
- Native saturated-zone drain suppression is now default-on for Phase 3 through a derived `_dr0` setup (`DrainCode.FixedValue = 0`), with `--keep-native-sz-drain` retained as the explicit comparison opt-out.
- Live WM timestep handling now follows `ms.wm.nextTimeStep()` before each coupling write, so diagnostics and bookkeeping use the actual upcoming WM step duration rather than a frozen first-step assumption.
- The latest documented test status is now a full passing unit suite at `46` tests.
- The Phase 3 20-step closeout diagnostic now closes the documented `virtual_cumulative_drain_depth` bookkeeping identity to floating tolerance while following the live `4`-`10` minute WM cadence.
- Phase 4 effective `UZ_WC` bookkeeping now routes through a shared helper in `src/coupling.py`, and the production diagnostics now expose explicit effective-state metadata such as `effective_uz_theta_before`, `effective_uz_theta_requested_after`, and `effective_uz_theta_after`.
- A new one-step Phase 5 smoke now writes both the detailed diagnostics CSV and an automatic summary CSV through the production runner:
	- `docs/investigations/phase5/phase5_coupling_summary_smoke_2026-06-01.md`
- Phase 5 plotting is now live in both production and standalone form:
	- `src/Test_Cernici.py` supports `--plot-diagnostics` for auto-generated timeseries + PNGs;
	- `src/diagnostics_plots.py` can regenerate the same bundle from an existing diagnostics CSV.

### Current adopted closeout choices and remaining deferred items

- Phase 1 now permanently accepts `virtual_ol_d_snapshot` + `OLDR_S` as the current-boundary closure policy.
- The shared Phase 0 / Phase 2 authority question is explicitly deferred for the current closeout, with `SZ_LEAK_FLX` retained as the provisional engineering target and final sign-convention lock against `UZ_SZ_EX_POSUP` left outside the accepted boundary.
- Phase 2 now stops at the already accepted bounded persisted-response implementation milestone for the current closeout.
- Phase 3 now permanently accepts `virtual_cumulative_drain_depth` as the current-boundary bookkeeping owner together with the default `DrainCode.FixedValue = 0` suppression policy.
- Phases 4 and 5 now stop at their accepted implementation-milestone boundary for the current closeout; any stricter final Phase 4 / Phase 5 package remains intentionally deferred unless later reopened.

### Practical next move depends on intent

- If the goal is **project closeout**, the adopted earlier-phase loose-end decisions now live in `docs/followup_decision_record_2026-06-01.md`; the remaining work is mainly to keep stricter final Phase 0 / 1 / 2 / 3 / 4 / 5 items deferred unless the project intentionally reopens them.
- If the goal is **more engineering later**, the clean next implementation pass is to reopen the Phase 4 effective `UZ_WC` helper formalization and the Phase 5 reporting package for a stricter final closeout pass.

## Phase 4 - Effective unsaturated-zone bookkeeping

### Goal

Maintain a bounded, effective MIKE SHE unsaturated-zone storage state that supports local water-balance closure without attempting to reproduce DAISY layer physics.

### Implementation tasks

1. **Formalize the bookkeeping definition**
	- Define `UZ_WC` as an effective storage state used only for DAISY-driven exchange bookkeeping.
	- Document that it is not a reconstruction of DAISY internal soil-layer states.

2. **Centralize all `UZ_WC` updates**
	- Ensure `UZ_WC` is updated by one helper function only.
	- Feed that helper net exchange terms from matrix percolation and future feedback terms if they are later introduced.

3. **Use a physically consistent effective-thickness model**
	- Prefer the authoritative MIKE SHE setup thickness when it can be derived from `Unsatzone -> UZSoilProfiles`.
	- Keep CLI / environment overrides available for controlled comparisons and non-standard setups.
	- If a layered dataset must still be written, distribute the effective change in a way that preserves the intended total storage change.

4. **Apply bounds and residual tracking**
	- Enforce lower and upper bounds using residual water content and saturated water content or porosity.
	- Any clipped amount becomes a reported residual, not a hidden loss.

5. **Add diagnostics**
	- Track, per cell and step:
	  - source exchange term,
	  - `delta_theta`,
	  - `UZ_WC` before and after,
	  - clipped residual.

### UZ bookkeeping acceptance criteria

- `UZ_WC` changes equal the cumulative net DAISY-driven storage correction within tolerance.
- No hidden volume is created by layered write-back logic.
- Bounded values and residuals are fully traceable.

### Phase 4 helper formalization scaffolding (2026-06-01)

- New artifacts:
	- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_smoke.csv`
	- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_smoke_summary.csv`
	- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md`
- Production implementation update:
	- `src/coupling.py` now provides `EffectiveUzCellBookkeepingResult` and `apply_effective_uz_storage_corrections(...)` as the shared owner for effective `UZ_WC` bookkeeping;
	- `src/Test_Cernici.py` now routes `calc_UZ_WC(...)` through that shared helper instead of keeping the bounded layer-shift logic inline;
	- `matrix_percolation` diagnostics metadata now records explicit effective bookkeeping semantics (`bookkeeping_mode = effective_uz_wc`, effective theta before/requested-after/after, and layer-delta fields).
- Validation status after the refactor:
	- full unit suite passed with `41` tests;
	- a one-step production smoke isolated the percolation/effective-UZ path and wrote both detailed and summary diagnostics.
- Focused smoke command used:
	- `pixi run python -m src.Test_Cernici --max-steps 1 --disable-runoff-coupling --disable-drain-coupling --diagnostics-output docs/investigations/phase4/phase4_effective_uz_bookkeeping_smoke.csv`
- Recorded smoke result:
	- `matrix_percolation` requested `0.2934274276489688 m^3` and target `0.2934274276489688 m^3`;
	- storage correction volume was `0.5528946982397542 m^3` with residual `-0.25946727059078545 m^3`;
	- requested-storage and target-storage closure both remained at `-9.771372079525609e-18 m^3` with max absolute target-storage closure `1.0842021724855044e-19 m^3`.
- Current implication:
	- Phase 4 now has a first-class shared bookkeeping helper and explicit effective-state diagnostics in the production runner;
	- broader Phase 4 closeout is still open because final acceptance criteria and longer-horizon interpretation are not yet fully locked.

### Phase 4 thickness-authority follow-up (2026-06-01)

- Production implementation update:
	- `src/setup_overrides.py` now derives effective UZ thickness directly from the MIKE SHE setup by reading `Unsatzone -> UZSoilProfiles` profile-layer depths and discretization totals;
	- `src/Test_Cernici.py` now resolves effective UZ thickness in this order: command line override, `EFFECTIVE_UZ_THICKNESS_M`, setup-derived thickness, built-in default;
	- `src/coupling.py` runtime context and production diagnostics metadata now record `effective_uz_thickness_source`.
- Live Cernici authority result:
	- the current bundled setup resolves `10 m` from both the profile-layer bottom depth (`Depth = 10`) and the UZ discretization sum (`0.05*4 + 0.1*3 + 0.25*6 + 0.5*6 + 1*5 = 10 m`).
- Validation status after the authority pass:
	- full unit suite passed with `44` tests;
	- `pixi run python src/Test_Cernici.py --print-config` now reports `Effective UZ:    10 m (setup UZSoilProfiles layer depth/discretization)` on the live repository setup.
- Current implication:
	- the earlier `10 m` bookkeeping thickness is now justified by explicit setup authority rather than only a built-in default;
	- remaining Phase 4 closeout work is now mainly about final acceptance criteria and final-abstraction decisions, not thickness provenance.

### Phase 4 longer-horizon interpretation follow-up (2026-06-01)

- New artifact:
	- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_longer_horizon_2026-06-01.md`
- Evidence/modeling stance:
	- this pass reinterprets the existing `120`-step bounded production artifact through the new Phase 4 helper semantics instead of generating a duplicate long run;
	- that is acceptable because the helper formalization changed bookkeeping ownership/observability while the live effective thickness remained `10 m`, now with setup-derived authority.
- Longer-horizon interpretation highlights:
	- candidate `UZ_WC` mutation remains visible before `setValues`, but immediate same-time `UZ_WC` readback still stays flat;
	- readable `UZ_WC` all-layer divergence appears at step `2`, top-layer divergence at step `8`, and delayed `UZ_SZ_EX_POSUP` divergence at step `31`;
	- the strongest `UZ_WC` / `UZ_SZ_EX_POSUP` separation still occurs at step `103` / WM step `104`, while `SZ_HEAD` keeps a stronger end-of-run memory than the `UZ_WC` / flux-side outputs;
	- bounded rows and residuals remain active over the long horizon, but the late crest still aligns better with a cadence transition plus propagated nonlinear response than with a single clipping spike.
- Current implication:
	- the Phase 4 “what is effective `UZ_WC` doing over long horizons?” question now has a documented answer;
	- the main remaining Phase 4 open item is no longer basic long-horizon interpretation, but rather the final acceptance criteria / permanent-abstraction decision.

### Phase 4 handoff (2026-06-01)

- New artifact:
	- `docs/investigations/phase4/phase4_handoff_2026-06-01.md`
- Purpose:
	- provides the short standalone Phase 4 handoff for the next engineering or review pass;
	- identifies the authoritative Phase 4 artifacts to open first;
	- reframes the remaining work as final abstraction / acceptance-criteria policy rather than missing plumbing.
- Main current Phase 4 statement captured there:
	- effective `UZ_WC` is now best treated as a bounded effective storage-state ledger that is solver-visible over time even though same-time readback still lags.

## Phase 5 - Quality control and mass-balance diagnostics

### Goal

Produce enough diagnostics to prove that the coupling does not create or destroy water.

### Implementation tasks

1. **Define a diagnostics output format**
	- Write per-step diagnostics to CSV or Parquet under a run-specific output directory.
	- Include run metadata such as setup path, DAISY file path, and sign-convention notes.

2. **Record per-variable diagnostics**
	- For runoff, percolation, and drain flow, store:
	  - DAISY source depth,
	  - DAISY interval seconds,
	  - applied MIKE SHE target value,
	  - associated storage correction,
	  - clipped residual.

3. **Compute cell-level closure**
	- For each cell, variable, and step, compute a residual such as:
	  - `closure = source_volume - applied_target_volume - storage_change_volume - clipped_residual_volume`
	- Flag rows outside tolerance.

4. **Compute domain-level closure**
	- Aggregate all coupled cells over time for each variable and for the full run.
	- Report cumulative totals and cumulative residuals.

5. **Add traceability fields**
	- Preserve:
	  - timestamp,
	  - DAISY class or simulation identifier,
	  - MIKE SHE row and column index,
	  - variable name,
	  - lower-boundary case if relevant.

6. **Add summary checks at the end of the run**
	- Emit a short summary of:
	  - total DAISY-applied water,
	  - total storage change,
	  - total residual,
	  - worst offending cells or steps.

### QC acceptance criteria

- Per-step and cumulative residuals remain within configured tolerances.
- Every clipped or unassigned amount is reported explicitly.
- Diagnostics are sufficient to reproduce and explain any mismatch.

### Phase 5 diagnostics summary scaffolding (2026-06-01)

- New artifacts:
	- `docs/investigations/phase5/phase5_coupling_summary_smoke.csv`
	- `docs/investigations/phase5/phase5_coupling_summary_smoke_summary.csv`
	- `docs/investigations/phase5/phase5_coupling_summary_smoke_2026-06-01.md`
- Production implementation update:
	- `src/diagnostics.py` now expands diagnostics metadata and emits a closure-aware volume summary table;
	- `src/Test_Cernici.py` now writes a sibling diagnostics summary CSV automatically whenever `--diagnostics-output` is enabled and prints per-variable end-of-run closure lines.
- Current QC summary model:
	- instead of one opaque combined residual, the new summary makes the two practical bookkeeping identities explicit:
	  - requested volume vs written target volume;
	  - requested volume vs applied storage correction plus explicit residual.
- Validation status after the summary update:
	- full unit suite passed with `39` tests.
- One-step production smoke used:
	- `pixi run python -m src.Test_Cernici --max-steps 1 --diagnostics-output docs/investigations/phase5/phase5_coupling_summary_smoke.csv`
- Recorded smoke result:
	- the production runner wrote both the detailed diagnostics CSV and the new summary CSV automatically;
	- the summary contained rows for `matrix_drain_flow`, `matrix_percolation`, `runoff`, and `TOTAL`;
	- `matrix_drain_flow` requested `0.37854530064516134 m^3` with zero target-storage closure;
	- `matrix_percolation` requested `0.2934274276489688 m^3`, total target-storage closure `-1.4148838350935833e-17 m^3`, and max absolute target-storage closure `4.336808689942018e-19 m^3`;
	- `runoff` remained `0.0 m^3` on this smoke input at the tested first step;
	- the combined `TOTAL` row reported requested `0.6719727282941301 m^3` with max absolute target-storage closure `4.336808689942018e-19 m^3`.
- Current implication:
	- the repository now has a first-class automated Phase 5-style closure summary layer rather than relying only on ad hoc notebook / terminal post-processing;
	- broader Phase 5 closeout is still open because the current work is summary scaffolding, not yet the full final QC/reporting package.

### Phase 5 diagnostics plotting (2026-06-01)

- New artifacts:
	- `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md`
	- `docs/investigations/phase5/phase5_coupling_plotting_smoke.csv`
	- `docs/investigations/phase5/phase5_coupling_plotting_smoke_summary.csv`
	- `docs/investigations/phase5/phase5_coupling_plotting_smoke_timeseries.csv`
	- `docs/investigations/phase5/phase5_coupling_plotting_smoke_plots/volume_terms_by_variable.png`
	- `docs/investigations/phase5/phase5_coupling_plotting_smoke_plots/closure_terms_by_variable.png`
	- `docs/investigations/phase5/phase5_coupling_plotting_smoke_plots/matrix_percolation_effective_state.png`
- Production implementation update:
	- `src/diagnostics.py` now derives timestamp-and-variable timeseries rollups and sibling output paths for plotting artifacts;
	- new module `src/diagnostics_plots.py` can regenerate the plot bundle from an existing diagnostics CSV or from in-memory diagnostics data;
	- `src/Test_Cernici.py` now supports `--plot-diagnostics`, which writes the detailed CSV, summary CSV, timeseries CSV, and PNG bundle in one production run;
	- `pixi.toml` now includes `matplotlib`.
- Windows runtime note:
	- `src/diagnostics_plots.py` sets `KMP_DUPLICATE_LIB_OK=TRUE` before importing matplotlib so plotting can coexist with the MIKE SHE/OpenMP runtime stack on this Windows setup.
- Validation status after the plotting pass:
	- full unittest suite passed with `46` tests;
	- a one-step production smoke completed successfully and wrote the full plotting artifact bundle.
- Recorded plotting-smoke totals:
	- total requested volume: `0.6719727282941301 m^3`;
	- total target-storage closure: `-9.771372079525609e-18 m^3`;
	- max absolute total target-storage closure: `1.0842021724855044e-19 m^3`.

## Test strategy

### Unit tests

Add unit tests before enabling the full workflow.

1. **DAISY interval handling**
	- Verify monthly rows are treated as interval totals, not linearly interpolated continuous values.
	- Verify interval duration is derived from timestamps rather than assumed to be 30 days.

2. **Conversion helpers**
	- Verify depth-to-rate, rate-to-flow, and depth-to-`delta_theta` conversions.

3. **Clipping logic**
	- Verify non-negative clipping for `OL_D` and any drain bookkeeping store.
	- Verify lower and upper clipping for `UZ_WC`.

4. **Block or mask application**
	- Verify only mapped cells are changed.
	- Verify uncoupled cells remain untouched.

5. **Mass-balance identities**
	- Verify synthetic cases where source depth, applied target, and storage change should exactly match.

### Integration tests

1. **Short MIKE SHE smoke run**
	- Run a limited number of time steps with diagnostics enabled.
	- Confirm the plugin can read DAISY input, apply updates, and terminate cleanly.

2. **Percolation regression check**
	- Compare the current proof-of-concept behavior with the refactored implementation for a controlled case.
	- Confirm the new implementation changes only the intended cells and uses interval-aware conversion.

3. **Uncoupled-cell invariance check**
	- Confirm uncoupled cells match baseline MIKE SHE behavior.

4. **Mass-balance summary check**
	- Confirm cumulative residuals stay below the agreed tolerance.

## Recommended delivery order

1. Foundation and refactoring.
2. Runoff coupling.
3. Matrix percolation coupling.
4. Matrix drain flow coupling.
5. Effective `UZ_WC` bookkeeping finalization.
6. QC diagnostics and end-of-run summaries.
7. Short integration runs and acceptance review.

This order is recommended because runoff and drain flow are direct routing problems, while matrix percolation depends on sign conventions, native MIKE SHE comparison terms, and effective-storage bookkeeping.

## Definition of done

The implementation is complete only when all of the following are true:

- DAISY interval totals are applied without inappropriate interpolation.
- Coupled-cell scope and drain scope are explicitly mapped.
- Runoff, matrix percolation, and matrix drain flow are implemented and independently testable.
- `UZ_WC` bookkeeping is physically bounded and mass consistent.
- Diagnostics identify every applied amount, every clipped amount, and every residual.
- Short MIKE SHE runs complete successfully with cumulative mass-balance residuals within tolerance.

## Open questions to resolve before coding starts

1. Which MIKE SHE variable is the correct writable target for percolation correction: `SZ_LEAK_FLO` or `SZ_LEAK_FLX`?
2. Is `UZ_SZ_EX_POSUP` the correct native comparison term for DAISY percolation, and what is its sign convention?
3. Is `OL_D` writable and appropriate as the runoff and drain bookkeeping store, or is a separate bookkeeping path needed?
4. Does the current coupled footprint represent one DAISY class or multiple classes that still need to be encoded in the mapping?
5. How should effective `UZ_WC` updates be distributed if the MIKE SHE API requires writing a layered structure?

These questions should be answered with a short diagnostic spike before the full implementation begins.
