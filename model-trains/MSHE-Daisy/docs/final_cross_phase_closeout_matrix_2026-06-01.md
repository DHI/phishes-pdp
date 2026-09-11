# Final cross-phase closeout matrix (2026-06-01)

_Current published decision record for the implementation package as of 2026-06-01._

## Purpose

This is the current cross-phase status matrix for Phases 0, 1, 2, 3, 4, and 5.

It supersedes the 2026-05-30 published matrix as the best single decision record for the repository’s current state.

It is intentionally honest about three things at once:

- Phases 0 through 3 are already accepted at the documented milestone boundary,
- Phase 4 and Phase 5 are now accepted at their implementation milestone boundary,
- and the current closeout explicitly stops at the accepted Phase 4 / Phase 5 implementation milestones while stricter final sign-off boundaries remain deferred where noted.

## Approval summary matrix

| Phase | Milestone boundary accepted? | Stricter final sign-off required? | Current final decision | Primary evidence | Main unresolved item | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Phase 0 | yes | no | accepted | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`; `docs/followup_decision_record_2026-06-01.md` | Final authoritative leakage target remains explicitly deferred under the adopted current-closeout policy | project | published |
| Phase 1 | yes | no | accepted | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md`; `docs/followup_decision_record_2026-06-01.md` | Stricter in-model runoff closeout remains intentionally deferred outside the adopted permanent current-boundary policy | project | published |
| Phase 2 | yes | no | accepted | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`; `docs/followup_decision_record_2026-06-01.md` | Stricter final Phase 2 physics-authority work remains intentionally deferred outside the adopted milestone boundary | project | published |
| Phase 3 | yes | no | accepted | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md`; `docs/followup_decision_record_2026-06-01.md` | Stricter in-model drain-storage authority remains intentionally deferred outside the adopted permanent current-boundary policy | project | published |
| Phase 4 | yes | no | accepted | `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md` | Promotion of the current working abstraction to stricter final policy remains deferred | project | published |
| Phase 5 | yes | no | accepted | `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` | Stricter longer-horizon QC/reporting boundary remains deferred | project | published |

## Cross-phase shared decisions

| Shared item | Why it matters | Decision required | Evidence | Outcome | Status |
| --- | --- | --- | --- | --- | --- |
| Leakage target authority (`SZ_LEAK_FLO` vs `SZ_LEAK_FLX`) | Shared dependency between Phase 0 and Phase 2 | defer for current closeout | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`; `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`; `docs/followup_decision_record_2026-06-01.md` | Explicitly deferred for the current closeout; `SZ_LEAK_FLX` retained as the provisional engineering target | accepted |
| Final sign convention vs `UZ_SZ_EX_POSUP` | Needed for Phase 0/2 closure consistency | defer for current closeout | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`; `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`; `docs/followup_decision_record_2026-06-01.md` | Explicitly deferred for the current closeout rather than over-claimed as final authority | accepted |
| Phase 4 effective-`UZ_WC` abstraction boundary | Determines whether the current bounded effective storage-state ledger is the accepted permanent engineering model | accept milestone / defer stricter final | `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md`; `docs/investigations/phase4/phase4_effective_uz_bookkeeping_longer_horizon_2026-06-01.md` | Current bounded effective-storage abstraction accepted as the implementation-milestone stop boundary for the current closeout; promotion to stricter final policy remains intentionally deferred unless reopened later | accepted |
| Phase 5 QC tolerance/reporting boundary | Determines whether current diagnostics + plotting are sufficient for sign-off or only implementation scaffolding | accept milestone / defer stricter final | `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` | Current `1.0e-15 m^3` engineering reporting threshold and summary+timeseries+plotting package accepted as the implementation-milestone stop boundary for the current closeout; stricter final reporting policy remains intentionally deferred unless reopened later | accepted |
| Overall sign-off boundary | Determines whether lighter or stricter closure is enforced | mixed | `docs/current_status_handoff_2026-05-30.md`; `docs/final_cross_phase_closeout_matrix_2026-06-01.md`; `docs/followup_decision_record_2026-06-01.md` | Phases 0-3 remain accepted at their chosen current-boundary policies or milestones, Phases 4-5 are accepted at implementation milestone boundaries, and stricter final sign-off items remain deferred where noted | accepted |
| Final cross-phase closeout publication | Ensures the project has one durable decision record | published | `docs/final_cross_phase_closeout_matrix_2026-06-01.md` | Updated current matrix published | accepted |

