# Recovery and deployment dry-run contracts

`hub_recovery.py` stores synthetic recoverable dead letters containing only
opaque matter/scope/event/replay/version references, policy/template/command
fingerprints, protected command-record reference, fixed error code and bounded
retry metadata. It does not copy failed command payloads, private exception text,
actor inputs, approval comments, attachments or tokens into the recovery record.

Scheduling checks explicit owner, scope, policy fingerprint, strict expected
revision, chronology, retry delay and maximum attempts. Imported retry limits
must match the pinned policy. Recovery succeeds only when the supplied canonical
matter/history contains the exact matching applied event, replay key and command
digest. A provider success boolean cannot substitute for that evidence.

These are immutable local transformations. No retry dispatcher, data store or
provider integration is deployed. A live worker must authenticate owners, resolve
the protected command record, perform atomic compare-and-swap and revalidate
current permissions before retry. Receipt replay has one documented minor
requirement: preserve the original receipt event timestamp in `now`; it belongs
to receipt identity and is not a fresh processing-clock timestamp. A changed
timestamp is a receipt collision.

`hub_release.py` creates an explicitly `dry_run_only` review plan. Opaque review
references never become proof of authenticity, and `deployment_authorized`
always remains false. Logical environment-variable and connection declarations
contain no tenant IDs, URLs, credentials or invented publisher prefix. Actual
prefix-qualified names must come from the confirmed publisher and environment.

When a Dataverse export and pre-change backup are supplied, the dry run reuses
the shared `local_alm.prepare_deployment` validator. It catches malformed and
unsupported artifact errors into one fixed gap code. The current shared
validator supports table exports; complete app/flow packages still need a
validated component adapter. No placeholder solution XML is created by this
track, and successful generic artifact preparation is not a completed hub release.

The restricted fallback remains low-sensitivity only and requires actual
configuration/backup exports and verified resource access/audit/continuity.
It does not require choosing a Dataverse publisher. Neither lane can proceed
from unsigned pointers or synthetic fixtures alone.

```powershell
uv run python -m careops_process.hub_release
uv run python -m careops_process.hub_release --request contracts/hub-release-request.example.json
uv run python -m careops_process.hub_release --request artifacts/ihg-hub/release-request.json --release artifacts/ihg-hub/release --backup artifacts/ihg-hub/prechange-backup --output artifacts/ihg-hub/review-plan-new.json
```

Exit zero means a review plan was produced, even when gaps remain. Invalid input,
unsafe output or report I/O errors return exit two with a fixed error code.
Output must be a new report outside the request, release and backup inputs;
existing files and aliases are refused, and exclusive creation protects against
overwriting evidence. No online import command is exposed.

The recovery policy-override and release manifest/output-collision findings had
failing regression cases before the fixes. The real shared ALM malformed-manifest
boundary is tested, not only a mocked exception. Synthetic tests and scoped lint,
typing and Bandit pass before this checkpoint's commit.

## Remaining-local and external-dependency audit

| Work | State and dependency |
| --- | --- |
| Canonical schemas/lifecycle, policy pinning, collective rules, scoped views | Implemented as synthetic contracts; live authentication/access adapter pending |
| Template activation/migration/rollback catalog | Implemented locally; actual approved clinical/executive rules and atomic persistent registry still needed |
| Approved-reference brief, agenda, minute and urgent ratification assembly | Implemented locally; reference authenticity, agenda snapshot replacement, persistent meeting events and calendar/Teams integration remain |
| Approval and Planner projection contracts | Implemented locally; real provider connections, notifications, reconciliation registry and failure testing remain |
| Dead-letter recovery contracts | Implemented locally; persistent queue, protected-command resolver and approved worker/continuity operations remain |
| Neutral release declaration and deployment dry run | Implemented locally; actual solution/configuration exports, app/flow validator adapter and private target bindings remain |
| PRA/Pitstop and research-specific routing/authority | Seven pathway IDs exist as drafts; policy mapping/clinical validation remains and cannot be inferred from generic tests |
| Dataverse tables, roles, auditing and Power App/flows | Requires confirmed lane/environment/publisher, proven permissions, actual environment-first authoring and exports |
| Existing-Team/List fallback | Requires confirmed existing resources and verified low-sensitivity/item-access/audit/continuity controls |
| Live multi-user pilot and production decision | Requires named participants/owners, information-steward and IHG policy approval, staged pilot evidence and manual verification |

Independent engineering remains possible for authenticated reference resolution,
persistent adapters, explicit agenda replacement, clinical-template validation
and notification/reconciliation behavior. Their storage/connector implementations
depend on the actual selected lane and component interfaces. This audit does not
erase those pending tasks or label them completed because the local snapshot is
green. It also does not treat every unfinished task as a human-only decision.

## Precise human/platform inputs

- Approved IHG role/authority/decision-owner, quorum/conflict/delegation, urgency,
  out-of-session and ratification source and its version. The user has explicitly
  kept this confirmation pending.
- Chosen pilot lane and target environment GUID/HTTPS URL or existing
  Team/site/List/Planner resource IDs, plus the publisher/prefix choice when
  Dataverse is selected. No target is selected from ambiguous discovery.
- Information-steward classification, protected-evidence location, access,
  retention/legal-hold/archive decisions and explicit pilot permission.
- Effective licensing/DLP/write/share/audit permissions, authenticated connector
  bindings, at least two co-owners with backups and actual Canvas authoring
  session/tooling where that lane uses it.
- Actual exported app/flow/component formats for the shared ALM validation
  adapters and pre-change/restore evidence before deployment.

No person was contacted, no delegated authority was created, and no synthetic
approval was recorded as live evidence. The track remains in progress.
