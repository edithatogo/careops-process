# Plan

## Phase 1 — Inventory

- [x] P1.1 Inventory every active Python surface and distinguish historical/version-test fixtures; see [inventory.md](inventory.md).
- [x] P1.2 Verify repo-local interpreter version and safe environment handover; `.venv/bin/python -VV` reports Python 3.15.1 after a new `uv sync --locked --group dev`.
- [x] P1.3 Review phase evidence and checkpoint under the repo workflow.

## Phase 2 — Qualification

- [x] P2.1 Reuse [merged migration](https://github.com/edithatogo/careops-process/pull/96) without repeating unchanged tests.
- [x] P2.2 Align current setup guidance and qualify the supported frozen dependency graph path; retain the unsupported optional Dependabot uv updater as an evidence-based exclusion.
- [x] P2.3 Verify phase evidence and checkpoint.

## Phase 3 — Integration

- [x] P3.1 Run affected structure/privacy checks and exact-head required checks; merge eligible work and verify main.
- [x] P3.2 Audit every acceptance requirement and explicit external blocker.
- [ ] P3.3 Record actual goal-tool result; close only when full evidence supports completion.

## Current boundary

A track or prompt is not an armed goal or completed runtime migration. Shared chat goal creation was rejected due to its unfinished goal.

The current CareOps absorption goal is active, so P3.3 remains open for its
final status record and requirement-by-requirement closure.

The optional Dependabot uv graph updater rejects Python >=3.15,<3.16 because
that provider supports only through 3.14. The supported replacement is already
qualified on the exact selected main commit: the main-only frozen dependency
graph run accepted GitHub snapshot `113632141` and passed exact graph readback.
Do not downgrade or bypass the provider limitation. CareOps issue #175 records
and closes this as an evidence-based exclusion.

## Inventory and exact-runtime checkpoint — 25 October 2026

The active runtime surfaces and old-version references are classified in
[inventory.md](inventory.md). The repo-local `.venv` was absent before this
checkpoint, so it was created rather than replacing an existing environment.
`uv sync --locked --group dev` resolved the committed lock and installed 49
packages; `.venv/bin/python -VV` reported Python 3.15.1. Current setup guidance
now uses the exact 3.15.1 pin; dated 3.14 receipts remain historical. `uv lock
--check` passed, and `uv run --no-sync python scripts/validate_conductor.py`
reported valid Conductor configuration, tracks and pinned skill entrypoints
after the exact nested plugin submodules were initialized. On source main, run
`40095092122` passed Python 3.15.1 quality, test, coverage, lint, type, security
and offline PowerShell steps; run `40095092121` passed exact frozen graph
submission and readback. Those are exact-main receipts, not results from this
documentation branch. This local checkpoint ran no tests.

## Integration closeout evidence — 25 October 2026

PR107 merged as `898a1157eed6aed187845421c6c6db44ad1f6ac9`. Its exact-head
checks passed: Python 3.15 quality/tests, CodeQL, shared source security and
reproducible wheel/content inventory. Exact-main runs `40168287869`,
`40168287884`, `40168288083` and `40168287875` passed; optional PM4Py remained
conditionally skipped. The updated setup, active-surface inventory and
dated-evidence classifications are included in that merged commit.

The acceptance audit found no remaining Python version/dependency/setup gap
within this child source. Keep the pytest-difftest0.3.0 PyO3 ceiling and
Dependabot uv graph updater's through-3.14 limit as explicit evidence-based
exclusions; no override or downgrade was used. The frozen graph path passed
exact submission/readback on the preceding selected main commit, with accepted
snapshot `113632141`. These provider limitations do not prevent required
Python 3.15.1 source qualification. P3.3 remains open because the overall
CareOps absorption goal is active; native/runtime acceptance is separate.
