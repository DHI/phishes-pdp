# Current status handoff (updated 2026-06-02)

## Purpose

This note is the shortest standalone answer to:

- where the repository currently stands,
- what has already been accepted,
- what is still open,
- and what the most sensible next move is.

Use this when you do **not** want to reread the full `docs/tasks.md` history first.

## Bottom line

The implementation is no longer blocked by low-level runtime feasibility.

The repository now has production-style coupling paths for:

- Phase 1 runoff,
- Phase 2 matrix percolation,
- and Phase 3 matrix drain flow.

The current package is now documented as accepted at the **milestone or implementation boundary** for Phases 0 through 5.

The earlier-phase loose ends are now recorded through an adopted follow-up decision record, and the remaining non-closed items are intentionally deferred stricter-final-signoff questions rather than unresolved current-boundary policy choices.

## Current approved boundary

| Phase | Current accepted boundary | Main evidence |
| --- | --- | --- |
| Phase 0 | Runtime-foundation / API-discovery milestone | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` |
| Phase 1 | Lighter runoff engineering-routing milestone | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` |
| Phase 2 | Bounded persisted-response implementation milestone | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` |
| Phase 3 | Lighter matrix-drain engineering-routing milestone | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md` |
| Phase 4 | Effective unsaturated-zone bookkeeping implementation milestone | `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md` |
| Phase 5 | Diagnostics and reporting implementation milestone | `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` |

## Current code-level state

### Production orchestration

- `src/Test_Cernici.py` is the active production-style orchestration entrypoint.
- It now drives:
  - runoff coupling,
  - matrix percolation coupling,
  - matrix drain flow coupling,
  - diagnostics writing,
  - and derived setup handling for Phase 3 native drain suppression.

### Runtime-write behavior

- Dataset-native writes are the working pattern.
- Earlier detached-row mutation false negatives are no longer the current implementation basis.

### Phase 3 drain policy

- Native saturated-zone drain suppression is now default-on when drain coupling is enabled.
- The working setup lever is:
  - `MIKESHE_FLOWMODEL.SaturatedZone.Drainage[1].DrainCode.FixedValue = 0`
- Explicit opt-out still exists for controlled comparisons via:
  - `--keep-native-sz-drain`

### Dynamic timestep handling

- The production loop now resolves the upcoming live WM step using `ms.wm.nextTimeStep()` before each coupling write.
- This fixed the earlier Phase 3 closeout bug where bookkeeping kept using the first WM step duration even though the live cadence changed during the run.

### Latest documented validation state

- The latest documented full unit status is `46` passing tests.
- The Phase 3 20-step closeout diagnostic now records live `wm_step_seconds` correctly and closes the documented drain bookkeeping identity to floating tolerance.
- A new Phase 4-focused one-step smoke now isolates matrix percolation/effective `UZ_WC` bookkeeping and closes the requested-vs-target-vs-storage identity to floating tolerance after the shared-helper refactor.
- A new Phase 5-style one-step smoke now writes both a detailed diagnostics CSV and an automatic closure-summary CSV from the production runner.
- A new Phase 4 follow-up pass now derives effective UZ thickness from the MIKE SHE setup itself; the live Cernici setup resolves `10 m` from both `UZSoilProfiles` layer depths and UZ discretization totals.
- A new Phase 4 longer-horizon interpretation note now translates the recorded `120`-step bounded persisted-response evidence into effective `UZ_WC` terms and interprets the step `103` crest as propagated nonlinear response exposed at a cadence transition rather than as a one-step clipping artifact.
- A new Phase 5 plotting smoke now writes the detailed CSV, summary CSV, timeseries CSV, and three PNG plots (`volume_terms_by_variable.png`, `closure_terms_by_variable.png`, `matrix_percolation_effective_state.png`) from the production runner.
- New Phase 4 and Phase 5 sign-off summaries now approve those phases for implementation milestones while explicitly deferring stricter final sign-off boundaries.
- A June 2026 Phase 1 targeted alternate-observable follow-up reran both one-step and 20-step suppression comparisons and confirmed that `OLDR_S` remains the only practical response observable, `OL_D` stays flat, and no delayed alternate discriminator emerged.

## What is still open

### Earlier-phase closeout choices now recorded

The following earlier-phase loose ends are now finalized for the current repository boundary:

- Phase 1 permanently accepts `virtual_ol_d_snapshot` + `OLDR_S` as the current closure policy; later June 2026 suppression and alternate-observable reruns did not change that boundary;
- the shared Phase 0 / Phase 2 authority question is explicitly deferred, with `SZ_LEAK_FLX` retained as the provisional engineering target and the final sign convention against `UZ_SZ_EX_POSUP` left outside the current closeout boundary;
- Phase 2 stops at the already accepted bounded persisted-response milestone rather than reopening stricter final physics-authority sign-off now;
- Phase 3 permanently accepts `virtual_cumulative_drain_depth` as the current bookkeeping owner together with the default derived-setup native-drain suppression policy.

