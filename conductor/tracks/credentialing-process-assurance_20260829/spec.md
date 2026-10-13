# Specification

## Goal

Add an organisation-neutral credentialing domain pack to CareOps Process that
can measure conformance, delay, rework, exceptions, capacity, and quality from
privacy-minimised events.

## Requirements

1. Versioned credentialing object and event ontology.
2. Strict JSON Schema for event projection.
3. Stable pseudonymous or source-local object references.
4. No names, emails, registration numbers, raw evidence, free text, patient
   information, decision reasons, or individual ranking.
5. Observed and inferred events represented separately.
6. Replay, duplicate, tombstone, watermark, and dead-letter safety.
7. Pathway and authority-version qualifiers.
8. Routine-renewal reference model and later separate pathway models.
9. Clear metric definitions and small-cohort protection.
10. Explainable, human-reviewed improvement hypotheses with no automatic
    workflow mutation.

## Acceptance criteria

- the ontology and projection schema validate;
- raw and prohibited fields are rejected;
- observed events require confidence 1.0;
- inferred events require confidence and provenance in the processing run;
- duplicate and replay fixtures do not double count;
- tombstoned events cannot reappear;
- routine renewal golden path and material deviations are testable;
- metrics reconcile to source event counts and stated exclusions;
- small cohorts are suppressed before broader reporting;
- AI-disabled operation remains complete; and
- repository completion is not represented as live ingestion, pilot success, or
  operating effectiveness.
