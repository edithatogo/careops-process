# Capacity evidence: observed work, estimates, claims and judgments

The original requirement is `capacity-released-to-higher-value-work` in
`contracts/credentialing-assurance-measures.json`; the original design names
exception management, practitioner support and quality assurance. This local
contract advances evidence collection and validation. **The original causal
released-capacity requirement remains partial.** Neither passing tests nor
human acceptance of a claim establishes the counterfactual that CareOps released
capacity or that the destination work improved outcomes.

`credentialing_capacity_evidence.py` keeps four results separate:

- Observed source-aggregated destination work, in TOTAL integer minutes.
- Recomputed baseline/current effort difference, in minutes PER CASE.
- A protected, externally supported claim about attributed redeployment.
- A protected human assessment, explicitly an external judgment only.

## Source aggregate and joint-person privacy

`RedeploymentActivityDefinition` supplies versioned activity codes and purpose
tags: exception management, practitioner support, quality assurance or other.
The source owner approves that mapping and what higher value means locally.
Definitions are fully fingerprinted; a version label alone cannot change them.
`RedeploymentCohort` pins source, cohort, aggregation definition, half-open aware
window, fixed release epoch and activity-definition digest. These are opaque
references, not worker/case/practitioner/patient identities.

`RedeploymentSnapshot` contains eligible, observed and participating worker counts;
per-activity integer minutes/contributors; source-supplied higher-value/other
distinct-worker UNION counts; and complete source-supplied JOINT participation
groups. Each group maps one unique nonempty activity-code set to a positive
distinct-worker count. Groups are disjoint worker atoms, not lists of people.
Reject unknown codes, duplicate groups and contradictory complete totals.

Joint counts sum to participating workers and reproduce every activity contributor
count. Against the supplied definition they also reproduce both purpose unions.
Worker memberships may overlap; never sum activity marginals into workforce size.
For example, support contributors three, other contributors three, union five
reveals an overlap of one. Large marginals cannot hide that singleton: its joint
atom suppresses the whole report. Every nonzero joint atom, coverage population,
activity/purpose union and inferable complement must meet the approved DISTINCT
PERSON threshold, technically at least two. Case privacy is a separate floor.

Source attestations explicitly cover distinct-person aggregation, complete joint
counts, purpose unions and disjoint allocation of WORK MINUTES. Worker activity
membership can overlap while each minute is assigned once. Missing any required
attestation suppresses all output. Attestations and arithmetic cannot authenticate
deduplication or prove that source intervals did not overlap. Cross-release,
intersection/differencing policy and retention still require privacy approval.

Eligible = observed + missing; observed = participating + observed nonparticipating.
Every participating activity contributor has positive work; observed zero-work
workers remain observed nonparticipants, not missing. Total minutes sum activities;
higher-value minutes sum supplied accepted purpose tags. Higher-value share uses
total observed minutes, unavailable for zero total. Mean uses observed workers,
unavailable for none. Full-cohort mean needs every eligible worker observed and
source-window completeness. Complete explicit zero is zero; missing is unknown.

`report_redeployment` admits one exact authorized frozen cohort/window snapshot.
`merge_redeployment_snapshots` deduplicates exact replay without summing snapshots;
changed IDs/content or a changed frozen source/cohort/release epoch fails. The
aggregate reports contain controlled activity codes and counts, not source
identities, windows, digests or worker identifiers.

## Retained-input effort linkage and public projection

`CapacityEvidenceBundle` retains source snapshot/definition/expected cohort,
baseline/current `WorkObservation` tuples, `MeasurementWindow`s and explicit
case-set grants. It reconstructs concrete public records and windows, detaches
sets, rejects conflicting observation replay and matches the current effort
window exactly to the redeployment window. `CapacityReportScope` and
`CapacityReportPolicy` keep cohort authority and person/case thresholds explicit.
The trusted service must authenticate role/grants and accept population mappings.

`build_capacity_evidence` RECOMPUTES public `compare_effort` from retained inputs.
A client cannot supply a ready-made comparison or availability flag. Negative
differences remain negative. Minutes per case are never subtracted from, equated
to, multiplied into, or capped against total redeployment minutes by default.
Credentialing case populations and worker cohorts are not assumed interchangeable.
External population-alignment/evaluation evidence must explain their relation.
An internal digest pins retained data, definitions, scope and release policy;
row ordering and exact replay do not change that identity.

