# Review Report: Authorised M365 corpus-scale process discovery

## Summary

The v2 evidence/report consumer closes the reproduced local scope, count, lineage and diagnostic gaps; complete track acceptance remains pending live evidence, owner decisions and final shared-repository verification.

## Verification Checks

- [ ] **Plan Compliance**: Partial — local evidence/reporting is implemented; Phases 6–7 live and human gates remain open.
- [x] **Style Compliance**: Pass for owned files — scoped formatting, Ruff and strict Pyright passed.
- [x] **New Tests**: Yes — 32 bound-evidence cases, six Outlook integration cases, four CLI subprocess cases and added report context/determinism/freshness checks.
- [x] **Test Coverage**: Reviewed scoped snapshot — 2384/2444 lines (97.55%) and 653/694 branches (94.09%), independently gated. Final whole shared-tree coverage remains a separate coordinator gate.
- [x] **Test Results**: 485 tests passed in a fresh isolated M365/Outlook snapshot; publication/CLI cases pass. Concurrent shared-tree verification remains distinct; see below.

## Scope and implemented fixes

This review covers the M365 v2 schema and consumer, closure handoff, report artifacts, CLI diagnostics, associated synthetic tests and operator interface. It follows commit `5903415`, which fixed checkpoint ordering, duplicate action IDs and count types. Shared Outlook acquisition/reconciliation and hardening changes are integration dependencies, not files authored in this change. Unrelated shared changes were preserved.

The consumer requires an exact frozen partition inventory, explicit timezone-aware observation period, approved destination/retention/mapping references, frozen full-inventory hash, exact configuration hash and input hash. Every fact belongs to exactly one partition. Each partition separately reconciles source candidates against acquired/duplicate/rejected/filtered records and emitted fact identities. Source records may emit multiple lifecycle events. Empty exhausted folders remain explicit. Wrong scope, missing membership, duplicate IDs, raw extra fields, changed hashes and out-of-period facts are rejected.

`close_reconciled_run` requires two successful source/destination reconciliations. Both must match the frozen inventory hash and each other on complete canonical facts and partition accounting. It validates both snapshots against the consumer and retains hashes of the initial and replay reconciliation artifacts. A mailbox `acquired` result, missing destination, changed replay or changed inventory cannot close. Synthetic integration exercises the Outlook producer through closure and the authorised report, including empty folders and a duplicate source record.

The approval configuration hash and exact scope must match the run. Reports retain evidence class, partition/configuration hashes, both reconciliation hashes, OCEL, candidate landscape, operational patterns, quality and a coverage ledger with source/event counts kept separate. Owner validation remains pending and tenant-wide coverage unknown. Restricted analytical artifacts do not become owner-validated executive findings.

CLI validation failures now omit payload-bearing exception diagnostics and preserve a previous output. A new regression reproduced direct publication damaging the old report on disk failure and a subprocess regression reproduced output overwriting its own input. Publication now stages/fsyncs/replaces complete JSON, removes failed stages, and rejects input/output aliases; serialization and replacement failures preserve the authoritative report. Closure configuration model errors are also sanitized. A single generation timestamp now supplies both report and semantic projection; fixed-input/fixed-time reports rebuild identically.

## Findings

### High — Live acceptance and authoritative evidence remain unverified

- **File**: `conductor/tracks/m365-corpus-process-discovery_20260719/plan.md`, Phases 6–7.
- **Context**: Local functions verify supplied artifacts, not their origin, source-system completeness or whether two actual live acquisitions happened. No source-owner/IG approvals, closed live corpus, operational-owner validations or executive decision were established by this work.
- **Suggestion**: Follow the documented handoff using actual approved folder/page/source/destination artifacts and independent replay. Retain both reconciliation artifacts in the authoritative store, obtain operational-owner review, then record the Executive decision. Keep the track in progress.

### Medium — Shared in-progress product work remains outside scoped verification

