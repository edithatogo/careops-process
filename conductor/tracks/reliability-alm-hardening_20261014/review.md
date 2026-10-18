# Review Report: Local reliability and ALM hardening

Current closure disposition: see [17 October closure review](closure-review-20261017.md).
The historical local review below remains scoped to its recorded revision.

## 18 October reconciliation

The bounded app-aware source adapter and navigation review fixes are committed in
`e7eaa50`, `14f8b96` and `ecb8fce`. Sixty-one scoped ALM tests pass; Coordination
independently verified all four hosted workflows at `ecb8fce`, including CodeQL
and 1,553 tests (97.60% line, 94.93% branch). Documentation `555f7d2` was pending
hosted verification at that handoff. No results are inferred for later revisions.

Personal Developer baseline import/export and restoration of the solution's
description are verified. This proves recovery of one metadata property only,
not schema/data rollback, managed promotion or disaster restore. See the
[independent hub rehearsal](../../../docs/vuw-hub-rehearsal-20261018.md) and
[app-aware validation limits](../../../docs/local-alm.md). The actual app export
remains refused because of declared platform dependencies and role mappings;
no component was relabelled and no validation bypass was introduced.

The isolated VUW Azure configuration now provides fresh verified Developer
organization/user identity. This does not grant missing TEST rights. Updater
ownership execution, executable cloud recovery and human verification remain open.

## Summary

Reviewed local implementation is ready for integration; the track remains open for
human checkpoints and hosted/live acceptance, and does not certify the moving shared revision.

## Verification Checks

- [ ] **Plan Compliance**: Partial — local technical tasks verified; Phase 6 and human checkpoints pending.
- [x] **Style Compliance**: Pass in the clean scoped snapshot.
- [x] **New Tests**: Yes — exporter, ALM, coverage and mining/rejection cases.
- [x] **Test Coverage**: Yes — 96.77% lines and 92.86% branches independently.
- [x] **Test Results**: Passed — 314 tests in fresh scoped checkout, offline Planner and delivered Outlook checks.

## Findings

### High — Planner interruption test assumed Windows sharing semantics (fixed)

- **File**: `tests/powershell/test_planner_export.ps1`, publication regression.
- **Context**: Unix can atomically replace a pathname while an open reader retains
  the original inode; expecting a sharing error would fail Ubuntu CI.
- **Resolution**: Windows verifies failure preserves prior bytes; Unix verifies the
  open reader sees old bytes and new pathname sees the replacement. Windows passed
  locally. Hosted Ubuntu execution remains pending rather than fabricated.

### Medium — Accepted solution JSON was not parsed (fixed)

- **File**: `src/careops_process/local_alm.py`, `_validate_files`.
- **Context**: A malformed accepted `.json` file passed source validation.
- **Resolution**: Regression first failed `DID NOT RAISE`; validator now parses every
  accepted JSON file and suppresses protected parse diagnostics. All 29 ALM tests pass.

### Medium — Case variations bypassed portability checks (fixed)

- **File**: `src/careops_process/local_alm.py`, protected/bound-value matcher.
- **Context**: Uppercase Dynamics URLs and camel-case clientSecret keys were accepted.
- **Resolution**: Two failing regressions now pass after case-insensitive matching
  and client-secret key spelling support; follow-up commit `351cbaa`.

## Review scope and decision

Fresh reviewer inspected the hardening-owned working-tree changes against spec,
workflow and style guides, including actual local PAC evidence. Root assessed
delivered Outlook regression separately. Implementation commit `d104961` contains
25 owned files; concurrent Teams/M365/Outlook/credentialing changes were preserved.
All actionable review/audit findings are fixed. No remaining local correctness finding
was identified in that scope. See [verification](verification.md) for audits,
exact evidence, transient integration failures and external limits.

Keep the track in progress and retain its files. Human phase/final verification,
hosted checks and authorised live promotion/recovery are required before completion.
No archive, deletion, external publication or live action was inferred from this review.