### Phase 4 / Phase 5 status

These are now milestone-approved, and the current closeout choice is to stop at those milestones rather than extend them into stricter final sign-off:

- Phase 4 effective `UZ_WC` bookkeeping implementation milestone
- Phase 5 diagnostics and reporting implementation milestone

Current June 2026 update:

- Phase 4 helper formalization now exists in production form;
- `src/coupling.py` now owns effective `UZ_WC` bookkeeping through `apply_effective_uz_storage_corrections(...)`, and `src/Test_Cernici.py` now emits explicit effective-state metadata in `matrix_percolation` diagnostics;
- `src/Test_Cernici.py` now also resolves effective UZ thickness from the MIKE SHE setup when no CLI or environment override is supplied, and diagnostics now record `effective_uz_thickness_source`;
- a dedicated longer-horizon Phase 4 interpretation note now exists and explains the recorded late-regime crest as cadence-exposed propagated state response rather than a single clipping spike;
- a dedicated Phase 4 handoff note now exists and reframes the remaining work as final abstraction / acceptance-criteria policy rather than missing plumbing;
- a dedicated Phase 4 sign-off summary now approves the effective-UZ bookkeeping implementation milestone while deferring stricter final abstraction policy;
- Phase 5 summary scaffolding now exists in production form;
- `src/Test_Cernici.py` can now emit an automatic sibling summary CSV for any diagnostics-enabled run;
- Phase 5 plotting now also exists in production form through `--plot-diagnostics`, and a standalone `src.diagnostics_plots` entrypoint can regenerate the same plots from an existing diagnostics CSV;
- a dedicated Phase 5 sign-off summary now approves the diagnostics/reporting implementation milestone while deferring stricter final QC/reporting policy;
- the current project choice is to stop at those implementation milestones for this closeout and keep stricter final Phase 4 / Phase 5 policy work deferred unless reopened later.

## Best next move depends on goal

### If the goal is project closeout

The next move is now mostly **final review and publication hygiene**, not runtime plumbing:

1. review `docs/followup_decision_record_2026-06-01.md` as the adopted earlier-phase closeout addendum;
2. keep the stricter final Phase 0 / 1 / 2 / 3 / 4 / 5 items deferred unless the project intentionally reopens them;
3. use the published matrix and follow-up decision record as the current closeout package.

### If the goal is more engineering work

The cleanest next implementation pass, if the project later chooses to reopen beyond the current stop boundary, is:

1. extend the new Phase 4 effective `UZ_WC` helper formalization into a fuller closeout-ready work package (explicit acceptance criteria and final abstraction decision);
2. extend the new Phase 5 summary + plotting package into a fuller longer-horizon QC/reporting work package with explicit phase-level closeout criteria and writeup.

That would convert the current strong phase-specific diagnostics into a more explicit whole-run closure layer.

## Best files to open next

- `docs/tasks.md` — full running implementation log
- `docs/post_implementation_signoff_tracker_2026-05-30.md` — what remains after implementation
- `docs/final_cross_phase_closeout_matrix_2026-06-01.md` — current published decision record
- `docs/signoff_and_followup_index_2026-05-30.md` — single navigation entry point
- `docs/investigations/phase4/phase4_handoff_2026-06-01.md` — short Phase 4 handoff and open-decision summary
- `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md` — current Phase 4 implementation-milestone decision
- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md` — shared-helper formalization and focused Phase 4 smoke
- `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md` — plotting workflow, artifacts, and interpretation guide
- `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` — current Phase 5 implementation-milestone decision
- `docs/investigations/phase5/phase5_coupling_summary_smoke_2026-06-01.md` — first production smoke for the new automatic closure-summary layer
- `docs/investigations/phase1/phase1_permanent_policy_recommendation_2026-06-01.md` — recommended final Phase 1 policy choice for the current boundary
- `docs/investigations/phase1/phase1_runoff_finalization_task_2026-06-01.md` — explicit final Phase 1 task status with the lighter-vs-stricter boundary spelled out
- `docs/investigations/phase1/phase1_runoff_alternate_observables_2026-06-02.md` — June 2026 confirmation that no delayed alternate Phase 1 discriminator emerged
- `docs/investigations/phase3/phase3_permanent_policy_recommendation_2026-06-01.md` — recommended final Phase 3 policy choice for the current boundary
- `docs/phase0_phase2_authority_recommendation_2026-06-01.md` — recommended shared Phase 0 / Phase 2 authority deferral choice
- `docs/followup_decision_record_2026-06-01.md` — adopted current-boundary resolution of the remaining earlier-phase loose ends

## One-sentence summary

As of 2026-06-02, the repository is in a **milestone-accepted, closeout-recorded** state: Phases 0 through 5 are accepted at their documented milestone or implementation boundary, the earlier-phase loose ends are now finalized for the current boundary, and the remaining non-closed items are intentionally deferred stricter-final-signoff questions only.
