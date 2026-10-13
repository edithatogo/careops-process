# Implementation Plan: Authorised M365 corpus-scale process discovery

## Shared hardening prerequisite

Use the exporter and assurance fixes from the
[reliability and ALM hardening plan](../reliability-alm-hardening_20261014/plan.md)
before the next live corpus extraction. Historical completion markers are
preserved; they do not establish that the newly identified exporter and coverage
requirements have been resolved. Complete-population acquisition and owner
validation remain in this track.

## Phase 1: Correct the baseline and define the evidence boundary

- [x] Task: Reclassify the four-record Dataverse run as a connectivity smoke test
    - [x] Update completion and pilot documentation so it is not described as representative process-mining evidence.
    - [x] Add automated checks preventing smoke-test or synthetic outputs from being labelled as corpus findings.
- [x] Task: Define corpus-inventory and coverage contracts test-first
    - [x] Add synthetic fixtures for accessible, inaccessible, empty, partial, paginated and withdrawn source partitions.
    - [x] Specify source, container, time-range, denominator, count, permission, provenance, retention and blind-spot fields.
    - [x] Test that inaccessible sources remain explicit unknowns and never become zero-activity claims.
- [x] Task: Execute the authorised M365 and Power Platform source inventory
    - [x] Probe Exchange/Outlook, Teams, SharePoint, Lists, Planner, Approvals, Power Automate and Dataverse through existing user-scoped interfaces.
    - [x] Record resource-owner actions and policy, licence, API, throttling and history-retention constraints.
    - [x] Produce a privacy-safe coverage ledger and proposed pilot observation period.
- [x] Task: Conductor - Automated Review and Triangulated Verification 'Baseline and corpus boundary' (Refer to workflow.md)
- [x] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Phase 2: Build complete-population acquisition lanes

- [x] Task: Define acquisition adapter contracts and reconciliation tests
    - [x] Test pagination, partitioning, historical backfill, throttling, retries, watermark boundaries and source withdrawal.
    - [x] Test source-to-event reconciliation, duplicate suppression, tombstones, dead letters and deterministic identifiers.
    - [x] Test strict rejection of prohibited raw fields and unapproved destinations.
- [x] Task: Implement Windows-native user-scoped acquisition adapters
    - [x] Implement adapters only for inventory-confirmed delegated APIs, Power Platform connectors or sanctioned exports.
    - [x] Support complete accessible-population extraction for each admitted source partition.
    - [x] Emit per-partition manifests, checksums, counts, exclusions and checkpoint state.
- [x] Task: Implement privacy and records controls
    - [x] Add keyed pseudonymisation, access-boundary labels, retention expiry, deletion and deterministic rebuild procedures.
    - [x] Add transient derived-feature mode guarded by explicit classification and approval configuration.
    - [x] Verify live corpora and protected inputs cannot enter Git, logs or public CI artefacts.
- [x] Task: Conductor - Automated Review and Triangulated Verification 'Complete-population acquisition' (Refer to workflow.md)
- [x] Task: Conductor - User Manual Verification (Refer to workflow.md)

- [x] Task: Define cloud-only Outlook historical backfill contract
    - [x] Separate arrival-trigger ingestion from historical `Get emails (V3)` backfill.
    - [x] Require folder inventory, nested-folder policy, all-page exhaustion and per-folder manifests.
    - [x] Define minimized projection, Dataverse idempotency and fail-closed completeness gates.
    - [x] Document Power Automate owner setup and the desktop/COM fallback boundary.

## Phase 3: Reconstruct the object-centric event corpus

- [x] Task: Extend activity, object and relationship contracts test-first
    - [x] Add multi-source fixtures for meetings, documents, messages, tasks, approvals, flows, governance matters and organisational units.
    - [x] Test many-to-many links, lifecycle gaps, clock anomalies, identity collisions and out-of-order events.
- [x] Task: Implement explainable cross-source correlation
    - [x] Implement deterministic correlation rules with versioned provenance.
    - [x] Add confidence-scored hypothesis links for unresolved cases without overwriting observed facts.
    - [x] Produce ambiguity, orphan-event and incomplete-case reports.
