# Implementation plan

Local implementation commit: `d104961`. Phase checkpoints await human verification.
Execute phases 1–5 locally before phase 6. Track
repository evidence, hosted GitHub evidence and live VUW evidence separately.

## Phase 1: Confirm defects and establish offline exporter tests

- [x] Task: Inspect exporter consumers, contracts and existing tests; record concrete failure cases and compatibility requirements.
- [x] Task: Add failing mocked PowerShell tests for prohibited raw fields, identifiers and mailbox identity in output and diagnostics.
- [x] Task: Add failing tests for encoded date filters, UTC boundaries, invalid windows and page-size inputs.
- [x] Task: Add failing tests for pagination, repeated pages, duplicate records, replay, empty results, token/API failure and interrupted output.
- [x] Task: Add Planner tests for measured duplicate/rejection counts and deterministic empty-result serialization.
- [~] Task: Record phase verification and manual checkpoint against the project workflow.

## Phase 2: Repair exporter privacy and reliability

- [x] Task: Implement allowlisted projections and keyed, domain-separated pseudonyms; update schema and consumer mappings where needed.
- [x] Task: Fix date-window query construction and validation without exposing protected input in diagnostics.
- [x] Task: Implement deterministic replay, duplicate/conflict reconciliation and safe output publication; preserve previous valid output on failure.
- [x] Task: Reconcile source candidates and emitted events separately; record exclusions, failures, checksums and explicit scope/completeness limits.
- [x] Task: Verify pagination destinations, retries and failure paths do not leak bearer tokens or mark partial runs complete.
- [~] Task: Run offline exporter tests and privacy scans; record phase verification and manual checkpoint.

## Phase 3: Strengthen mining and coverage assurance

- [x] Task: Measure current line and branch coverage separately and identify uncovered behaviour rather than assuming the combined score proves both targets.
- [x] Task: Write mining edge-case/property tests for empty/mixed traces, repeated activities, ordering, unequal lengths, determinism and metric bounds.
- [x] Task: Repair only reproduced mining defects and document the simple fitness/precision definitions and their limits.
- [x] Task: Test optional PM4Py availability and the supported integration boundary in an isolated dependency profile; retain licence-review requirements.
- [x] Task: Reconcile the PM4Py manifest/lockfile mismatch; verify locked sync and audit the resulting normal and optional dependency profiles.
- [x] Task: Enforce independent 90% line and branch gates and add offline PowerShell checks to CI with pinned dependencies.
- [~] Task: Run the complete quality/security suite; record phase verification and manual checkpoint.

## Phase 4: Clarify CodeQL and dependency maintenance

- [x] Task: Inspect CodeQL workflow requirements and repository-setting dependencies; make activation explicit in configuration and documentation.
- [x] Task: Inspect effective shared Renovate configuration and Dependabot scopes; choose and document one updater owner per ecosystem, including submodule pins.
- [x] Task: Remove verified overlap while retaining security-update coverage, lockfile handling, pinned Actions and required checks.
- [x] Task: Validate workflow and updater configuration locally; prepare hosted acceptance checks without claiming they have run.
- [~] Task: Record phase verification and manual checkpoint.

## Phase 5: Build reusable local ALM safeguards and refresh documentation

- [x] Task: Inventory the harvested solution, component dependencies, existing scripts and missing flow/configuration assets; distinguish shared tooling from Teams product implementation.
- [x] Task: Verify current official PAC and Power Platform/Fabric ALM documentation; record supported feature choices, licensing/access gates and optional capabilities.
- [x] Task: Write failing synthetic tests for solution structure/versioning, missing references, secret-bearing settings and environment-bound values.
- [x] Task: Write failing tests for dry-run, interrupted packaging/deployment preparation, export-before-change and rollback planning.
- [x] Task: Implement local solution validation, supported packaging and integrity-checked release artifacts with explicit prerequisite diagnostics.
- [x] Task: Add tenant-neutral environment-variable/connection-reference templates and deployment-settings generation; keep real bindings outside Git.
- [x] Task: Document dev/test/prod promotion gates, managed/unmanaged policy, connection ownership, solution-check results, rollback and approval evidence.
- [x] Task: Document optional Power Platform pipelines and Fabric Git/deployment integration without requiring admin/service-principal access or creating unused infrastructure.
- [x] Task: Update current README and operator/CI runbooks; annotate stale historical documents with links to superseding evidence.
- [~] Task: Validate a fresh local checkout and complete regression/security checks; record phase verification and manual checkpoint.

