# Implementation Plan: Authorised M365 corpus-scale process discovery

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

- [~] Task: Define executive visual and metric contracts test-first
    - [ ] Require observation period, accessible denominator, included population, exclusions, confidence and freshness on every output.
    - [ ] Test suppression and aggregation for small cells, protected attributes and individual-level scoring risks.
- [ ] Task: Implement process-landscape and drill-down outputs
    - [ ] Build the ranked process-family landscape and source/organisation coverage view.
    - [ ] Build variant, hand-off, bottleneck, rework, escalation, ageing, incomplete-case and data-quality views.
    - [ ] Separate observed facts, inferred hypotheses, owner-validated processes and proposed improvements visually.
- [ ] Task: Implement governed improvement handoff
    - [ ] Translate validated findings into candidate improvement experiments with guardrails and owners.
    - [ ] Prevent analytics outputs from automatically changing workflows, authority rules or individual performance records.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Executive intelligence' (Refer to workflow.md)
- [ ] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Phase 6: Run the corpus-scale pilot and validate findings

- [ ] Task: Approve pilot entry and stop criteria
    - [ ] Obtain source-owner and information-governance confirmation for each admitted source family and destination.
    - [ ] Freeze the observation period, configurations, authorised population and rollback procedure.
- [ ] Task: Execute complete accessible-population extraction and discovery
    - [ ] Run each admitted source partition to exhaustion with pagination and reconciliation evidence.
    - [ ] Generate OCEL corpus, quality report, coverage ledger, discovery models and executive views from the same run manifest.
    - [ ] Repeat or incrementally refresh the run to prove idempotency and operational feasibility.
- [ ] Task: Validate highest-ranked process families with operational owners
    - [ ] Record accepted, rejected, merged, split and unresolved families with reasons.
    - [ ] Re-run affected models and preserve before/after validation metrics.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Corpus-scale pilot and owner validation' (Refer to workflow.md)
- [ ] Task: Conductor - User Manual Verification (Refer to workflow.md)

## Phase 7: Assurance, handover and executive decision

- [ ] Task: Complete repository and live-evidence assurance
    - [ ] Run formatting, linting, typing, unit, property, privacy, security, dependency, licence, workflow and secret checks.
    - [ ] Reconcile repository capability, live corpus evidence, coverage claims, human validation and residual external gates.
    - [ ] Confirm at least 90% line and branch coverage and document any non-code assurance limitations.
- [ ] Task: Produce operator and governance runbooks
    - [ ] Document inventory, extraction, refresh, recovery, deletion, rebuild, review, publication and owner-departure procedures.
    - [ ] Document source expansion, retention, access review, model/version change and rollback controls.
- [ ] Task: Obtain the IHG Executive post-pilot decision
    - [ ] Demonstrate the validated process landscape with coverage and uncertainty.
    - [ ] Record whether evidence is fit for improvement planning and which experiments or remediation are authorised.
    - [ ] Record production, expansion, pause or closure decisions without implying tenant-wide completeness.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Assurance and executive decision' (Refer to workflow.md)
- [ ] Task: Conductor - User Manual Verification (Refer to workflow.md)
