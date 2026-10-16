# Aggregate practitioner/staff experience contract

This implements local arithmetic for the original
[experience measure](../contracts/credentialing-assurance-measures.json) and
[user-experience comparison requirement](../conductor/tracks/credentialing-process-assurance_20260829/plan.md).
It supplies no survey questions, satisfaction thresholds, sampling design,
approved instrument or real baseline. Fixtures are explicitly synthetic.

`credentialing_experience.py` accepts source-produced distinct-person aggregates,
not respondent records. Names, practitioner/registration identifiers, case links,
comments and raw survey contents are absent from the exact wire contract.
Source/cohort/snapshot references are protected provenance metadata; question and
category codes must come from an approved non-identifying vocabulary. Syntax
cannot prove a code is non-identifying.

## Explicit supplied instrument and cohort

`ExperienceInstrument` contains an instrument code/version and a nonempty set of
question definitions. Every question explicitly declares `single_select` and
`nominal` or `ordinal`, with distinct allowed category codes. Unsupported scales
and multiselect are rejected rather than interpreted as mutually exclusive
counts. Nominal category ordering is normalized; ordinal ordering is retained.
No ordinal average, numerical score, composite, individual ranking or automated
operational recommendation is calculated.

The complete instrument has a deterministic fingerprint. A snapshot must match
its code, version, fingerprint, every question and every allowed category,
including zero-count categories. A caller cannot drop a rare question before
release or reinterpret an ordinal ordering under the same snapshot.

`ExperienceCohort` pins the source namespace, opaque cohort reference, cohort
definition version, epoch and increasing aware observation-window bounds.
The reporting caller supplies the exact expected cohort, independently of the
snapshot. Timestamps normalize to UTC. Source, definition, window or epoch drift
fails closed. The contract does not select people or infer population coverage
from process-event counts.

## Counts, denominators and release

For one chosen snapshot:

- Invitations = responding persons + survey nonresponders.
- Per question, responding persons = answered persons + missing answers.
- Single-select category counts sum exactly to answered persons.
- Answered persons ≤ responding persons ≤ invited persons.
- Response rate = responding/invited; item response/missing rates divide by
  responding persons; category rates divide by answered persons.

Counts are bounded nonnegative integers; booleans, strings and fractional units
are rejected. Zero denominators produce unavailable rates. Missing answers and
survey nonresponse remain separate, and neither becomes a negative experience
rating. Mutually exclusive respondent aggregation is a source assertion, not
something these integer totals can prove.

`report_experience` requires a trusted `report_reader` role, actual set-based
cohort grants, explicit expected cohort and configured distinct-person threshold
of at least two. It never reuses case-grant semantics for people. The strict
`distinct_person_aggregation_attested` flag must be true for release. It is
supplied evidence, not authentication, source approval or local identity dedup.
The adapter must establish one counted person per relevant source population
and single-select question category.

Whole-report suppression covers every nonzero released invitation, response,
survey-nonresponse, answered, item-missing and response-category cell. Empty
invitation populations and unverified distinct-person aggregation are suppressed.
A rare later question suppresses earlier results and all totals too. Released
records contain category/question codes and aggregate arithmetic, with no
source, snapshot, cohort, epoch, exact window or person identifiers.

One report accepts exactly one selected snapshot. Replay union retains separate
snapshots; it never sums overlapping cohorts or timepoints. Exact source/snapshot
identity replay is idempotent; changed content under that identity is rejected.
Corrections need a new explicitly selected snapshot. There is no automatic
latest-snapshot selection, cross-window trend or causal interpretation.

## Wire, verification and operational boundaries

[The Draft 2020-12 schema](../contracts/credentialing-experience.schema.json)
publishes both instrument and snapshot envelopes with exact keys and true-end
lexical patterns. Schema consumers must enable RFC3339 format validation.
Runtime validation additionally enforces reconciliation, uniqueness by code,
frozen bindings and release policy. JSON Schema integer semantics may accept a
JSON number represented as `1.0`; the runtime requires actual Python integers.
Use the parser at ingestion. Retained constructor, replay, export and reporting
boundaries revalidate/detach nested frozen records to reject mutation bypasses.

36 focused tests pass, including independent hand arithmetic and generated
person-partition privacy cases. Categories cover every privacy cell, missing
attestation, zero denominators, a rare later question, exact/conflicting replay,
source/window/epoch/instrument drift, ordinal order, unsupported multiselect,
strict scalar/grant/wire rejection, malformed calendar/offset values and retained
mutation. A reproduced source-namespace switch failed its regression before the
cohort binding was tightened. Scoped Ruff and strict Pyright pass.

Source owners still approve the instrument and version, question/category
vocabularies, sampling/eligibility and distinct-person aggregation rules,
source/cohort/window/epoch mappings and privacy/retention policy. Live adapters
must authenticate roles, resolve grants and authoritative definitions, validate
source provenance, control corrections and prevent cross-release differencing.
No survey was conducted; no source connector, person mapping, dependency,
notification, scheduler, source writer or deployment was added. Local tests do
not establish experience improvement, host repair or pilot/manual acceptance.

## Reviewed checkpoint

Source commit: `91e1ac5b7e210fca74de152846dd4b9eb26dd7d8`, based on isolated head
`4812ee0b767385d1df43b987115eccc5fa3cb5f1`. A fresh independent read-only reviewer
found no actionable correctness, privacy or semantic issue and independently ran
the 36 focused experience tests successfully. It checked frozen source/cohort/
instrument bindings, whole-release suppression, source attestation, denominators,
replay conflicts, nested revalidation and structural schema/parser agreement.

Independent Draft 2020-12 validation agrees with the runtime on two valid exports
and twelve invalid field, boolean/fractional-count, terminal-newline, calendar,
offset and multiselect fixtures. The RFC3339 calendar checker was explicitly
verified active. Scoped Ruff lint/format, strict Pyright, Bandit, Conductor
validation and a redacted one-commit Gitleaks scan pass. No broad test loop or
live/host reliability verification is claimed. Final shared integration belongs
to the coordinator and must use the combined authoritative revision.

## Concrete record boundary repair

Contract boundaries reject subclasses of cohort, snapshot, instrument, question
and question-count records before reconstruction. Python dataclass replacement
preserves runtime subclasses, whose overridden post-initialization can skip
validation. Rejecting those unsupported records prevents invalid totals, windows,
versions and selection modes from entering exports, merges, digests or reports.
The wire schema is unchanged. Fifteen adversarial regressions failed before this
repair and pass afterward; the focused experience suite now contains 51 tests.
