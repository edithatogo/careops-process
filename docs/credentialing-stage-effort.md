# Professional-review and committee-preparation effort

`report_stage_effort` in `credentialing_stage_effort.py` adds a source-mapped
breakdown over existing `WorkObservation` records. It reports observed worker
minutes and manual touches for `professional_review`, `committee_preparation`
and `other`, with case coverage and missingness for each stage. It does not add
a new observation wire contract or infer work from process events.

The trusted adapter supplies an explicit observation-ID-to-stage mapping, a
controlled stage-mapping version, the full eligible case population and an
existing `MeasurementWindow` with source/cohort versions and coverage attestation.
Every distinct input observation ID needs exactly one registered assignment;
missing/extra assignments and unknown/raw labels fail. `other` is an explicit
source assignment, never a default for missing classification.

## Units, coverage and reconciliation

Each unique work observation is a source-observed effort/touch **delta**.
Exact replay counts once; changed replay conflicts. The adapter must prevent
duplicate representation of the same underlying work under different IDs and
allocate a work minute to one stage only. A mapping/version label does not prove
classification approval, correct allocation or source truth. Retain the actual
approved mapping and source evidence in the restricted evidence location.

The source adapter must establish that work belongs to the accepted measurement
window and cohort. This function additionally checks each granted observation's
`recorded_at_utc` against the half-open capture window. A capture instant alone
does not establish when the underlying work occurred. Structurally valid
observations outside the case grant set contribute nothing.

Per stage, the reporter reuses `report_effort`:

- Sum the explicit observed minutes and touches, counting source replay once.
- Count distinct observed and missing **cases**, not workers or observations.
- Count a case's stage measurement as complete only when all its observations at
  that stage's latest capture instant have `effort_complete=True`. Earlier deltas
  remain in the total. The flag concerns measurement coverage, not clinical
  completion of the review or preparation.
- Divide observed minutes by distinct observed cases for the observed-case mean.
- Release `full_cohort_mean_minutes` only when source-window coverage is attested
  and every granted case's stage measurement is complete.

No observation means unknown work, so totals and means are null rather than
invented zeros. Explicit source-observed zero is zero. If a stage is known to be
not applicable, the source owner must define its treatment and denominator;
absence of a work record is not an automatic non-applicability determination.

Worker effort is not elapsed time: parallel workers may contribute more minutes
than a case-calendar interval. This reporter does not subtract work from elapsed
time, infer queue state, count workers, produce a time-saving/capacity estimate
or certify a policy pathway. Stage-specific queue-time attribution remains a
separate mapping/reporting gap; the existing calendar reporter provides a whole
case queue/active/unknown partition.

## Privacy and trusted access

The caller must provide a server-resolved `report_reader` role, explicit mapped
case grants and an approved distinct-case threshold of at least two. This pure
function authenticates no caller. It reconstructs concrete work observations
and windows before use, rejecting subclass/mutation and scalar coercion bypasses.

Before releasing any stage it counts the full joint case signature across all
three stages: missing/complete/partial measurement, positive-versus-zero minutes
and positive-versus-zero touches. If any nonzero joint cell is below the floor,
the **entire report** is suppressed, with no counts, labels or reasons. The
underlying individual-stage suppression also remains in force. Outputs contain
no case/observation/source identities, capture times or mapping versions.

These are distinct-case protections. They do not establish a distinct-worker
privacy threshold or prevent staff inference from outside knowledge. Workforce
aggregation, overlapping releases and joins to other reports need separate
privacy acceptance. No individual practitioner/staff ranking is provided.

## Verification and remaining acceptance

Run `uv run --no-sync pytest tests/test_credentialing_stage_effort.py --no-cov -q`.
The synthetic tests independently reconcile professional/committee minutes,
missing/zero/partial evidence, replay and source mapping. A case fixture has safe
individual-stage marginals but rare cross-stage intersections; it confirms whole
release suppression. A Hypothesis check exercises arbitrary replay/input order.

This closes a local stage-worker-effort reporting gap. Actual source/mapping,
baseline, deployed access, retrospective/silent-mode, privacy/governance and
human acceptance remain pending. It supplies no actual causal released-capacity
evidence and does not close the full track.

## Verification receipt — 17 October 2026

All 26 owned tests pass; the module reaches 97% statement/branch coverage across
97 statements and 38 branches. The combined stage/work-observation/local-reporting/
store slice passes 148 tests. Scoped lint/formatting, strict typing, Bandit,
Conductor and whitespace checks pass. No dependency, observation schema, source
adapter or deployment changed. A bounded owned-file secret-pattern check and
manual review found no matches; Gitleaks was unavailable locally.

Independent read-only review found no actionable correctness/privacy or wording
issues. These are synthetic repository receipts, not an approved stage baseline,
privacy policy, causal evaluation or maintainer/governance signature.
