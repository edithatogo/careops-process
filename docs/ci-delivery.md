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
on commit distance. Required CI installs the committed frozen lock and does not
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
