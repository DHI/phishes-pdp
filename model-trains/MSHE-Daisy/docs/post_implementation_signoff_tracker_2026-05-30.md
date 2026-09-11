# Post-implementation sign-off tracker (2026-05-30)

## Purpose

Use this tracker **after the implementation plan is otherwise finished**.

It combines the remaining sign-off and closeout items from the Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5 packages into one place so the final follow-up work is visible without rereading every investigation note.

## Current status at a glance

| Phase | Approved now | Not yet approved |
| --- | --- | --- |
| Phase 0 | Runtime-foundation and API-discovery milestone | Stricter final leakage-target authority sign-off (intentionally deferred under the adopted current-closeout policy) |
| Phase 1 | Lighter runoff engineering-routing milestone | Stricter final in-model runoff closeout sign-off (intentionally deferred outside the adopted Phase 1 current-boundary policy) |
| Phase 2 | Bounded persisted-response implementation milestone | Stricter final Phase 2 physics-authority sign-off (intentionally deferred outside the adopted Phase 2 current-boundary policy) |
| Phase 3 | Lighter matrix-drain engineering-routing milestone | Stricter final in-model drain-storage closeout sign-off (intentionally deferred outside the adopted Phase 3 current-boundary policy) |
| Phase 4 | Effective unsaturated-zone bookkeeping implementation milestone | Stricter final abstraction / physics-authority sign-off (intentionally deferred under the current closeout choice) |
| Phase 5 | Diagnostics and reporting implementation milestone | Stricter final QC / reporting sign-off (intentionally deferred under the current closeout choice) |

## Main source summaries

- `docs/signoff_and_followup_index_2026-05-30.md`
- `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`
- `docs/investigations/phase1/phase1_signoff_summary_2026-05-30.md`
- `docs/investigations/phase1/phase1_runoff_finalization_task_2026-06-01.md`
- `docs/investigations/phase1/phase1_runoff_alternate_observables_2026-06-02.md`
- `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_memo_2026-05-30.md`
- `docs/investigations/phase3/phase3_signoff_summary_2026-05-30.md`
- `docs/investigations/phase3/phase3_matrix_drain_closeout_diagnostic_2026-05-30.md`
- `docs/investigations/phase1/phase1_permanent_policy_recommendation_2026-06-01.md`
- `docs/investigations/phase3/phase3_permanent_policy_recommendation_2026-06-01.md`
- `docs/phase0_phase2_authority_recommendation_2026-06-01.md`
- `docs/followup_decision_record_2026-06-01.md`
- `docs/investigations/phase4/phase4_handoff_2026-06-01.md`
- `docs/investigations/phase4/phase4_signoff_summary_2026-06-01.md`
- `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md`
- `docs/investigations/phase5/phase5_signoff_summary_2026-06-01.md`

## Recommended order after implementation is complete

### 1. Lock the project’s sign-off policy explicitly

Before doing extra technical work, decide whether the project intends to finish under the already documented **lighter milestone boundaries** or whether it requires **stricter final sign-off** for one or more phases.

This choice changes the size of the remaining work dramatically.

Current recorded choice for this closeout: stop at the accepted Phase 4 / Phase 5 implementation milestones and leave any stricter final Phase 4 / Phase 5 policy work out of scope unless those phases are later reopened.

### 2. Shared Phase 0 / Phase 2 authority remains deferred under the adopted closeout policy

The current closeout does **not** force final authoritative closure of `SZ_LEAK_FLO` vs `SZ_LEAK_FLX`.

The adopted current-boundary decision is:

- keep `SZ_LEAK_FLX` as the working provisional engineering target;
- keep the present implementation sign convention unchanged for the accepted boundary;
- defer final target-authority and final sign-convention lock unless stricter final physics-authority sign-off is later reopened.

If the project later reopens stricter final authority, the preferred ways to close it remain:

1. DHI documentation that explicitly defines the intended correction target, or
2. a runtime setup where the injected leakage target measurably affects accessible outputs strongly enough to distinguish authority.

Current adopted decision record for the present closeout:

- `docs/followup_decision_record_2026-06-01.md`

### 3. Phase 1 current-boundary policy is now adopted

The current closeout now adopts the lighter documented Phase 1 boundary as the permanent repository policy for the present project boundary.

That means the accepted Phase 1 policy is:

- explicitly accept `virtual_ol_d_snapshot` as the bookkeeping store;
- explicitly accept `OLDR_S` as the response observable;
- explicitly record that native runoff suppression remains a documented deferred limitation.

June 2026 confirmation update:

