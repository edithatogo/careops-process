# Local case reporting

`credentialing_local_reporting.py` provides one combined aggregate release for
case demand/pathway mix, correction/further-information/deferral/exception rates,
queue versus active-work time and observed process variants. This is synthetic
repository functionality. Source mapping, clinical/authority approval, live
ingestion, pilot effectiveness and manual track acceptance remain pending.

## Protected input and source responsibilities

`CaseReportingObservation` is a protected case/window snapshot. Its structural
wire contract is [credentialing-case-reporting.json](../contracts/credentialing-case-reporting.json).
Use `CaseReportingObservation.model_validate_json` for JSON ingestion and
`model_dump_json` to export protected observations. The runtime additionally
checks uniqueness of reasons and the complete time partition; JSON Schema cannot
express those cross-field checks. Unknown fields, raw text, unregistered activity
labels, invalid reference tokens and nonfinite/coerced minute values are rejected.

A trusted adapter must supply the full eligible request-case population for one
source-defined reporting window, an approved definition version, approved pathway
and administrative process-reason vocabularies, and a coverage attestation.
The codes and booleans do not authenticate these assertions. Role and case grants
must be resolved by the server. An empty vocabulary does not invent defaults.
No clinical decision explanations, names, addresses, registration numbers,
worker identifiers or case-level ranking belong in this contract.

The adapter must use retained, deletion-aware source evidence. Snapshots must be
rebuilt or removed after source deletions; this reporting function is stateless
and does not create a second durable ledger. Exact observation replay is
idempotent. Consistent repeat case assessments count once; conflicting identities
or case assessments fail. There is no arbitrary latest-wins policy. Separate
windows and definition versions must be reported separately.

Reasons are explicitly observed **case assessments**, independent of ontology
event counts. `null` means unassessed; `[]` means explicitly assessed negative;
a nonempty unique set means positive. Source-approved further-information
criteria must be supplied explicitly: the existing correction activity is not
silently redefined as further information. Reason memberships may overlap.

`observed_trace` is the complete source-defined ordered administrative activity
sequence for the assessment window, with repeated activities preserved. It must
come from observed retained facts, never inferred facts. The adapter must supply
`null` for missing, ambiguous-order or incomplete traces; an empty sequence is
rejected. This input contract has no NLP/inference field. The reporter counts
each available case trace once and does not certify conformance to a clinical
pathway or authority model.

## Denominators and reconciliation

| Output | Definition |
| --- | --- |
| Demand | `population_case_count`: distinct eligible request cases in the trusted window grant set, including missing snapshots. This is a case count, not an arrival-event count or arrival rate. |
| Coverage | `observed_case_count + missing_case_count = population_case_count`. |
| Pathways | Each observed classified case contributes once; known pathway counts plus missing-pathway cases equal the full case population. |
| Pathway mix | Each pathway count divided by all classified cases; missing classification is separately visible and is never assigned to a pathway. No classified cases yields an empty mix. |
| Four case rates | Positive cases divided by explicitly assessed cases for that measure. Assessed positives plus assessed negatives plus missing assessments equal the full population. No assessments yields a null rate. |
| Reason rates | Each reason's distinct-case count divided by the same explicitly assessed measure population; rates may sum above the overall positive rate because reasons overlap. |
| Population rates | Available only when every case has the relevant assessment and trusted source coverage is confirmed. Otherwise the observed rate remains separate and the population rate and reason rates are null with an explicit unavailable reason. |
| Variants | Distinct-case frequencies of full observed activity tuples; variant frequencies plus missing-trace cases equal the case population. |
| Time | Assessed case spans partition into mutually exclusive observed `queue`, `active` and `unknown` intervals; elapsed total equals those three totals within floating-point precision. |

Time offsets are minutes from a source-defined case span start. Intervals must be
positive, contiguous, ordered, start at zero, have no overlaps/gaps, and end at
the supplied elapsed time. Both elapsed and intervals must be supplied together
or both be null. A genuinely zero-length span has zero elapsed and an empty
partition. Unknown state must remain explicit. Whole-case missing time is counted
separately and does not contribute invented minutes.

Active time is exclusive **case elapsed time in an observed active state**;
it is not worker effort or a claim about capacity released. Concurrent-worker
effort remains in the separate work-observation contract. Queue time is not
inferred from elapsed time or calculated by subtracting worker minutes. There
are no causal claims, source writes or automatic workflow changes.
Stage-specific professional-review and committee-preparation worker effort
remains a separate partial original outcome. Parallel workers can contribute
more worker minutes than calendar minutes; this partition does not constrain or
replace their effort observations.

## Privacy release

The minimum is a deployment-approved distinct-case threshold of at least two.
The function checks the full joint categorical signature across pathway,
four complete reason memberships (including missing/negative), observed variant,
time availability and queue/active/unknown state participation. Every nonzero
joint cell must meet the threshold. This protects intersections as well as
individual marginals within the combined release. A rare cell suppresses **all**
counts, rates, labels, variants and time totals, including the overall population
and missingness. Suppression never returns a rare-cell explanation.

Reports contain no case/observation/source references or individual durations.
This conservative rule may suppress many detailed cohorts. It does not provide
differential privacy, protect arbitrary external background knowledge or perform
cross-query/cross-release accounting. A production adapter must control repeated
overlapping releases and joins with other reports; an isolated safe report must
not be treated as permission to publish arbitrary slices.

## Reproduce the synthetic check

Run `uv run --no-sync python examples/credentialing_local_reporting.py`.
The example intentionally includes replay and repeated correction activities.
It produces four demand cases, two cases per pathway, correction and exception
rates of 0.5, and two variants with two cases each. Four 60-minute spans reconcile
to 240 elapsed minutes: 160 queue, 60 active and 20 unknown. All role, grant,
coverage, vocabulary and definition inputs are synthetic fixtures.

Run `uv run --no-sync pytest tests/test_credentialing_local_reporting.py --no-cov`.
Tests exercise denominator reconciliation, missing/negative distinctions, reason
overlap, replay/conflicts, scope isolation, joint suppression, strict wire values,
interval partitions, mutation/subclass boundaries and aggregate overflow.

## Verification receipt — 17 October 2026

The 57 owned tests pass with ordinary assertion rewriting, including a Hypothesis
replay/order invariant. The reporting module reaches 100% statement and branch
coverage (191 statements, 52 branches). The example has independent arithmetic
expectations. The integration slice with existing acceptance, measurements,
observations and projection-schema tests passes 142 tests. Scoped Ruff
lint/format, strict Pyright, Bandit, Conductor and whitespace checks pass.
Independent full Draft 2020-12 validation accepts a runtime export and rejects
10 structural mutations, including terminal newlines, raw fields, boolean
minutes and an unregistered activity. It used a disposable `jsonschema==4.26.0`
overlay; repository dependencies and lockfiles are unchanged.

Independent read-only review found a hostile integer-subclass threshold bypass;
the new reporting boundary now requires concrete integer/string scope scalars.
Regression tests cover threshold, role and reference subclasses, and the
reviewer independently confirmed the fix with no remaining findings. This receipt
is scoped repository evidence, not a full combined revision, live source trial,
operating-effectiveness judgment or final track acceptance.
