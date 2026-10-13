# Review Report: Credentialing process assurance — 2026-10-14

## Summary

The track is not ready for completion: deterministic fixes pass regression tests,
but native runtime failures are reproducible and required capabilities and pilot
gates remain open.

## Verification Checks

- [ ] **Plan Compliance**: Partial — minimum counters/reference/reporting are
  implemented; measurement, later-pathway and manual/live gates remain open.
- [x] **Style Compliance**: Pass — repository-wide Ruff lint and formatting pass;
  Pyright and Conductor validation pass after f2c2eed (source checkpoint 7ecd397).
- [x] **New Tests**: Yes — deterministic boundary, restoration, direct-merge
  source-field validation, summary rejection and nested snapshot isolation tests.
- [ ] **Test Coverage**: Partial — current scoped line 99.33%, branch 98.91%;
  both credentialing modules individually reach 100% line and branch coverage.
  The latest full run crashed and produced no completed coverage report. Earlier
  repository-wide line 97.70% and branch 94.91% are historical evidence only.
- [ ] **Test Results**: Failed full run — 81 scoped tests pass, but the latest
  full run crashed with 0xC0000005 in
  `test_arbitrary_deleted_stage_sets_never_reappear`. Earlier full-suite evidence
  was 664 passes; repeated deletion/replay and standalone probes still fail.

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

Direct merges now revalidate and detach both input projections, including nested
source-field values; the metrics function revalidates before counting. Four new
cases first demonstrated invalid mutated source acceptance, unsafe counting and
caller mutation of returned history, then passed after fixes. Scoped lint/format,
Pyright, Bandit and patch secret checks pass. This changes contract correctness,
not the unresolved native-runtime finding.

### High — Reproducible native runtime failures

**New isolation evidence (2026-10-14):** the standard-library-only synthetic
deepcopy/JSON workload fails with CPython 3.14.8 both normally (1/16 processes)
and with `-S` (2/16). It also produces native access violations on a separate
CPython 3.13.15 installation (2/12). It imports neither Pydantic nor CareOps.
A plain-Python serialization comparison still failed (2/24); therefore replacing
`model_dump` is not a demonstrated remedy. Corrected processor parity events
and a 12/12 passing process-local CPU-0 arm support a host-stability lead, not
proof of the precise cause. The private diagnostic package contains exact
scripts, interpreter builds, results, hashes and capture limitations. Machine
operator firmware/hardware intervention and repeatable unpinned verification
are now the concrete next actions. No product dependency or machine-wide
setting was changed; the native-runtime finding remains open.

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
  Saved exception registers and instruction bytes agree: `rdx=0x14` and the fault
  instruction reads `byte ptr [rdx]`. This confirms the immediate invalid read,
  not the origin of the pointer. A separate probe disabling GC before Pydantic
  imports/model definitions also failed, with zero collector callbacks observed;
  the proposed GC workaround remains unverified.

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

The requirement-by-requirement [completion audit](completion-audit.md) records
the remaining specification, acceptance, plan, artifact and evidence gates.
Fresh schema and diagram validation passes, with explicit RFC3339 format
checking. This does not resolve the native failure or missing full-pack features.
