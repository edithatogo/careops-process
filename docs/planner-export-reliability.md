# Planner export reliability

Run `scripts/export-planner-corpus.ps1 -OutputPath <approved-private-path>` with
PowerShell 7, delegated Azure CLI Graph access and `CAREOPS_PSEUDONYM_KEY` supplied
outside Git. Use a random secret of at least 32 bytes and protect it as a credential.
Use separate keys/destinations for accounts and approved scopes. Key rotation
changes identities; record the rotation outside the public manifest.

Only id, planId, bucketId and lifecycle dates are requested. Output facts retain
only keyed identities, UTC timestamps, controlled activities/source, and object
links. HMAC domains distinguish task, plan and bucket, even for equal raw IDs.
Narrative, assignments and human identities are never projected. Existing exports
used unseparated pseudonyms; regenerate privately rather than merge identity schemes.

Candidates reconcile as accepted candidates + duplicate candidates + rejected
candidates. Accepted candidates can emit one or two lifecycle events, so
`acquired_count` counts events and does not equal accepted candidates. Missing
IDs, invalid or timezone-free dates, and candidates without lifecycle events are
rejected. Conflicting replay for one task aborts the entire snapshot.

Identities and fact ordering are deterministic. `content_hash` is SHA-256 of
compact PowerShell JSON serialization of the ordered facts array (including `[]`
for an empty result); timestamps in the manifest vary per run. Cross-language
consumers must reproduce that serialization to compare hashes.

Graph continuation is restricted to HTTPS, port 443, the same Planner collection,
no userinfo/fragments, no repeated URLs, and no redirects. Transient 429 and selected
5xx responses receive at most two retries with bounded backoff. Other failures
abort. Error text contains no source payload, URLs, mailbox identities or tokens.
There is no partial-success publication or automatic authentication fallback.

The complete snapshot and manifest are staged together in a same-directory temporary
file then atomically replaced. An acquisition or write failure preserves previous
output. A process kill before replacement can leave a `.tmp` file; ignore it and
clean it only after checking the committed snapshot. Restrict destination permissions
and run a single writer per destination. `exhausted` refers only to the assigned-task
API listing; inaccessible tasks/plans and tenant-wide populations remain unknown.
Do not use assigned-task exhaustion as complete-population or governance approval.

Offline evidence: `pwsh -NoProfile -File tests/powershell/test_planner_export.ps1`.
Live consent, source-owner approval and smoke testing remain separate gates.
