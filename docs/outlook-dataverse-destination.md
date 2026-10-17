# VUW synthetic destination integration

The current lane targets the verified personal VUW Developer environment.
VUW-AI-TEST acceptance remains blocked by its effective privileges; QH work is
deferred. Only explicitly synthetic rows are used. The retained 30-record mailbox
test is neither copied nor reacquired for this work.

## Shared v1 mapping

`outlook_dataverse_destination.py` owns the shared pure mapping functions for
the writer and M365 provenance verifier. It performs no authentication or writes.

The verified table is `cop_processevent`, entity set `cop_processevents`, primary
key `cop_processeventid`. The five mapped columns are `cop_eventkey` (String200),
`cop_activity` (String100), `cop_sourcesystem` (String100), `cop_objectids`
(Memo4000), and `cop_timestamputc` (DateAndTime, TimeZoneIndependent).
There are no alternate keys or run-binding columns.

`row_id(org_id, run_id, fact_id)` requires canonical nonzero UUIDs and a strict
mail pseudonym. The UUID5 namespace is the run UUID; its name is compact ASCII
JSON `["careops-outlook-destination-v1", org_id, fact_id]`. Organization, run and
fact jointly bind each primary key. This is application-scoped synthetic-run
identity, not a server-enforced unique event key or cross-run deduplication.

`serialize_fact` revalidates the exact canonical five-field mail model, checks
whole-second timezone-aware instants, writes explicit UTC `Z`, and serializes
nonempty unique conversation references as sorted compact JSON within 4000
characters. Subsecond timestamps are rejected rather than rounded.
`parse_readback` accepts exactly the five selected mapped fields. The transport
must first validate the expected primary key and separately handle permitted
OData annotations; unselected content must not silently become a fact.

## Service boundary and remaining work

Only a confirmed exact-primary-key 404 may establish absence. Create must supply
the deterministic primary key. Conflict or ambiguous create requires readback of
that same key and exact canonical equality; changed existing content must fail
without overwrite. An unchanged replay must reuse the same keys and create zero
new rows. Partial writes do not establish atomic multi-row completion.

Reliability owns platform authentication, baseline and metadata changes.
Destination writes require its completed baseline handoff and the coordinator's
serialized writer slot. Supported managed SDK reads/writes must explicitly target
Developer, regardless of the active PAC profile. M365 independently owns actual
service-origin identity/readback verification; local mapping tests cannot confer
that provenance or unlock live-corpus closure.

Initial local evidence: ten tests pass, including five failing-before-code codec
tests. Scoped Ruff formatting/lint and strict Pyright pass. Actual synthetic
create/readback/replay and service timestamp representation remain to be tested.
