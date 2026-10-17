# Discovery/report integration and live-closure readiness

Reviewed against the current APIs on 17 October 2026. VUW development evidence
does not grant Queensland Health source access or pilot acceptance.

## Executable path and its trust boundaries

| API | Actual checks and output | What it cannot establish |
| --- | --- | --- |
| `outlook_reconciliation.collect_folder_inventory` | Traverses supplied source pages and builds the minimized folder inventory | Authentic source origin, approved population or durable recovery from an interrupted process |
| `outlook_reconciliation.reconcile_outlook_evidence` | Validates folder graph/admission, page order/exhaustion, source denominators, fact membership and supplied destination equality | Service origin of supplied rows; it returns generic `destination_reconciled`, while `dataverse_reconciled` remains false |
| `backfill_evidence.close_reconciled_run` | Binds two supplied reconciliations to frozen inventory/configuration, compares facts/partitions/content and validates the v2 envelope | That two real acquisitions happened; it explicitly rejects `live_corpus` while synthetic/smoke closure is supported |
| `dataverse_provenance.verify_synthetic_destination` | Requeries pinned WhoAmI and exact expected primary keys through authenticated service interfaces; checks row organisation and shared serialization | Full destination population, cross-run deduplication, complete source acquisition or live approval; output is only `synthetic_service_readback` |
| `backfill_run.run_closed_backfill` | Checks closed status, strict counts/completeness flags and bound fact/configuration/partition hashes; runs the OCEL pipeline and assigns lineage | Authenticity of the supplied manifest or independent source/destination evidence |
| `backfill_run.run_authorised_closed_backfill` | Adds pilot-entry validation plus exact configuration-hash and partition-scope binding | Actual authority behind caller booleans or the referenced approval record |
| `report.build_closed_run_report` / `build_authorised_closed_run_report` | Runs discovery, quality/operational summaries, OCEL, semantic projection and coverage ledger from the validated run | Clinical/business correctness, owner acceptance or executive approval; owner validation stays pending and publication is restricted analytical review |
| `scripts/build-closed-run-report.py` | Loads supplied JSON, invokes the authorised report API and publishes atomically through `report_publication.publish_report` | Trusted source acquisition or authenticated approval resolution merely because input files exist |

The synthetic integration fixture in `tests/test_backfill_outlook_integration.py`
passes nested/empty/excluded folders, multiple pages and a duplicate through the
real reconciler, closure, discovery and report functions. The separate
`test_verified_expected_content_binds_synthetic_discovery_report` in
`tests/test_dataverse_provenance.py` also binds the mocked-service verification
digest to report content. Neither test is a source-service observation.

Actual service evidence is narrower: two synthetic Developer destination rows
were independently read and verified, then both were deleted with absence
confirmed by the Outlook owner. The earlier real VUW Inbox test remains a
30-message bounded smoke test with a local destination. These two observations
must not be joined into a claim that real mailbox facts flowed into Dataverse.

## Direct-entry enforcement finding

The helper's `live_corpus` rejection is not currently a universal report guard.
An in-memory probe using `tests.backfill_fixture.sealed_evidence`, synthetic
facts, a caller-selected `live_corpus` label and synthetic approval booleans was
accepted by `build_authorised_closed_run_report`. The direct report path does
not call `close_reconciled_run`. Hash consistency does not authenticate origin.

This finding has been sent to the coordinator before overlapping source edits.
The proposed repair is a fail-closed check at the common execution boundary
until a real live-evidence validator is integrated. No synthetic proof should
unlock that path. This document records the current limitation, not a claim
that all live entry points are already blocked.

## Requirements before live closure can be enabled

1. **Approved source population and controls.** Resolve authentic source-owner
   and information-governance decisions, admitted sources/partitions, observation
   period, destination/access, retention/disposal and rollback. Freeze the exact
   inventory and mapping/control versions. Bind them to the run and accountable
   approval record through a trusted operational layer. `validate_pilot_entry`
   checks supplied values; it is not an authority resolver.
2. **Durable source/run completeness.** Retain measured complete folder tree,
   exclusions/inaccessible populations, per-partition denominator, page/fact
   ledgers, exhaustion and rejected/filtered/duplicate accounting. Persist run
   identity, checkpoints, deletion/replay state and failure outcomes atomically
   enough to recover or explicitly abandon an interrupted acquisition. Current
   local functions validate supplied snapshots; they do not implement an
   operational durable source acquisition service or prove source truth.
3. **Authenticated destination/run binding.** Supply an approved destination
   schema and read/write scope, actual mapping and authenticated readback for
   the same run/configuration/source population. The current table has no
   alternate key or run column; UUID5 primary keys bind only the application's
   expected organisation/run/fact set. Define and verify completeness and
   isolation semantics beyond that expected subset before claiming a full
   destination population. Bind identity consistently throughout the operation;
   the current separate WhoAmI/SDK reads assume a stable auth profile.
4. **Measured replay and recovery.** Independently repeat or refresh the source
   and destination under frozen controls. Reconcile identities, content changes,
   deletion behaviour and interruption recovery; retain actual service/run
   evidence. Two hashes of supplied snapshots cannot demonstrate the external
   acquisitions or absence of drift on their own.
5. **One trusted admission path.** Integrate supported live source/destination/
   approval verification into every runner, report and CLI entry point. Reject
   caller-authored booleans, type labels or receipt-shaped JSON as proof.
   Preserve synthetic/smoke classes and prevent their promotion into live
   acceptance. Keep the live path closed until these checks are implemented
   and independently exercised.
6. **Review and acceptance.** Validate ranked families with operational owners,
   retain dispositions and rerun metrics, complete integrated code/runtime
   assurance, then record the executive fit-for-purpose/expansion decision.
   VUW Developer rehearsal and hosted test success do not meet these gates.

No additional platform reads, acquisition, private evidence copies, approval
invention or live-path enabling was performed for this review.
