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

PM4Py remains an optional, licence-gated dependency. Installing its extra during
source qualification does not establish a production adapter or native licence
acceptance; the current deterministic conformance functions do not invoke it.
Runtime/tool canaries, real optional interfaces and signed release distributions
remain explicit follow-ups in the Conductor track. No tenant login, mailbox
processing or deployment follows from these source checks.

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
candidates run all existing quality/property/privacy/coverage/audit gates. Newer
published CPython previews are discovered through the frozen upstream manifest;
unavailable previews remain untested/skipped. The project's supported runtime
range is widened only in the isolated candidate copy, never in the source lock
or production declaration. Changed production range requires explicit review of
the canary preparation contract. Each candidate retains exact package versions,
source commit, lock digest and actual setup/test outcome without promotion.

Local isolated Python3.15 qualification passed all156tests at90.88%coverage,
strict Ruff/Pyright and the optional PM4Py dependency load with pandas3.1rc0 and
lxml7beta. This is source compatibility and dependency loading only; PM4Py's
licence/adoption gate and absent production adapter remain explicit. Hosted
qualification and downloaded receipt checks are required before any promotion.

## Actual wheel candidates

The package workflow builds once with exact locked Hatchling and no isolated
network backend resolution. An independent environment installs the actual wheel
with hash-locked base dependencies and executes the fictional CLI pipeline.
The SPDX inventory describes actual wheel files; the separate CycloneDX export
describes resolved base and optional dependencies, which are not bundled in the
wheel. PM4Py inventory does not establish an implemented provider or licence
adoption. Main-only federated provenance/SPDX signatures bind the downloaded
package to its exact source and workflow; independently verify them before
acceptance. This creates Actions candidates, not a PyPI publication or deployment.
