# Live corpus operating controls

## Preconditions

Before a live run, the operator must record the approved source partitions,
observation period, classification, access boundary, destination type, retention
period, stable pseudonym key location and named source/information owners. The key
must be supplied through `CAREOPS_PSEUDONYM_KEY`; it must never be written to the
repository, command output, run manifest or corpus.

The example policy in `contracts/corpus-handling-policy.example.json` is a
template, not evidence of approval. Transient feature extraction is disabled by
default and requires explicit allow-listing in an approved policy.

## Planner full-snapshot validation

Run from a Windows PowerShell session authenticated through Azure CLI:

```powershell
$env:CAREOPS_PSEUDONYM_KEY = '<retrieve from approved secret location>'
./scripts/export-planner-corpus.ps1 -OutputPath 'C:\approved\careops-planner-corpus.json'
Remove-Item Env:CAREOPS_PSEUDONYM_KEY
```

The script requests only opaque identifiers, lifecycle timestamps and completion
percentage; emits pseudonymous object relationships; follows `@odata.nextLink` to
exhaustion; and reports counts, exclusions, checkpoint state and a content hash.
The result covers only the tasks returned to the signed-in user by
`/me/planner/tasks`. It is not an IHG-wide or tenant-wide denominator.

## Refresh and deterministic rebuild

1. Freeze the policy version, source query, observation boundary and stable key.
2. Preserve the prior manifest and content hash, not the protected source payload.
3. Re-run the full snapshot or an approved exclusive-watermark acquisition.
4. Reconcile candidates, acquisitions, duplicates, filtered rows, rejections and
   pages before advancing a checkpoint.
5. Compare event identities and hashes. Investigate unexplained drift before
   publishing refreshed analytics.
6. If a source is withdrawn, mark it withdrawn and retain the coverage limitation;
   do not replace it with an empty partition.

## Deletion and expiry

1. On expiry, withdrawal or revocation, stop refresh jobs and remove live corpus,
   intermediate features, caches and derived drill-down artifacts from approved
   destinations.
2. Record only the run identifier, deletion time, artifact hashes and deleted
   count in a deletion receipt. Do not retain deleted payload in a dead letter or
   audit attachment.
3. Remove temporary environment variables and revoke resource-owner connections
   when no longer needed.
4. Rebuild only after a new or still-valid approval is confirmed. Use the same
   stable key only when the approved purpose requires longitudinal linkage.

## Failure and continuity

- Treat permission denial, throttling beyond retry budget, cursor loops, unknown
  retention, unapproved destinations and policy ambiguity as incomplete runs.
- Never publish partial runs as complete accessible-population results.
- Multiple authorised operators should hold documented run permissions and know
  how to verify connection health without sharing credentials.
- Live corpora remain outside Git and public CI. Repository fixtures remain
  synthetic and tenant-neutral.