## Phase 0 closeout matrix

| Item | Needed for milestone closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Stable isolated runtime probe setup established | yes | no | Established during Phase 0 runtime foundation work | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| Grid cell size / area established from API | yes | no | Required API geometry basis already documented | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| Key parameter IDs and read/write behavior established | yes | no | Runtime interface discovery completed | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| `OL_D` confirmed non-writable in current setup | yes | no | Confirmed and used to shape later phase boundaries | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| `UZ_WC` confirmed writable and layered | yes | no | Confirmed and used in Phase 2 production coupling | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| `SZ_LEAK_FLO` / `SZ_LEAK_FLX` confirmed writable | yes | no | Writable-path discovery complete | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| Final authoritative leakage target confirmed | no | yes | Current closeout explicitly defers final target authority while retaining `SZ_LEAK_FLX` as the provisional engineering target | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |
| Final sign convention locked vs `UZ_SZ_EX_POSUP` | no | yes | Current closeout explicitly defers the final sign convention together with the same shared authority question | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |

## Phase 1 closeout matrix

| Item | Needed for lighter closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Dataset-native `OLDR_IN_FLO` writes validated | yes | yes | Production route executes and was accepted for the lighter routing milestone | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| Interval-aware DAISY runoff conversion validated | yes | yes | Interval-total conversion basis already recorded | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| Coupled-cell scoping validated | yes | yes | Phase 1 mapped coupling scope accepted | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| `OLDR_S` accepted as response observable | yes | maybe | Accepted as the permanent current-boundary response observable for Phase 1 | `docs/followup_decision_record_2026-06-01.md` | accepted | closed |
| `virtual_ol_d_snapshot` accepted as bookkeeping policy | yes | maybe | Accepted as the permanent current-boundary bookkeeping policy for Phase 1 | `docs/followup_decision_record_2026-06-01.md` | accepted | closed |
| Native runoff suppression proven | no | yes | Intentionally deferred because it is not required for the adopted current-boundary Phase 1 policy | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |
| Live writable `OL_D` correction path proven | no | yes | Intentionally deferred because it is not required for the adopted current-boundary Phase 1 policy | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |
| Strict no-double-count argument closed | no | yes | Intentionally deferred with the stricter final Phase 1 boundary | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |

## Phase 2 closeout matrix

| Item | Needed for milestone closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Production matrix-percolation path executes cleanly | yes | yes | Accepted within the documented bounded persisted-response milestone | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | accepted | closed |
| Dataset-native `UZ_WC` write path validated | yes | yes | Confirmed in production and diagnostics | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | accepted | closed |
| Bounded/residual-aware bookkeeping validated | yes | yes | Accepted for current milestone boundary | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | accepted | closed |
| Persisted `UZ_WC` response demonstrated | yes | yes | Demonstrated in the accepted probe package | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | accepted | closed |
| Persisted `UZ_SZ_EX_POSUP` response demonstrated | yes | yes | Demonstrated within the accepted milestone evidence | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | accepted | closed |
| `SZ_HEAD` accepted as alternate supporting observable | yes | yes | Accepted as supporting evidence, not a blocker | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | accepted | closed |
| `OL_SZ_EX` explicitly deprioritized or accepted as non-required | yes | yes | Deprioritized within the milestone package | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | accepted | closed |
| Final authoritative leakage target confirmed | no | yes | Explicitly deferred under the adopted current-closeout authority policy | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |
| Long-horizon closure policy/report published | no | yes | Intentionally deferred because the current closeout keeps Phase 2 at the accepted milestone boundary | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |
| Late nonlinear regime interpretation accepted | no | yes | Intentionally deferred because the current closeout does not reopen stricter final Phase 2 sign-off | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |
| Schedule sensitivity addressed to required level | no | yes | Intentionally deferred because the current closeout does not reopen stricter final Phase 2 sign-off | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |

## Phase 3 closeout matrix

