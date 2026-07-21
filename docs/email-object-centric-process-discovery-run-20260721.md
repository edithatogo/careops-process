# Email object-centric process-discovery run

**Run date:** 2026-07-21  
**Repository:** `careops-process`  
**Purpose:** Execute the available Outlook/email ingestion and object-centric process-discovery path, and report only evidence obtained during the run.

## Executive outcome

The email-specific live run could not acquire mailbox data. The Microsoft Graph request to enumerate the signed-in user's Outlook mail folders returned **HTTP 403 Forbidden**. Consequently, no email events were reconstructed and no email-derived process families, bottlenecks, or hand-offs can be reported.

The repository workflow is structurally ready for a low-privilege, user-owned email source. Its contract validation succeeded, and the object-centric process-mining components are implemented and tested against synthetic/previously acquired data. The missing result is tenant access and an approved mailbox scope—not an analytical output.

## Execution evidence

| Check | Result | Interpretation |
|---|---|---|
| Microsoft Graph Outlook mail-folder probe | **Failed: HTTP 403** | Current delegated token cannot enumerate the mailbox; email population remains unknown. |
| Email flow-contract validation | **Passed** | `contracts/power-automate-tesl-flow.json` conforms to the repository contract validator. |
| Focused flow/OCEL/landscape tests | **16 passed** | Core contract and analytical behaviour passed the selected tests. |
| Focused-test command exit status | **Failed on coverage threshold** | The repository enforces 90% overall coverage; a partial test selection measured 33.55%, so this is not a functional test failure. |

## Intended workflow confirmed

1. Trigger on a narrow, user-owned Outlook/TESL source.
2. Keep only minimized event metadata: identifier, timestamp, activity classification, source, and pseudonymous object references.
3. Reject message body, preview, subject, sender, recipients, and other raw narrative/identity fields.
4. Persist the minimized event projection and checkpoint in Dataverse.
5. Reconstruct OCEL 2.0 objects, events, and relationships.
6. Discover process families empirically from object-linked traces, including sequence variants, cross-source hand-offs, loops, durations, and incomplete lifecycles.

## Findings from this run

- **Email-derived process identification:** not available; zero mailbox records were acquired.
- **Coverage denominator:** unknown; the 403 response prevents treating the mailbox as empty or complete.
- **Object-centric method:** verified in the repository contract and implementation, but not exercised against live email during this run.
- **Privacy controls:** verified in the email contract: raw message fields are forbidden and raw payloads must not be stored.
- **Human/tenant gate:** an approved delegated Outlook connection or Power Automate flow with an authorised mailbox scope is required before rerunning.

## What this does not establish

This run does not establish that there are no email-based processes, nor does it identify the main IHG executive processes. Planner and Dataverse evidence cannot be substituted for email evidence because those sources have different coverage and semantics.

## Rerun condition

Rerun the same command-line probe and ingestion path after the resource owner enables the approved user-scoped Outlook/Power Automate connection. A valid run must record the mailbox scope, pages exhausted, candidate and acquired counts, rejection/duplicate counts, watermark, and content hash before process discovery is accepted.

## Follow-up diagnosis and remediation

The delegated Graph token was inspected without recording the token itself. Its `scp` claim contained profile, directory, group, audit, and application-management permissions, but **did not contain `Mail.Read`**. The token therefore authenticates the user but does not authorise Outlook mail access.

An explicit token request for `https://graph.microsoft.com/Mail.Read` was then attempted. Microsoft Entra returned **AADSTS65002**, stating that consent for the Azure CLI first-party application and Microsoft Graph must be preauthorised by the API owner. This confirms that the missing permission cannot be repaired inside this repository or by retrying the request.

An Outlook-resource token was also tested. It was still issued to the **Microsoft Azure CLI** application (`appid` `04b07795-8ddb-461a-bbee-02f9e1bf7b46`) with only `user_impersonation`, not to an Outlook/Power Automate connector identity with mailbox access. Calling the legacy Outlook REST endpoint with that token returned **HTTP 401**. An Outlook connector in Power Automate is a managed connector connection; it is not an app ID that can be selected for an Azure CLI token request.

Required tenant-side remediation:

1. Have the resource owner/administrator approve an appropriately scoped Outlook or Power Automate connection for the authorised mailbox/source.
2. Grant or preauthorise the minimum delegated mail permission required by the selected connection (`Mail.Read` if message metadata must be read), subject to NSW Health policy.
3. Reauthenticate to obtain a fresh token containing the approved scope.
4. Rerun the mailbox-folder probe, then the minimized ingestion and OCEL discovery pipeline.

No repository code change is required for this specific 403. The privacy and fail-closed behaviour should remain unchanged.

## Source artefacts

- `contracts/power-automate-tesl-flow.json`
- `docs/live-pilot.md`
- `src/careops_process/ocel.py`
- `src/careops_process/correlation.py`
- `src/careops_process/landscape.py`
