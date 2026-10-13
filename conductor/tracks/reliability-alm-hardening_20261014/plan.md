# Implementation plan

All tasks start pending. Execute phases 1–5 locally before phase 6. Track
repository evidence, hosted GitHub evidence and live VUW evidence separately.

## Phase 1: Confirm defects and establish offline exporter tests

- [ ] Task: Inspect exporter consumers, contracts and existing tests; record concrete failure cases and compatibility requirements.
- [ ] Task: Add failing mocked PowerShell tests for prohibited raw fields, identifiers and mailbox identity in output and diagnostics.
- [ ] Task: Add failing tests for encoded date filters, UTC boundaries, invalid windows and page-size inputs.
- [ ] Task: Add failing tests for pagination, repeated pages, duplicate records, replay, empty results, token/API failure and interrupted output.
- [ ] Task: Add Planner tests for measured duplicate/rejection counts and deterministic empty-result serialization.
- [ ] Task: Record phase verification and manual checkpoint against the project workflow.

## Phase 2: Repair exporter privacy and reliability

- [ ] Task: Implement allowlisted projections and keyed, domain-separated pseudonyms; update schema and consumer mappings where needed.
- [ ] Task: Fix date-window query construction and validation without exposing protected input in diagnostics.
- [ ] Task: Implement deterministic replay, duplicate/conflict reconciliation and safe output publication; preserve previous valid output on failure.
- [ ] Task: Reconcile source candidates and emitted events separately; record exclusions, failures, checksums and explicit scope/completeness limits.
- [ ] Task: Verify pagination destinations, retries and failure paths do not leak bearer tokens or mark partial runs complete.
- [ ] Task: Run offline exporter tests and privacy scans; record phase verification and manual checkpoint.

## Phase 3: Strengthen mining and coverage assurance

- [ ] Task: Measure current line and branch coverage separately and identify uncovered behaviour rather than assuming the combined score proves both targets.
- [ ] Task: Write mining edge-case/property tests for empty/mixed traces, repeated activities, ordering, unequal lengths, determinism and metric bounds.
- [ ] Task: Repair only reproduced mining defects and document the simple fitness/precision definitions and their limits.
- [ ] Task: Test optional PM4Py availability and the supported integration boundary in an isolated dependency profile; retain licence-review requirements.
- [ ] Task: Reconcile the PM4Py manifest/lockfile mismatch; verify locked sync and audit the resulting normal and optional dependency profiles.
- [ ] Task: Enforce independent 90% line and branch gates and add offline PowerShell checks to CI with pinned dependencies.
- [ ] Task: Run the complete quality/security suite; record phase verification and manual checkpoint.

## Phase 4: Clarify CodeQL and dependency maintenance

- [ ] Task: Inspect CodeQL workflow requirements and repository-setting dependencies; make activation explicit in configuration and documentation.
- [ ] Task: Inspect effective shared Renovate configuration and Dependabot scopes; choose and document one updater owner per ecosystem, including submodule pins.
- [ ] Task: Remove verified overlap while retaining security-update coverage, lockfile handling, pinned Actions and required checks.
- [ ] Task: Validate workflow and updater configuration locally; prepare hosted acceptance checks without claiming they have run.
- [ ] Task: Record phase verification and manual checkpoint.

## Phase 5: Build reusable local ALM safeguards and refresh documentation

- [ ] Task: Inventory the harvested solution, component dependencies, existing scripts and missing flow/configuration assets; distinguish shared tooling from Teams product implementation.
- [ ] Task: Verify current official PAC and Power Platform/Fabric ALM documentation; record supported feature choices, licensing/access gates and optional capabilities.
- [ ] Task: Write failing synthetic tests for solution structure/versioning, missing references, secret-bearing settings and environment-bound values.
- [ ] Task: Write failing tests for dry-run, interrupted packaging/deployment preparation, export-before-change and rollback planning.
- [ ] Task: Implement local solution validation, supported packaging and integrity-checked release artifacts with explicit prerequisite diagnostics.
- [ ] Task: Add tenant-neutral environment-variable/connection-reference templates and deployment-settings generation; keep real bindings outside Git.
- [ ] Task: Document dev/test/prod promotion gates, managed/unmanaged policy, connection ownership, solution-check results, rollback and approval evidence.
- [ ] Task: Document optional Power Platform pipelines and Fabric Git/deployment integration without requiring admin/service-principal access or creating unused infrastructure.
- [ ] Task: Update current README and operator/CI runbooks; annotate stale historical documents with links to superseding evidence.
- [ ] Task: Validate a fresh local checkout and complete regression/security checks; record phase verification and manual checkpoint.

## Phase 6: Hosted and VUW verification after local work

- [ ] Task: Complete the separately agreed VUW CLI setup and verify account, authorised environments, tools, roles and consent; record unavailable capabilities.
- [ ] Task: Publish reviewed changes when authorised and verify required Actions, offline PowerShell checks and actual CodeQL analysis/SARIF upload.
- [ ] Task: Verify the selected updater configuration in hosted runs and confirm that duplicate ecosystem responsibility is removed.
- [ ] Task: Run an authorised low-sensitivity exporter smoke test, compare date-window/replay behaviour with local evidence, and reconcile manifests without committing live data.
- [ ] Task: Validate solution checking, configuration binding, import/export and rollback in an authorised non-production environment when permissions allow.
- [ ] Task: Verify selected optional pipeline features only if relevant resources and permissions exist; record explicit limitations otherwise.
- [ ] Task: Hand evidence to the Outlook, M365 discovery and Teams tracks; their complete-population runs and governance pilots remain there.
- [ ] Task: Record final review, unresolved external gates and human verification before completing the track.
