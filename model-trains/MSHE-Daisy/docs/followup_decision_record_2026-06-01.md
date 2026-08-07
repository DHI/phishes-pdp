# Follow-up decision record (2026-06-01)

## Purpose

This note records the adopted closeout decisions for the remaining earlier-phase loose ends after the implementation program was completed and assessed.

It is narrower than a new implementation plan.

It answers a simpler question:

> For the current repository closeout boundary, which earlier-phase follow-up recommendations are now adopted, and which stricter items remain intentionally deferred?

## Adopted decisions

### 1. Phase 1 permanent policy is accepted for the current boundary

Adopt the recommendation in:

- `docs/investigations/phase1/phase1_permanent_policy_recommendation_2026-06-01.md`
- `docs/investigations/phase1/phase1_runoff_finalization_task_2026-06-01.md`
- `docs/investigations/phase1/phase1_runoff_alternate_observables_2026-06-02.md`

Current adopted interpretation:

- `virtual_ol_d_snapshot` is accepted as the permanent Phase 1 bookkeeping ledger for the current repository boundary;
- `OLDR_S` is accepted as the practical Phase 1 response observable for that same boundary;
- the accepted Phase 1 closure remains a lighter engineering-routing policy rather than a stricter in-model overland-state correction sign-off.

June 2026 confirmation note:

- later mapped-cell preprocessed-suppression and targeted alternate-observable reruns did not change this adopted interpretation;
- no targeted alternate observable improved on `OLDR_S` or separated the tested suppression variants;
- the adopted lighter Phase 1 policy therefore remains the correct current-boundary reading.

### 2. Shared Phase 0 / Phase 2 authority remains explicitly deferred

Adopt the recommendation in:

- `docs/phase0_phase2_authority_recommendation_2026-06-01.md`

Current adopted interpretation:

- do **not** force final authoritative closure of `SZ_LEAK_FLO` vs `SZ_LEAK_FLX` in the current closeout;
- retain `SZ_LEAK_FLX` as the working provisional engineering target for the accepted implementation boundary;
- keep the final sign convention against `UZ_SZ_EX_POSUP` explicitly deferred;
- treat stronger vendor-authoritative target/sign confirmation as out of scope unless stricter final physics-authority sign-off is reopened later.

### 3. Phase 2 stops at the currently accepted milestone boundary

Current adopted interpretation:

- the bounded persisted-response implementation milestone is sufficient for the present repository closeout;
- stricter final Phase 2 physics-authority sign-off is **not** reopened now;
- the longer-horizon closure-policy question, late-regime physical interpretation question, and formal schedule-sensitivity question remain intentionally deferred unless the project later chooses a stricter final Phase 2 boundary.

Primary basis:

- `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_memo_2026-05-30.md`
- `docs/investigations/phase4/phase4_effective_uz_bookkeeping_longer_horizon_2026-06-01.md`
- `docs/investigations/phase5/phase5_diagnostics_plotting_2026-06-01.md`

### 4. Phase 3 permanent policy is accepted for the current boundary

Adopt the recommendation in:

- `docs/investigations/phase3/phase3_permanent_policy_recommendation_2026-06-01.md`

Current adopted interpretation:

- `virtual_cumulative_drain_depth` is accepted as the permanent Phase 3 bookkeeping ledger for the current repository boundary;
- derived-setup native drain suppression through `DrainCode.FixedValue = 0` remains the standard production execution mode when Phase 3 coupling is enabled;
- the accepted Phase 3 closure remains a routing/bookkeeping boundary rather than a stricter in-model drain-storage authority claim.

### 5. Phase 4 and Phase 5 remain at their accepted implementation milestones

Retain the already recorded closeout choice:

- Phase 4 stops at the accepted effective `UZ_WC` implementation milestone;
- Phase 5 stops at the accepted diagnostics/reporting implementation milestone;
- stricter final Phase 4 / Phase 5 policy work remains intentionally deferred unless those phases are later reopened.

## Net effect on the closeout package

With these decisions recorded, the current closeout package should be interpreted as follows:

- the implementation mission is complete for the accepted project boundary;
- the remaining earlier-phase loose ends are no longer active decision placeholders;
- they are now either:
  - adopted repository policy choices, or
  - explicitly deferred stricter-final-signoff items.

That means the repository is no longer in a “milestone accepted but several earlier-phase policy choices still unresolved” state.

It is now in a “closeout policy choices recorded; stricter items deferred by decision” state.

## What remains intentionally deferred

The following items remain outside the current closeout boundary unless the project later reopens stricter final sign-off:

- final authoritative closure of `SZ_LEAK_FLO` vs `SZ_LEAK_FLX`;
- final sign-convention lock against `UZ_SZ_EX_POSUP`;
- stricter in-model Phase 1 runoff closure;
- stricter final Phase 2 physics-authority closure;
- stricter in-model Phase 3 drain-storage authority;
- stricter final Phase 4 abstraction policy;
- stricter final Phase 5 QC/reporting policy.

## Stakeholder-ready summary

> As of 2026-06-01, the remaining earlier-phase loose ends have been finalized for the current repository closeout boundary. Phase 1 permanently accepts `virtual_ol_d_snapshot` + `OLDR_S` as the current closure policy, and later June 2026 suppression / alternate-observable reruns did not change that choice. The shared Phase 0 / Phase 2 leakage-target authority question remains explicitly deferred with `SZ_LEAK_FLX` retained as the provisional engineering target, Phase 2 stops at the already accepted bounded persisted-response milestone, and Phase 3 permanently accepts `virtual_cumulative_drain_depth` plus the default native-drain suppression policy as the current bookkeeping boundary. Stricter final-signoff items remain intentionally deferred unless the project later reopens them.
