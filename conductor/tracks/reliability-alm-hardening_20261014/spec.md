# Local reliability and ALM hardening

## Purpose

Address the outstanding exporter, assurance, dependency-maintenance and
application lifecycle management (ALM) issues identified after the PR merges.
Complete reproducible local work first, then verify hosted checks and platform
behaviour using the separately agreed VUW CLI setup stage.

This track adds shared engineering prerequisites to the existing product tracks.
It does not replace their pilot, source-owner or governance requirements.

## Repository observations

Observed in the current checkout on 14 October 2026 (Australia/Brisbane):

- `scripts/Invoke-GraphMailboxBackfill.ps1` selects and writes subjects,
  sender/recipient addresses and raw identifiers. Its manifest writes the mailbox
  address. Excluding bodies alone does not meet the minimised-projection policy.
- That exporter appends JSONL output on repeat runs and has no explicit duplicate
  reconciliation. Its single-quoted filter fragment includes a literal backtick
  before `$filter`; date-window query construction needs regression coverage.
- `scripts/export-planner-corpus.ps1` declares zero duplicates and rejections
  without explicit reconciliation, and needs executable failure-path tests.
- CodeQL analysis is conditional on `ENABLE_CODEQL`. Workflow presence does not
  prove that analysis or SARIF upload ran; hosted configuration needs inspection.
- Dependabot covers Python and Actions while Renovate extends a shared config.
  Inspect effective Renovate rules before deciding whether their scopes overlap.
- Coverage uses branch measurement with a combined 90% gate. This does not
  independently establish the product guideline's 90% line and 90% branch targets.
- Mining has three basic tests. Edge cases, metric interpretation and the
  optional PM4Py integration boundary need explicit assurance.
- `pyproject.toml` pins PM4Py 2.7.23.8 while the committed `uv.lock` records
  2.7.23.1. Reconcile this drift and verify locked dependency consistency.
- A harvested Dataverse solution exists under `powerplatform/solutions`, but
  source presence alone does not establish portable packaging or deployment.

## Requirements

1. Make mailbox and Planner exports privacy-minimised, deterministic and
   reconciled. Use keyed pseudonyms and explicit projection allowlists; prevent
   identities, narrative, tokens and secrets entering outputs or diagnostics.
2. Correct date-window construction and validation, pagination, duplicate/replay
   handling and interrupted-write behaviour. Publish success/completeness only
   after all checks pass. Preserve uncertainty about inaccessible populations.
3. Add offline PowerShell tests with mocked token/API calls and synthetic data,
   including privacy, pagination, empty results, repeated runs, partial failures,
   rejected records and date boundaries. Require no account for these checks.
4. Independently measure and enforce line and branch coverage. Add meaningful
   mining edge-case/property tests and document the simple metrics' limits.
   Validate the optional mining dependency separately without making it mandatory
   or representing simple sequence metrics as PM4Py token-replay results.
5. Make CodeQL activation and dependency-update ownership explicit. Keep pinned
   Actions and required checks; assess effective bot scopes before consolidating
   them. Do not lower assurance thresholds or enable automatic merges to reduce noise.
6. Provide reusable local ALM validation and packaging for the existing solution:
   environment-independent configuration, solution-aware flow conventions,
   connection-reference/environment-variable templates, versioning, artifact
   integrity, dry-run, export-before-change and rollback procedures.
7. Evaluate current PAC solution checking, deployment-settings generation,
   Power Platform pipelines and Fabric Git/deployment pipelines against actual
   project needs and permissions. Verify official documentation at implementation
   time; adopt supported features only where they improve the release process.
   Fabric capabilities remain optional when no authorised workspace is available.
8. Refresh current setup, CI, exporter, privacy and deployment documentation.
   Preserve dated historical evidence; annotate superseded conclusions rather
   than rewriting old runs as newly successful evidence.

## Acceptance criteria

- Synthetic executable tests demonstrate every corrected exporter defect and
  recovery case; repeat runs introduce no duplicate identities. Output schemas
  and consumers agree, and manifests reconcile candidates, events, exclusions,
  duplicates and failures without misleading completeness claims.
- Full application checks pass with separate line and branch results meeting
  90%, or the track remains open with the specific deficit recorded.
- PowerShell assurance runs locally and in CI without live authentication.
- Effective dependency-update scopes have documented owners without duplicate
  responsibility. A successful hosted CodeQL analysis and upload is recorded
  before its external task is completed.
- Local ALM checks reject malformed, secret-bearing and environment-bound
  fixtures. Packaging produces a versioned, integrity-checked artifact using
  supported tooling; repeatability and any unavoidable packaging variation are
  documented. Validation never silently imports or modifies an environment.
- Live promotion/rollback claims require authorised environment evidence;
  unavailable permissions or resources remain explicit external gates.
- Each phase has recorded verification and the final track has human approval.

## Dependencies and boundaries

Local implementation needs no tenant access. Hosted GitHub execution requires
publishing the reviewed changes and checking repository settings. VUW CLI
authentication, authorised environment discovery and delegated consent are a
separate setup stage; no credentials are stored in this track or repository.

Do not register Entra applications, require tenant administration, deploy to
production, broaden mailbox scope, ingest live data or install new platform
resources as part of planning. Product-specific solution construction and pilot
decisions remain in the Teams, Outlook and M365 discovery tracks. Credentialing
semantics and conformance models remain in the credentialing track.

Existing installed skills cover Conductor, Dataverse solutions, Microsoft 365,
Power Automate and Fabric ALM. No additional skill installation is required to
register this plan.
