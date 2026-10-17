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

## Actual Developer rehearsal — 17 October 2026

The coordinator granted a serialized ingestion-row-only writer slot after
Reliability's completed baseline and bounded metadata-recovery handoff. Using
the official Dataverse Client SDK 1.1.0, managed Azure CLI credentials and an
explicit Developer endpoint, the operator verified current WhoAmI organization
and user against the private baseline before writes. No auth profile was changed.

Two synthetic mail facts with distinct synthetic conversation references were
created under one fixed run UUID. The first attempt stopped after one create:
the service included `_organizationid_value` despite the selected columns.
That response failed the initial strict field allowlist. After explicitly
validating the returned organization lookup against the expected organization,
the next attempt read the existing row and created only the second row.
Both full payloads read back exactly; an unchanged replay read both existing
primary keys and created zero new rows. The TimeZoneIndependent column returned
the supplied whole-second UTC `Z` values exactly; compact object JSON also matched.
This is an observed partial-attempt recovery, not an atomic two-row transaction.

The private script/inputs/service receipt are in the ignored `artifacts/alm`
directory. They contain synthetic rows and private environment identifiers;
none contain the retained 30-record mailbox test. The writer slot was explicitly
released to coordination and Governance. The two rows are temporarily retained
for M365's independent authenticated service readback; exact-key cleanup is
pending that verification and its serialized cleanup slot.

The reusable `Records` protocol, `read_fact` and `ensure_synthetic_fact` functions
use the supported SDK interface. They never overwrite conflicting existing
payloads; ambiguous creates reconcile by reading the same primary key without
resending. The host must verify service identity before invoking the writer.
Local protocol tests cover lost acknowledgements, changed content and partial
readback. The first actual service rehearsal used a private bounded SDK script;
it does not by itself verify the reusable writer or independently authenticate
M365 provenance. Neither result completes TEST deployment or live-corpus closure.

## Independent verification and exact cleanup

M365 independently acquired current service identity and read both exact primary
keys through the managed SDK. Organization, user, primary keys, organization
lookups and canonical contents matched. This independently observed result is
`synthetic_service_readback`; local receipt JSON did not establish it.

After Governance explicitly paused its writer and coordination granted the
cleanup slot, fresh WhoAmI and both complete synthetic payloads were checked
again. Exactly two single-primary-key SDK deletes succeeded. Subsequent SDK
retrieval returned confirmed absence for both keys. The cleanup slot was
explicitly released to Governance and coordination. No synthetic service rows
from this rehearsal remain; private synthetic receipts are retained locally.
No real mailbox evidence, source record, authentication profile or schema was
changed by cleanup.

Sixteen destination tests and 48 existing reconciliation tests pass together
(64 total). Additional cases verify an unavailable read cannot authorize create
and an ambiguous create without a committed row cannot trigger a resend.
Scoped Ruff lint/format, strict Pyright, Bandit and Conductor checks pass.
Independent review/publication of the reusable writer remains with coordination.

## Timestamp precision repair

Panel review reproduced a lexical precision bug: Python's datetime parser can
truncate a seven-digit fractional second or accept fractional offset seconds
before the earlier microsecond check. Both changed instants could therefore
compare equal to a stored whole second during replay.

The codec now checks the timestamp grammar before parsing: full calendar date,
`T`, hours/minutes/seconds, optional all-zero fractional digits, and `Z` or a
minute-resolution `+HH:MM`/`-HH:MM` offset. Nonzero fractional digits, offset
seconds and alternate datetime syntaxes are rejected without rounding. Calendar
validity and UTC normalization are still checked by datetime. All-zero fractions
represent an exact whole second and remain safe to normalize.

Four initial regression cases failed before repair. Expanded serialize/readback/
replay regressions and a zero-fraction/minute-offset control now pass. The combined
destination, provenance and reconciliation suite passes 97 tests. No live service
calls or changes to the completed synthetic rehearsal were needed for this repair.
