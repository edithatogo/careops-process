# Condition and supervision review completion

`credentialing_review_quality.py` measures administrative review completion from
explicit source observations. It does not establish that clinical conditions
are satisfied, approve supervision arrangements or supply clinical intervals.
One report uses one supplied kind (`condition_review` or `supervision_review`),
definition version and aware as-of instant. Source-owner acceptance remains
required for obligation identity, deadlines, completion and censoring semantics.

The mathematical unit is a review obligation. A case may have several obligations.
`ReviewObligationGrant` explicitly maps each granted obligation to its privacy
case ID, including obligations with no observations. `ReviewReportScope` admits
only an explicit tuple/frozenset of grants, detaches it to a canonical tuple,
deduplicates exact grants and rejects conflicting case mappings. A shared case
does not grant access to all its obligations. The trusted service must resolve
role and grants; this pure function does not authenticate them.

`ReviewObligationSnapshot` records bounded observation/obligation/case references,
source, kind, definition, snapshot-as-of, capture instant, nullable effective
deadline, state, nullable completion instant and strict coverage flag. Capture
cannot precede snapshot-as-of. Completed state requires completion at/before
snapshot-as-of; other states require null completion. The source's effective
deadline already includes approved extension, grace-period and timezone rules.
Runtime validates chronology and supported UTC range. Wire schema is
`contracts/credentialing-review-quality.schema.json`; schema consumers must
enable date-time format validation. Exact keys reject raw data and narrative;
strict scalars reject coercion, terminal newlines and naive timestamps.

`merge_review_obligation_snapshots` revalidates/detaches records and counts exact
ID/content replay once. Changed replay, including source change, fails. Stable
observation IDs must be unambiguous within retained population. At report time,
each granted snapshot must match case mapping, kind, definition and as-of exactly.
Consistent duplicate observations for an obligation collapse, with different
capture instants allowed. Conflicting evidence fails; no latest state overwrites
contrary evidence. Valid ungranted obligations do not affect the report. Frozen
records, nested grants and policy are revalidated at public boundaries.

Classification uses first-applicable precedence:

1. Missing snapshot.
2. Explicit out-of-scope censoring.
3. Unknown status or incomplete observation coverage.
4. Missing effective deadline.
5. Not yet due: deadline at/after as-of, including early completed reviews.
6. Matured completed on time: deadline before as-of, completion at/before deadline.
7. Matured completed late: deadline before as-of, completion after deadline.
8. Matured outstanding: deadline before as-of, pending.

Total granted obligations equals the sum of these disjoint cells. Matured
denominator includes on-time completed, late completed AND outstanding. Observed
completion rate is (on-time + late completed) / matured. Observed on-time rate
is on-time / matured, not on-time / completed. Zero matured means unavailable.
Exact-deadline equality is not yet due under this metric convention; completion
exactly at deadline is on time once as-of is later. These boundary definitions
require source-owner acceptance and are not statements about clinical policy.

Population counterparts use the same fractions only with complete obligation
evidence, explicit source-completeness attestation and nonzero matured denominator.
Unavailable reason precedence is `incomplete_obligation_evidence`,
`source_coverage_unconfirmed`, then `no_matured_obligations`. Censored and future
obligations are accounted exclusions; missing/unknown obligations do not become
non-completion or measured zero. Attestation is an input assertion, not proof.

Rates are obligation-weighted, but privacy uses DISTINCT CASES in every nonzero
classification, matured denominator and total population. Many obligations from
one case cannot meet a two-case technical floor. Missing-obligation cells use
case identities from trusted grants. Every cell must meet the approved threshold,
otherwise suppress the whole report, including counts, both rate pairs and
unavailable reason. Empty grants suppress. Outputs contain no case/obligation/
source IDs or timestamps. Cross-release privacy, retention and authorised mapping
are deployment controls; token syntax alone cannot prove pseudonymisation.

No existing wire union, renewal module, source adapter, backend or dependency is
changed. The public measurement scope validator is reused for role, case codes
and threshold rules. There is no AI service call or workflow mutation. Local
synthetic capability does not establish approved baseline, retrospective or
silent-mode effectiveness, policy compliance or human acceptance.

## Scoped verification — 16 October 2026

All 66 owned synthetic tests pass, with 215/215 statements and 78/78 branches
covered in an isolated module dataset. Scoped Ruff lint/formatting, strict
Pyright using the project interpreter, Bandit and whitespace checks pass.
Draft 2020-12 schema checking, one positive roundtrip and twelve negative
runtime/schema parity fixtures pass with active date-time validation in a
disposable environment; project dependencies are unchanged. Independent
read-only review found no actionable findings. This supports the component,
not a new full-repository or exact-head hosted verification claim. Approved
source definitions, baseline, live/pilot and human acceptance remain open.
