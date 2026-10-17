# Synthetic Dataverse provenance verification

`dataverse_provenance.verify_synthetic_destination` independently reads the
explicit Developer destination after the Outlook writer has finished. It does
not accept a caller-supplied receipt, verification boolean or row list as service
proof. Expected canonical facts describe what must be verified, not what was read.

The adapter validates a commercial Dataverse HTTPS origin, canonical nonzero
organisation/user/run UUIDs and a nonempty unique expected fact population before
credential access. It uses existing Azure CLI delegated authentication without
starting login. WhoAmI must match the pinned organisation and user. Identity GET
redirects are disabled, response size is bounded and failures are sanitised.

For each expected fact it imports Outlook's committed `row_id` contract:
UUID5 with run UUID namespace and compact JSON of protocol version, organisation
UUID and canonical fact ID. Exact primary-key reads use the official managed
Dataverse SDK against the explicit origin. Each returned primary key, required
automatic organisation lookup and canonical five-field content must agree.
Unexpected fields and collection continuations fail closed. Selected OData
context/etag annotations are permitted; the SDK's automatic organisation lookup
is checked before removal. The shared codec enforces whole-second UTC timestamp
serialization, sorted unique object references and actual column constraints.

The main project runtime validates the codec. A fixed worker in the existing
`artifacts/alm/sdk-venv/Scripts/python.exe` reads selected rows through
`DataverseClient`, `AzureCliCredential` and the closed `dv-query` operation
context. Its stdin/stdout carry only target/key/column instructions and returned
rows in memory. No package installation, compiled-package path mixing, token
cache parsing, auth-profile mutation or credential persistence is performed.
Unavailable runtime or auth fails without initiating sign-in. Authentication
profiles must remain stable during the bounded operation; identity is checked
through WhoAmI before the separate SDK reads. This is a local development
adapter, not a portable deployment or atomic multi-request identity transaction.

The summary records organisation/run binding, verified row count and the digest
of normalized canonical facts sorted by fact ID. Its class is always
`synthetic_service_readback`. The returned dataclass is not a signed credential
or transferable proof; merely constructing one has no authority. No consumer
uses it to set `dataverse_reconciled` or unlock `live_corpus` closure.

With no alternate unique key or run column in the current table, this proves
only the expected explicit primary-key set in an application-scoped synthetic
run. It does not prove no additional rows exist, full source population,
cross-run/global deduplication, source acquisition, transaction atomicity,
VUW-AI-TEST acceptance or Queensland Health permission.

## Verification on 17 October 2026

After Outlook supplied the real two-row synthetic Developer rehearsal, this
adapter independently re-queried WhoAmI and retrieved both rows through the SDK.
Organisation/user, deterministic primary keys, automatic organisation lookup,
UTC timestamps and canonical content matched. Two rows were verified, with no
new evidence files, private source-data copies, writes or login. The writer was
notified that readback was complete and cleanup could proceed under coordination.
This live service observation is distinct from the mocked unit tests.

The unit suite covers identity/content drift, wrong primary key/organisation,
unexpected fields/continuations, invalid target/run/population, missing auth,
command construction, sanitized failures, redirect/status/size/JSON handling and
the managed worker boundary. A synthetic integration test passes the same
verified expected-content digest through real reconciliation, closure, discovery
and reporting modules. Its service responses are mocked; it is not an additional
live service observation. Owner validation remains pending in that report.

No retained real VUW mailbox facts were read or copied for this work. Their
existing disposal deadline and allowlist are unchanged. The future live-corpus
adapter still requires actual authorised source inventory/population,
destination scope, frozen controls, independent replay and acceptance evidence.
