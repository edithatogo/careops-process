# Dependency maintenance and CI

Current policy, 14 October 2026. Repository configuration is local evidence;
successful hosted execution remains a separate acceptance gate.

## Ownership

| Ecosystem | Owner | Scope |
| --- | --- | --- |
| Python/uv | Dependabot | Root pyproject and uv.lock, weekly version PRs and GitHub security updates |
| GitHub Actions | Dependabot | SHA-pinned workflow Actions, weekly version PRs and security updates |
| Skill Git submodules | Renovate | .gitmodules/gitlink pins; review upstream skill changes before accepting |

The inspected [shared preset](https://github.com/edithatogo/renovate-config/blob/f16a84f40c6a6cf1e61c8d96051d272de647342e/default.json)
extends `config:recommended`, enables git-submodules, and sets pin/digest/patch
automerge. Without local constraints its Python and Actions managers overlap
Dependabot. `enabledManagers` now permits only `git-submodules`; the final local
package rule disables inherited automerge for every package. No checks or coverage
thresholds are relaxed. The preset is mutable: verify resolved configuration in
the Renovate dashboard/log when accepting future preset changes.

[Renovate submodule documentation](https://docs.renovatebot.com/modules/manager/git-submodules/)
describes its pin updates. Dependabot security updates must also be enabled in
repository settings; YAML schedules alone do not prove that setting. Confirm
Python PRs regenerate uv.lock and run locked sync; reject manifest-only updates.

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
and CodeQL. Inspect Renovate resolved manager lists and a submodule PR, and verify
Dependabot Python/Actions updates without duplicate Renovate PRs. Do not claim
these checks succeeded from a local configuration review.
