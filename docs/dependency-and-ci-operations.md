# Dependency maintenance and CI

Current policy, 18 October 2026. Effective default-branch operation and reviewed
branch configuration are separate evidence.

## Ownership

| Ecosystem | Owner | Scope |
| --- | --- | --- |
| Python/uv | Renovate | Root pyproject.toml and uv.lock via pep621, including lockfile maintenance |
| GitHub Actions | Dependabot | SHA-pinned workflow Actions; weekly updates |
| Skill Git submodules | Renovate | Gitlink pins; review upstream skill changes before accepting |

The default branch at `1e092ffb11c165c7d23fc9a217a76783577b8624` assigns Python
to Renovate `pep621` and GitHub Actions to Dependabot. This supersedes the older
branch plan assigning Python to Dependabot. The reconciled branch adds
`git-submodules` alongside `pep621`, preserving main's schedule, timezone,
ignoreUnstable setting and Monday lockfile maintenance. Explicit repository and
final all-package rules disable automerge and platform automerge, including
inherited preset rules. No checks or security scanning are relaxed.

[Renovate's pep621 documentation](https://docs.renovatebot.com/modules/manager/pep621/)
documents pyproject/uv.lock management. Do not add a competing Dependabot Python
entry. If ownership is deliberately changed in future, [uv's native Dependabot
integration](https://docs.astral.sh/uv/guides/integration/dependabot/) uses the
`uv` ecosystem, not a guessed pip lockfile configuration.

[Renovate submodule documentation](https://docs.renovatebot.com/modules/manager/git-submodules/)
describes gitlink updates. Confirm resolved managers and no-automerge behavior
in actual hosted evidence after integration. Inspect Python updates for a
regenerated uv.lock and successful locked installation; inspect a real submodule
PR. Dependency dashboards, local configuration and manifest-only updates do not
complete those checks. Verify repository security-update settings separately.
The shared preset remains mutable; inspect its resolved configuration when changed.

## CodeQL

The Python CodeQL job now runs on PRs, main pushes, weekly schedule and manual
dispatch without the `ENABLE_CODEQL` variable. Remove any obsolete variable only
when authorised; it no longer controls this workflow. Actions remain SHA pinned,
checkout credentials are disabled, and SARIF upload has job-scoped
`security-events: write`.

[GitHub advanced setup requirements](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning)
require Actions, a supported language, and eligible repository visibility or
GitHub Code Security. Check advanced setup versus default setup before publication.
Record run URL, reviewed commit SHA, analysis success, upload success and the
code-scanning tool status. A skipped job or workflow file is not analysis evidence.
Repository administrators own eligibility, Actions permissions and required-check
settings; these were not modified locally.

## Local and hosted verification

Run locked sync, Ruff format/check, strict Pyright, pytest, the independent coverage
gate, Bandit, dependency audits, and every `tests/powershell/test_*.ps1` using
PowerShell 7. PowerShell tests mock token/API calls and need no account or Pester.
Use the optional mining profile separately; retain PM4Py licence review.
CI pins downloaded Actions; Python packages are resolved by the committed lock.

Before accepting a hosted release, inspect actual Actions checks and branch
protection for Python quality, offline PowerShell, workflow security, secret scan,
and CodeQL. Inspect Renovate resolved manager lists, Python lockfile updates and a submodule
PR, and verify Dependabot Actions updates without duplicate ecosystem owners. Do not claim
these checks succeeded from a local configuration review.