- [x] Task: Validate corpus integrity and scalability
    - [x] Reconcile every normalized event and object to a source partition and run manifest.
    - [x] Benchmark partitioned processing against the inventoried corpus and record bounded-resource limits.
    - [x] Prove deterministic rebuild and incremental refresh equivalence.
- [x] Task: Conductor - Automated Review and Triangulated Verification 'Object-centric corpus reconstruction' (Refer to workflow.md)
- [x] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Phase 4: Discover the main process families empirically

- [x] Task: Define discovery quality and anti-bias tests
    - [x] Test source exclusion, time-window, mapping and correlation-threshold sensitivity.
    - [x] Test that process ranking includes evidence volume, recurrence, organisational reach, confidence and source dependence.
    - [x] Test stable deterministic baselines and optional model-enrichment parity boundaries.
- [x] Task: Implement corpus-level process discovery
    - [x] Discover candidate activity vocabularies and process families without seeding predefined approval labels.
    - [x] Generate variants, directly-follows graphs, object-centric models, hand-offs, loops, ageing and incomplete-case patterns.
    - [x] Quantify assignment ambiguity, drift, temporal stability and process-family confidence.
- [x] Task: Build the human review queue
    - [x] Select representative provenance references without exposing protected narrative.
    - [x] Support family naming, validation, rejection, merge, split and correlation correction with rationale.
    - [x] Preserve reviewer identity, configuration version and decision history.
- [x] Task: Conductor - Automated Review and Triangulated Verification 'Empirical process discovery' (Refer to workflow.md)
- [x] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Phase 5: Produce coverage-honest executive intelligence

- [x] Task: Define executive visual and metric contracts test-first
    - [x] Require observation period, accessible denominator, included population, exclusions, confidence and freshness on every output.
    - [x] Test suppression and aggregation for small cells, protected attributes and individual-level scoring risks.
- [x] Task: Implement process-landscape and drill-down outputs
    - [x] Build the ranked process-family landscape and source/organisation coverage view.
    - [x] Build variant, hand-off, bottleneck, rework, escalation, ageing, incomplete-case and data-quality views.
    - [x] Separate observed facts, inferred hypotheses, owner-validated processes and proposed improvements visually.
- [x] Task: Implement governed improvement handoff
    - [x] Translate validated findings into candidate improvement experiments with guardrails and owners.
    - [x] Prevent analytics outputs from automatically changing workflows, authority rules or individual performance records.
- [x] Task: Conductor - Automated Review and Triangulated Verification 'Executive intelligence' (Refer to workflow.md)
- [x] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Phase 6: Run the corpus-scale pilot and validate findings

- [~] Task: Approve pilot entry and stop criteria
    - [x] Implement executable fail-closed pilot-entry validation and sanitized template.
    - [ ] Obtain source-owner and information-governance confirmation for each admitted source family and destination.
    - [ ] Freeze the observation period, configurations, authorised population and rollback procedure.
- [~] Task: Execute complete accessible-population extraction and discovery
    - [x] Implement the cloud-only Outlook backfill, closed-run gate, OCEL pipeline, and lineage-preserving report command.
    - [ ] Run each admitted source partition to exhaustion with pagination and reconciliation evidence.
    - [ ] Generate OCEL corpus, quality report, coverage ledger, discovery models and executive views from the same run manifest.
    - [ ] Repeat or incrementally refresh the run to prove idempotency and operational feasibility.
- [ ] Task: Validate highest-ranked process families with operational owners
    - [ ] Record accepted, rejected, merged, split and unresolved families with reasons.
    - [ ] Re-run affected models and preserve before/after validation metrics.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Corpus-scale pilot and owner validation' (Refer to workflow.md)
- [ ] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Phase 7: Assurance, handover and executive decision

- [~] Task: Complete repository and live-evidence assurance
    - [x] Run formatting, linting, typing, unit, coverage, privacy, security, workflow and secret checks in CI.
    - [ ] Reconcile repository capability, live corpus evidence, coverage claims, human validation and residual external gates.
    - [ ] Confirm at least 90% line and branch coverage and document any non-code assurance limitations.
