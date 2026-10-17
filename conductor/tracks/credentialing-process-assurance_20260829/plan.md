# Implementation plan

Current handover (17 October 2026): see
[synthetic acceptance, original-outcome audit and real-source checklist](../../../docs/credentialing-acceptance-handover.md).
Historical receipts below retain their original verification scope. Local
measurement contracts do not close remaining aggregation/decomposition work,
source/authority/instrument acceptance, pilot/manual gates or causal capacity.

## Repository tranche

### Authorised local reporting follow-up — 17 October 2026

- [x] Add explicit case-demand/pathway mix, missing classifications and case denominators.
- [x] Add correction/further-information/deferral/exception and overlapping reason case rates.
- [x] Add source-observed queue/active/unknown calendar-state partition with reconciliation.
- [x] Add case-scoped observed administrative variants and whole-release joint-cell protection.

See [local reporting semantics and executable example](../../../docs/credentialing-local-reporting.md).
These are local synthetic capabilities. Stage-specific professional/committee
worker effort, true model fitness, causal capacity, approved source/authority
mapping, live integration and manual track acceptance remain open. Calendar active
time is not worker effort. This update does not complete the original track.

- [x] Add a generic credentialing ontology.
- [x] Add a strict privacy-minimised event projection schema.
- [x] Add the credentialing process-assurance design note.
- [x] Genericise the active feasibility baseline.
- [x] Add a permissive licence and process-assurance review agent.
- [x] Register this Conductor track.
- [x] Add strict projection validation and normalization tests.
- [x] Add explicit credentialing ontology-registry validation tests.
- [x] Add synthetic valid projection and invalid/deviation fixtures in tests.
- [x] Add deep raw-field rejection, replay, duplicate and watermark tests.
- [x] Add credentialing-specific tombstone and minimized-dead-letter tests.
- [x] Add routine-renewal conformance model and metric dictionary.
- [x] Add small-cohort suppression and role-scoped semantic projection tests.
- [x] Add BPMN and rendered process diagrams.

Repository tranche implemented on 2026-10-14 in
`src/careops_process/credentialing_assurance.py` and
`tests/test_credentialing_assurance.py`, alongside the existing projection.
The published schema now accepts nullable qualifiers emitted by the runtime;
the ontology registers the existing duration bucket. This records synthetic
repository evidence, not live tenant execution or governance approval.

### Verification evidence (2026-10-14)

- 52 scoped credentialing/ontology tests pass, including 27 new assurance tests.
- Full shared-checkout suite: 352 tests pass, 91.37% overall coverage; the new
  assurance module has 100% statement and branch coverage at this snapshot.
- Scoped Ruff formatting/lint and strict Pyright pass.
- Draft 2020-12 schema validation and runtime round trips pass; observed
  confidence below one is rejected by the published schema.
- Non-executable BPMN stage/reference integrity and SVG XML checks pass;
  the PNG rendering was visually inspected.
- Credentialing Bandit and scoped secret scan pass. Dependency audit reports
  no known vulnerabilities (the unpublished local package is not auditable).
- Offline Zizmor reports no findings, with one suppressed finding.
- Independent read-only scoped review found no actionable issues.
- Whole-checkout Conductor, lint and typing checks saw concurrent unrelated
  hardening-track index/status and unused-import failures. Those files belong
  to their respective track agents; this tranche does not claim global readiness.

### Manual checkpoint and integration limits

Follow-up audit on 2026-10-14 identified unrestricted string values in allowed
qualifier/source fields. Runtime and published schema now require bounded
code-shaped tokens. Sixteen regression tests reject narrative and email values;
68 scoped credentialing/ontology tests pass. Syntax alone cannot prove that
identifiers or codes are non-identifying; approved vocabularies and source
pseudonymisation remain an external gate.

- [ ] Maintainer verifies the repository tranche using
  `docs/credentialing-renewal-reference.md` and accepts the generic-model limits.
- [ ] Integration owner reruns all required checks on the final shared revision.
- [ ] Resolve reproduced native-runtime failures and demonstrate repeatability.

Runtime follow-up (2026-10-14): ten fresh deletion/replay test processes yielded
eight passes, one access violation and one Hypothesis FlakyFailure. A minimal
nested Pydantic serialization probe also fails without repository/test imports
or deepcopy. Disposable Pydantic 2.12.5, Python 3.13.15 and Python 3.14.7 comparisons
still failed; no runtime fix is established and product dependencies are unchanged.
Repository-wide lint/format, offline PowerShell tests, Bandit, dependency audit,
offline Zizmor and scoped review-commit Gitleaks checks pass with limitations
recorded in `review.md`. The earlier green full-suite result is not superseding
the reproduced failures.

A second monitored standalone run produced a native full dump matched to PID and
creation time; exception-thread metadata matches faulthandler. It records a core
module read access violation during `model_dump`. Offline metadata inspection
provides a native exception/build checkpoint, not root-cause proof or a fix.