| Item | Needed for lighter closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Drain-specific mapped cell scope validated | yes | yes | Phase 3 updates only the mapped drained subset | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md` | accepted | closed |
| Dataset-native `SZDR_IN_FLO` routing validated | yes | yes | Production drain coupling route executes cleanly | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md` | accepted | closed |
| Native SZ drain suppression proven by probe evidence | yes | yes | `DrainCode.FixedValue = 0` established as the working suppression lever | `docs/investigations/phase3/phase3_matrix_drain_double_count_probe_2026-05-30.md` | accepted | closed |
| Default production suppression policy validated | yes | yes | Repository now defaults to the tested suppression policy with explicit opt-out only for comparisons | `docs/investigations/phase3/phase3_native_sz_drain_default_policy_2026-05-30.md` | accepted | closed |
| Dynamic WM timestep handling aligned with live `nextTimeStep()` cadence | yes | yes | Production loop now uses the upcoming WM step before each coupling write | `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md` | accepted | closed |
| `virtual_cumulative_drain_depth` bookkeeping closes to tolerance | yes | yes | 20-step closeout run closes to floating tolerance while following the variable 4-10 minute WM cadence | `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md` | accepted | closed |
| Current Phase 3 bookkeeping policy accepted for the lighter boundary | yes | yes | The lighter engineering-routing milestone bookkeeping policy is now also accepted as the permanent current-boundary policy | `docs/followup_decision_record_2026-06-01.md` | accepted | closed |
| Permanent authoritative Phase 3 storage owner accepted | no | yes | The current closeout accepts `virtual_cumulative_drain_depth` as the authoritative current-boundary bookkeeping owner; stronger in-model authority remains outside this boundary | `docs/followup_decision_record_2026-06-01.md` | accepted | closed |
| Stricter in-model drain-storage observable / owner proven if required | no | yes | Intentionally deferred unless the project later rejects the adopted current-boundary bookkeeping owner | `docs/followup_decision_record_2026-06-01.md` | deferred | deferred |

## Phase 4 closeout matrix

| Item | Needed for implementation-complete milestone? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Shared effective `UZ_WC` helper formalized | yes | yes | `src/coupling.py` now owns effective bookkeeping through `apply_effective_uz_storage_corrections(...)` | `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md` | accepted | closed |
| Effective-state diagnostics exposed in production | yes | yes | `matrix_percolation` rows now report effective theta before, requested-after, after-bounds, and provenance metadata | `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md` | accepted | closed |
| Effective UZ thickness derived from setup authority | yes | yes | Live Cernici setup resolves `10 m` from `UZSoilProfiles` and UZ discretization totals | `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md` | accepted | closed |
| Focused production smoke closes requested-vs-target-vs-storage identity to tolerance | yes | yes | One-step smoke closes to floating tolerance after the shared-helper refactor | `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md` | accepted | closed |
| Longer-horizon effective-state interpretation documented | yes | yes | The 120-step artifact is now explicitly interpreted as propagated nonlinear response exposed by cadence transitions | `docs/investigations/phase4/phase4_effective_uz_bookkeeping_longer_horizon_2026-06-01.md` | accepted | closed |
| Current effective abstraction accepted for the chosen boundary | yes | yes | Accepted as the working engineering abstraction for the implementation milestone only | `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md` | accepted | closed |
| Explicit Phase 4 acceptance criteria published | no | yes | Current milestone acceptance criteria are now recorded directly in the sign-off summary | `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md` | accepted | closed |

## Phase 5 closeout matrix

