# Mining metrics and local assurance

`careops_process.mine` implements sequence comparisons. Fitness is the total
number of equal activities at the same position divided by the sum of
`max(trace length, reference length)` over traces. Reordering, missing activities
and extra repetitions reduce fitness. Precision is the number of distinct
observed activities also in the reference divided by all distinct observed
activities. It ignores order and repetition: a reversed path can have zero
fitness and precision one. Neither metric is token replay, alignment fitness,
model precision, causal evidence or clinical assurance.

The reference and trace collection must be nonempty. Individual empty traces
count against fitness, produce an `empty trace` deviation, and are omitted from
variant discovery. An entirely empty observation has precision zero. Variants
sort by decreasing frequency, then lexical identity; deviation entries preserve
input order and repetition. Activity labels must already be approved and
minimised because deviation strings preserve them.

Tests cover empty/mixed traces, repeated activities, reversed order, unequal
lengths, deterministic frequency ties, input preservation, exact replay and
metric bounds using synthetic Hypothesis examples. These tests reproduced no
mining defect, so the algorithm remains unchanged.

## Selected default analytical scope

The selected baseline answers four bounded questions from privacy-minimised,
source-ordered event facts: which complete activity sequences occurred and how
often; how each sequence compares positionally with a supplied reference; which
sequence strings differ from that reference; and whether the analytical pass
left the observed input facts untouched. These are descriptive cohort measures,
not claims about why a difference occurred or whether a case was handled
correctly. The raw OCEL log and derived `ConformanceResult` are separate fields
of `PipelineResult`; derived findings are not appended as observed events.

A fictional six-case request log qualifies the baseline against exact replay,
an omitted step, an additional review step, and a reordered trace. It yields
four variants with frequencies 3/1/1/1, positional fitness 13/19, set-based
precision 3/4, and three deviations. The test also confirms the input traces
remain unchanged. This exercises sequence counts and the documented metric
semantics; it is not a live-source or production acceptance result.

| Requirement | Baseline coverage | Limitation |
| --- | --- | --- |
| Deterministic full-trace variants and counts | Covered, including ties and repeats | Requires already minimised activity labels and case/object traces |
| Compare to one supplied reference sequence | Covered with positional fitness and activity-set precision | No executable model, branching, concurrency, weighted costs, or alignment |
| Preserve observed facts separately from findings | Covered by separate pipeline result fields and non-mutation qualification | Source completeness and correctness need independent evidence |
| Microsoft paid mining service optional | No service dependency in core code or required dependencies | Service-specific dashboards and hosted analytics are not reproduced |

## Optional engines and paid service

The deterministic sequence implementation is the selected default. Power
Automate Process Mining is an optional external service; neither source imports
it nor the core dependency set requires its capacity. Microsoft describes
Process Mining as a capacity add-on with Power Automate Premium as a qualifying
prerequisite in its current [licensing guidance](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/add-ons).
This project does not infer an entitlement from a tenant login or require that
add-on for the selected scope.

PM4Py is also not required for these baseline measures. Its additional Petri-net
alignment capability is relevant only when a governed executable model and
costed alignment are a selected requirement. The upstream public PM4Py package
is [AGPL-3.0](https://github.com/process-intelligence-solutions/pm4py/blob/release/LICENSE)
and its [maintainers describe a separate commercial licence](https://processintelligence.solutions/pm4py#licensing)
for closed-source use. Since this project-owned source is Apache-2.0, keep
PM4Py outside the default runtime and do not activate or distribute it for this
use until licence compatibility is confirmed. The existing optional dependency
and separate credentialing alignment lane remain explicitly gated; they are
not evidence that the default process route needs PM4Py.

## Independent coverage checks

Run `uv sync --locked --group dev`, `uv run --no-sync pytest`, then
`uv run --no-sync python scripts/check_coverage.py coverage.xml`. The final command
uses exact XML numerator/denominator counts and requires **both line and branch
coverage to reach 90%**. The pytest aggregate threshold remains an additional
check; it cannot replace the independent gate. Missing or invalid measurements
fail closed. CI also executes each `tests/powershell/test_*.ps1` in a separate
`pwsh -NoProfile` process; these synthetic scripts require no account or Pester.

## Optional PM4Py boundary

PM4Py remains optional and subject to the existing licence review before
production adoption. `scripts/check_pm4py.py` checks availability and preservation
of event ID, activity, object ID and relation qualifier when PM4Py reads a native
OCEL 2 JSON fixture. The application envelope is a separate schema and has no
PM4Py conversion adapter. This check does not claim envelope interchangeability,
token replay or end-to-end conformance integration.

Use a separate environment, for example in PowerShell:

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'artifacts/mining-venv'
try {
    uv sync --locked --group dev --extra mining
    if ($LASTEXITCODE -ne 0) { throw 'Optional dependency sync failed' }
    uv run --no-sync python scripts/check_pm4py.py
    if ($LASTEXITCODE -ne 0) { throw 'Optional import boundary failed' }
    uv run --no-sync pip-audit
    if ($LASTEXITCODE -ne 0) { throw 'Optional audit failed' }
} finally { Remove-Item Env:UV_PROJECT_ENVIRONMENT }
```

CI runs this independent job only when repository variable `ENABLE_PM4PY` is
`true`; leaving it disabled retains the dependency-free mining implementation.
Both jobs install from the checked lockfile and pinned Action commits. Hosted
execution and repository-variable configuration require separate evidence.

## Local evidence, 14 October 2026

Before these changes, the shared checkout passed 250 tests with line coverage
1594/1687 (94.49%) and branch coverage 444/506 (87.75%). The aggregate was 92.93%,
which concealed the branch shortfall. Uncovered behavior included malformed
cross-source fact shapes and invalid governance field types; additional tests
exercise those fail-closed paths without changing production behavior.

The final focused mining/coverage/rejection run passed 45 tests with clean Ruff
lint and formatting. A subsequent shared-checkout run during concurrent track
work measured 2133/2216 lines (96.25%) and 598/656 branches (91.16%), passing both
independent gates. It passed 375 tests with one then-unfinished exporter CLI
privacy test failing; this snapshot is not a full-suite completion claim.
The track's final verification records the consolidated result after all owners
finish their changes.

The working `uv.lock` was already modified before this task: it had reconciled
PM4Py 2.7.23.1 to the manifest's 2.7.23.8 and removed its obsolete setuptools/wheel
dependencies. Those generated changes were inspected and retained. This task
also moved `defusedxml` from the dev group into runtime dependencies for the ALM
validator, then regenerated and checked the lockfile.

On Windows with Python 3.14.8, locked normal and isolated optional sync succeeded;
the optional native OCEL import check passed with PM4Py 2.7.23.8. `pip-audit` found
no known vulnerabilities in either installed profile; the local
`careops-process` package was skipped because it is not published on PyPI.
This is dependency evidence, not a licence approval or live platform check.
