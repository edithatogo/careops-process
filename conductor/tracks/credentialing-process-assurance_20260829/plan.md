# Implementation plan

## Repository tranche

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

The track remains in progress. Durable ledger storage, concurrency, trusted
authorisation/case mapping and cross-release privacy controls are production
adapter responsibilities. Local pathway/authority mapping and every live
pilot gate below remain pending. A reference match does not certify compliance.

## CHHHS silent-mode tranche

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

- [ ] Changed or additional scope.
- [ ] Mutual recognition.
- [ ] Interim, emergency, disaster, and other temporary pathways.
- [ ] Conditions and supervision.
- [ ] Review, reduction, suspension, revocation, and appeal.
- [ ] Register and roster reconciliation.
- [ ] Controlled AI-assisted root-cause and improvement review.
