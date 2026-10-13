# Review Report: Authorised M365 corpus-scale process discovery

## Summary

The v2 evidence/report consumer closes the reproduced local scope, count, lineage and diagnostic gaps; complete track acceptance remains pending live evidence, owner decisions and final shared-repository verification.

## Verification Checks

- [ ] **Plan Compliance**: Partial — local evidence/reporting is implemented; Phases 6–7 live and human gates remain open.
- [x] **Style Compliance**: Pass for owned files — scoped formatting, Ruff and strict Pyright passed.
- [x] **New Tests**: Yes — 32 bound-evidence cases, six Outlook integration cases, four CLI subprocess cases and added report context/determinism/freshness checks.
- [ ] **Test Coverage**: Pending final aggregate snapshot — hardening owns the independent line/branch gate; historical combined scores are insufficient.
- [x] **Test Results**: Scoped pass — 60 targeted cases. Latest completed shared snapshot: 494 passed; earlier concurrent failures resolved. Shared typing still had one active Teams-test error; see below.

## Scope and implemented fixes

This review covers the M365 v2 schema and consumer, closure handoff, report artifacts, CLI diagnostics, associated synthetic tests and operator interface. It follows commit `5903415`, which fixed checkpoint ordering, duplicate action IDs and count types. Shared Outlook acquisition/reconciliation and hardening changes are integration dependencies, not files authored in this change. Unrelated shared changes were preserved.

The consumer requires an exact frozen partition inventory, explicit timezone-aware observation period, approved destination/retention/mapping references, frozen full-inventory hash, exact configuration hash and input hash. Every fact belongs to exactly one partition. Each partition separately reconciles source candidates against acquired/duplicate/rejected/filtered records and emitted fact identities. Source records may emit multiple lifecycle events. Empty exhausted folders remain explicit. Wrong scope, missing membership, duplicate IDs, raw extra fields, changed hashes and out-of-period facts are rejected.

`close_reconciled_run` requires two successful source/destination reconciliations. Both must match the frozen inventory hash and each other on complete canonical facts and partition accounting. It validates both snapshots against the consumer and retains hashes of the initial and replay reconciliation artifacts. A mailbox `acquired` result, missing destination, changed replay or changed inventory cannot close. Synthetic integration exercises the Outlook producer through closure and the authorised report, including empty folders and a duplicate source record.

The approval configuration hash and exact scope must match the run. Reports retain evidence class, partition/configuration hashes, both reconciliation hashes, OCEL, candidate landscape, operational patterns, quality and a coverage ledger with source/event counts kept separate. Owner validation remains pending and tenant-wide coverage unknown. Restricted analytical artifacts do not become owner-validated executive findings.

CLI validation failures now omit payload-bearing exception diagnostics and preserve a previous output. Closure configuration model errors are also sanitized. A single generation timestamp now supplies both report and semantic projection; fixed-input/fixed-time reports rebuild identically.

## Findings

### High — Live acceptance and authoritative evidence remain unverified

- **File**: `conductor/tracks/m365-corpus-process-discovery_20260719/plan.md`, Phases 6–7.
- **Context**: Local functions verify supplied artifacts, not their origin, source-system completeness or whether two actual live acquisitions happened. No source-owner/IG approvals, closed live corpus, operational-owner validations or executive decision were established by this work.
- **Suggestion**: Follow the documented handoff using actual approved folder/page/source/destination artifacts and independent replay. Retain both reconciliation artifacts in the authoritative store, obtain operational-owner review, then record the Executive decision. Keep the track in progress.

### Medium — Final shared typing and aggregate coverage need confirmation

- **File**: `tests/test_hub_domain.py:580`, plus shared aggregate coverage evidence.
- **Context**: The latest full suite completed with 494 tests passed. All five failures from the earlier 474/5 snapshot subsequently resolved; a separate 72-case Outlook/M365/Teams integration check also passed. Shared Ruff lint/format and Bandit passed. Strict Pyright reported one partially unknown `changes` dictionary in the actively edited Teams test; M365 scoped typing passed.
- **Suggestion**: The Teams owner resolves that typing error and the hardening owner produces final independent line/branch measurements for the consolidated snapshot. A previous passing coverage snapshot does not prove the current integrated tree's rates.

An earlier aggregate process exited after a Windows access violation while executing credentialing tests. It was confirmed terminal before retry; subsequent complete suites ran successfully. This was a transient observed runtime failure, not a reported test pass. The dependency audit reported no known vulnerabilities; the local project itself is not available on PyPI. Hosted CodeQL, full-history secret scans and live licence/records determinations were not performed here.

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
