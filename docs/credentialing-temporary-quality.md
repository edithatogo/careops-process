# Temporary episode conversion, expiry and review

`credentialing_temporary_quality.py` implements explicit temporary-episode and
separate required-review observations. Original design questions include all
three domains (`credentialing-process-assurance.md`, temporary approval question
and metrics list). This module neither supplies approval durations nor establishes
legal validity, clinical competence or unauthorised practice.

## Episode evidence

`TemporaryEpisodeGrant` maps each source-defined episode to a privacy case.
Several episodes may belong to one case. `TemporaryReportScope` takes trusted
report-reader role and explicit tuple/frozenset grants, detaches canonical grants,
deduplicates exact mappings and rejects conflicting mappings. The service adapter
must authenticate them and provide an approved cohort/definition mapping.

`TemporaryEpisodeSnapshot` records bounded observation/episode/case references,
source, definition, snapshot-as-of/capture, nullable observed start and effective
expiry, state, nullable conversion and observed expiry-transition instants, and
strict coverage-complete flag. States are active, converted, expired, closed
without conversion, out of scope and unknown. Capture cannot precede as-of;
known start cannot exceed as-of; known expiry cannot precede known start.
Converted/expired states require their respective observed transition at/before
as-of and at/after known start. Other states require null transition fields.

An effective expiry deadline passing does NOT establish an observed expiry.
Early source-observed expiry is admissible and separately visible. Conversion
meaning, extensions/reopenings, closure and effective deadline semantics require
source-owner acceptance. No generic register event is assumed to be conversion.

`report_temporary_episodes` uses one explicit definition/as-of, strict source
coverage attestation and approved minimum case threshold. Main first-applicable
classification is missing snapshot; explicit censoring; unknown/incomplete
coverage; missing start; missing expiry; not yet matured; then matured converted
by expiry, converted after expiry, observed expired, closed without conversion,
or source-active past effective expiry. Deadline at/after as-of is not matured,
even if already converted/expired. Conversion exactly at expiry is by-expiry once
the as-of instant is later. These are explicit metric boundary conventions,
subject to source-owner acceptance, not clinical policy conclusions.

All main cells sum to granted episodes. Matured denominator includes ALL five
matured outcomes. Observed conversion rate = both converted outcomes / matured;
conversion-by-expiry rate = converted-by-expiry / matured. Zero matured means
unavailable. Population counterparts additionally require source-completeness
attestation and no missing/unknown/start/expiry evidence. Reason precedence is
`incomplete_episode_evidence`, `source_coverage_unconfirmed`, `no_matured_episodes`.

Observed expiry transitions have their OWN eligible denominator: expired source
state, complete coverage, known start/effective expiry and observed transition.
They are classified before/at/after effective expiry. This includes early expiry
of not-yet-matured episodes. Eligible plus excluded episode counts reconcile to
the granted episode population. Excluded includes non-expired and missing or
insufficiently observed episodes; it is not evidence of no expiry problem.
No transition timing rate is emitted or divided by the matured denominator.

## Separate temporary-review evidence

`TemporaryReviewGrant` maps each required review obligation to episode AND case.
`TemporaryReviewReportScope` includes both episode grants and review grants;
reviews outside the granted episode/case mapping fail. A case or episode alone
does not grant all of its reviews. Multiple required reviews remain distinct.

`TemporaryReviewSnapshot` records common identity/source/as-of/coverage evidence,
review obligation ID, nullable effective deadline, pending/completed/out-of-scope/
unknown state and nullable completion instant. Completed state requires completion
at/before as-of; other states require null completion. The separate wire schema
and API do not extend condition/supervision review kinds or their existing enum.

`TemporaryReviewReportPolicy` explicitly includes
`required_review_population_complete` as well as source coverage. Unknown required
reviews are NEVER represented as a zero unknown count. Output says how many
obligations are KNOWN and whether their required population was attested complete.
Known zero obligations with unconfirmed requirements cannot produce a full rate.
Source owners must establish the complete required-review population for all
granted episodes; no obligation is inferred from episode events.

`report_temporary_reviews` reconciles missing snapshot, censoring, unknown/
incomplete coverage, missing deadline, future/not-yet-due, matured on-time,
matured late and matured outstanding. Main counts sum to KNOWN granted reviews.
Matured denominator includes outstanding. Observed completion rate is
(on-time+late)/matured; observed on-time rate is on-time/matured. Both are explicitly
restricted to supplied known obligations. Full-population rates need complete
evidence, required-review enumeration, source coverage and nonzero matured.
Unavailable reason precedence is `incomplete_review_evidence`,
`review_population_unconfirmed`, `source_coverage_unconfirmed`, `no_matured_reviews`.

## Shared boundaries and privacy

Each domain has its own exact-key Draft 2020-12 schema:
`contracts/credentialing-temporary-episode.schema.json` and
`contracts/credentialing-temporary-review.schema.json`. Enable date-time format
checks. Runtime additionally checks chronology and supported UTC range. Raw
fields/narrative, coercion, naive instants and terminal newlines are rejected.
Opaque token syntax cannot prove that actual identifiers are non-identifying.

Public parser/export/merge/report boundaries revalidate and detach frozen records,
nested grants and policies. Exact observation-ID/content replay counts once;
changed replay/source fails. Consistent distinct IDs collapse per episode/review;
capture time may differ. Conflicting evidence fails; no newest-label preference.
Granted mappings, definition and as-of match exactly. Valid ungranted evidence
does not contribute. Existing wire unions and modules remain unchanged.

Mathematical units are EPISODES or REVIEW OBLIGATIONS, but ALL released nonzero
cells and totals require the approved minimum DISTINCT CONTRIBUTING CASES,
technically at least two. This includes missing cells from trusted mappings,
expiry-transition cells, their eligible/excluded totals, known review population,
matured populations and overall episode/case populations. Many episodes/reviews
from one case cannot satisfy the floor. A failing cell suppresses the entire
corresponding report, including rates/totals/reasons/coverage flags. Empty episode
scope suppresses. Released reports contain no identifiers, source instants or
case classifications. Cross-report/release privacy remains a deployment control.

Pure local evidence functions do not implement durable tombstones, storage,
concurrency, retention, acquisition or authentication. Approved source definitions,
cohort, privacy, actual baseline, retrospective/silent-mode and human acceptance
remain open. There is no AI call or workflow/source mutation.

## Scoped verification — 16 October 2026

The owned suite passes 92 tests using explicit `--assert=plain`, with 338/338
statements and 102/102 branches covered in an isolated module dataset. Scoped
Ruff lint/formatting, strict Pyright with the project interpreter, Bandit and
whitespace checks pass. Both Draft 2020-12 schemas pass positive roundtrips and
twelve negative runtime/schema parity fixtures each, with active date-time
checking in a disposable environment; project dependencies remain unchanged.

Independent review reproduced a subclass-validation bypass: dataclass `replace`
preserved overridden validators. Two regression tests failed before the fix.
Snapshot/report boundaries now reconstruct declared concrete contract types;
policy, scope and nested population-flag regressions pass. Read-only recheck
found no remaining actionable issues.

The first ordinary pytest attempt, before the module existed, hit a native
access violation in assertion rewriting. One plain-assert diagnostic then
confirmed the expected missing-module failure. Subsequent owned tests explicitly
used plain assertions; no permanent pytest, dependency, affinity or BIOS change
was made. The sanitized failure excerpt and source-checkpoint limitations are
preserved outside Git. These results do not establish ordinary assertion-rewrite
reliability, host repair, a full-suite pass or final hosted acceptance. Standard
pytest on the final published revision remains an integration requirement.
