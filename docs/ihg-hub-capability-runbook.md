# IHG hub capability discovery

This implements the first capability-contract task and the read-only probe runner
for the IHG Governance and Executive Action Hub. It does not implement the hub,
deploy a solution, approve a pilot or confirm the IHG operating model.

## Current evidence and remaining gates

The 14 October 2026 Brisbane discovery run observed a cached delegated PAC
profile and successful PAC environment discovery. Microsoft 365 CLI reported
`Logged out`. No pilot environment, Team, site, List, app or Planner plan has been
confirmed. An attempt to resolve one current environment from the PAC profile
and discovery output was inconclusive; no target was chosen automatically.

The live report selects `fail_closed`. It contains no resource URLs, identities,
titles, CLI response bodies, error details, tokens or sensitive records.
`observed` means a read succeeded, not that a capability is approved or verified.
Operating-model confirmation remains pending at the user's explicit request.

The next Phase 1 task requires an approved source for the executive operating
model and a named pilot scope. Confirm these in the controlled governance record:

| Required input | Current state |
| --- | --- |
| Chair, secretariat, sponsors, decision owners and advisers | Pending |
| Information steward, maintainers, delegates and acting arrangements | Pending |
| Authority source for each decision type and escalation route | Pending |
| Collective decision rules, quorum, conflicts and recusals | Pending |
| Urgency, out-of-session expiry, chair confirmation and ratification | Pending |
| District escalation, meeting cadence and agenda deadlines | Pending |
| Brief requirements, action follow-up and closure evidence | Pending |
| Target environment/Team/site/List/app/Planner plan | Unconfirmed |
| Classification, records controls and protected evidence location | Pending |
| Licence, connector/DLP, access and sharing verification | Unverified |
| Two or more co-owners, target three, plus confirmed backups | Unverified |
| Resource-owner actions and explicit pilot-lane decision | Pending |

Technical completion cannot fill these fields or create a delegation.

## Run from the repository root on Windows

The runner uses the installed Python runtime, PAC CLI and Microsoft 365 CLI.
It invokes the installed Microsoft 365 Node entrypoint directly with argument
arrays, so the timeout terminates the CLI rather than a shell wrapper. It requires
an existing delegated sign-in and never opens login,
registers an Entra application, obtains additional consent, changes the active
profile or grants a role. A missing runtime or sign-in is reported as a gap.

```powershell
uv run python -m careops_process.hub_probe --dry-run
uv run python -m careops_process.hub_probe --output artifacts/ihg-hub/capabilities.json
```

The default probes only inspect cached identity type and accessible PAC
environment discovery. Exit code zero means the report was collected; inspect
`assessment.lane` and `assessment.gaps` to determine eligibility. In particular,
exit zero with `fail_closed` is not permission to deploy. Invalid input or an
unwritable report destination returns exit code two and a fixed error code.

For selected-resource probes, copy
`contracts/hub-probe-config.example.json` to the ignored `artifacts/ihg-hub/`
directory and fill only the confirmed targets. Keep real resource configuration
out of Git. The configuration schema is `contracts/hub-probe-config.schema.json`.
Dataverse PAC reads require the explicit environment HTTPS URL. Microsoft 365
environment reads require the environment GUID. An app or table requires that
GUID; a List requires an explicit site URL. Confirm that URL and GUID identify
the same pilot environment before running. An app, table or List does not have
to exist to run environment discovery.

```powershell
uv run python -m careops_process.hub_probe --config artifacts/ihg-hub/scope.json --dry-run
uv run python -m careops_process.hub_probe --config artifacts/ihg-hub/scope.json --output artifacts/ihg-hub/capabilities.json
```

Each operation times out after 30 seconds. A failed independent resource probe
does not stop the other probes. Failed identity checks suppress all subsequent
resource reads for that tool. Certificate, secret and managed-identity Microsoft
365 sessions are rejected; unknown authentication shapes also fail closed.
Raw stdout and stderr stay internal and are not written to reports or logs.

## What the probes establish

