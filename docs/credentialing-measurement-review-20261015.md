# Review Report: Credentialing measurement extension

## Summary

The extension implements local measurement and human-review contracts; full track
completion remains unproven because host/runtime reliability, live adapters,
approved local policy/source mappings and pilot/manual acceptance remain open.

## Verification Checks

- [x] **Plan Compliance**: Tasks 1–3 implemented at `5bfd37e`; Task 4 review and
  evidence are recorded here. Original Conductor scope is retained.
- [x] **Style Compliance**: Repository Ruff lint/format (113 files), strict Pyright,
  Bandit and Conductor validation passed at that executable checkpoint.
- [x] **New Tests**: Stage-time, observed effort, case-level quality, provenance,
  privacy and human-review tests use synthetic evidence and independent assertions.
- [ ] **Test Coverage**: Full-worktree coverage is unusable: its 192751-byte XML
  is entirely zero-filled. Historical scoped coverage does not replace this gate.
- [ ] **Test Results**: Scoped results are valid; the full-suite attempt is
  inconclusive, with no retained trustworthy terminal result. It is not a pass.

## Risk-linked test categories

| Risk | Assertions and evidence |
| --- | --- |
| Invented delays | Hand-calculated quantiles; observed endpoints only; missing/repeated/tied/reversed/qualifier-mismatched facts have explicit exclusions |
| Inflated case counts | Multi-object links count each granted case once; replay deduplicates exact kind/observation IDs; repeated consistent evaluations count one case/reference |
| Privacy through rare cells | Whole-report suppression covers nonzero outcome, eligible, exclusion, missing and completeness cells; grant strings/iterators are rejected; source IDs/times absent from aggregate/proposal payloads |
| Missing work treated as zero | Explicit observed zero differs from missing observations; work minutes/touches are observed deltas, never process-event counts |
| Misleading effort comparisons | Compatible versioned source/cohort definitions, ordered nonoverlapping half-open windows, source completeness and latest per-case effort attestations are required; tied/later partial work blocks complete coverage |
| Invalid quality claims | FP/(FP+TN), FN/(FN+TP) checked with independent two-case cells; zero denominators unavailable; contradictory labels and wrong approved reference fail closed |
| Unsafe retained input | Frozen observations revalidated on merge; tampered work values and proposal fields rejected; existing mutable projections revalidated/detached |
| Stale human review | Equal aggregates with replaced observed facts change fingerprints; changed threshold/version changes identity; row order does not; stale or repeated review rejected |
| Authority overreach | Review roles, opaque references and aware timestamps validated; only accepted/rejected/needs-more-evidence, explicitly measurement-review-only; no operational writer or AI dependency |
| Schema drift | Independent Draft 2020-12 validator with an active RFC3339 calendar checker validates runtime fractional-second exports for both variants and rejects invalid dates, offsets and excess precision |

Threshold suppression is one-report protection, not a solution to repeated-query
differencing. Controlled code syntax does not establish pseudonymisation or source
authenticity. Service authentication, trusted case mapping, current-policy resolution,
atomic persistence, retention and cross-release privacy controls remain required.

## Verification receipt

- Source base: `bbb347a81d907912316e2f6872adc672e27a7606`.
- Stage-time: `663a474ba020a9902296434b370c059cdd28199a` with container fixes
  `12bd50f` and `005b5e4`; 37 scoped tests pass.
- Observations: `a2a1e3b28ad4e1b208cfd71fd38701b9492cfab7`; 36 tests pass.
- Human review: `5bfd37e5abadcb0b77fa1e3a5f042d283662bac9`; 22 tests pass.
- Two additional fractional-export tests pass with independent schema round trips.
- Dependency audit: no known vulnerabilities; editable local package skipped.
- Gitleaks: six commits `bbb347a..5bfd37e`, no leaks; output redacted.
- Offline Zizmor: no findings, one configured suppression.
- Both offline PowerShell suites pass under `pwsh`. A preceding attempt under
  Windows PowerShell failed its HTTP type compilation and was corrected to the
  documented PowerShell runtime; that failure is not a product regression.
- Full attempt scratch directory:
  `.superpowers/sdd/2026-10-14-credentialing-measurements`.
  `full-suite.txt`: 6337 bytes, 5770 NULs beginning at offset 567,
  SHA256 `7a53e378648954d95d7203bed2094d23fe76504ee44873f31c1041341d9c7b59`.
  `final-coverage.xml`: 192751 NUL bytes,
  SHA256 `c4a776b8f93d145b8af620c55ddf3cbb303729be13521b4170f75803223a86ae`.
  Process inventory showed no live Python process after interruption. No repeat
  full run was used to conceal or replace the inconclusive receipt.

No dependency, interpreter, existing ledger/projection module, source connection,
shared deployment or live policy was changed by this isolated extension. Final
shared integration belongs to the coordinator; matched shared/hosted evidence is
separate from this worktree's checks.

## Remaining original scope

The original track remains in progress. Actual CHHHS/Queensland Health authority,
pathway, pseudonymisation, source and approved measurement definitions are not
supplied by synthetic tests. Baseline observation, approved retrospective and
prospective silent-mode cases, user/privacy/workload evaluation, live governance,
records/security/support/continuity gates and maintainer manual acceptance remain
open. Later pathway packs are separately owned work, not completed by this review.

No pilot or production approval is inferred. The native-runtime fault and newly
observed zero-filled artifacts still prevent a reliability/completion claim.

## Independent review

A fresh read-only reviewer inspected `bbb347a..5bfd37e`, source/tests/schema,
specification and implementation plan. No actionable correctness, privacy,
provenance or review-transition defect was found. The reviewer did not rerun
tests or claim a full-suite pass. Its minor finding was a stale paragraph in
`credentialing-measurements.md` describing the implemented observation/review
contracts as future work; that paragraph now links to the current manual,
dictionary and this receipt. Live authorization/recomputation and atomic
persistence remain explicit adapter obligations.

## Schema parity follow-up — 16 October

Independent Draft 2020-12 validation reproduced a concrete lexical mismatch:
the observation schema accepted `case_id` with a terminal newline, while the
runtime rejected it. A regular-expression `$` anchor can match before that final
newline. Nine failing regression fixtures covered both schema variants' source,
case, observation and timestamp fields plus the evaluation reference version.

Published patterns now add a negative lookahead for any remaining character,
requiring the true end of input without Python-specific regex anchors. All nine
fixtures pass. Independent schema/runtime validation agrees on two valid
fractional-second payloads and all nine invalid terminal-newline payloads.
The observation and lexical-schema slice passes 47 tests; scoped Ruff and strict
Pyright pass. No runtime, dependency, live binding or policy was changed.
This corrects the schema contract; it does not resolve host reliability.
