# Review Report: Authorised M365 corpus-scale process discovery

## Summary

Two reproduced validation defects are fixed and tested; the track remains unfit for live-pilot completion until evidence binding, shared exporter hardening, independent branch coverage and human gates are resolved.

## Verification Checks

- [ ] **Plan Compliance**: Partial — phases 6–7 and the shared hardening prerequisite remain open.
- [x] **Style Compliance**: Pass — Ruff formatting, lint and strict Pyright pass.
- [x] **New Tests**: Yes — 21 new cases cover action ordering, unique IDs, malformed flow contracts and invalid closed-run counts.
- [ ] **Test Coverage**: Partial — 94.38% lines and 87.55% branches; the combined 92.80% score does not prove both independent targets.
- [x] **Test Results**: Passed — 219 tests at the reviewed working-tree snapshot, including concurrent credentialing tests.

Conductor validation, Bandit and pip-audit also passed. The local project is not available on PyPI and is excluded from pip-audit's dependency lookup. Hosted CodeQL, workflow security and full-history secret scans were not executed in this session.

## Scope and implemented fixes

Reviewed the working-tree flow-contract and closed-backfill changes against the track specification and inspected the report, ingestion, exporter and pilot-entry boundaries. The plan has no implementation commit range, so this is a scoped implementation/readiness review, not a claim of exhaustive historical review. Concurrent uv.lock and credentialing changes were preserved and excluded from this change.

The flow validator now requires unique action IDs and the full read-checkpoint → project-fact → validate-watermark → write-projection → advance-checkpoint order. Four regression cases failed before the fix. Additional malformed-action and failure-policy tests exercise fail-closed behavior. Removed a redundant type check already enforced on every action.

The closed-run gate now rejects negative counts, booleans and string counts. All nine regression cases failed before the fix and pass afterward. Counts are source-record counts, so this fix intentionally does not assume they equal event counts.

## Findings

### High — Closed-run completeness is declared rather than reconciled

- **File**: `src/careops_process/backfill_run.py`, required-field and boolean-gate validation; authorised wrapper.
- **Context**: The gate validates count shape and declared flags, but does not verify folder/partition manifests, candidate/acquired/rejected/duplicate reconciliation or bind input partitions to the approved scope. A positive candidate count unrelated to supplied facts is still accepted when the flags are true. The wrapper validates approval fields independently of the actual run. This does not meet the specification's per-partition completeness proof.
- **Suggestion**: Define a versioned per-partition evidence contract, require scope membership, compare measured counts with documented source-to-event cardinalities, and bind facts/configuration hashes to the run. Add negative tests for wrong scope, missing partitions, conflicting counts and changed inputs. Keep the pilot pending until this is implemented.

### High — Historical mailbox exporter persists protected identifiers

- **File**: `scripts/Invoke-GraphMailboxBackfill.ps1`, lines 38–45 and 52.
- **Context**: The exporter writes subjects, sender/recipient addresses, raw message/folder identifiers and mailbox identity. It appends to an existing event file, so replay is not an idempotent snapshot. Its filtered query also contains a literal backtick before `$filter` at line 22. These are concrete prerequisites already assigned to the reliability/ALM hardening track.
- **Suggestion**: Complete that track's allowlisted projection, keyed pseudonyms, corrected query construction, atomic output, reconciliation and offline PowerShell tests before using this exporter. No live exporter was run during this review.

### High — Independent branch coverage gate remains unmet

- **File**: `pyproject.toml`, pytest addopts; `.github/workflows/ci.yml`, pytest step.
- **Context**: The current pytest gate checks combined coverage. It passed at 92.80% while branch coverage was only 87.55%, below the required 90%. The shared hardening plan already owns the independent gate.
- **Suggestion**: Enforce each XML coverage rate separately and add behavioral coverage for remaining failure paths. Do not mark the assurance task complete based on the combined score.

## Decision and remaining gates

Fix the high findings before live extraction or publication. Keep this track in progress and retain its existing manual checkpoints. Source-owner/information-governance approvals, observation/configuration freeze, approved destinations and retention, complete-population extraction, replay, operational-owner validation and executive decision remain unverified. No approvals were inferred or fabricated, and no live data was extracted.