- later mapped-cell preprocessed-suppression and targeted alternate-observable reruns did not change this adopted policy;
- `OLDR_S` remained the only reproducibly responding observable in the checked Phase 1 probe family;
- `OL_D` remained flat and no targeted alternate observable provided a better or delayed discriminator.

Current adopted decision record for the present closeout:

- `docs/followup_decision_record_2026-06-01.md`

If the project later rejects that adopted boundary and reopens stricter final Phase 1 sign-off, then the following would still be required:

- native MIKE SHE runoff is disabled or zeroed for the coupled cells;
- a live writable overland-storage correction path exists, or an equally strong replacement is accepted;
- strict no-double-count closure in the live setup is proven.

### 4. Phase 2 currently stops at the accepted implementation milestone

The current closeout now keeps Phase 2 at the already accepted bounded persisted-response implementation milestone.

That means the current boundary accepts all of the following for the present closeout:

- accept `SZ_LEAK_FLX` as a provisional engineering target pending final authority;
- accept the bounded/effective `UZ_WC` representation as an engineering bookkeeping model;
- accept the late nonlinear regime and schedule sensitivity as deferred interpretation topics.

If the project later reopens stricter final Phase 2 sign-off, the remaining follow-up is:

- authoritative target confirmation (shared with Phase 0);
- a final long-horizon closure policy and report;
- fuller interpretation of the late nonlinear regime;
- any required proof that the response is not materially dependent on the active WM timestep schedule.

### 5. Phase 3 current-boundary policy is now adopted

The current closeout now adopts the lighter documented Phase 3 boundary as the permanent repository policy for the present project boundary.

That means the accepted Phase 3 policy is:

- explicitly accept `virtual_cumulative_drain_depth` as the authoritative Phase 3 bookkeeping store;
- explicitly accept the default `DrainCode.FixedValue = 0` derived-setup suppression policy as the repository’s standard Phase 3 execution mode;
- explicitly record that the current approval is an engineering-routing / bookkeeping milestone rather than a stricter in-model drain-storage closeout.

Current adopted decision record for the present closeout:

- `docs/followup_decision_record_2026-06-01.md`

If the project later rejects that adopted boundary and reopens stricter final Phase 3 sign-off, then the following would still be required:

- an accepted final storage owner for drain extraction exists inside the final sign-off boundary;
- any stricter required storage observable or longer-horizon closeout report is published;
- and any stronger in-model drain-storage acceptance test required by the project is explicitly passed.

### 6. Phase 4 currently stops at the approved implementation milestone

The repository now already has:

- a shared owner for effective `UZ_WC` bookkeeping,
- setup-derived authority for the live `10 m` effective thickness,
- a focused helper-preservation smoke,
- and a longer-horizon interpretation note.

For the current closeout, the repository stops at that approved milestone boundary.

That means the Phase 4 stricter-final items are not part of the active finish path right now.

Reopen them only if the project later decides it wants stricter final Phase 4 sign-off beyond the current milestone.

If that happens, the main remaining Phase 4 work is still policy rather than missing plumbing:

- decide whether the current bounded effective-storage abstraction should stay a milestone-only engineering model or be promoted to the permanent final policy;
- publish any stricter long-horizon / closure criteria required beyond the new milestone boundary.

### 7. Phase 5 currently stops at the approved implementation milestone

The repository now already has:

- detailed diagnostics CSVs,
- automatic summary CSVs,
- derived timeseries CSVs,
- reusable PNG plot generation,
- and a validated one-step production plotting smoke.

For the current closeout, the repository stops at that approved milestone boundary.

That means the Phase 5 stricter-final items are not part of the active finish path right now.

Reopen them only if the project later decides it wants stricter final Phase 5 sign-off beyond the current milestone.

If that happens, the main remaining Phase 5 work is still the policy/reporting layer:

- decide whether the current `1.0e-15 m^3` reporting threshold is only a milestone engineering threshold or the final project-wide QC threshold;
- publish the longer-horizon multi-step QC interpretation/report the project wants beyond the new milestone boundary;
- decide whether any additional domain-level reporting artifacts are required for final Phase 5 sign-off.

### 8. Publish a final cross-phase closeout matrix

After the policy decisions and any remaining strict follow-up work are complete, publish one final matrix that records:

- which milestone boundary was accepted for each phase;
- which caveats were explicitly accepted;
- which technical items were closed;
- which limitations remain intentionally deferred.

Template available:

- `docs/final_cross_phase_closeout_matrix_template.md`

Current published status matrix:

- `docs/final_cross_phase_closeout_matrix_2026-06-01.md`

## Action matrix

### Phase 0 follow-up items

#### Only needed if stricter final sign-off is later reopened

- [ ] Confirm whether `SZ_LEAK_FLO` or `SZ_LEAK_FLX` is the final authoritative leakage target.
- [ ] Lock the final sign convention against `UZ_SZ_EX_POSUP`.