Further boundary follow-up (2026-10-14): direct merge revalidates/detaches both
input models and metric summary revalidates before counting. Four regression
cases failed before the fixes. 81 scoped tests pass; each credentialing module
reaches 100% line and branch coverage in that scoped run (ontology also measured).
Scoped lint/format, Pyright, Bandit and patch secret checks pass. The fresh full
suite crashed in `test_arbitrary_deleted_stage_sets_never_reappear` with
0xC0000005, yielding no completed full coverage report. Do not mark integration
verification complete. Saved native instruction/register inspection and an
early-GC-disabled failure comparison strengthen the runtime evidence, not a fix.

The track remains in progress. Durable ledger storage, concurrency, trusted
authorisation/case mapping and cross-release privacy controls are production
adapter responsibilities. Local pathway/authority mapping and every live
pilot gate below remain pending. A reference match does not certify compliance.

## CHHHS silent-mode tranche

Review follow-up (2026-10-14): constructor input isolation, mutable-model ingestion
revalidation and atomic tombstone preparation now have regression evidence.
74 scoped tests and 661 full repository tests passed; lint, formatting, type and
Conductor checks passed. See `review.md` for requirement coverage and unresolved
intermittent runtime evidence. External and manual gates remain open.

- [ ] Map the routine-renewal pathway and current authority version.
- [ ] Confirm approved pseudonymisation and event sources.
- [ ] Establish baseline time, touch, quality, rework, exception, and effort
  measures before enabling new workflow features.
- [ ] Run synthetic cases, then approved de-identified retrospective cases.
- [ ] Run prospective silent mode with no source-system writes.
- [ ] Compare false alerts, missed requirements, process variants, workload,
  user experience, and privacy effects.
- [ ] Complete governance, privacy, security, records, architecture, support,
  and continuity gates before live ingestion.

## Later packs

Follow-up boundary review (2026-10-14): renewal assessment and reporting now
revalidate mutable projection contents. Restored tombstones are applied before
provenance is required for the retained population. 77 scoped tests and 664 full
repository tests pass, along with scoped lint/format, typing and Conductor checks.
The measurement and human-review gaps in `review.md` remain open.

- [ ] Changed or additional scope.
- [ ] Mutual recognition.
- [ ] Interim, emergency, disaster, and other temporary pathways.
- [ ] Conditions and supervision.
- [ ] Review, reduction, suspension, revocation, and appeal.
- [ ] Register and roster reconciliation.
- [ ] Controlled AI-assisted root-cause and improvement review.

## Phase: Review Fixes

- [x] Isolate constructor state and validate ingestion — 289dc3e.
- [x] Validate assessment/report boundaries and restored inference — dcd50a2.
- [x] Close direct merge and metric-summary boundary gaps — f2c2eed.
- [ ] Resolve the independently reproduced native runtime failure.

### Host-isolation checkpoint — 2026-10-14

Subsequent user preference: leave BIOS settings alone. Verification on a
known-stable authorised host is the alternative next step for the runtime gate;
no firmware intervention is a prerequisite for continuing independent code work.

The standard-library-only synthetic deepcopy/JSON probe also fails, without
Pydantic, CareOps or test-framework imports. CPython 3.14.8 default initialization
failed in 1/16 fresh processes; `-S` failed in 2/16. A separate Anaconda CPython
3.13.15 `-S` comparison produced access violations in 2/12 processes. Replacing
native model serialization with plain-Python serialization failed in 2/24
processes, so no serialization rewrite or dependency change is justified.

The host reports corrected processor internal-parity WHEA events. A process-local
CPU-0 standard-library arm passed 12/12, which is diagnostic evidence only.
This supports a host-stability investigation; it does not establish the precise
cause or a repair. The full private package preserves scripts, results, hashes,
interpreter builds and source-capture limitations outside public Git.

The user's direction is to leave BIOS settings alone. Verification on a
known-stable authorised host is the alternative; hosted checks establish their
specific revision's behavior, not repair of this machine. No firmware,
machine-wide affinity or dependency change was made. Keep the host-reliability
question separate from approved-source, design, manual and pilot gates.

### Local first-submission measurement checkpoint — 2026-10-16

Commit `e72fe67` adds explicit first-submission quality observations, strict
schema, replay/conflict handling, observed and source-attested population rates,
coverage/missingness reconciliation and whole-report small-cell suppression.
See [the scoped receipt and manual](../../../docs/credentialing-submission-quality.md).
All 56 owned tests pass with 100% scoped module statement/branch coverage;
lint, typing, Bandit, schema parity and independent review pass. The integration
owner separately reports 103 passing tests across the new-measure/schema/
observation slice. These are component/integration-slice receipts, not a new full
suite, stable-host verification, real baseline or pilot result. Existing
approved-source, authority, privacy, baseline, silent-mode and human acceptance
tasks remain unchecked.