- **Files**: actively edited Teams domain/decision/view modules and tests; shared aggregate coverage.
- **Context**: The earlier shared 494-test snapshot passed, but a later full-suite attempt stopped at collection because `tests/test_hub_views.py` imported an as-yet-unimplemented `careops_process.hub_views` module. Shared lint also reported an active Teams decision docstring/import issue, and shared typing reported unresolved view symbols. These source-owner RED/GREEN stages were preserved and excluded from the fixed-scope snapshot.
- **Suggestion**: The coordinator verifies the final shared revision after all source owners commit. The scoped snapshot verifies M365 and the delivered Outlook evidence interface, not unfinished Teams product work.

## Reproducible scoped verification — 14 October 2026

The isolated snapshot uses committed baseline `75613ab` plus the exact captured
M365 publication/CLI files, delivered Outlook reconciliation module/tests and
Outlook backfill-contract validator/tests. Uncommitted Teams product code and
live exporter/operator work are excluded. Its complete pytest suite passed all
485 tests, with independent line coverage 2384/2444 (97.55%) and branch coverage
653/694 (94.09%). Locked `uv sync`, Ruff formatting/lint, strict Pyright, Bandit
and pip-audit passed; the local unpublished project is skipped by the PyPI audit.
All captured overlay hashes still matched the shared files after verification.

Private reproducibility artifacts are at
`C:/Users/doughnut/Documents/Codex/2026-10-14/c/work/m365-verification-22305927`:
`snapshot-evidence.json` records the baseline, overlay file hashes and exclusions;
`verification-result.json` records observations and `coverage.xml` hashes/counts.
No shared `.coverage` or aggregate report was overwritten.

The isolated run is stronger evidence for this reviewed change than an evolving
shared-tree snapshot, but does not establish final whole-project acceptance,
hosted checks, live source verification or human decisions. An earlier transient
Windows access violation remains in the historical record; later scoped and
shared complete runs succeeded. No private source payload was used in tests.

## Acceptance evidence matrix

| Specification criterion | Repository evidence | Live/human evidence | State |
| --- | --- | --- | --- |
| 1. Signed coverage ledger | v2 inventory/coverage schema and report context | Owner/IG sign-off absent | Pending |
| 2. Complete approved historical acquisition per admitted family | Outlook acquisition/consumer interfaces | Actual approved runs absent | Pending |
| 3. Source/event reconciliation per partition | Strict consumer; Outlook supplied-ledger reconciliation; negative tests | Authoritative page/destination records absent | Local capability verified; live pending |
| 4. Empirical families and variants with confidence/stability | Discovery library and same-run report | Live combined corpus absent | Pending live |
| 5. Cross-source/object correlations and uncertainty | Existing reconstruction/landscape tests | Live ambiguous links not reviewed | Pending live |
| 6. Operational owners accept/reject/merge/split | Review queue capability exists | Owner decisions absent | Pending |
| 7. Coverage-honest executive views | Restricted candidate report and semantic projection | Validated live executive landscape absent | Pending |
| 8. Synthetic/smoke/live separation | Explicit evidence class; claim safeguards; synthetic integration labels | No live finding published | Local verified |
| 9. Idempotent repeat/incremental refresh | Two-snapshot closure checks and deterministic rebuild tests | Actual independently repeated run absent | Pending live |
| 10. Quality/security/privacy/licence/records gates | Scoped checks pass; aggregate work ongoing | Hosted/live determinations absent | Partial |
| 11. Executive fit-for-purpose decision | No automatic decision or workflow change | Executive decision absent | Pending |

## Decision and handoff

Retain the track and its open human/live checkpoints. Local M365 artifacts are ready for scoped integration; full completion is not claimed. The final source-to-report interface is documented in `docs/closed-run-evidence-v2.md` and `docs/closed-run-report-cli.md`; its strict machine schema is `contracts/closed-run-evidence-v2.schema.json`. Outlook supplies the actual folder/page/destination reconciliations. Hardening owns exporters outside Outlook, dependency/CI safeguards and authoritative aggregate coverage. No synthetic record was recorded as live approval or tenant evidence.


## User account/stage clarification — 14 October 2026