#### Safe to defer if milestone boundary is accepted

- [ ] Any stronger vendor-authority proof beyond the current runtime-foundation milestone.

### Phase 1 follow-up items

#### Required only if stricter final in-model sign-off is required

- [ ] Prove native MIKE SHE runoff suppression in the coupled cells.
- [ ] Demonstrate a live writable overland-storage correction path, or explicitly replace that requirement with an accepted policy.
- [ ] Close the stricter no-double-count argument in the live setup.
- [ ] Decide whether a final acceptance observable must live in `OL_D` rather than `OLDR_S`.

#### Adopted for the current closeout boundary

- [x] `virtual_ol_d_snapshot` + `OLDR_S` is accepted as the permanent Phase 1 current-boundary policy.
- [x] June 2026 confirmatory reruns did not change the adopted Phase 1 current-boundary policy.

### Phase 2 follow-up items

#### Only needed if stricter final Phase 2 sign-off is later reopened

- [ ] Close the shared authoritative leakage-target question.
- [ ] Publish the final long-horizon closure policy/report.
- [ ] Decide whether the late nonlinear regime requires a stronger physical interpretation for sign-off.
- [ ] Decide whether schedule sensitivity must be tested more formally.

#### Deferred under the adopted Phase 2 current-boundary policy

- [ ] Stronger final-physics interpretation of the `103` / `104` crest.
- [ ] Broader schedule-sensitivity characterization beyond the current documented cadence-transition finding.

### Phase 3 follow-up items

#### Required only if stricter final in-model sign-off is required

- [ ] Decide whether `virtual_cumulative_drain_depth` is accepted as the permanent Phase 3 storage owner.
- [ ] If not, replace it with an accepted stronger in-model storage owner or closeout observable.
- [ ] Publish any stricter longer-horizon or in-model drain-storage closeout report required by the project.

#### Adopted for the current closeout boundary

- [x] `virtual_cumulative_drain_depth` is accepted as the permanent Phase 3 current-boundary bookkeeping policy.

### Phase 4 follow-up items

#### Only needed if Phase 4 is later reopened for stricter final sign-off

- [ ] Decide whether the current bounded effective `UZ_WC` representation is the accepted permanent engineering abstraction.
- [ ] Publish any stricter final long-horizon / closure criteria required beyond the current milestone boundary.

#### Deferred under the current chosen Phase 4 stop boundary

- [ ] Any stronger physical interpretation work beyond the current cadence-transition / propagated-response explanation.

### Phase 5 follow-up items

#### Only needed if Phase 5 is later reopened for stricter final sign-off

- [ ] Decide whether `1.0e-15 m^3` remains the final authoritative QC threshold or is replaced.
- [ ] Publish the longer-horizon multi-step QC interpretation/report required by the project.
- [ ] Decide whether any additional domain-level reporting artifacts are required for final Phase 5 sign-off.

#### Deferred under the current chosen Phase 5 stop boundary

- [ ] Broader reporting polish beyond the current validated CSV + summary + timeseries + plot bundle.

## Smallest practical finish path

If the project is satisfied with the currently documented milestone boundaries, the shortest path to overall post-implementation closure is:

1. use `docs/followup_decision_record_2026-06-01.md` as the adopted earlier-phase closeout addendum;
2. keep the stricter final Phase 4 / Phase 5 follow-up items deferred under the currently chosen implementation-milestone stop boundary;
3. close the shared target-authority / sign-convention item only if the project wants to go beyond the adopted deferral boundary now;
4. use the published matrix as the current decision record unless a stricter final pass is later reopened.

## Stricter finish path

If the project requires stricter final sign-off across all phases, the likely critical path is:

1. close the shared Phase 0 / Phase 2 leakage-target authority question;
2. prove or replace the missing strict Phase 1 in-model runoff conditions;
3. finish the stricter Phase 2 long-horizon closure and interpretation work;
4. prove or replace the missing strict Phase 3 in-model drain-storage conditions;
5. publish explicit Phase 4 acceptance criteria and final abstraction policy;
6. publish explicit Phase 5 thresholds and broader QC closeout reporting;
7. then publish the final closeout matrix.

## Bottom line

The implementation plan is no longer blocked by missing low-level runtime feasibility.

The remaining post-implementation work is mostly about **which sign-off boundary the project wants to enforce**:

- lighter documented milestone closure, or
- stricter final in-model / physics-authority closure.

This tracker is the place to resolve that cleanly once implementation is otherwise complete.

If you need the single navigation entry point into the whole package, start with:

- `docs/signoff_and_followup_index_2026-05-30.md`
