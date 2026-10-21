# Queue and calendar time by explicitly mapped stage

`report_stage_calendar` in `credentialing_stage_calendar.py` allocates existing
observed `CaseReportingObservation` intervals to source-defined stages. It closes
the local queue-time-by-stage reporting gap without introducing a new observation
schema or inferring queue time from elapsed time, event gaps or worker effort.

This is a local pure reporter. Source access, approved interval/stage definitions,
actual baseline/pilot results, deployed authentication and human/governance
acceptance remain external requirements. It does not establish causal capacity,
clinical pathway applicability or organisational policy compliance.

## Explicit source mapping

The trusted adapter supplies:

- Existing strict case snapshots, with their complete observed case-span
  queue/active/unknown partition, or explicitly missing time evidence.
- `StageCalendarPolicy`: matching source definition/window codes, a separate
  stage-mapping version, a nonempty controlled stage vocabulary and strict
  source-coverage attestation. No stage names or classification defaults are
  installed by the library.
- An observation-ID-to-tuple mapping. Each tuple assigns one registered stage to
  each interval in its existing order. Every input observation identity must be
  covered exactly; there must be no stale extra mappings or unlabeled intervals.
  Missing partitions and genuinely observed zero spans both need an explicit
  empty tuple; the snapshot distinguishes them.
- A server-resolved `report_reader` role, full eligible case-span population and
  approved distinct-case privacy floor, technically at least two.

The reporter reconstructs concrete snapshots and nested intervals before use.
The existing contract still requires positive ordered intervals, no gaps or
overlaps, a zero start offset and an endpoint equal to supplied elapsed time.
It rejects observation, nested-interval and policy subclass/mutation bypasses.
Exact observation replay counts once. Consistent repeated case snapshots count
once; changed identities, conflicting case evidence or inconsistent repeated
case stage assignments fail. No latest-wins replacement occurs.

Valid records outside grants contribute nothing. A granted snapshot with a
different source definition/window fails. The adapter must ensure an accepted
span/window has the intended temporal coverage, and must bind the actual mapping
and its version to approved source evidence. Codes, tuple positions and a
coverage boolean do not prove source truth or authenticate the caller.

## Counts, minutes and denominators

`observed_case_count` counts granted cases with available complete partitions of
their accepted spans; `missing_case_count` counts all other granted cases.
Their sum is the eligible population. A case snapshot with missing time is still
missing for these calculations. No observed spans means null minute totals,
not invented zero. An observed zero-length span has an empty partition and zero
elapsed time.

For each configured stage:

| Output | Meaning |
| --- | --- |
| `stage_case_count` | Observed-span cases containing at least one interval explicitly assigned to that stage |
| `absent_stage_case_count` | Observed-span cases with no such stage interval; together with stage cases equals observed cases |
| Queue/active/unknown case counts | Distinct observed cases contributing positive time to that state in that stage; memberships can overlap |
| Queue/active/unknown minutes | Sum of explicitly assigned positive interval durations for that stage/state |
| `mean_queue_minutes_per_observed_case` | Stage queue total divided by all cases with observed spans, including those with no stage interval |
| `mean_queue_minutes_per_stage_case` | Same total divided by cases with any interval in that stage; it is not a queue-positive-only mean |
| `full_population_mean_queue_minutes` | Available only when all eligible case spans have observed partitions and source coverage is attested |

An absent stage in a complete **accepted span** contributes observed zero to
that span's stage total. This does not prove that a pathway requirement was not
applicable, a stage was clinically completed, or the stage cannot occur outside
the accepted span/window. The source owner must accept the span and denominator
semantics, especially for open or censored cases. Missing spans never contribute
zero by default.

Across all configured stages, the three state totals reconcile to total observed
case-span elapsed minutes within floating-point precision. Stage labels partition
each interval once, including repeated visits to a stage. Unknown state remains
unknown even when its stage is known. There is no arbitrary proportional split,
interpolation or conversion of unknown time into queue time.

These are **case-calendar minutes**, summed across cases that may run in parallel.
They are not worker effort, unique staff time or savings. Actual professional/
committee worker effort remains in the separate stage-effort reporter. The two
reports must not be subtracted or interpreted as a causal capacity estimate.

## Privacy release

Before releasing labels, totals, counts or means, the reporter checks complete
joint case signatures across all configured stages and queue/active/unknown
participation, including observed zero/absent-stage and missing-span groups.
Every nonzero joint atom must meet the case floor. A rare atom suppresses the
whole report, with no counts, labels or rare-cell explanation. This protects
intersections and complements within this release even when each stage's
marginal counts appears safe.

Outputs omit source/case/observation identities, source times and mapping/version
metadata. Approved stage codes must themselves be non-identifying. This does not
provide distinct-worker protection, differential privacy, cross-query accounting
or protection against arbitrary background knowledge. Deployment privacy policy
must govern joins and overlapping/repeated releases. A pure role argument is not
an authentication mechanism.

## Synthetic verification

Run `uv run --no-sync pytest tests/test_credentialing_stage_calendar.py --no-cov -q`.
The fixture independently maps four 60-minute spans: validation queue totals
160 minutes; committee active and unknown totals are 60 and 20 minutes. These
reconcile to 240 elapsed case-minutes. Replay does not change the result.
Missing/zero spans, absent stages, unknown labels, wrong mapping length, mixed
definition/window, conflicting replay, frozen-record tampering, overflow, scope
checks and joint intersections are separately tested. A Hypothesis property
checks arbitrary exact replay and input ordering.

This is a local reporting capability. Actual source/deployment/causal/human gates
remain open. No source collection, platform mutation, dependency change or
inference/AI operation is performed by this reporter.

## Verification receipt — 18 October 2026

All 25 owned tests pass with ordinary assertions and a Hypothesis replay/order
property. The stage-calendar module reaches 100% statement and branch coverage
(127 statements, 44 branches). The combined calendar/stage-effort/local-reporting/
store slice passes 135 tests. Scoped lint/format, strict typing, Bandit, Conductor
and whitespace checks pass. Independent read-only review found no actionable
findings and independently reran all 25 tests successfully. A bounded owned-file
secret-pattern check and manual review found no matches; this is not a full
repository/history security-scan claim. Repository dependencies are unchanged.

These are synthetic local receipts, not operational baseline, policy approval,
causal capacity evidence or maintainer/governance sign-off.
