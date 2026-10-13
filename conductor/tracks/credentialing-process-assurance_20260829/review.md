# Review Report: Credentialing process assurance — 2026-10-14

## Summary

The track is not ready for completion: deterministic fixes pass regression tests,
but native runtime failures are reproducible and required capabilities and pilot
gates remain open.

## Verification Checks

- [ ] **Plan Compliance**: Partial — minimum counters/reference/reporting are
  implemented; measurement, later-pathway and manual/live gates remain open.
- [x] **Style Compliance**: Pass — repository-wide Ruff lint and formatting pass;
  Pyright and Conductor validation pass at dcd50a2.
- [x] **New Tests**: Yes — deterministic boundary and restoration regressions.
- [x] **Test Coverage**: Yes — line 97.70%, branch 94.91%, measured independently.
- [ ] **Test Results**: Failed repeatability — the full suite passed 664 tests,
  but a fresh ten-process deletion/replay run passed only eight; one access
  violation and one Hypothesis FlakyFailure remain. Standalone probes also fail.

Both offline PowerShell regression scripts pass. Bandit JSON audit: zero findings
and parse errors (four configured skipped checks). Dependency audit: no known
vulnerabilities, unpublished local package unauditable. Offline Zizmor: no findings,
one suppression. Gitleaks: no leaks in the two review-fix commits. These scopes do
not establish reliability or live effectiveness. All fixtures are synthetic.

## Findings

Fixed: caller-owned tombstones and provenance records could mutate ledger state;
existing mutable projection models could bypass ingestion validation; deletion
preparation failures could leave deletion memory inconsistent with retained facts.
Constructor inputs are detached, model contents are revalidated at ingestion,
and tombstone replacements are prepared before state changes. Regression tests
demonstrate deletion replay safety, nested provenance isolation, invalid assignment
rejection and injected deletion-copy failure consistency. Constructor projection
isolation and unrelated-tombstone snapshot preservation also have regression tests.
Assessment and reporting additionally revalidate model contents. Restored deleted
inference is removed before retained-event provenance checks; deleted run links
are not required or retained. These follow-up defects were reproduced in failing
tests before fixes.

### High — Reproducible native runtime failures

- **File**: `src/careops_process/credentialing.py` (validation/serialization boundary).
- **Context**: fresh subprocesses reproduce access violations and intermittent
  malformed model results. A minimal nested Pydantic model with no CareOps imports,
  custom validators, pytest or Hypothesis also fails; serialization-only runs fail
  without deepcopy. The root cause remains unproven. Disabling cyclic GC, comparing
  Pydantic 2.12.5, Python 3.13.15 and Python 3.14.7 did not eliminate failure.
- **Suggestion**: keep completion gated; analyse the captured native exception and
  object ownership before applying a speculative runtime fix. A ProcDump full dump
  is now matched to the synthetic process PID 84172 and creation time. Limited
  offline metadata records thread 57196, read access violation targeting `0x14`,
  core module offset `0x16dfdc`; the matching faulthandler location is `model_dump`.
  The module location does not prove the root cause. No symbolized analysis or
  product dependency/runtime change has been made.

```diff
- Treat a single passing full-suite run as sufficient runtime evidence.
+ Require resolution and repeatable verification of reproduced native failures.
```

### Medium — Full requested measurement and review capability is incomplete

- **File**: `contracts/credentialing-assurance-measures.json` (line 78), track plan.
- **Context**: the minimum event counters do not implement delay, workload/capacity,
  quality evaluation or an evidence-bound human improvement-review workflow.
- **Suggestion**: review the proposed completion design, implement and verify its
  agreed stages, and keep live/source/manual gates open until evidenced.

```diff
- Accept minimum event counters as evidence for all assurance dimensions.
+ Verify each measurement and human-review requirement independently.
```

Present requirements: versioned ontology and projection contract, prohibited-field
rejection, observed/inferred separation, provenance requirements, replay/deletion
handling, synthetic renewal reference comparison, event counters, scoped reporting
and whole-report small-cell suppression.

Incomplete requirements: delay/stage-time, manual effort/capacity and quality
measures; separately mapped non-renewal pathways; a human-reviewed improvement
hypothesis workflow. Actual source completeness and denominators remain unverified.

External/manual gates remain open: approved CHHHS pathway/authority mapping,
pseudonymisation and vocabularies, trusted case grants, durable atomic storage,
concurrency, cross-release privacy, retrospective and prospective silent-mode
evaluation, governance approvals and maintainer acceptance. See the open plan
items. Final local checks above do not constitute integration-owner acceptance.
