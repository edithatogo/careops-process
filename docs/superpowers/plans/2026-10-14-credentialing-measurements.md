# Credentialing Measurements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in this chat. Steps use checkbox syntax.

**Goal:** Implement the missing deterministic delay, observed workload, quality and human-review interfaces without live policy assumptions or source writes.

**Architecture:** New measurement modules consume the existing validated projection and trusted case grants. Frozen aggregate records contain no case/event IDs; frozen observation records validate explicit source measurements. The human-review module binds deterministic proposals to released evidence and permits measurement review only.

**Tech Stack:** Python 3.14, existing uv lockfile, dataclasses, pytest, Hypothesis, Ruff and Pyright. No runtime/dependency changes.

**Spec:** `docs/superpowers/specs/2026-10-14-credentialing-measurements.md`.

## Global Constraints

- Inferred events never substitute for observed endpoints.
- Stage intervals can overlap and must not be summed as staff effort or queue time.
- Missing effort observations are unknown, not zero.
- Counts of process events are never relabelled as manual touches or work minutes.
- Broader reports contain no case IDs, event IDs, exact timestamps, staff identifiers or run details.
- Every nonzero measurement or exclusion cell must meet the approved distinct-case threshold; otherwise suppress the entire report.
- Empty populations are suppressed.
- AI is optional and disabled by default.
- Acceptance changes measurement-review state only.
- No source writes, automatic approvals, clinical recommendations or deployment actions.
- A single-report threshold does not solve differencing attacks.

## Ownership and decisions

Base: bbb347a; isolated managed worktree `credentialing-measurements`.
This plan owns the three new modules/tests below, new observation contract and
its design/manual documents. Existing projection/ledger modules, pyproject,
uv.lock and shared runtime environments are excluded. Native diagnosis belongs
to the active credentialing chat. Final shared integration belongs to the
coordinator. The original governance-hub implementation is unchanged.

Ruling: the user's "Address the blocker" directs continuation of the concrete
completion design and necessary implementation steps. Execute inline without
introducing another approval stop. It does not approve CHHHS policy, sources,
pilot evidence, privacy thresholds or live use.

Ruling: use frozen Python dataclasses for new scalar observation/output records,
with explicit validation. Reuse the existing Pydantic projection ingestion
boundary; do not change the native dependency or claim this avoids its defect.

## Review Focus

- Shared events with several granted object links: count each explicitly mapped case once per interval, never each link as an extra observation.
- Rare exclusions and missing observations: suppress totals as well as percentiles/rates.
- Replayed observations and conflicting IDs: deduplicate exact records, reject changed history.
- Undefined quality denominators and zero measured work: distinguish unavailable evidence from an observed zero.
- Changed evidence or repeat review: reject stale/terminal transitions; acceptance cannot activate operational work.

## Task 1: Stage-time reporting

**Files:** create `src/careops_process/credentialing_measurements.py`,
`tests/test_credentialing_measurements.py`, `docs/credentialing-measurements.md`.

**Interfaces:** `validate_measurement_scope(*, role: str, case_ids: AbstractSet[str], minimum_cases: object) -> tuple[frozenset[str], int]`;
`report_stage_times(projection: CredentialingProjection, *, role: str, case_ids: AbstractSet[str], minimum_cases: object, authority_version: str) -> StageTimeReport`.
Frozen `StageTimeReport` has `suppressed`, optional `population_case_count`
and optional tuple `measures`. Each frozen `StageTimeMeasure` has
`interval_id`, `eligible_case_count`, tuple `excluded_case_counts`,
`median_hours`, `p75_hours`, `p90_hours`, `p95_hours`.

- [x] Write hand-calculated tests: four complete cases with stage hours
  1,2,3,4 give median 2.5 and nearest-rank p75=3,p90=4,p95=4; counts reconcile.
- [x] Add missing/repeated/tied/reversed/mismatched qualifier/inferred-only,
  overlapping links, invalid policy, empty population and rare-cell suppression tests.
- [x] Run the new module tests with `--no-cov -q`; observe missing implementation failure.
- [x] Implement adjacent renewal intervals plus request-to-completion,
  recommendation-to-decision, communication-to-activation and decision-to-activation.
  Deduplicate interval pairs. Validate/detach projection, then derive each
  case's mutually exclusive outcome from observed evidence only.
- [x] Run tests, scoped lint/format and Pyright; document current native limitation.
- [x] Commit the independently tested module and record evidence in the ledger.

## Task 2: Observed workload and quality

