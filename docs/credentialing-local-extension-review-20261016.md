# Review Report: Credentialing local measurement extensions

## Summary

The reviewed local contracts advance the original measurement requirements; final hosted verification and source, privacy, platform and human acceptance remain separate gates.

## Scope

Reviewed delivered first-submission, renewal, condition/supervision, experience and temporary-episode/review semantics against the original measure dictionary and approved local designs. The most recent source checkpoints are temporary implementation `c9c96f2` with boundary regressions `f03ec3e`, and experience repair source `a191ecd`, integrated as `1d7ec9c` with review receipt `cc30ae4`. This is a component review, not completion of the full credentialing track or an audit of every file in the integration PR.

## Verification Checks

- [x] **Plan Compliance**: Partial — explicit source observations, deadlines, denominators, missingness, replay and privacy controls are implemented locally. Real mappings, baseline, retrospective/silent-mode evidence and human acceptance remain open.
- [x] **Style Compliance**: Pass — scoped Ruff and Conductor validation passed after integration; owner receipts also record typing, formatting and security checks.
- [x] **New Tests**: Yes — arithmetic, reconciliation, grant conflicts, missingness, censoring, time boundaries, schema parity, mutation, privacy and subclass regressions.
- [x] **Test Coverage**: Partial evidence — owner receipts record isolated component coverage; these are not a fresh full-repository coverage result.
- [ ] **Test Results**: Final combined verification pending — the root's ordinary temporary-reporting run passed 98 tests. Experience owner and independent reviewer passed 51 tests. The root's original impossible-rate reproducer is rejected after repair. The later combined local run ended in a native access violation and is inconclusive; it must not be recorded as a pass.

## Findings

### Medium — Adapter subclasses could bypass retained-state validation (fixed)

`dataclasses.replace` preserves the runtime class. An experience snapshot subclass overriding `__post_init__` could skip count reconciliation: the coordinator reproduced an unsuppressed response rate of 1.25 and negative nonresponse count using synthetic data. The temporary component's independent reviewer found the same validation family in its report boundaries before final integration.

The experience repair rejects unsupported subclasses at snapshot, cohort, instrument and nested question/count boundaries before replacement. The temporary contracts reconstruct declared concrete snapshot/scope/policy types and guard grant types. Wire schemas remain unchanged. Direct and nested regression cases cover export, merge, reporting and instrument fingerprinting. The coordinator reran the original experience reproducer against the integrated repair and observed the expected contract rejection.

## Local execution limitation

During the final combined ordinary pytest attempt, Windows reported a native access violation in `abc.__subclasscheck__`, reached from the existing credentialing projection validation during a stage-time property test. No test assertion established a new source defect or the cause of that native failure. This is additional unresolved local runtime evidence, not proof of a particular hardware cause.

The coordinator stopped the test sequence without retries or configuration changes. Tracked files still matched the reviewed commit; Git connectivity, scoped lint and Conductor checks passed. A sanitized private failure receipt preserves the checkpoint and failed command. BIOS, affinity, dependencies and the ordinary pytest configuration were unchanged. Publish the exact completed revision and use its standard hosted CI result for integration acceptance; do not erase the local failure when that independent run succeeds.

## Remaining scope

The source owner must supply approved episode, obligation, case/cycle, instrument, cohort, deadline, completion and coverage definitions. Local aggregates do not establish clinical competence, satisfaction of a condition, unauthorised practice, causal benefit or operational effectiveness. No live source acquisition, source write or production adapter is introduced by these components. Preserve the original track's baseline, policy, privacy, deployment and human checkpoints.
