# Shared Phase 0 / Phase 2 authority recommendation (2026-06-01)

## Recommended decision

**Do not force final authoritative closure of `SZ_LEAK_FLO` vs `SZ_LEAK_FLX` for the current repository closeout boundary.**

**Retain `SZ_LEAK_FLX` as the working provisional engineering target, keep the current implementation sign convention unchanged, and explicitly defer vendor-authoritative target confirmation and final sign-convention lock unless the project later reopens stricter final physics-authority sign-off.**

That recommendation is a deliberate choice to avoid over-claiming authority that the current evidence does not actually provide.

## Why this is the right follow-up decision now

The evidence base supports a coherent engineering implementation choice, but not a stronger final authority claim:

- Phase 0 established that both `SZ_LEAK_FLO` and `SZ_LEAK_FLX` are writable and that `UZ_SZ_EX_POSUP` is the practical native comparison/output term;
- the follow-up runtime probes remained inconclusive for discriminating final target authority because accessible outputs did not respond strongly enough in the tested setups;
- Phase 2 implementation and milestone sign-off already proceeded coherently with `SZ_LEAK_FLX` as the working engineering target;
- `SZ_LEAK_FLX` remains the most coherent present implementation choice because it matches DAISY percolation and `UZ_SZ_EX_POSUP` flux-style units;
- forcing a final authority declaration now would mostly be paperwork cosplay unless supported by stronger DHI documentation or a more responsive runtime setup.

## Recommended shared policy boundary

For the current closeout package, record the following shared Phase 0 / Phase 2 policy:

1. keep `SZ_LEAK_FLX` as the provisional engineering target used by the current implementation;
2. keep the current implementation sign convention unchanged for the accepted milestone boundary;
3. do **not** elevate that working convention into a vendor-authoritative final physics claim;
4. treat stronger target-authority confirmation and final sign-convention lock as deferred unless stricter final Phase 0 / Phase 2 sign-off is later reopened.

## What this recommendation does **not** claim

This recommendation does **not** claim that:

- DHI documentation has confirmed the final authoritative target;
- the current runtime probes proved final authority through solver-visible response;
- the present sign convention has been locked as the permanent final physical interpretation.

Instead, it recommends explicitly preserving the current project boundary: coherent engineering implementation, honest deferred authority.

## Main evidence cited

- `docs/investigations/phase0/phase0_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_summary_2026-05-30.md`
- `docs/investigations/phase2/phase2_signoff_memo_2026-05-30.md`
- `docs/post_implementation_signoff_tracker_2026-05-30.md`
- `docs/final_cross_phase_closeout_matrix_2026-06-01.md`

## Practical closeout implication

If the project accepts this recommendation, the shared Phase 0 / Phase 2 authority question stops being an active blocker for the current closeout package.

The issue remains documented, but it becomes an intentionally deferred stricter-final-signoff item rather than a missing implementation prerequisite.

## PR / stakeholder-ready summary

> Recommended follow-up decision: do not force final target-authority closure for the shared Phase 0 / Phase 2 `SZ_LEAK_FLO` vs `SZ_LEAK_FLX` question in the current repository closeout. Keep `SZ_LEAK_FLX` as the working provisional engineering target and preserve the current implementation sign convention, but do not overstate either as vendor-authoritative final physics policy. This keeps the present implementation boundary honest: the engineering path is coherent and accepted, while stronger authority confirmation remains a deferred item only if the project later reopens stricter final sign-off.