| Probe | Observation only; remaining verification |
| --- | --- |
| PAC identity/environment discovery | Cached delegated profile and discovery call; no pilot resource choice |
| Explicit Dataverse environment | Read accessibility; effective privileges remain unverified |
| Direct and team-assigned roles | Up to 100 role records per query; role/privilege completeness is not asserted |
| Solution inventory | Read access; solution import, customization and rollback rights remain unverified |
| Organisation audit setting | Readable configuration; table/column audit and usable audit trail still need verification |
| Table metadata and selected table | Metadata access; audit settings and access controls require review |
| Connector inventory | Custom connectors only; standard/premium connector use, licences and DLP need independent proof |
| App and permission inventory | Existing grants; ability to share, non-owner access and continuity need multi-user checks |
| Selected Team, site and List metadata/permissions | Read access; item-level controls, records rules and auditability need review |
| Selected Planner plan | Read access; task creation/reconciliation rights remain unverified |

No probe reads List items, messages, patient records, task descriptions, approval
comments or evidence attachments. The initial probe does not send a test approval,
modify sharing, import a solution or create a Planner task. Approvals usability,
standard connectors, write privileges, DLP and continuity require an approved
test scope and appropriate owner evidence before a lane can become eligible.

The CLI contracts were checked against installed PAC 2.13.1 command help and
installed Microsoft 365 CLI help. PAC uses `pac env <command> help`; its installed
version rejects `--help`. Relevant primary references are the
[PAC CLI reference](https://learn.microsoft.com/power-platform/developer/cli/reference),
[PAC authentication reference](https://learn.microsoft.com/power-platform/developer/cli/reference/auth)
and [Microsoft 365 CLI reference](https://pnp.github.io/cli-microsoft365/cmd/).

## Reviewed capability evidence

`contracts/hub-capabilities.schema.json` and the executable
`CapabilitySnapshot` model define the review input. A check has a fixed name,
status, opaque scope reference, timezone-aware timestamp and optional opaque
evidence reference. `verified` requires a reference to the controlled external
evidence register. The register holds approver identities and detailed evidence;
this contract deliberately does not copy them. Model validation also checks the
verification-reference rule, which JSON Schema alone does not enforce.

Only an authorised reviewer can turn an observation into verified evidence.
This library validates the shape and eligibility rules; it does not authenticate
the reviewer or prove that a supplied reference actually resolves. Do not accept
an arbitrary client-supplied snapshot as deployment authorization. Preserve the
controlled evidence register and signed review separately from the report.

The assessor rejects unknown fields, unknown check names, ambiguous dates,
stale/future evidence and mismatched scope. Both snapshots and checks expire
after 24 hours. Checks cannot postdate collection. Every required check must be
verified. At least two co-owners and a confirmed backup are required; three is
the target. A Dataverse lane is preferred when its controls all pass. The initial
restricted fallback accepts only approved low-sensitivity metadata; stronger
fallback classifications are not implemented by this capability slice.

The public `assess_capabilities(snapshot, now=...)` function returns a minimised
assessment with fixed gap codes. It always returns `pilot_authorized: false`.
Even an eligible lane still needs the operating model, steward, resource-owner
and pilot decisions recorded separately before deployment. Synthetic fixtures
under `tests/fixtures/hub_capabilities/` exercise both eligible lanes and
fail-closed behavior; they are not live tenant or governance evidence.

## Verify and resume

```powershell
uv run pytest tests/test_hub_capabilities.py tests/test_hub_probe.py --no-cov
uv run ruff check src/careops_process/hub_capabilities.py src/careops_process/hub_probe.py tests/test_hub_capabilities.py tests/test_hub_probe.py
uv run pyright src/careops_process/hub_capabilities.py src/careops_process/hub_probe.py tests/test_hub_capabilities.py tests/test_hub_probe.py
uv run python scripts/validate_conductor.py
```

Independent Phase 2 schema, lifecycle, privacy and template-version contracts
can proceed locally with synthetic policy fixtures while Phase 1 gates stay
open. IHG roles, thresholds, quorum and authority are configuration inputs,
never inferred implementation defaults. Resume live Phase 1 verification once
the operating model and pilot scope are provided. Do not mark the operating model, selected deployment
lane, live multi-user pilot, later phases or manual verification complete from
these synthetic tests. Shared ALM packaging and release controls belong to the
reliability and ALM hardening track and are dependencies for Phase 4.
