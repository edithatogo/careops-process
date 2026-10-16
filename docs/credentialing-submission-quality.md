# First-submission completeness

`credentialing_submission_quality.py` measures explicit observed assessments of
first submissions. It does not infer completeness from an `application_ready`
event, lack of correction events, elapsed time or a later successful submission.
An approved source mapping defines the first submission, completeness criteria,
case population and assessment-definition version. No clinical default is supplied.

The independent frozen `FirstSubmissionObservation` contract records bounded
opaque observation/case references, source code, aware observation timestamp,
definition version and a strict boolean assessment. Its exact wire schema is
`contracts/credentialing-submission-quality.schema.json`. Schema consumers must
enable date-time format validation. Runtime ingestion rejects scalar coercion,
extra fields, narrative, terminal newlines and naive timestamps. Bounded token
syntax cannot establish that real source references are non-identifying.
Runtime ingestion also rejects instants whose offset conversion exceeds Python's
supported UTC range, even if their wire syntax passes schema validation.

`merge_first_submission_observations` detaches retained records, counts exact
observation replay once and rejects reused IDs with changed content, including
changed source. Sources must use stable globally unambiguous observation IDs
within this retained population. The function does not provide durable storage,
tombstones, source acquisition or concurrency control.

`report_first_submission_quality` takes a trusted `report_reader` role, explicit
case-set grants, assessment-definition version, strict `source_complete` coverage
attestation and minimum distinct-case threshold. These arguments must be resolved
by the service adapter; this function does not authenticate them. The adapter must
bind definition, approved sources, reporting window and cohort to those grants.
All records are revalidated before aggregation, including frozen records.

Each granted case contributes once. Repeated consistent labels collapse even
when observation IDs differ. Conflicting case assessments fail; a later label
never overwrites an earlier contrary assertion. Wrong definition versions within
the granted population fail. Valid out-of-grant records do not contribute.

Population equals assessed plus missing; assessed equals complete plus incomplete.
Missing is unknown, not false. `observed_complete_rate` is complete divided by
assessed; no assessed cases means unavailable. `population_complete_rate` uses
that same rate only when every granted case is assessed and source coverage is
explicitly attested. Otherwise its controlled reason is `missing_assessments`
(first precedence) or `source_coverage_unconfirmed`. Coverage attestation is an
input assertion, not proof that a source is complete.

For two complete and two incomplete cases, both rates are 0.5 with confirmed
coverage. For two complete and two missing, the observed rate is 1.0 and the
population rate is unavailable. These populations must never be compared without
their coverage counts and approved definitions.

Every nonzero population, assessed, missing, complete and incomplete case cell
must reach the approved threshold, with a technical floor of two. Otherwise the
entire report is suppressed, including totals, rates and unavailable reasons.
Empty grants are suppressed. Released reports contain no observation/case IDs,
source codes or timestamps. Cross-release privacy remains a deployment control.

This local capability supplies neither an actual baseline nor retrospective,
prospective silent-mode or operating-effectiveness evidence. Original source,
authority, privacy and human acceptance gates remain open. It does not rank
people, judge competence, mutate a workflow or call an AI service.

## Scoped verification — 16 October 2026

The owned suite passes 56 synthetic tests. Its isolated coverage dataset records
108/108 statements and 30/30 branches in the new module. Scoped Ruff lint and
formatting, strict Pyright using the project interpreter, Bandit and whitespace
checks pass. Draft 2020-12 schema checking, one runtime/schema roundtrip and eight
negative parity fixtures pass with an explicitly active date-time checker in a
disposable environment; project dependencies are unchanged.

Independent read-only review found a UTC conversion overflow at the supported
datetime boundaries. Two regression cases failed before the fix; parser and
direct-construction paths now reject those instants with a controlled contract
error. Read-only recheck found no remaining actionable findings. This is scoped
component evidence, not a fresh full-repository or hosted verification result,
host repair, approved clinical mapping or live operating evidence.