**Files:** create `src/careops_process/credentialing_observations.py`,
`tests/test_credentialing_observations.py`,
`contracts/credentialing-observation.schema.json`; extend the new manual.

**Interfaces:** frozen `WorkObservation` and `EvaluationObservation` share
`observation_id`, `case_id`, `source_system`, UTC `recorded_at_utc`, and
contract version 0.1.0. Work adds strict nonnegative integer
`manual_touch_count`, `active_work_minutes` and strict `effort_complete`. Evaluation adds strict booleans
`alert_raised`, `requirement_present`, and `evaluation_reference_version`.
`parse_observation(payload: Mapping[str, object]) -> WorkObservation | EvaluationObservation`
rejects uncontrolled keys/types and canonicalizes aware dates.
`merge_observations(existing, incoming) -> tuple[Observation, ...]` uses
kind/ID identity and exact-record equality.
`report_effort(...role, case_ids, minimum_cases) -> EffortReport` and
`report_quality(...role, case_ids, minimum_cases, reference_version) -> QualityReport`
consume Task 1 scope validation. Quality counts one consistent case/reference,
not repeated observation rows. Frozen output records omit identifying data.
`MeasurementWindow` specifies aware start/end, source/cohort definition versions
and strict completeness attestation. `compare_effort(...baseline_window,
current_window, baseline_case_ids, current_case_ids, role, minimum_cases)`
returns `EffortComparison` with an arithmetic per-case difference only when
sources/cohorts/windows and observed populations are comparable.

- [x] Test strict rejection, dates, independent duplicate/conflict replay,
  missing observations versus actual zero and rare missing-case suppression.
- [x] Test quality counts with two contributing cases per nonzero TP/FP/TN/FN
  cell: FP/(FP+TN), FN/(FN+TP); zero denominators yield None.
- [x] Test out-of-grant observations, incompatible evaluation references,
  noncomparable windows, missing effort, and equal source/cohort versions.
- [x] Observe missing-implementation failures; implement frozen validation,
  replay, reporting and comparison without event-count/effort substitution.
- [x] Publish strict draft-2020-12 observation schema; verify independent
  positive/negative fixtures with explicit RFC3339 checker availability.
- [x] Run task tests/lint/type checks and commit with the ledger receipt.

## Task 3: Evidence-bound human improvement review

**Files:** create `src/careops_process/credentialing_improvements.py`,
`tests/test_credentialing_improvements.py`; extend the new manual.

**Interfaces:** `propose_stage_improvements(projection, *, role, case_ids,
minimum_cases, authority_version, threshold_hours, threshold_version)
-> tuple[ImprovementProposal, ...]` recomputes Task 1 report. Frozen proposals
contain rule version, evidence digest, interval ID, measured value, threshold,
threshold version, controlled investigation/alternative-explanation codes and
optional frozen human review. No identifiers from source facts are emitted.
`review_proposal(proposal, *, decision, reviewer_reference, reviewer_role,
decided_at_utc, current_evidence_digest) -> ImprovementProposal` requires a trusted
process-owner/assurance-reviewer role; accepts accepted/rejected/needs-more-evidence
once, only for the unchanged evidence digest. Accepted means measurement review.

- [x] Test deterministic digest/ID, genuine threshold breach, no proposals
  from suppressed/empty reports, changed threshold/evidence causing new IDs.
- [x] Test unknown roles, unsafe review references, naive review times,
  invalid decision, stale evidence and repeated terminal review rejection.
- [x] Observe failures; implement controlled explanations and pure review
  transitions. Run end-to-end with AI disabled and no operational adapter.
- [x] Run tests/lint/type checks and commit with the ledger receipt.

## Task 4: Integration evidence and independent review

**Files:** update this plan/manual, scoped completion/review addendum, and
the metric dictionary addendum (do not overwrite shared runtime-owner findings).

- [ ] Run the entire test suite once in this worktree with its own coverage
  file; retain native failures and do not retry merely for a green claim.
- [ ] Run meaningful property/privacy tests, schema verification, Ruff,
  Pyright, Bandit, dependency/secret/workflow checks; report precise scopes.
- [ ] Request one fresh read-only review of the isolated task range.
  Fix actionable findings with regression evidence.
- [ ] Publish immutable commit/base/path/verification receipts for the
  coordinator to read and integrate. Do not merge/push/deploy or change login.
- [ ] Retain CHHHS mapping, approved source data, live pilot, later policy
  pathways, durable adapter controls, native reliability and manual acceptance
  as actual remaining gates. The full Conductor track stays in progress.
