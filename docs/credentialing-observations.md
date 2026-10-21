# Observed workload and case-level quality

`credentialing_observations.py` accepts versioned opaque-reference observations.
The wire shape is published in
[the observation schema](../contracts/credentialing-observation.schema.json).
Use `parse_observation` at ingestion; JSON Schema integer semantics alone do not
enforce strict Python integer types. Schema consumers must enable date-time
format validation. Raw source records, names, narrative and clinical conclusions
are outside this contract. Opaque references still require controlled access.

Work observations are deltas in manual touches and active working minutes.
Stable kind/observation IDs deduplicate exact replay; changed replay fails.
Missing observations are unknown, while an observed zero remains zero.
`effort_complete` attests measurement coverage, not completion of a credentialing
case or approval. All observations at the latest timestamp must attest complete;
later partial work or a simultaneous partial delta keeps that case partial.

Quality uses one independently adjudicated case at one controlled reference
version. Repeated consistent reviews count once, including reviews with distinct
IDs. Conflicting labels or an unexpected reference within the granted population
fail closed. False-positive rate is FP/(FP+TN); false-negative rate is FN/(FN+TP).
An empty denominator is unavailable. These are case-level rates; alert-level or
requirement-level measures require separately approved unit mappings.

Both report builders require a trusted `report_reader` role, explicit case-set
grants and a configured distinct-case threshold of at least two. Every nonzero
coverage/outcome cell must meet that threshold, otherwise the entire report is
suppressed. Reports contain aggregates only. These functions do not authenticate
callers: a service adapter must obtain roles and grants from its trusted access
boundary. Caller-provided role strings cannot establish authorization.

Effort comparisons use explicit baseline/current grants, half-open aware windows,
matching source/cohort-definition versions and source-completeness attestations.
Every granted case must have complete effort coverage. Only then is baseline
mean minus current mean available. This arithmetic observation does not establish
causation, released capacity, staffing savings or a clinical decision.

Frozen records are revalidated and detached when merged, before aggregation.
There is no source writer, scheduled acquisition, deployment or AI dependency.
Synthetic fixtures prove local contracts only. Actual Queensland Health source
bindings, approved definitions, privacy policy and pilot acceptance remain open.

## Human measurement review

`credentialing_improvements.propose_stage_improvements` recomputes the stage-time
report and emits deterministic `investigate_stage_delay` candidates only for
released p95 values above an explicit versioned threshold. Fixed alternative
explanations preserve uncertainty: source coverage, legitimate variants, clock
quality and case mix. These are investigation hypotheses, not recommendations to
alter credentials, clinical services or staffing.

The evidence fingerprint binds the granted observed facts and source/contract
versions, case grants, authority mapping, released report and threshold policy.
It changes when observed evidence or policy changes, even if aggregates happen
to stay equal. Input row ordering does not affect identity. Fingerprints contain
no reversible payload, but remain controlled review metadata, not public proof
of source authenticity. Retain source/proposal linkage in the protected store.

`review_proposal` validates retained immutable fields and permits one accepted,
rejected or needs-more-evidence disposition from a trusted process owner or
assurance reviewer, with an opaque actor reference and an aware timestamp.
The input remains unchanged. Every disposition terminates this proposal's review;
changed evidence or policy creates a new proposal. Acceptance is explicitly
`measurement_review_only`, and does not activate a workflow or change a source.

A live adapter must authenticate the reviewer, resolve current grants and policy,
recompute the current proposal fingerprint, and persist the transition atomically.
The supplied `current_evidence_digest` must come from that trusted recomputation,
not from the client's retained proposal. These pure functions do not establish
identity, database concurrency, signatures or deployment approval. AI is not used.
