# Final cross-phase closeout matrix (2026-05-30)

_Current published decision record for the implementation package as of 2026-05-30._

## Purpose

This is the current cross-phase status matrix for Phases 0, 1, 2, and 3.

It is intentionally honest about what is already accepted at the documented milestone boundary and what is still deferred for stricter final sign-off.

## Approval summary matrix

| Phase | Milestone boundary accepted? | Stricter final sign-off required? | Current final decision | Primary evidence | Main unresolved item | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Phase 0 | yes | no | accepted | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | Final authoritative leakage target remains deferred | project | published |
| Phase 1 | yes | no | accepted | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | Permanent strict in-model runoff closeout policy remains deferred | project | published |
| Phase 2 | yes | no | accepted | `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | Final leakage-target authority and stricter long-horizon interpretation remain deferred | project | published |
| Phase 3 | yes | no | accepted | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md` | Permanent authoritative drain-storage owner remains deferred | project | published |

## Cross-phase shared decisions

| Shared item | Why it matters | Decision required | Evidence | Outcome | Status |
| --- | --- | --- | --- | --- | --- |
| Leakage target authority (`SZ_LEAK_FLO` vs `SZ_LEAK_FLX`) | Shared dependency between Phase 0 and Phase 2 | defer | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`; `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | Deferred outside the currently accepted milestone boundary | open |
| Final sign convention vs `UZ_SZ_EX_POSUP` | Needed for Phase 0/2 closure consistency | defer | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`; `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md` | Deferred outside the currently accepted milestone boundary | open |
| Overall sign-off boundary | Determines whether lighter or stricter closure is enforced | lighter | `docs/post_implementation_signoff_tracker_2026-05-30.md` | Current package is accepted at the documented milestone boundary for all implemented phases | accepted |
| Final cross-phase closeout publication | Ensures the project has one durable decision record | published | `docs/final_cross_phase_closeout_matrix_2026-05-30.md` | Current matrix published | accepted |

## Phase 0 closeout matrix

| Item | Needed for milestone closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Stable isolated runtime probe setup established | yes | no | Established during Phase 0 runtime foundation work | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| Grid cell size / area established from API | yes | no | Required API geometry basis already documented | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| Key parameter IDs and read/write behavior established | yes | no | Runtime interface discovery completed | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| `OL_D` confirmed non-writable in current setup | yes | no | Confirmed and used to shape later phase boundaries | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| `UZ_WC` confirmed writable and layered | yes | no | Confirmed and used in Phase 2 production coupling | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| `SZ_LEAK_FLO` / `SZ_LEAK_FLX` confirmed writable | yes | no | Writable-path discovery complete | `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md` | accepted | closed |
| Final authoritative leakage target confirmed | no | yes | Still deferred because milestone closure does not require choosing between the two leakage targets yet | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |
| Final sign convention locked vs `UZ_SZ_EX_POSUP` | no | yes | Still deferred with the same shared Phase 0 / Phase 2 authority question | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |

## Phase 1 closeout matrix

| Item | Needed for lighter closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Dataset-native `OLDR_IN_FLO` writes validated | yes | yes | Production route executes and was accepted for the lighter routing milestone | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| Interval-aware DAISY runoff conversion validated | yes | yes | Interval-total conversion basis already recorded | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| Coupled-cell scoping validated | yes | yes | Phase 1 mapped coupling scope accepted | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| `OLDR_S` accepted as response observable | yes | maybe | Accepted for the lighter milestone boundary | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| `virtual_ol_d_snapshot` accepted as bookkeeping policy | yes | maybe | Accepted for the lighter milestone boundary only | `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md` | accepted | closed |
| Native runoff suppression proven | no | yes | Not required for the accepted lighter boundary | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |
| Live writable `OL_D` correction path proven | no | yes | Not required for the accepted lighter boundary | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |
| Strict no-double-count argument closed | no | yes | Deferred with the stricter Phase 1 boundary | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |

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
| Final authoritative leakage target confirmed | no | yes | Deferred with the shared Phase 0 / Phase 2 authority question | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |
| Long-horizon closure policy/report published | no | yes | Further strict closeout work remains optional, not current blocker | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |
| Late nonlinear regime interpretation accepted | no | yes | Deferred outside accepted milestone boundary | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |
| Schedule sensitivity addressed to required level | no | yes | Broader schedule-sensitivity characterization remains deferred | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |

## Phase 3 closeout matrix

| Item | Needed for lighter closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Drain-specific mapped cell scope validated | yes | yes | Phase 3 updates only the mapped drained subset | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md` | accepted | closed |
| Dataset-native `SZDR_IN_FLO` routing validated | yes | yes | Production drain coupling route executes cleanly | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md` | accepted | closed |
| Native SZ drain suppression proven by probe evidence | yes | yes | `DrainCode.FixedValue = 0` established as the working suppression lever | `docs/investigations/phase3/phase3_matrix_drain_double_count_probe_2026-05-30.md` | accepted | closed |
| Default production suppression policy validated | yes | yes | Repository now defaults to the tested suppression policy with explicit opt-out only for comparisons | `docs/investigations/phase3/phase3_native_sz_drain_default_policy_2026-05-30.md` | accepted | closed |
| Dynamic WM timestep handling aligned with live `nextTimeStep()` cadence | yes | yes | Production loop now uses the upcoming WM step before each coupling write | `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md` | accepted | closed |
| `virtual_cumulative_drain_depth` bookkeeping closes to tolerance | yes | yes | 20-step closeout run closes to floating tolerance while following the variable 4–10 minute WM cadence | `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md` | accepted | closed |
| Current Phase 3 bookkeeping policy accepted for the lighter boundary | yes | yes | The current lighter engineering-routing milestone explicitly uses `virtual_cumulative_drain_depth` as its bookkeeping ledger | `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md` | accepted | closed |
| Permanent authoritative Phase 3 storage owner accepted | no | yes | Deferred pending explicit project choice on whether the external ledger is the final authority or must be replaced by a stronger in-model owner | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |
| Stricter in-model drain-storage observable / owner proven if required | no | yes | Still deferred unless the project rejects the current lighter bookkeeping boundary | `docs/post_implementation_signoff_tracker_2026-05-30.md` | deferred | open |

## Deferred limitations register

| Limitation accepted as deferred? | Scope | Reason accepted | Evidence / decision note | Review trigger | Status |
| --- | --- | --- | --- | --- | --- |
| yes | Phase 0 / Phase 2 shared authority | The current milestone package does not require final leakage-target authority yet | `docs/post_implementation_signoff_tracker_2026-05-30.md` | If stricter cross-phase physics authority is required | deferred |
| yes | Phase 1 stricter runoff closure | Lighter routing milestone already accepted | `docs/post_implementation_signoff_tracker_2026-05-30.md` | If the project requires strict in-model runoff closure | deferred |
| yes | Phase 3 stricter drain-storage authority | Lighter routing/bookkeeping milestone already accepted | `docs/post_implementation_signoff_tracker_2026-05-30.md` | If the project rejects `virtual_cumulative_drain_depth` as permanent policy | deferred |

## Final sign-off record

- Closeout date: `2026-05-30`
- Prepared by: `GitHub Copilot`
- Reviewed by: `pending project review`
- Approved by: `pending project decision`

### Accepted sign-off boundary by phase

- Phase 0: `milestone`
- Phase 1: `lighter milestone`
- Phase 2: `milestone`
- Phase 3: `lighter milestone`

### Final decision statement

> The current implementation package is accepted at the documented milestone boundary for Phases 0 through 3. Cross-phase stricter final sign-off items remain explicitly deferred rather than implicitly ignored.

## Seed evidence used

- `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`
- `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_memo_2026-05-30.md`
- `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md`
- `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md`
- `docs/post_implementation_signoff_tracker_2026-05-30.md`