`report_capacity_evidence` is the PUBLIC measurement projection. It takes no claim,
assessment or artifact inputs and exposes NO attributed amount, assessment state,
reviewer, claim ID or evidence digest. A safe observed workforce does not establish
privacy for an externally claimed subset. No client approval flag can publish it.
If either constituent suppresses, BOTH are redacted even in the protected build
record; no safe effort value can reverse a rare worker-group suppression, or vice
versa. Unsuppressed but unavailable measurements retain explicit coverage/reasons.

## Protected attribution and external judgment

`CapacityAttributionClaim` binds claim/version, current evidence digest, exact
cohort/window, method/version, bounded integer attributed-redeployment minutes
and explicit minute units. Claim meaning is a subset of the SAME measured
higher-value work, not future savings. It must not exceed that complete measured
quantity; the bound is arithmetic consistency, not causal proof. Missing complete
measurement coverage or effort comparison makes the claim unavailable for
assessment. Shape/unit/binding errors do not turn into attributed results.

Claims require distinct protected reference/hash roles for evaluation method,
population alignment, evaluation design and study results. `ResolvedCapacityEvidenceManifest`
contains actual hashes resolved by a trusted adapter. These constructors resolve
nothing: hash syntax cannot prove a document exists, is authentic or supports the
claim. No raw studies, narrative, signatures, source identities or causal defaults
are invented here.

`assess_capacity_claim` recomputes current evidence and records one supplied
`accepted_for_evaluation_record`, `rejected` or `needs_more_evidence` disposition
from a trusted owner/assurance context, at/after the measured window. Acceptance
needs exact resolved artifact bindings. Rejection or a request for evidence may
retain an incomplete artifact manifest without fabricating resolution. Assessment
pins evidence, claim and manifest digests. Changed facts, claims, definitions,
thresholds or artifact hashes invalidate the old binding.

`summarize_capacity_evidence` returns `ProtectedCapacitySummary`, for protected
service/storage use ONLY. It distinguishes no claim, unverified, unavailable,
rejected, needs-more-evidence and human-assessed-external-judgment states. It may
retain an admissible claimed amount without asserting truth. No
`verified_causal_release` state or authentication boolean exists. The entire
protected summary still redacts constituent values on measurement suppression.
Do not display/serialize this record as a public aggregate.

Reviewer/role strings, supplied manifests and parsed assessment records do not
authenticate themselves. The adapter must authenticate users, resolve actual
artifacts and hashes, recompute current grants/policy/evidence, control protected
access and atomically persist one assessment transition. These pure functions do
not provide storage concurrency, signing, replay-proof reviewer authority or an
automatic transition from client claims to trusted stored judgments. An external
judgment does not authorise workflow mutation or establish clinical/causal effect.

## Wire contracts and remaining evidence

`contracts/credentialing-capacity-evidence.schema.json` defines exact protected
definition, snapshot, claim, assessment and manifest shapes. Public parser/export
boundaries reconstruct concrete nested contracts, rejecting subclass/mutation
bypasses, extra raw fields, coercion, duplicate membership codes, naive instants,
terminal newlines and UTC overflow. Enable date-time format checks in schema
consumers. Runtime adds joint/count/definition reconciliation and strict Python
integer semantics (JSON Schema may accept `1.0` as an integer).

Source-owner activity/cohort/unit/window/coverage definitions, approved privacy
and retention, genuine complete work evidence, credible evaluation design and
control of alternative causes, artifact provenance and human appraisal remain
required. Approved baselines, retrospective/prospective silent mode and governance
acceptance are still open. Local record/math completeness must not close the
original released-capacity outcome or full track. There is no acquisition,
backend/dependency change, person ranking, AI call or workflow/source write.

## Scoped verification — 16 October 2026

All 67 owned tests pass with ordinary pytest assertion rewriting. The isolated
dataset covers 523/523 statements and 176/176 branches in this module. Scoped
Ruff lint/formatting, strict Pyright with the project interpreter, Bandit and
whitespace checks pass. Draft 2020-12 schema validation checks five positive
protected-record roundtrips and nineteen negative runtime/schema parity cases
with active date-time validation in a disposable environment. Project
dependencies are unchanged.

Tests include a singleton intersection hidden behind safe marginal counts,
combined constituent suppression, retained-input effort recomputation and unit
separation, stale claim/assessment bindings, unresolved artifacts and subclass/
nested-mutation boundaries. A safe observed cohort with a one-minute claimed
subset confirms that public output omits claim amount and judgment status.
Independent read-only source/test and completed schema/manual reviews found no
actionable findings. These are local component receipts, not final-revision
hosted checks, a host repair, source authentication or causal capacity evidence.
The original released-capacity requirement and full track remain incomplete.
