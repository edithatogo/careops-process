# Implementation plan

## Repository tranche

- [x] Add a generic credentialing ontology.
- [x] Add a strict privacy-minimised event projection schema.
- [x] Add the credentialing process-assurance design note.
- [x] Genericise the active feasibility baseline.
- [x] Add a permissive licence and process-assurance review agent.
- [x] Register this Conductor track.
- [x] Add strict projection validation and normalization tests.
- [ ] Add explicit credentialing ontology-registry validation tests.
- [x] Add synthetic valid projection and invalid/deviation fixtures in tests.
- [x] Add deep raw-field rejection, replay, duplicate and watermark tests.
- [ ] Add credentialing-specific tombstone and minimized-dead-letter tests.
- [ ] Add routine-renewal conformance model and metric dictionary.
- [ ] Add small-cohort suppression and role-scoped semantic projection tests.
- [ ] Add BPMN and rendered process diagrams.

Reconciled against `src/careops_process/credentialing.py` and
`tests/test_credentialing.py` on 2026-10-13. This records repository evidence,
not live tenant execution or governance approval. Conformance, small-cohort
suppression and role-scoped projections remain pending.

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
