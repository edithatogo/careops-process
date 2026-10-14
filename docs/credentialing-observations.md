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
