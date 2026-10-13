# Local verification — 14 October 2026

Implementation commits: `d104961` and ALM follow-up `351cbaa`. Local scope is Planner export, mining assurance,
independent coverage, CI/dependency ownership and shared table-solution ALM.
Outlook owns mailbox exporter delivery; M365 owns closed-run reconciliation/reporting;
Teams owns hub components; Credentialing owns its assurance. Their concurrent
working-tree changes were preserved and excluded from this implementation commit.

## Phase 1: Reproduced defects and contracts

Read exporters and their ingestion/acquisition consumers. Facts retain the five
canonical fields (`id`, `activity`, `timestamp_utc`, `source_system`, `object_ids`);
export wrappers carry separate reconciliation evidence. Planner candidates can
emit two events, so event and source counts are distinct. No shared schema was
silently expanded to accommodate wrapper metadata.

The initial real mailbox regression failed `Raw protected data persisted`.
The initial Planner regression failed because the empty facts pipeline produced
null rather than an array. Tests were written before replacing the Planner
implementation. Synthetic token/API calls are mocked; serialization/publication
and actual scripts execute. Further tests exercise domains, ordering, replay,
invalid records, conflicts, unsafe/repeated continuation, retry budget and failures.

Manual checkpoint: prepared; awaiting human review of synthetic cases and limits.

## Phase 2: Export reliability

Planner requests only identifiers and lifecycle dates, uses domain-separated
keyed pseudonyms, sorts facts deterministically, measures duplicate/rejected
candidates and retries, and stages facts and manifest in one same-filesystem
atomic replacement. Rejected candidates do not create partial lifecycle events.
Failures emit sanitised diagnostics and preserve prior snapshots. Success records
assigned-task pagination exhaustion and leaves tenant-wide coverage unknown.

The offline Planner script passes, including bounded 429 retry and an interrupted
Windows publication that preserves prior bytes. The review found Unix rename
semantics differ: the test now verifies old-reader/new-path consistency on Unix
instead of expecting Windows sharing failure. That Unix branch requires hosted
Ubuntu execution; it is not claimed as executed on this Windows host.

Delivered Outlook regression passes for privacy, date boundaries, pagination,
replay and failure paths. This is working-tree evidence from its owner, not a
mailbox implementation committed by this track or a full-mailbox/live claim.

Manual checkpoint: prepared; require review of key custody, scope, rejection policy
and previous-output recovery before a live smoke test.

## Phase 3: Mining and coverage

Baseline shared snapshot: 250 tests passed; lines 1594/1687 (94.49%), branches
444/506 (87.75%). The combined score hid the branch deficit.
Added edge/property and rejection-path tests; no mining algorithm defect was
reproduced. Documented position-match fitness and observed-activity-set precision;
neither is PM4Py token replay. The new XML-count gate independently requires 90%
for lines and branches. Existing aggregate pytest threshold remains additional.

Normal and isolated mining profiles pass locked sync and lock consistency checks.
PM4Py 2.7.23.8 native synthetic OCEL JSON import preserves expected IDs/activity/
relations; normal fresh profile has no mandatory PM4Py installation. Both installed
profiles pass pip-audit, with the unpublished local project skipped. Licence review
is still required. Pre-existing generated PM4Py lock correction was inspected and
retained; `defusedxml` moved from dev to runtime for safe ALM parsing.

Manual checkpoint: prepared; review metric limitations and separate licence gate.

## Phase 4: CI and updater ownership

Pinned CodeQL workflow no longer silently skips on `ENABLE_CODEQL` and supports
manual dispatch. Actual hosted analysis/upload and repository eligibility remain
unverified. CI runs locked dependencies, independent coverage and offline PowerShell
scripts; optional mining stays a separate opt-in job. Zizmor offline scan passes
with one existing suppression. Renovate strict local configuration validation exits
zero; the available npm validator resolved to older 37.440.7, so this is a syntax/
compatibility check, not current hosted effective-config proof.

Inspected shared preset at `f16a84f40c6a6cf1e61c8d96051d272de647342e`.
Local Renovate now permits only git-submodules and overrides inherited automerge.
Dependabot owns Python/uv and SHA-pinned Actions. Hosted bot execution/security
settings/required checks remain separate acceptance tasks.

