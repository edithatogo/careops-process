# Live pilot result - 2026-07-16

The first low-privilege pilot was executed against the user-scoped Dataverse
environment using the existing approval metadata tables. Only metadata fields
were read: record timestamps, status/result, source, stage, and pseudonymous
approval identifiers. Titles, details, comments, people, email addresses, and
payloads were not read or persisted.

## Observed result

- 4 approval objects were observed.
- 8 minimized events were emitted: 4 `approval_created` and 4
  `approval_decided`.
- The event log was validated as OCEL 2.0 and pseudonymized with an ephemeral
  HMAC secret.
- PM4Py loaded the equivalent OCEL 2.0 JSON and confirmed 8 events, 4 objects,
  one object type, and 4 identical `approval_created` -> `approval_decided`
  variants.
- Mean observed approval lifecycle duration was approximately 0.0104 hours
  (37.5 seconds).

The local, non-repository artifacts are written to:

- `C:\Temp\careops-live-event-log.json`
- `C:\Temp\careops-live-projection.json`
- `C:\Temp\careops-live-review.json`

These artifacts must not be committed or uploaded because they are derived
from live tenant records, even though their fields were minimized.

## Review and improvement state

The review queue is pending human confirmation that this four-record sample is
representative. A non-automated experiment named
`approval-turnaround-baseline-20260716` is proposed with a 48-hour duration
guardrail and 0.2 deviation guardrail. No recommendation breached either
guardrail, and no workflow was changed automatically.

## Remaining platform gates

- Creating dedicated `careops_*` Dataverse tables failed with the explicit
  `prvCreateEntity` privilege denial. The user has Environment Maker and
  Approvals User roles, but not the required table-creation privilege.
- Power BI API access currently returns zero workspaces, so semantic projection
  publication cannot yet be verified.
- No tenant-approved embedding, Copilot, or LLM endpoint was available through
  the current low-privilege surface; enrichment remains deterministic and
  explainable.
