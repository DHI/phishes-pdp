# Final cross-phase closeout matrix template

_Created 2026-05-30, updated 2026-06-01 for post-implementation use._

## Purpose

Use this template **after the implementation plan is otherwise complete**.

It is meant to be copied or filled in as the final decision record that closes out Phases 0, 1, 2, 3, 4, and 5 together.

## How to use

1. Duplicate this template for the actual closeout run if you want to preserve a blank version.
2. For each row, replace placeholders with one of:
   - `accepted`
   - `deferred`
   - `open`
   - `rejected`
   - `n/a`
3. Link the exact evidence artifact(s) used for the decision.
4. Be explicit about whether the project accepted a **lighter milestone boundary** or required a **stricter final sign-off**.

## Approval summary matrix

| Phase | Milestone boundary accepted? | Stricter final sign-off required? | Current final decision | Primary evidence | Main unresolved item | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Phase 0 | `[yes/no]` | `[yes/no]` | `[accepted/deferred/open]` | `[link]` | `[text]` | `[name/role]` | `[status]` |
| Phase 1 | `[yes/no]` | `[yes/no]` | `[accepted/deferred/open]` | `[link]` | `[text]` | `[name/role]` | `[status]` |
| Phase 2 | `[yes/no]` | `[yes/no]` | `[accepted/deferred/open]` | `[link]` | `[text]` | `[name/role]` | `[status]` |
| Phase 3 | `[yes/no]` | `[yes/no]` | `[accepted/deferred/open]` | `[link]` | `[text]` | `[name/role]` | `[status]` |
| Phase 4 | `[yes/no]` | `[yes/no/tbd]` | `[accepted/deferred/open]` | `[link]` | `[text]` | `[name/role]` | `[status]` |
| Phase 5 | `[yes/no]` | `[yes/no/tbd]` | `[accepted/deferred/open]` | `[link]` | `[text]` | `[name/role]` | `[status]` |

## Cross-phase shared decisions

| Shared item | Why it matters | Decision required | Evidence | Outcome | Status |
| --- | --- | --- | --- | --- | --- |
| Leakage target authority (`SZ_LEAK_FLO` vs `SZ_LEAK_FLX`) | Shared dependency between Phase 0 and Phase 2 | `[choose target / defer / n/a]` | `[link]` | `[text]` | `[status]` |
| Final sign convention vs `UZ_SZ_EX_POSUP` | Needed for Phase 0/2 closure consistency | `[locked / deferred / n/a]` | `[link]` | `[text]` | `[status]` |
| Phase 4 effective-`UZ_WC` abstraction boundary | Determines whether the current bounded effective storage-state ledger is the accepted permanent engineering model | `[accept / defer / require stricter]` | `[link]` | `[text]` | `[status]` |
| Phase 5 QC tolerance/reporting boundary | Determines whether current diagnostics + plotting are sufficient for sign-off or only implementation scaffolding | `[accept / defer / require stricter]` | `[link]` | `[text]` | `[status]` |
| Overall sign-off boundary | Determines whether lighter or stricter closure is enforced | `[lighter / stricter / mixed]` | `[link]` | `[text]` | `[status]` |
| Final cross-phase closeout publication | Ensures the project has one durable decision record | `[published / pending]` | `[link]` | `[text]` | `[status]` |

## Phase 0 closeout matrix

| Item | Needed for milestone closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Stable isolated runtime probe setup established | yes | no | `[text]` | `[link]` | `[text]` | `[status]` |
| Grid cell size / area established from API | yes | no | `[text]` | `[link]` | `[text]` | `[status]` |
| Key parameter IDs and read/write behavior established | yes | no | `[text]` | `[link]` | `[text]` | `[status]` |
| `OL_D` confirmed non-writable in current setup | yes | no | `[text]` | `[link]` | `[text]` | `[status]` |
| `UZ_WC` confirmed writable and layered | yes | no | `[text]` | `[link]` | `[text]` | `[status]` |
| `SZ_LEAK_FLO` / `SZ_LEAK_FLX` confirmed writable | yes | no | `[text]` | `[link]` | `[text]` | `[status]` |
| Final authoritative leakage target confirmed | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Final sign convention locked vs `UZ_SZ_EX_POSUP` | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |

## Phase 1 closeout matrix