## Phase 6: Hosted and VUW verification after local work

- [ ] Task: Complete the separately agreed VUW CLI setup and verify account, authorised environments, tools, roles and consent; record unavailable capabilities.
- [x] Task: Publish reviewed changes when authorised and verify required Actions, offline PowerShell checks and actual CodeQL analysis/SARIF upload. Draft PR 73, exact code head `ecb8fce`: Coordination verified all four expected hosted workflows passed, including CodeQL and 1,553 tests (97.60% line, 94.93% branch). Documentation revision `555f7d2` was hosted-pending at this handoff; results are exact-revision evidence. This does not complete other live/human gates or merge the PR.
- [ ] Task: Verify the selected updater configuration in hosted runs and confirm that duplicate ecosystem responsibility is removed.
- [x] Task: Run an authorised low-sensitivity exporter smoke test, compare date-window/replay behaviour with local evidence, and reconcile manifests without committing live data. Bounded VUW test completed 16 October; local destination and independent replay/readback only, not Dataverse or full-corpus closure. See closure-review-20261017.md.
- [~] Task: Validate solution checking, configuration binding, import/export and rollback in an authorised non-production environment when permissions allow. Developer baseline import/export and description-only restoration verified; checker passed for table-only package, binding N/A there. Full schema/data recovery, managed promotion and TEST acceptance remain unverified; actual app export still refused for declared dependencies and role mappings.
- [ ] Task: Verify selected optional pipeline features only if relevant resources and permissions exist; record explicit limitations otherwise.
- [ ] Task: Hand evidence to the Outlook, M365 discovery and Teams tracks; their complete-population runs and governance pilots remain there.
- [ ] Task: Record final review, unresolved external gates and human verification before completing the track.

18 October reconciliation of the 17 October closure checkpoint: evidence recorded in
[closure-review-20261017.md](closure-review-20261017.md). VUW PAC sign-in succeeded;
required write/customization rights remain absent in VUW-AI-TEST. A later read-only
check verified authoring capabilities in the existing personal VUW Developer
environment, selected for an isolated synthetic rehearsal. This does not close
the Test acceptance gate. Live checker succeeded with zero findings for the
table-only package; binding is N/A there. Personal Developer baseline import/export
succeeded, followed by read-verified restoration of a synthetic description change.
This is not schema/data rollback. The actual app export was inspected and the
bounded app-aware validator implemented (`e7eaa50`, `14f8b96`, `ecb8fce`); it still
refuses declared platform dependencies and target-specific role mappings. See
[independent hub evidence](../../../docs/vuw-hub-rehearsal-20261018.md) and
[ALM profile limits](../../../docs/local-alm.md). Isolated encrypted VUW Azure
authentication was restored and fresh Developer organization/user identity matched;
existing unrelated/PAC profiles and the old cache were preserved. Updater,
executable cloud-runtime, TEST and human gates remain open. Keep the track in progress.

## Evidence and review — 14 October 2026

- [Verification record](verification.md) distinguishes owned clean-snapshot results,
  delivered Outlook checks, concurrent integration failures and external gates.
- [Conductor review](review.md): three reproduced findings fixed; no remaining
  correctness finding in the reviewed local scope. The whole track is incomplete.
- Implementation: `d104961` (Planner, mining/coverage, CI/dependencies, local ALM).
  Outlook owns its exporter/test/runbook delivery in the shared checkout; those
  files are not part of this commit and must be integrated by their owner.
- Phase 1–5 technical tasks are locally verified. Every phase's human checkpoint
  remains pending; no automated test is recorded as human approval.
- Historical 14 October snapshot: Phase 6 was pending separately authorised VUW setup, publishing/hosted
  Actions and SARIF, bot execution, approved live smoke tests and non-production
  checker/import/export/rollback, optional authorised pipeline verification,
  final cross-track evidence handoff and human approval.
- Do not mark the registry complete or archive the track until those gates close.
## Phase: Review Fixes

- [x] Task: Apply review suggestions for platform-specific publication tests and malformed JSON validation d104961.
- [x] Task: Reject case-varied environment URLs and client-secret bindings 351cbaa.

Ruling: Keep track in progress and retain its folder because human checkpoints and
Phase 6 are genuine uncompleted gates. Validate a stable scoped checkout while
concurrent owners run RED/GREEN cycles; coordinator owns final shared integration.
No test, packaging run, or local status substitutes for live/human approval.