The user clarified that VUW is a test account only and that the actual pilot is
intended for Queensland Health. The approval preparation has been corrected:
VUW has a synthetic-first development/integration test plan; the Queensland
Health decision brief and pilot-entry draft remain unapproved. This resolves
the earlier account/stage ambiguity, not the actual Queensland Health authority
or live-evidence gates. Outlook owns VUW authentication; the coordinator owns
final combined verification. No duplicate login or unattended polling is needed.


## Integrated blocker receipt — 14 October 2026

The coordinator's `898d1b1` checkpoint records successful repository-wide
Conductor/Ruff/typing/Bandit checks at `bbb347a`, 203 scoped Teams feature tests,
and both offline exporter PowerShell suites after `cd934bc`. This strengthens
integration evidence without establishing final full-suite coverage or live
acceptance. See [the coordinator receipt](orchestration-checkpoint-20261014.md).

### High — Native processing runtime reliability remains unproven

The credentialing-owned finite investigation reports failures in standard-library
JSON as well as Pydantic serialization, with corrected processor-parity events
as a diagnostic lead. No host root cause or safe remedy is proven. This newer
receipt supersedes treating the earlier access violation as a closed transient
issue. The M365 scoped 485-test pass remains valid for that captured run; it does
not establish that repeated live corpus processing is operationally reliable.

Keep the runtime/operational-feasibility gate open. The native investigator owns
the minimal reproduction, exact build/failure counts and proposed remedy; the
coordinator owns matched final-revision verification. Do not duplicate that
investigation, alter shared dependencies from an unproven Pydantic hypothesis,
or infer live fitness from the scoped pass.

The next M365 pilot inputs remain authentic Queensland Health account/source
access, admitted scope, data-owner/IG decisions, storage/retention/rollback and
actual reconciled/replayed corpus evidence. VUW is development testing only.
No authentication polling, duplicate sign-in or unattended follow-up is required
from this chat while human sign-in or recorded decisions are needed.


## VUW connection-route update — 14 October 2026

The Outlook receipt now records verified VUW Azure/Graph identity and Power
Automate environment access, operator authorisation for the limited Inbox-only
seven-day metadata development test outside Git, and selection of an existing
Outlook connection in the developer environment. The initial unconfirmed-scope
note is historical; this newer receipt does not make VUW an organisational pilot.

The Graph mail-token route is unavailable. FlowAgent authentication and exact
connection binding remain incomplete, with no mailbox extraction or connection
identity verification yet established. Outlook owns that blocker. M365 does not
start duplicate authentication or repeat answered scope requests. Full Queensland
Health pilot decisions, corpus evidence, runtime remedy, owner validation and
Executive acceptance remain independent gates.


## Connection discovery correction — 14 October 2026

The developer environment was a proposed connection location, not a verified
binding: later discovery found zero connections there. The user selected VUW
STAFF Default for connection discovery. Outlook alone owns that lookup. VUW
Azure/FlowAgent identities match the test account, but an appropriate usable
Outlook connection has not been established by this receipt.

Update the test prerequisite to discovery and exact binding in the newly selected
environment. Do not repeat authentication, modify credentials, create a duplicate
connection or assume permission to use another owner's connection. MFA remains
human. This environment change does not approve extraction, change the actual
Queensland Health pilot target or fill its pending owner/IG record. No direct
notification/alert route is established by this work.


## Completed VUW connection scan — 14 October 2026

The Outlook completion audit now records checks of all seven accessible VUW
environments, including the final VUW-AI-TEST browser check using the existing
session. No existing Outlook connection was found for this operator. This
supersedes the earlier pending-discovery prerequisite. No mailbox data was read
and no new connection was created.

The next VUW test dependency is the operator's environment choice for a new
Office 365 Outlook connection, already requested in the Outlook chat. Outlook
owns creation and exact binding after that choice; this chat does not duplicate
the request or repeat authentication. Browser login to Queensland Health is
reported by the user, but its actual pilot scope and owner/IG decisions remain
pending. The full corpus track remains in progress.