| Item | Needed for lighter closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Dataset-native `OLDR_IN_FLO` writes validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Interval-aware DAISY runoff conversion validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Coupled-cell scoping validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| `OLDR_S` accepted as response observable | yes | maybe | `[text]` | `[link]` | `[text]` | `[status]` |
| `virtual_ol_d_snapshot` accepted as bookkeeping policy | yes | maybe | `[text]` | `[link]` | `[text]` | `[status]` |
| Native runoff suppression proven | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Live writable `OL_D` correction path proven | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Strict no-double-count argument closed | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |

## Phase 2 closeout matrix

| Item | Needed for milestone closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Production matrix-percolation path executes cleanly | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Dataset-native `UZ_WC` write path validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Bounded/residual-aware bookkeeping validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Persisted `UZ_WC` response demonstrated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Persisted `UZ_SZ_EX_POSUP` response demonstrated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| `SZ_HEAD` accepted as alternate supporting observable | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| `OL_SZ_EX` explicitly deprioritized or accepted as non-required | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Final authoritative leakage target confirmed | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Long-horizon closure policy/report published | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Late nonlinear regime interpretation accepted | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Schedule sensitivity addressed to required level | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |

## Phase 3 closeout matrix

| Item | Needed for lighter closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Drain-specific mapped cell scope validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Dataset-native `SZDR_IN_FLO` routing validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Native SZ drain suppression proven by probe evidence | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Default production suppression policy validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Dynamic WM timestep handling aligned with live `nextTimeStep()` cadence | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| `virtual_cumulative_drain_depth` bookkeeping closes to tolerance | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Current Phase 3 bookkeeping policy accepted for the chosen boundary | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Permanent authoritative Phase 3 storage owner accepted | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Stricter in-model drain-storage observable / owner proven if required | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |

## Phase 4 closeout matrix

| Item | Needed for milestone closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Shared effective `UZ_WC` helper formalized in production | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Setup-derived effective UZ thickness authority validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Effective-state diagnostics exposed in production | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Focused one-step closure smoke validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Longer-horizon effective `UZ_WC` interpretation documented | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Current effective abstraction accepted for the chosen boundary | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Explicit Phase 4 acceptance criteria published | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |

## Phase 5 closeout matrix

| Item | Needed for milestone closure? | Needed for stricter final closure? | Decision/evidence notes | Evidence link | Outcome | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Detailed diagnostics CSV production path validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Summary CSV production path validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Timeseries rollup validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| PNG plot bundle generation validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Standalone plot-regeneration path validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| One-step production plotting smoke validated | yes | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Final QC tolerance policy accepted | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Longer-horizon QC/reporting interpretation published | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |
| Phase 5 closeout boundary accepted | no | yes | `[text]` | `[link]` | `[text]` | `[status]` |

## Deferred limitations register

| Limitation accepted as deferred? | Scope | Reason accepted | Evidence / decision note | Review trigger | Status |
| --- | --- | --- | --- | --- | --- |
| `[yes/no]` | `[phase or cross-phase]` | `[text]` | `[link]` | `[text]` | `[status]` |
| `[yes/no]` | `[phase or cross-phase]` | `[text]` | `[link]` | `[text]` | `[status]` |
| `[yes/no]` | `[phase or cross-phase]` | `[text]` | `[link]` | `[text]` | `[status]` |

## Final sign-off record

- Closeout date: `[YYYY-MM-DD]`
- Prepared by: `[name/role]`
- Reviewed by: `[name/role]`
- Approved by: `[name/role]`

### Accepted sign-off boundary by phase

- Phase 0: `[milestone / stricter final / other]`
- Phase 1: `[lighter milestone / stricter final / other]`
- Phase 2: `[milestone / stricter final / other]`
- Phase 3: `[lighter milestone / stricter final / other]`
- Phase 4: `[milestone / stricter final / open / other]`
- Phase 5: `[milestone / stricter final / open / other]`

### Final decision statement

> `[Write the final cross-phase decision here.]`

## Suggested seed evidence

Use these as the starting links when filling the real closeout matrix:

- `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`
- `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_memo_2026-05-30.md`
- `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md`
- `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md`
- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_2026-06-01.md`
- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_longer_horizon_2026-06-01.md`
- `docs/investigations/phase4/phase4_handoff_2026-06-01.md`
- `docs/investigations/phase5/phase5_coupling_summary_smoke_2026-06-01.md`
- `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md`
- `docs/post_implementation_signoff_tracker_2026-05-30.md`