| Item | Needed for implementation-complete milestone? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Detailed diagnostics CSV production-live | yes | yes | Production runner writes per-step detailed diagnostics | `docs/investigations/phase5/phase5_coupling_summary_smoke_2026-06-01.md` | accepted | closed |
| Closure-aware summary CSV production-live | yes | yes | Automatic sibling summary CSV now written by the runner | `docs/investigations/phase5/phase5_coupling_summary_smoke_2026-06-01.md` | accepted | closed |
| Timeseries rollup production-live | yes | yes | Timestamp-and-variable rollup is now emitted as a sibling timeseries CSV | `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md` | accepted | closed |
| PNG plotting bundle production-live | yes | yes | Runner now writes volume, closure, and matrix-percolation-effective-state PNGs | `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md` | accepted | closed |
| Standalone plot regeneration from existing diagnostics CSV validated | yes | yes | `src.diagnostics_plots` can regenerate the bundle without rerunning MIKE SHE | `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md` | accepted | closed |
| One-step production plotting smoke validated | yes | yes | One-step MIKE SHE smoke wrote detailed CSV, summary CSV, timeseries CSV, and the three expected PNGs | `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md` | accepted | closed |
| Explicit QC tolerance policy accepted | no | yes | `1.0e-15 m^3` is now recorded as the working engineering reporting threshold for the implementation milestone | `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` | accepted | closed |
| Longer-horizon QC/reporting interpretation published | no | yes | Current approval remains based on smoke-level validation plus reusable reporting infrastructure, not a broader multi-step QC report | `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` | deferred | open |
| Phase 5 closeout boundary accepted | no | yes | Phase 5 is now approved for the diagnostics/reporting implementation milestone | `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` | accepted | closed |

## Deferred limitations register

| Limitation accepted as deferred? | Scope | Reason accepted | Evidence / decision note | Review trigger | Status |
| --- | --- | --- | --- | --- | --- |
| yes | Phase 0 / Phase 2 shared authority | The current closeout explicitly defers final leakage-target authority and final sign-convention lock | `docs/followup_decision_record_2026-06-01.md` | If stricter cross-phase physics authority is required | deferred |
| yes | Phase 1 stricter runoff closure | The current closeout permanently adopts the lighter current-boundary policy instead of reopening strict in-model runoff closure | `docs/followup_decision_record_2026-06-01.md` | If the project requires strict in-model runoff closure | deferred |
| yes | Phase 3 stricter drain-storage authority | The current closeout permanently adopts the lighter current-boundary bookkeeping owner instead of reopening stricter in-model authority | `docs/followup_decision_record_2026-06-01.md` | If the project rejects `virtual_cumulative_drain_depth` as permanent policy | deferred |
| yes | Phase 4 stricter final abstraction policy | Phase 4 is now milestone-approved, and the current closeout stops there; promotion of the current working abstraction to stricter final policy remains deferred | `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md` | Only if the project later reopens stricter final Phase 4 sign-off | deferred |
| yes | Phase 5 stricter final QC/reporting policy | Phase 5 is now milestone-approved, and the current closeout stops there; broader thresholds/reporting policy remain deferred | `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md` | Only if the project later reopens stricter final Phase 5 sign-off | deferred |

## Final sign-off record

- Closeout date: `2026-06-01`
- Prepared by: `GitHub Copilot`
- Reviewed by: `pending project review`
- Approved by: `current project direction recorded 2026-06-01 (earlier-phase loose ends finalized for the current boundary; Phase 4 / Phase 5 stop at accepted implementation milestones)`

### Accepted sign-off boundary by phase

- Phase 0: `milestone`
- Phase 1: `lighter milestone`
- Phase 2: `milestone`
- Phase 3: `lighter milestone`
- Phase 4: `implementation milestone`
- Phase 5: `implementation milestone`

### Final decision statement

> As of 2026-06-01, the repository is accepted at the documented milestone or implementation boundary for Phases 0 through 5. Phases 0 through 3 now also have their current-boundary loose ends finalized through the adopted follow-up decision record, while Phase 4 and Phase 5 are accepted for their implementation milestones and currently stop there for this closeout. Stricter final sign-off items remain explicitly deferred where noted rather than implicitly ignored.

## Seed evidence used

- `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`
- `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_memo_2026-05-30.md`
- `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md`
- `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md`
- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md`
- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_longer_horizon_2026-06-01.md`
- `docs/investigations/phase4/phase4_handoff_2026-06-01.md`
- `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md`
- `docs/investigations/phase5/phase5_coupling_summary_smoke_2026-06-01.md`
- `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md`
- `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md`
- `docs/investigations/phase1/phase1_permanent_policy_recommendation_2026-06-01.md`
- `docs/phase0_phase2_authority_recommendation_2026-06-01.md`
- `docs/investigations/phase3/phase3_permanent_policy_recommendation_2026-06-01.md`
- `docs/followup_decision_record_2026-06-01.md`
- `docs/post_implementation_signoff_tracker_2026-05-30.md`
