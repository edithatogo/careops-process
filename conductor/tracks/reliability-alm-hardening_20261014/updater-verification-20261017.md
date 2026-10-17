# Hosted updater verification — 17 October 2026

Result: partial operational verification; keep the updater acceptance gate open.

## Dependabot

[PR 72](https://github.com/edithatogo/careops-process/pull/72) was created by
`dependabot[bot]` on 14 October 2026. Its head is
`53ed3a7347f60a599016d25b9e69ae68f0129e5d`. The inspected patch changes only the
SHA-pinned `astral-sh/setup-uv` action in `.github/workflows/ci.yml`, from v6 to
v10.2.0, preserving checkout credential settings and action inputs.

Exact-head hosted checks report:

- [Python quality and tests](https://github.com/edithatogo/careops-process/actions/runs/38644518738/job/116127970745): success.
- [Gitleaks](https://github.com/edithatogo/careops-process/actions/runs/38644518797/job/116127970827): success.
- [Zizmor](https://github.com/edithatogo/careops-process/actions/runs/38644518419/job/116127969457): success.
- [CodeQL](https://github.com/edithatogo/careops-process/actions/runs/38644518838/job/116127974693): skipped, not analysis proof.

This proves Actions PR generation and successful execution of those three checks.
It does not approve the major upgrade or prove Python dependency/lockfile updates,
security-update settings, or the newer hardening workflow on this bot PR.
No Python PR with a verified regenerated `uv.lock` was established in this review.
An empty or unavailable search response is not evidence that no such PR exists.

## Renovate and effective ownership

[Onboarding PR 66](https://github.com/edithatogo/careops-process/pull/66) was merged
on 13 October 2026. [Dashboard 67](https://github.com/edithatogo/careops-process/issues/67)
shows a detected conductor submodule update awaiting schedule. It also detects
Python and GitHub Actions updates. No actual submodule update PR was established.

The inspected default branch (`main`, base commit
`26f5b3e94b776c04853169ba9b3c604967899b3b`) still has only the inherited preset in
`renovate.json`. Dependabot's pip and github-actions entries are also present.
The hardening branch restricts Renovate to `git-submodules` and disables automerge,
but that configuration has not reached the default branch. Therefore hosted
removal of overlapping ecosystem responsibility is not yet demonstrated.

## Remaining acceptance evidence

1. Integrate the reviewed ownership configuration through the normal PR process;
   this verification does not authorize or perform a merge.
2. Inspect a subsequent Renovate job/dashboard resolving only the intended
   submodule manager, with automerge disabled, and inspect a real submodule PR.
3. Inspect a Dependabot Python update that regenerates `uv.lock` and passes locked
   dependency installation and relevant checks.
4. Verify repository security-update settings through an authorized settings
   surface; schedule YAML alone is insufficient.

No remote configuration, dashboard checkbox, PR, bot setting or merge was changed.
