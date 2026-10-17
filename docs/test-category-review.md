# Testing categories and review evidence — 15 October 2026

This assessment maps risks to useful assertions and outstanding evidence. Test
counts and line/branch coverage are diagnostics, not completion scores. Existing
coverage gates remain in effect; this document does not change them.

The coordinator's completed integration receipt at the pathway checkpoint is
799 passing tests. That run does not establish host/storage repair, hosted CI,
live connector behavior, clinical policy correctness or production acceptance.
The damaged output of a different agent's full run remains inconclusive.

## Risk and evidence map

| Category / requirement | Local evidence inspected | Required next evidence / owner |
| --- | --- | --- |
| Contract and input validation: reject unknown fields, unsafe codes, wrong primitive/container types and invalid time values | `test_contract_files.py`, `test_credentialing_measurements.py`, `test_credentialing_observations.py`, `test_credentialing_pathways.py`; scope-container regressions failed before their fix | Independent schema/runtime fixtures for each deployed adapter; reference/source owner confirms admitted vocabularies |
| Algorithm correctness: reconcile population/exclusions, hand-calculated quantiles, distinct-case quality denominators and unknown versus measured zero | Measurement/observation tests; repeated reviews cannot inflate case counts; partial effort blocks comparison | Approved source semantics and representative independently adjudicated cases; credentialing owner |
| Privacy: prevent narrative/identities in broad reports; suppress rare cells and totals | Credentialing tests and exporter offline tests; current report shapes inspected | Cross-release/cohort differencing policy, retained evidence access and deployed-role tests; information steward and app owner |
| Authorization and governance: require explicit case grants, scope, policy versions and genuine canonical decision evidence | Pathway access tests, `test_hub_decisions.py`, `test_hub_views.py`, `test_hub_recovery.py` | Actual identity/role resolution, revocation and acting-role behavior for multiple users; governance owner |
| Lifecycle, replay and deletion: reject conflicting history, stale revisions, restored deleted inference and activity after terminal events | Credentialing ledger/assurance tests; pathway post-terminal case was observed failing and then passed; hub replay/recovery tests | Durable transaction/concurrency and restore verification; storage adapter owner |
| Acquisition and failure handling: pagination, window limits, interruptions, duplicates and independently measured reconciliation | Outlook/backfill tests plus both offline PowerShell suites | Real bounded connector acquisition, source/destination/page reconciliation and independent replay; Outlook then M365 owners |
| Publication and evidence integrity: prevent partial output, overwriting source/backup inputs and false closed-run claims | `test_report_publication.py`, `test_closed_run_report_cli.py`, `test_hub_release.py`, closed-run evidence tests | Actual evidence-store access, retention/disposal and publication/rollback receipt; M365 owner |
| Property and stateful invariants: exercise populations, deleted-stage sets and changing histories beyond examples | Existing Hypothesis tests inspected; deterministic expected outcomes remain important | Add stateful/concurrency scenarios only for actual durable adapters and identified risks; implementation owner |
| Static/security/dependency/secret checks: detect unsafe code/configuration and vulnerable dependencies | Ruff, strict Pyright, Bandit, Conductor and scoped prior security receipts; CI defines dependency/workflow checks | Matched final revision hosted checks, dependency and secret receipts; ALM owner/coordinator |
| Packaging and deployment: validate actual component types and preserve pre-change/restore evidence | `test_local_alm.py` and hub dry-run tests; current generic validator supports table exports | Real app/flow validation adapter, import and restore verification in the selected lane; ALM owner |
| Power Platform UI and functional integration: prove actual app/flow behavior and user journeys | No local synthetic contract test is a deployed UI/flow receipt | Deployed app target, authorized accounts, connection transport and synthetic test data; governance/Outlook/ALM owners |
| Accessibility, performance, usability and continuity: keyboard/focus/errors, executive effort, notification burden, downtime and owner departure | No completed deployed-category receipt found in inspected evidence | Actual experience and multi-user staged cases with entry/stop/rollback criteria; app and pilot owners |
| Host/storage reliability: trusted source, index, caches and process output | Git index recovered; tracked content audited against committed object hashes; corrupted pathway drafts reconstructed and regression verified | Known-stable authorized host or serviced host, unchanged unpinned reproduction and trustworthy final receipts; machine operator |

Each row is a requirement category, not a declaration that all tests in that
category are sufficient. Synthetic policy versions are fixtures, not approved
Queensland Health/CHHHS rules. VUW testing is separate from the actual pilot.

## Assertion-quality review

For a new or changed test, record the production behavior change that should
make it fail. Prefer real boundary calls and hand-calculated expectations over
mock assertions or copies of the implementation. Check that the test distinguishes
missing data from zero, inferred evidence from observed execution, authorization
from caller-supplied labels, and package validation from functional behavior.

Concrete recorded examples are the five invalid case-container regressions,
the post-terminal pathway assertion, conflicting observation replay and
source-replacement invalidating a proposal despite identical aggregates. These
protect behavior rather than increase a coverage number. A bounded mutation
experiment can assess a selected calculation or gate after the host is stable;
no mutation-testing tool or successful mutation score is claimed here.

## Modern Power Platform test dependencies

Microsoft deprecated Power Apps Test Engine effective April 2026 and directs
users to its Power Platform Playwright samples. Do not add Test Engine as the
new functional-test foundation. [Deprecation notice](https://learn.microsoft.com/en-us/power-platform/important-changes-coming#deprecation-of-test-engine).

The candidates for actual app UI/E2E tests are `@playwright/test` and Microsoft's
locally referenced `power-platform-playwright-toolkit`, with page objects and
authentication helpers. The samples are a Rush monorepo. The documented start
requires Node.js 20 or later, a deployed app and an authorized user.
[Framework overview](https://learn.microsoft.com/en-us/power-platform/developer/playwright-samples/overview),
[setup requirements](https://learn.microsoft.com/en-us/power-platform/developer/playwright-samples/get-started).

Evaluate a pinned toolkit source and locked Node test package in a separate E2E
directory once the app target and lane are confirmed. Start with authorized
synthetic journeys, negative access and keyboard/focus checks, then measure
actual response time and user effort. Keep session state and private bindings
outside Git, preserve MFA as a human action, and record the real app/solution
version with each receipt. This is a dependency decision and entry checklist;
no toolkit installation, browser test, app deployment or live acceptance is
claimed. A connected Outlook account alone is not a deployed app test target.

PAC Solution Checker and package/static scans complement functional tests;
they do not prove flows execute correctly or users can complete a journey.

## Task-to-review receipts and percentages

Track implementation percentages must state their denominator: completed leaf
plan items divided by all planned leaf items, including outstanding live gates.
They are not effort estimates. Original Teams work and the credentialing
measurement extension must have separate denominators.

A formal review percentage needs an explicit planned-review denominator.
Do not divide test counts, coverage or the categories above by checklist tasks.
Where no task-to-review mapping exists, report the percentage as unrecorded.
Existing phase-review checkboxes retain their meaning and are not checked by
this assessment.

For each future review receipt record: track/task or gate ID; requirement;
immutable source revision and test environment; relevant assertions and result;
reviewer and scope; disposition/fix revision; remaining local/live/manual limits.
Count a mapped review only when its required scope has a real receipt. The
coordinator's existing receipts are in
[the integration log](orchestration-checkpoint-20261014.md),
[pathway recovery review](credentialing-pathways.md), and the owning tracks'
review documents. This assessment establishes the mapping conventions and
category gaps; it does not invent historical task-level reviews.
