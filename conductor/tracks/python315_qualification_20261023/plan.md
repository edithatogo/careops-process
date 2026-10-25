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

- [ ] P3.1 Run affected structure/privacy checks and exact-head required checks; merge eligible work and verify main.
- [ ] P3.2 Audit every acceptance requirement and explicit external blocker.
- [ ] P3.3 Record actual goal-tool result; close only when full evidence supports completion.

## Current boundary

A track or prompt is not an armed goal or completed runtime migration. Shared chat goal creation was rejected due to its unfinished goal.

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
