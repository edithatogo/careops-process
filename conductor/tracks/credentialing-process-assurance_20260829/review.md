# Credentialing process assurance review — 2026-10-14

## Summary

Partial acceptance of the disconnected repository tranche. The track remains in
progress; this review does not approve live ingestion or certify operating
effectiveness. Independent read-only review identified three actionable defects;
the implementer reproduced them and added passing regression tests after fixes.

## Verification Checks

- Credentialing and ontology slice: 77 tests passed.
- Fresh full repository run: 664 tests passed; combined coverage 97.06%, with
  line and branch coverage separately above 90%.
- Scoped Ruff lint and formatting, Pyright, and Conductor validation passed.
- All fixtures are synthetic. No live source writes or pilot evaluation occurred.

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

Unresolved runtime evidence: the independent reviewer observed a Hypothesis
FlakyFailure inside standard-library deepcopy; an isolated rerun and the final
full run passed. Earlier native Windows failures have no established root cause.
These changes are not evidence that the runtime issue is resolved.

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
