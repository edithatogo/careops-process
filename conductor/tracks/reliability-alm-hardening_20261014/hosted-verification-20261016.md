# Hosted verification — 16 October 2026

Draft [PR 73](https://github.com/edithatogo/careops-process/pull/73) published head
`6d87b9106cf8a98d47824519f6d6ed182530ad87`. These receipts belong to that head;
Actions checked out its GitHub merge ref `d816462fcb25ba33b5abdd0a1c468f7ca4b5ae78`
against base `26f5b3e94b776c04853169ba9b3c604967899b3b`. New commits need new checks.
The GitHub connector and Codex checks backend worked without GitHub CLI login.

## Observed checks

| Check | Result and evidence |
| --- | --- |
| Python quality/tests | [Job 116790716977](https://github.com/edithatogo/careops-process/actions/runs/38844148718/job/116790716977) passed on Ubuntu 24.04.5 / Python 3.14.8: 866 tests, Conductor, formatting/lint, typing, independent coverage gate, both offline PowerShell scripts, Bandit and dependency audit. |
| CodeQL Python | [Job 116790717281](https://github.com/edithatogo/careops-process/actions/runs/38844148766/job/116790717281) passed. Logs explicitly report SARIF exported, results successfully uploaded, and analysis upload complete. This establishes an actual analysis/upload, not workflow presence. |
| Workflow security | [Job 116790716956](https://github.com/edithatogo/careops-process/actions/runs/38844148705/job/116790716956) passed. |
| Secret scan | [Job 116790717152](https://github.com/edithatogo/careops-process/actions/runs/38844148748/job/116790717152) failed on one historical generic-api-key prose match. The staged repair below has local pinned-scanner evidence; its hosted rerun remains pending. |
| Optional PM4Py | Skipped under its existing opt-in policy; not a hosted integration pass. Earlier isolated local evidence remains separate. |

Line coverage was 4320/4413 and branch coverage 1268/1332. These are secondary
diagnostics. More useful category evidence is that Linux executed the exporter
privacy, approval, window, replay, pagination and failure regressions, and the
full application suite completed on a separate runner. This does not establish
deployed Power Platform behaviour, live approvals or a repair of the local host.

## Reproduced scan defect and narrow correction

Read the exact pinned action's [README](https://github.com/gitleaks/gitleaks-action/blob/dcedce43c6f43de0b836d1fe38946645c9c638dc/README.md)
and [implementation](https://github.com/gitleaks/gitleaks-action/blob/dcedce43c6f43de0b836d1fe38946645c9c638dc/src/gitleaks.js).
`ScanPullRequest` uses the first commits API page without pagination; its last
entry becomes the range endpoint. The observed job scanned 30 commits ending
at `f3f6b8c`, rather than all history reachable from the published head.
There is no `GITLEAKS_LOG_OPTS` override at this action pin.

The correction retains the same pinned action and its licensing context, pins
its installed scanner to the observed 8.24.3, disables optional PR comments
without increasing permissions, and adds an explicit `gitleaks git --redact
--log-opts=--all` step using the installed binary. Checkout already fetches full
history. No toolchain/version upgrade, broad exclusion or history rewrite is used.

The action's original match and two additional matches found by the expanded
scan were inspected at their exact historical revisions. They are ordinary
operator, testing-matrix and pilot-control prose, not credentials. Only their
three exact fingerprints are in `.gitleaksignore`, with individual reasons.
No protected matched value is included in this record.

Downloaded scanner 8.24.3 release checksum verified. Before correction, its
full published-head reachable scan found the two additional prose matches.
After the three exact exceptions, the original hosted 30-commit range passes
and all locally fetched history passes (165 commits). Local offline Zizmor
reports no findings with one existing suppression; `git diff --check` passes.
These local results do not replace a hosted run of the corrected workflow.

## Remaining gates

- Coordinator reviews/publishes the narrow fix and verifies secret scan on the
  new head. Other checks must also bind to that new head; retain PR as draft.
- Hosted dependency-updater responsibility is not fully verified. Local config
  limits Renovate to submodules and assigns Python/Actions to Dependabot;
  remote Dependabot branch refs exist, but an open bot PR search returned none.
  Branch refs alone do not establish active updater/security settings or lack
  of duplicate responsibility. Dashboard/resolved-run evidence remains needed.
- Existing Actions emit Node 20 migration warnings and CodeQL v3 deprecation
  warnings. These did not fail the observed checks; review pinned upgrades
  separately, without mixing them into the scan correction.
- Human checkpoints, full-mailbox/Dataverse and Queensland Health evidence,
  non-production solution checking/binding/import/export/recovery, optional
  infrastructure, governance approvals and final track acceptance remain open.

## Corrected workflow and bounded VUW follow-up

Coordinator published repair `a068a92f630a343c020f34c8087b3a612d5c91bf`.
The [new secret-scan job](https://github.com/edithatogo/careops-process/actions/runs/38844551023/job/116791990365)
passed on its merge ref `6293543` against the same base. Logs verify scanner
8.24.3, the original 30-commit PR scan, comments disabled, and the additional
explicit `gitleaks git --redact --log-opts=--all` step. The latter scanned 147
hosted fetched commits and reported no leaks. Local and hosted fetched-ref sets
differ, so their scan counts need not be identical. This closes the reproduced
PR-range defect for this revision; it does not certify future heads.
The [new workflow audit](https://github.com/edithatogo/careops-process/actions/runs/38844551162/job/116791990243)
also passed. Python quality and CodeQL were still running at the initial bounded
check; final results are recorded below when observed.

The [public Outlook receipt](../outlook-cloud-historical-backfill_20260721/test-connection-20261015.md)
supersedes the earlier VUW retention/acquisition blocker. The user approved the
bounded Inbox metadata test and disposal controls. Thirty records were acquired,
strictly validated in a separate process, read back from the local canonical
destination, and compared with a separate replay: zero new identities and no
content drift. Source count remains the same service's claim, and the destination
is local JSONL. Evidence is `smoke_test`, not full-mailbox, Dataverse or Queensland
Health pilot acceptance. No repeat source read is needed for this receipt.

Disposal deadline is 23 October 2026 at 13:02:12 Brisbane time. The coordinator's
existing 13:03 follow-up covers the exact 14-file allowlist and unique encrypted
pseudonym key. Disposal is scheduled, not yet executed; no duplicate schedule
was created here. Final absence and receipt still need verification then.

No PR merge, platform deployment, permission broadening or firmware change occurred.
