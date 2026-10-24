# Agent instructions

## Modular suite delivery — 18 October 2026

Follow [the suite delivery queue](conductor/suite-delivery.md) and
[the module profile](.careops/module.json). Apply development-first, exact-pinned
qualification and low-hanging-fruit sequencing; this supersedes stable-only
dependency wording for new candidates. Preserve working runtimes until verified
promotion, private source boundaries, current native/file ownership and existing
enterprise authority. Optional integrations never become new MVP closeout gates.

## Required Python execution

All active Python development, build, test, automation and CI execution uses
Python3.15, currently exact patch3.15.1. Use an explicit repo-local interpreter,
verify its version, and align constraints, locks and current setup instructions.
Older runners are not compatibility defaults; preserve only historical evidence
and intentional synthetic version tests. Do not replace a running environment.

## Targeted test execution

Follow the [shared targeted-testing policy](https://github.com/edithatogo/careops/blob/main/docs/targeted-testing.md).
During edits, select exact affected files/nodes or native runner checks and reuse
unchanged evidence. Use an explicitly selected repo-local Python3.15.1 via
REPO_PYTHON where applicable. Do not rerun unchanged whole suites during each edit.
Run broader tests for shared fixtures, schemas, dependencies or uncertain impact;
retain full coverage/security/integration and release gates at coherent milestones.

For pytest, preserve cacheprovider per worktree/environment: --lf together with
--last-failed-no-failures=none never silently runs all tests; empty means no tests
verified. --ff still runs all selected tests; --sw is local debugging only. Do not
set selection flags globally or present partial coverage as full coverage.
Default to no automatic retries. skip/skipif requires a real capability condition
and reason; xfail needs a known issue/reason and strict=True. Neither is for speed.
Never retry native mutations, sends or real external effects through test plugins.
Difftest0.3.0 failed actual3.15.1 qualification (PyO3 maximum3.14); do not install
it with a compatibility override or downgrade Python. Rerunfailures16.7 is opt-in
for bounded, diagnosed fictional/read-only transient cases with first failure
visible; it must not turn flaky outcomes into clean acceptance.

Existing runner example (select the actual changed case, not this example blindly):

```sh
make test-focused TESTS=tests/test_ci_canary.py
```

Use `make test-failed`, `make test-stepwise`, `make test-failed-first` and
`make test-full` for the corresponding modes. Focused/stepwise modes use --no-cov;
full modes retain the existing coverage threshold. The optional locked
`test-diagnostics` group contains rerunfailures, excluded from default CI; use
`--reruns 1 --fail-on-flaky` only for an explicitly selected eligible diagnostic.

## Project-owned code licensing

Use Apache-2.0 for project-owned source and active package metadata. Include the
licence and notice in source distributions. Preserve third-party terms, notices
and attribution, historical evidence and private/external source rights. This
standard changes no publication, native, access or email authority.
