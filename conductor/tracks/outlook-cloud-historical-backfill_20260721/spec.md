# Specification: Cloud-only complete historical Outlook mailbox backfill

## Objective

Provide a cloud-only Power Automate acquisition route that reads the entire
authorised historical Outlook mailbox through the existing Office 365 Outlook
connection, projects privacy-minimized facts to Dataverse, and gates OCEL
process discovery on demonstrable completeness and reconciliation.

## Requirements

- Reuse the existing TESL Office 365 Outlook connection; no new Entra app is
  required.
- Use `Get emails (V3)` for historical acquisition, separate from the arrival
  trigger used for future events.
- Inventory and freeze all authorised folders, including nested folders.
- Process every included folder to end-of-pagination with no implicit date
  restriction.
- Record excluded, inaccessible and empty folders distinctly.
- Persist only minimized, pseudonymised metadata and never mailbox body,
  subject, sender, recipients or attachments.
- Write per-folder manifests with counts, pages, timestamps, hashes,
  duplicates, rejections, dead letters and checkpoint state.
- Require source-to-projection reconciliation and idempotent rerun before
  declaring the backfill complete.
- Run OCEL reconstruction and process discovery only from a closed run manifest.
- Preserve source coverage, uncertainty and governance approval boundaries in
  executive outputs.

## Acceptance criteria

1. The contract validates and rejects incomplete or privacy-unsafe manifests.
2. The flow blueprint covers folder inventory, nested folders, pagination,
   retries, checkpointing, idempotency and minimized Dataverse projection.
3. A live authorised run records every included folder and exhausted page.
4. Candidate, acquired, duplicate, rejected and dead-letter counts reconcile.
5. An unchanged rerun produces no new event identities.
6. The resulting OCEL corpus and process findings are traceable to the same run
   manifest and are not labelled tenant-wide without evidence.
7. Governance approval, owner validation and the IHG Executive decision are
   recorded before operational use.

## Out of scope

- Outlook desktop/COM as the production route.
- Circumventing Entra, Exchange, Power Automate or information-governance
  controls.
- Claiming a complete mailbox where a folder is inaccessible or pagination is
  not exhausted.
