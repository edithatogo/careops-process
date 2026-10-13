# Account and stage boundary — user direction, 14 October 2026

The user clarified: VUW is to be leveraged for testing, not piloting. An actual
process-discovery pilot is intended only for the user's Queensland Health account.

## VUW testing

Complete the authorised account sign-in and verify available user-scoped test
capabilities. Use synthetic or explicitly designated non-sensitive test data to
exercise connection, contracts, minimized projection, pagination/checkpoints,
source/destination reconciliation, replay and report publication. Record this
as development/integration test evidence, with synthetic/smoke-test labels.

The earlier proposed seven-day Inbox read was not confirmed by the user and is
not a requirement for synthetic-first account testing. Login authority is not
recorded as authority to extract an organisational mailbox population. VUW
bindings and results must not become Queensland Health configuration or evidence.

## Queensland Health pilot

Phases 6–7 of the corpus-scale track refer to the actual Queensland Health pilot.
Before actual acquisition, verify that account/source access and record the
relevant data-owner and information-governance decisions, admitted partitions,
observation period, approved destination/access, retention/disposal and rollback.
Freeze/hash the exact inventory and configuration. Retain those genuine records
outside Git. Actual source/destination reconciliation and independent replay,
operational-owner validation and the Executive decision remain required.

Development testing is useful preparation and does not satisfy these pilot gates.
No approval, source permission, live extraction or pilot finding is established
by the account/stage clarification itself. Do not waive acquisition controls by
renaming a real-data run as testing.

## Current handoff

The M365 chat prepared a VUW test plan, a Queensland Health pilot decision brief
and a deliberately unapproved pilot-entry JSON under its local `outputs/`.
The VUW pilot-labelled draft is superseded. Outlook owns the active VUW sign-in;
no duplicate sign-in should be started. Once human authentication or source/IG
decisions are needed, stop rather than scheduling or repeatedly polling.
The coordinator owns final shared integration verification.
