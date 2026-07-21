# Corpus-scale pilot gate - 2026-07-21

## Current decision

The corpus-scale pilot is **not authorised to start**. The repository and
delegated Planner adapter are ready for gated execution, but source-owner and
information-governance approval have not been recorded.

## Gate state

| Gate | State | Evidence |
| --- | --- | --- |
| Source inventory | partial | `docs/corpus-inventory-20260719.md` |
| Planner delegated endpoint | adapter validation complete | 28 tasks, 38 minimized events, one page exhausted |
| Outlook mailbox | blocked | current Graph probe returned HTTP 403 |
| SharePoint search | blocked | current Graph probe returned HTTP 403 |
| Teams discovery | inconclusive | current Graph probe returned HTTP 400 |
| Dataverse source | narrow smoke test only | four approval records; no corpus claim |
| Source-owner approval | pending | no approval evidence recorded |
| Information-governance approval | pending | no approval evidence recorded |
| Observation/configuration freeze | pending | no pilot configuration signed off |
| Rollback and retention approval | pending | runbook exists; operational approval absent |
| Repeat governed run | pending | Planner validation used an ephemeral key |

## Consequence

The system must not publish a claim about IHG's main processes, begin workflow
improvement experiments, or mark this track complete. The next valid action is to
obtain approvals and broaden the authorised source set, then run the manifest gate
before extraction.
