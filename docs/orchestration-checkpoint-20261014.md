# Local orchestration checkpoint — 14 October 2026

This is a scoped integration receipt, not track completion or live acceptance.

## Verified shared evidence

At `bbb347a81d907912316e2f6872adc672e27a7606`, the coordinator independently
verified Conductor configuration and pinned skill entrypoints, repository-wide
Ruff lint/format (107 files), strict Pyright with the explicit local interpreter,
and Bandit over `src`. All passed.

The coordinator also ran 203 tests across hub capabilities, domain, decisions,
views, catalog, projections, meetings, recovery and release. All passed with
`--no-cov`, preserving other agents' coverage evidence. The recovery/release
subset separately passed 28 tests. These results do not establish full-suite
coverage, runtime reliability, persistent provider integration or pilot acceptance.

After documentation commit `cd934bc2cffee562c433201fb31356459af7054d`, both
offline PowerShell suites passed: Outlook approval/privacy/pagination/replay/
window/failure checks and Planner privacy/empty-result/domain/reconciliation/
replay/fail-closed pagination checks. The Outlook completion-audit edit was still
owned by its implementation chat and was not staged by the coordinator.

GitHub connector search returned no open repository PR. GitHub CLI was signed
out. No hosted checks for this local implementation revision have been verified,
and no implementation push or PR was performed by this checkpoint.

## Ownership and next handoff

| Owner | Current work | Required next evidence |
| --- | --- | --- |
| Credentialing chat | Finite native-runtime investigation with disposable probes | Minimal reproduction, exact interpreter/build, failure counts, diagnostic conclusion and proposed remedy |
| Teams chat | User-directed credentialing measurement extension in an isolated worktree | Final commit and base revision, review/test receipt, explicit remaining original Teams scope |
| Outlook chat | VUW sign-in and acquisition-gate preparation | Human-completed authentication; actual source access and separately recorded acquisition decisions when appropriate |
| M365 chat | Test-to-pilot boundary and approval preparation | Genuine Queensland Health pilot source, scope, owner and information-governance decisions |
| Hardening chat | Existing local hardening receipt and blocker routing | Any new independent defect or platform prerequisite |
| Coordinator | Shared integration and final verification | Owner checkpoints before consolidation; matched final-revision local and hosted evidence |

The native investigator reports failures in standard-library-only JSON code as
well as Pydantic serialization, and corrected processor-parity events in Windows
logs. These are diagnostic leads. No host root cause or safe remedy is proven;
passing feature tests do not close this blocker. Shared dependency changes must
not be based solely on a Pydantic hypothesis.

## Account and unattended-work boundaries

VUW is for development testing. The intended actual discovery pilot is
Queensland Health; see [the account-stage boundary](m365-test-to-pilot-boundary.md).
Login authorization does not authorize mailbox extraction. Synthetic contracts
and VUW test receipts cannot become Queensland Health pilot evidence.

The user instructed unattended agents to stop repeated login/status checks when
human sign-in is the blocker. This instruction was sent to the Outlook and M365
owners. Independent local work can continue; no duplicate sign-in, live approval,
pilot result or production authority is inferred. Implementation owners are asked
to report completion, blockers and scope changes to the coordinator.

All unfinished tracks retain their original scope and incomplete state. Final
integration, real app/flow authoring and validation, authentic source/policy
evidence, multi-user pilot and manual acceptance remain unproven.

## Subsequent coordination update

The Outlook chat now records verified VUW login and Power Automate access. The
user selected an existing Outlook connection and a developer environment. The
Azure mail-token route was unavailable; the implementation owner is working
with the selected connector route. These updates supersede the earlier pending
authentication state, but do not establish completed acquisition or a pilot.

The coordinator checked the direct user reply in the M365 chat: VUW is for
testing, and an actual pilot is intended for Queensland Health. The Outlook
draft runbook still used pilot terminology for VUW, so the coordinator sent
this exact clarification to both owners and requested reconciliation while
preserving any genuinely approved later connection or extraction scope.

The measurement extension's design and task plan are committed as `3c1d4c0` in
its isolated worktree. Implementation is underway and not yet integrated.
Review feedback requests explicit handling of repeated or contradictory
case evaluations, distinct-case suppression and partial effort observations.

## Stage-time integration receipt

The coordinator reproduced a scope-container defect in the initial stage-time
checkpoint: a string became character grants, and a one-shot iterator was
consumed before population construction. The owner confirmed five failing
regressions and fixed the boundary to require a set and detach it once.

Source commits `3c1d4c0`, `663a474`, `12bd50f` and `005b5e4` were reviewed and
integrated as `313435b`, `3049bad`, `5d308c6` and `2fd218f`. At shared executable
revision `2fd218ffe53861c864b2ce251de13945b9e34fe0`, the coordinator independently
verified 37 stage-time tests, repository-wide Ruff lint/format (109 files),
strict Pyright, Conductor validation and Bandit. All passed.

One full-suite run passed 705 tests. Its separate coverage dataset passed the
line and branch gate: 3755/3841 lines (97.76%) and 1103/1160 branches (95.09%).
The private receipt is
`careops-integration-10f31ef9208d430fa7cdd738d0ba5a77/coverage.xml` under the
coordinator's temporary directory. No retry or CPU-affinity workaround was used
for this receipt. The unrelated Outlook runbook edit was preserved and is not
part of the executable verification claim.

This successful run does not close the independently reproduced intermittent
host/runtime fault or prove the remaining workload, quality and human-review
interfaces. Those tasks are still being implemented in the isolated worktree.
Hosted checks, real source/policy approvals and full track acceptance remain
pending.