- [~] Task: Produce operator and governance runbooks
    - [x] Document inventory, extraction, recovery, review, publication and rollback procedures for the current Outlook lane.
    - [x] Document source expansion, retention, access review, model/version change and approval controls for the current lane.
- [ ] Task: Obtain the IHG Executive post-pilot decision
    - [ ] Demonstrate the validated process landscape with coverage and uncertainty.
    - [ ] Record whether evidence is fit for improvement planning and which experiments or remediation are authorised.
    - [ ] Record production, expansion, pause or closure decisions without implying tenant-wide completeness.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Assurance and executive decision' (Refer to workflow.md)
- [ ] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Repository implementation and review — 2026-10-14

- [x] Task: Reject duplicate flow action IDs and enforce the full checkpoint-safe action sequence; add regression and malformed-contract tests.
- [x] Task: Reject negative, boolean and textual closed-run counts; add nine regression cases.
- [x] Task: Perform conductor-review of these changes and inspect live-pilot readiness; see `docs/m365-corpus-review-20261014.md`.
- [x] Task: Implement v2 consumer checks binding closed-run evidence to authorised partitions, per-partition reconciliation and input/configuration hashes before accepting completeness.

Verification: 219 tests passed at this working-tree snapshot; Ruff formatting,
lint, strict Pyright, Bandit, dependency audit and Conductor validation passed.
Line coverage is 94.38%; branch coverage is 87.55%, so the independent 90%
branch target is still pending in the shared hardening track. Concurrent
credentialing work was present and included in the full-suite snapshot, but is
not part of this change. Hosted security checks were not executed here. Live
approval, acquisition, owner validation and executive acceptance remain pending;
this review does not complete the track or replace human verification.

## Evidence-bound reporting and Outlook handoff — 2026-10-14

- [x] Task: Define the strict v2 evidence schema, frozen full-inventory hash and approval/configuration binding.
- [x] Task: Enforce complete partition membership, source-record accounting, emitted-fact accounting, time boundaries and canonical input hashes; retain empty partitions.
- [x] Task: Build source/destination reconciliation plus matching replay into closed evidence, retaining hashes of both supplied reconciliation artifacts.
- [x] Task: Test Outlook reconciliation-to-closure-to-authorised-report end to end with synthetic nested/empty/excluded folders and duplicates.
- [x] Task: Emit OCEL, candidate landscape, operational patterns, quality and coverage context from the same validated run; keep owner validation pending and tenant-wide coverage unknown.
- [x] Task: Prevent protected input values appearing in validation diagnostics and use one freshness timestamp across report/projection.
- [x] Task: Document the acquisition-to-closure handoff and update the scoped conductor review.
- [ ] Task: Verify these changes together with the committed Outlook support and hardening aggregate coverage evidence in the final shared repository snapshot.

Verification: 60 targeted M365 cases passed after the implementation, including
six Outlook handoff cases and four real CLI subprocess scenarios. Scoped Ruff,
formatting, strict Pyright and Bandit passed. The most recent completed shared
suite at that point was 474 passed / 5 failed: four active Teams domain cases
and an Outlook direct-envelope fixture using the earlier interface. The source
owners are completing those changes; do not interpret that snapshot as a green
aggregate result. An earlier aggregate attempt terminated with a Windows
access violation in credentialing tests, and the subsequent completed retry is
recorded above. Aggregate coverage is owned by the shared hardening track and
was not regenerated by this work after coordination was established.

The v2 interface and local closure helper verify supplied minimized artifacts.
They do not prove a live acquisition occurred, grant approval, make tenant-wide
coverage claims or complete Phases 6–7. Actual approved source/destination runs,
independent repeat-run artifacts, operational-owner validation, executive
acceptance and manual verification remain pending. See
[interface and operator handoff](../../../docs/closed-run-evidence-v2.md) and
[review](../../../docs/m365-corpus-review-20261014.md).

