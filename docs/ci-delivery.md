# CI delivery

Keep immutable action commits and the complete `uv.lock` when updating tools or
runtime dependencies. Qualification uses the supported Python 3.14 range, strict
Ruff/Pyright, the existing property/privacy/domain tests, branch coverage at the
existing 90 percent threshold, Bandit and dependency audit. Do not replace tests
with a successful dependency resolution. The installed local project is not a
PyPI dependency and pip-audit explicitly skips its source; source tests, Bandit
and CodeQL cover separate concerns.

The shared CareOps workflow at immutable revision
3712b88f438b046e68fe37d8db2f4b6a4387b473 supplies full-history Gitleaks,
immutable-reference checks, actionlint and pedantic offline zizmor. It replaces
the two former duplicate secret/workflow-security jobs while retaining the
module's domain job. Public CodeQL now runs without an absent opt-in variable.
Existing required contexts must be migrated to the successfully qualified
replacement checks before normal merge, preserving strict/admin safeguards.

Dependabot is the sole Actions updater. Renovate's PEP 621 manager owns Python
and `uv.lock`, with scheduled lock maintenance and prerelease proposals but no
automatic merge. This uses Renovate's supported lock-maintenance integration:
https://docs.renovatebot.com/modules/manager/pep621/ . Apply exact generated
locks and require all current-head checks; never advance a module pin based only
on commit distance. Required CI first runs `uv lock --check` to reject stale declarations, then
installs the committed frozen lock and does not
perform an untracked pip upgrade after installation.

The upgrade to Ruff 0.17.1 requires copyright notices. Source headers repeat the
existing MIT licence attribution, Copyright (c) 2026 CareOps contributors, rather
than inventing ownership. The existing intentional hyphenated CLI filename
exceptions move from line-level directives to equivalent per-file configuration.
The dominant sequence calculation uses `min` with the same frequency/identity
ordering; the complete landscape/domain suite must remain green.

PM4Py remains optional and requires operational licence review. The deterministic
sequence metrics do not invoke it; the separate canonical weighted alignment and
authenticated local reporting tests do exercise the pinned backend when installed.
Neither these synthetic tests nor installing the extra establishes operational
source/model acceptance. Runtime canaries and wheel candidates are implemented;
their source-only evidence does not establish deployment or human acceptance.

The initial shared scan reviewed all238historical commits and found five
`generic-api-key` matches containing exactly the English data-lifecycle phrase
`retention/disposal`: four historical documentation passages and an old ignore
comment quoting the same prose. Private local inspection verified all five exact
match values. `.gitleaksignore` records only those revision/file/rule/line
fingerprints; no credential detector, path or history interval is disabled.
No source history was rewritten and no credential recovery was performed.

Development qualification runs weekly/manually and for relevant CI dependency
changes. It snapshots committed source into an isolated workspace and resolves
all declared extras with prereleases allowed. Exact Python3.14.8 and3.15.0
candidates run source formatting, lint, typing, pytest coverage and audit checks.
Stable CI additionally checks Conductor/submodule pins, the independent coverage
gate and offline PowerShell regressions. Newer
published CPython previews are discovered through the frozen upstream manifest;
unavailable previews remain untested/skipped. The project's supported runtime
range is widened only in the isolated candidate copy, never in the source lock
or production declaration. Changed production range requires explicit review of
the canary preparation contract. Each candidate retains exact package versions,
source commit, lock digest and actual setup/test outcome without promotion.

An earlier default-branch local Python3.15 receipt passed all156tests at90.88%coverage,
strict Ruff/Pyright and the optional PM4Py dependency load with pandas3.1rc0 and
lxml7beta. This is source compatibility and dependency loading only; PM4Py's
licence/adoption gate and absent production adapter remain explicit. Hosted
qualification and downloaded receipt checks are required before any promotion.

After integration at `ae2f234`, actual hosted Python3.14.8 and3.15.0 source canaries
each passed 1,724 tests with one intentionally absent-backend case skipped.
The pinned backend's synthetic alignment/store tests executed. Successful receipts
now name that scope; unsuccessful receipts explicitly remain unqualified. Receipt
classification tests execute the unchanged Python body on Windows and the actual
Bash wrapper on Linux, preserving all seven setup/failure/success scenarios.

## Actual wheel candidates

The package workflow builds once with exact locked Hatchling and no isolated
network backend resolution. An independent environment installs the actual wheel
with hash-locked base dependencies and executes the fictional CLI pipeline.
The SPDX inventory describes actual wheel files; the separate CycloneDX export
describes resolved base and optional dependencies, which are not bundled in the
wheel. PM4Py inventory does not establish an accepted operational provider or licence
adoption. Main-only federated provenance/SPDX signatures bind the downloaded
package to its exact source and workflow; independently verify them before
acceptance. This creates Actions candidates, not a PyPI publication or deployment.


## Squash-merge fingerprint reconciliation — 22 October 2026

PR73 merged ascca6d0a after all applicable exact-head checks passed. Its main
full-history scan returned four documentation matches because squash changed
the commit identity and line positions of previously reviewed English lifecycle
wording. Each redacted match was independently reconstructed against its actual
source line and the exact prior reviewed phrase above; none is a credential.
Retain the original five historical fingerprints and add only these four exact
commit/path/rule/line fingerprints. The default generic detector, paths and
full-history scope remain enabled. Main security remains failed until the
corrective source passes fresh checks and native main readback.
