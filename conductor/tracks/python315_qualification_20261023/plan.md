# Plan

## Phase 1 — Inventory

- [x] P1.1 Inventory active Python surfaces: `.python-version`, `requires-python`, CI, package, dependency-inventory and development-canary runners all select or enforce Python3.15.1. Remaining older-version references are dated receipts/plans or deliberate synthetic version cases, not active defaults.
- [x] P1.2 In the isolated selected-source checkout, create `.venv` from the previously qualified repo-local Python and verify `.venv/bin/python --version` reports Python3.15.1 before installing the locked development group. No active job or environment was replaced.
- [ ] P1.3 Review phase evidence and checkpoint under the repo workflow.

## Phase 2 — Qualification

- [x] P2.1 Reuse [merged migration](https://github.com/edithatogo/careops-process/pull/96) without repeating unchanged tests.
- [x] P2.2 Align current setup and runtime documentation to Python3.15.1. The exact-main frozen dependency graph workflow passed on selected source `5c2cc222cc4cbb97e1f34bcf9f8c28404fdee8c5` (`40095092121`); the separate Dependabot uv graph updater failure (`40095095610`) remains a provider limitation and is not bypassed or represented as success.
- [ ] P2.3 Verify phase evidence and checkpoint.

## Phase 3 — Integration

- [ ] P3.1 Run affected structure/privacy checks and exact-head required checks; merge eligible work and verify main.
- [ ] P3.2 Audit every acceptance requirement and explicit external blocker.
- [ ] P3.3 Record actual goal-tool result; close only when full evidence supports completion.

## Current boundary

A track or prompt is not an armed goal or completed runtime migration. Shared chat goal creation was rejected due to its unfinished goal.

GitHub uv dependency-graph run 39950579338 rejects Python >=3.15,<3.16 because its updater supports only through 3.14. Source tests pass. Preserve 3.15; qualify a supported graph path separately.