Integration update: after the Outlook/Teams owners corrected their active
fixtures, the combined 72-case integration check passed and the complete shared
suite passed all 494 tests (`--no-cov`). Shared Ruff formatting/lint and Bandit
passed; a newly edited Teams test still produced one strict typing error at
`tests/test_hub_domain.py:580` in that snapshot. M365 scoped typing passes.
The final independent aggregate coverage run remains with hardening. This
supersedes the earlier temporary 474/5 result without erasing its provenance.


## Atomic publication and reproducible scoped verification — 2026-10-14

- [x] Task: Reproduce interrupted report publication and input/output alias overwrite; implement atomic staging, flush/replacement, cleanup and safe diagnostics.
- [x] Task: Verify successful serialization, failed serialization and failed publication preserve the intended authoritative artifact.
- [x] Task: Verify a fresh M365/Outlook scoped snapshot with locked dependencies, full snapshot tests and independent line/branch gates.
- [x] Task: Refresh conductor-review with exact scope, current integration limits and the unchanged live/human acceptance matrix.

Fresh scoped verification: baseline `75613ab` plus the recorded publication and
delivered Outlook evidence overlays; 485 tests passed. Lines: 2384/2444 (97.55%);
branches: 653/694 (94.09%). Locked sync, formatting, lint, strict typing, Bandit
and dependency audit passed. Overlay hashes remained unchanged after capture.
The private snapshot has its own coverage files and excludes uncommitted Teams
product work. It does not complete the final whole-shared-tree task above or
Phases 6–7 live/human gates. Publication/rollback instructions and the review
record are updated; approvals or live data were not fabricated.


## Account and stage direction — 2026-10-14

The user clarified that VUW is for testing, not piloting; the actual pilot is
intended for the Queensland Health account. See
[the test-to-pilot boundary](../../../docs/m365-test-to-pilot-boundary.md).
VUW sign-in and synthetic/non-sensitive integration tests prepare the system;
they do not satisfy Phase 6 live coverage or Phase 7 owner/Executive acceptance.
The earlier seven-day Inbox suggestion was not confirmed. Queensland Health
source/IG decisions and frozen scope/storage/retention/rollback remain pending.

- [x] Task: Prepare a finite VUW development/integration test plan and Queensland Health pilot decision brief with a non-authorising draft record.
- [~] Task: Complete VUW connection authentication/binding and verify authorised test capabilities through the Outlook work; Azure/Graph identity and Power Automate environment access are verified.
- [ ] Task: Record the actual Queensland Health pilot decisions and scope before live acquisition.


## Integrated blocker receipt — 2026-10-14

- [x] Task: Reconcile the coordinator's new scoped verification and unresolved native-runtime evidence with the M365 review.
- [ ] Task: Obtain the native investigator's supported remedy and coordinator verification before claiming operationally reliable local corpus processing.

Coordinator receipt `898d1b1` strengthens local integration evidence but does not
close final aggregate/runtime or live/human gates. Reported JSON/Pydantic native
failures are under a finite investigation owned by credentialing; their root
cause and remedy remain unproven. VUW testing and the actual Queensland Health
pilot remain separate. Human sign-in and authentic source/IG decisions are still
required before the corresponding account/live work proceeds; no repeat login
or unattended status polling is scheduled by this chat.


## VUW connection-route handoff — 2026-10-14

The later Outlook receipt records operator authorisation for a limited Inbox-only
seven-day metadata development test outside Git and selection of the existing
Outlook connection in the developer environment. Azure/Graph identity and Power
Automate environment access are verified. This supersedes the earlier scope-
unconfirmed note only for that limited VUW test; Queensland Health remains the
actual pilot target with its own genuine decisions and evidence pending.

The mail-token route is unavailable; the selected connector route still needs
FlowAgent authentication, exact connection enumeration/binding and frozen
scope/storage/retention controls. No mailbox extraction or deployed connector
identity verification is claimed. Outlook owns those remaining steps. The M365
consumer and report handoff remain ready; no duplicate auth, answered scope
question or unattended login polling is started here.