Manual checkpoint: prepared; review ownership and hosted acceptance checklist.

## Phase 5: ALM and clean snapshot

ALM supports the current two-table harvest; validates structure/version/references,
safe XML/JSON and protected/bound-value patterns; uses actual local PAC pack and
create-settings commands; publishes integrity-checked immutable release directories;
requires a pre-change export artifact for preparation and managed/version progression
for downstream promotion. Unknown component types/binaries require explicit adapters.
Configuration examples are tenant-neutral; real bindings remain ignored.

Actual PAC 2.13.1 packed the harvest twice, verified both releases and generated
empty settings without authentication. Source hashes matched across all 29 files;
ZIP hashes varied. See local-alm documentation for digests, official sources, and
managed/promotion/rollback limits. Online checking, import and rollback were not run.
Review reproduced malformed JSON passing validation; the new test failed before
JSON parsing was added, then all 29 ALM tests passed with sanitised diagnostics.

Clean scoped checkout: Git clone of baseline `01f8c5d` plus the exact 25 owned files
listed in implementation commit `d104961` and the two-file `351cbaa` follow-up, excluding concurrent uncommitted product work.
Fresh virtual environment; `uv sync --locked --group dev` succeeded.
Its isolated `coverage-fresh.xml` reports **314 tests passed**, lines **1797/1857
(96.77%)**, branches **533/574 (92.86%)**. Ruff formatting/lint, strict Pyright,
Bandit and Planner PowerShell regression pass. Full-history Gitleaks scans 92 commits
with no leaks; candidate snapshot directory scan also passes, with release checksum
verified for the downloaded scanner. No broad exclusions were added.

Evidence is retained privately in `artifacts/hardening-owned-fresh-path.txt`, the
referenced temporary checkout's `fresh-suite.log`/`coverage-fresh.xml`/`sync.log`,
and `artifacts/hardening-*-secret-scan.json`. Coverage datasets are isolated so
concurrent focused runs cannot replace this full scoped run's denominator.

Current README/runbooks updated; dated feasibility and solution-harvest documents
are annotated with superseding local evidence, preserving historical claims.
No change to product identity, platform strategy or core guidelines was needed.

Manual checkpoint: prepared; review local artifacts and downstream release gates.

## Concurrent integration evidence and limitations

Earlier integrated shared suite passed 387 tests (97.11% lines, 92.84% branches).
Later snapshots caught other owners' intentional RED stages: Outlook reconciliation
`NotImplementedError` (24 failures, 412 passed), and Teams `hub_domain` not yet
importable. Those changes were not reverted or included in the clean scoped claim.
One later Windows runtime access violation occurred in Pydantic deep-copy during
credentialing; a focused retry passed all 27 credentialing tests. Root cause of
that intermittent native crash is not established. Final shared revision verification
belongs to the coordinator after owners finish; this record does not certify it.

An initial broad candidate secret scan flagged two synthetic examples in Planner
test and Outlook runbook. Planner now derives its synthetic key from test bytes;
Outlook's owner updated its example. The scoped candidate and Git history scans
then passed; no real credential was detected and no matched value was published.

## Phase 6 and human completion

Pending: separately agreed VUW CLI setup/access/consent, publication, actual hosted
Actions/CodeQL SARIF and updater evidence, approved low-sensitivity smoke/replay,
non-production checker/binding/import/export/recovery, selected optional resources,
cross-track evidence integration and human approval. No live extraction, tenant
change, resource creation, push, PR, deployment or governance approval was performed.
The registry and metadata remain in progress; retain the track for those gates.

## Final acceptance audit follow-up

Two additional tests reproduced portability bypasses for uppercase Dynamics URLs
and camel-case clientSecret keys (`DID NOT RAISE`). Commit `351cbaa` rejects both;
29 ALM tests and the full 314-test clean scoped run pass. No bound value or matched
secret is retained in public evidence. Scope, human and external gates above remain
unchanged. Technical local tasks are handled; final shared integration remains pending.