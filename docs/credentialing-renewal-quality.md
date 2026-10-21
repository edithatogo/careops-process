# Outstanding overdue renewal prevalence

`credentialing_renewal_quality.py` reports outstanding overdue obligations at one
explicit aware `as_of_utc`. It uses supplied effective deadlines; it never derives
them from reminders or assumes renewal periods, extensions or clinical policy.
The source owner must accept the definition, cohort/cycle mapping, completion
and censoring states, source coverage and effective deadline semantics before use.

The unit is one granted renewal case/cycle. Different cycles must have distinct
opaque case IDs supplied by the trusted adapter. The definition version binds
the source's cycle, cohort, deadline and status mapping. No person-level ranking
or operating-effectiveness judgment follows from this rate.

`RenewalSnapshot` records observation/case/cycle codes, source, definition,
snapshot-as-of, capture time, nullable effective deadline, state, nullable
completion time and strict coverage flag. States are pending, completed,
out-of-scope and unknown. Capture cannot precede snapshot-as-of. Completed state
requires completion at/before snapshot-as-of; other states require null completion.
Schema is `contracts/credentialing-renewal-quality.schema.json`; consumers must
enable date-time format checks. Runtime additionally checks cross-field chronology
and UTC normalisation range. No raw fields, narrative, scalar coercion, terminal
newlines or naive times are accepted.

`merge_renewal_snapshots` detaches/revalidates records, deduplicates exact replay
and rejects changed ID/content replay, including changed source. IDs must be
unambiguous in the retained population. It provides no durable state, tombstone
storage, concurrency or source connector.

`report_overdue_renewals` revalidates frozen policy, scope and snapshots. Policy
supplies definition, as-of, strict source-completeness attestation and minimum
case threshold. Scope supplies trusted report-reader role and actual case-set
grants. The adapter must authenticate them. Each in-scope snapshot must match
definition and as-of exactly. Different IDs for the same consistent case evidence
collapse; capture time may differ. Conflicting cycle, source, status, deadline,
completion or coverage fails. No latest snapshot overwrites contrary evidence.

Each granted case occupies the first applicable category:

1. Missing snapshot.
2. Explicit out-of-scope censoring (not inferred from withdrawal/appeal).
3. Unknown state or incomplete snapshot coverage.
4. Missing deadline.
5. Deadline at/after as-of: not yet due, including already-completed cases.
6. Matured completed: deadline before as-of and completed.
7. Matured outstanding overdue: deadline before as-of and pending.

Population equals these disjoint counts. Matured denominator equals completed
plus outstanding overdue. Observed rate is outstanding overdue / matured;
zero matured means unavailable. Equality with the effective deadline is not
overdue under this explicit metric convention. Source owners must provide an
effective instant that already incorporates their approved timezone, grace-period
and extension rules. Completion after deadline but before as-of counts completed,
not currently outstanding. Historical lateness is a different measure.

The source-attested population rate is available only with complete case evidence,
explicit source coverage and a nonzero matured denominator. Controlled unavailable
reason precedence is incomplete-case-evidence, source-coverage-unconfirmed, then
no-matured-cases. Accounted censoring and not-yet-due cases remain outside matured
denominators. Missing/unknown cases do not become non-overdue zeros. Source
coverage is an input attestation; the function cannot prove source truth.

Every nonzero classification, matured denominator and population count must meet
the approved distinct-case floor, technically at least two. Otherwise suppress
the whole report, including totals, rates and unavailable reasons. Empty grants
are suppressed. Reports expose no case/cycle/source IDs, timestamps or case rows.
Cross-release privacy, retention and trusted mappings remain deployment controls.

This is local synthetic capability. Approved source/authority/privacy definitions,
actual baseline, retrospective/silent-mode evidence and human acceptance remain
open. There is no AI call, workflow mutation, live extraction or backend change.

## Scoped verification — 16 October 2026

The owned suite passes 66 synthetic tests, with 171/171 module statements and
66/66 branches covered in an isolated dataset. Scoped Ruff formatting/lint,
strict Pyright with the project interpreter, Bandit and whitespace checks pass.
Draft 2020-12 schema validation, a positive runtime/schema roundtrip and eleven
negative parity cases pass with active date-time checking in a disposable
environment; no project dependency change was made. Independent read-only review
found no actionable issues. This receipt supports this component only, not a
fresh full-repository, hosted or stable-host pass, real baseline, source-owner
acceptance or pilot result.
