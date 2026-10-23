# Plan

## Phase 1 — Inventory

- [ ] P1.1 Inventory every active Python surface and distinguish historical/version-test fixtures.
- [ ] P1.2 Verify repo-local interpreter version and safe environment handover.
- [ ] P1.3 Review phase evidence and checkpoint under the repo workflow.

## Phase 2 — Qualification

- [x] P2.1 Reuse [merged migration](https://github.com/edithatogo/careops-process/pull/96) without repeating unchanged tests.
- [ ] P2.2 Close remaining runtime, lock, dependency and current setup-document gaps with focused checks.
- [ ] P2.3 Verify phase evidence and checkpoint.

## Phase 3 — Integration

- [ ] P3.1 Run affected structure/privacy checks and exact-head required checks; merge eligible work and verify main.
- [ ] P3.2 Audit every acceptance requirement and explicit external blocker.
- [ ] P3.3 Record actual goal-tool result; close only when full evidence supports completion.

## Current boundary

A track or prompt is not an armed goal or completed runtime migration. Shared chat goal creation was rejected due to its unfinished goal.

GitHub uv dependency-graph run 39950579338 rejects Python >=3.15,<3.16 because its updater supports only through 3.14. Source tests pass. Preserve 3.15; qualify a supported graph path separately.
