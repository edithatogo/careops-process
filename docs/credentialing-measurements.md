# Credentialing measurements — disconnected reference

The measurement extension describes administrative evidence. It does not
approve policy, judge clinical competence, rank people or change a workflow.
Trusted server-side access control must supply the reporting role and case
population; user-selected role labels and object IDs are not grants.

## Observed elapsed time

`report_stage_times` accepts the retained projection, a `report_reader`
role, explicitly mapped case grants, approved authority version and a minimum
distinct-case threshold of at least two. This is a technical floor, not an
approved deployment privacy policy. Use ledger-retained events; a projection
alone does not preserve tombstone/provenance state.

Each granted case contributes one outcome per interval. Only observed events
are endpoints. Cases with no observed events, any observed pathway/authority
mismatch, missing endpoints, repeated endpoints, tied times or reversed times
have a controlled exclusion. In that order, the first applicable exclusion
wins. Eligible plus excluded cases reconcile to the entire supplied population.
Cases without events remain missing evidence rather than measured zero.

Intervals cover each adjacent generic renewal stage plus request-to-completion,
recommendation-to-decision, communication-to-register and decision-to-register.
They overlap and must not be summed as work time, queue time or released capacity.
Timing uses aware UTC instants. A case linked through the same event receives
one sample per interval, regardless of its other object links.

Reports contain eligible/excluded counts, median and nearest-rank 75th, 90th
and 95th percentile elapsed hours. For four samples 1,2,3,4 hours, the median
is 2.5, p75 is 3 and p90/p95 are 4. With no eligible samples, quantiles are
unavailable (`None`), not zero.

Every nonzero eligible or exclusion cell in every interval must reach the
approved case threshold. Otherwise the whole report is suppressed, including
population totals and earlier computed intervals. Empty grants are suppressed.
Released records contain no case/event IDs, source timestamps or run details.
Cross-release and overlapping-cohort privacy controls remain deployment work.

## Verification and boundaries

The tests use synthetic cases, explicit endpoints and hand-calculated expected
values, with property checks for bounded/reconciled complete samples. They do
not prove real source completeness, case mapping or authority approval.
Native runtime reliability remains separately under investigation; a passing
component test is not evidence that the known process crash is fixed.

Workload/quality observations and evidence-bound human review are subsequent
tasks in the isolated implementation plan. Do not infer them from event counts
or label this first component the completed credentialing assurance pack.
