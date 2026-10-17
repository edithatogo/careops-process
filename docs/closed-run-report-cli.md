# Closed-run report command

The consumer now requires the [v2 evidence interface](closed-run-evidence-v2.md)
and [machine-readable schema](../contracts/closed-run-evidence-v2.schema.json).
Summary-only evidence is rejected. Approval must bind the configuration hash,
and facts must match the partition and complete-input hashes. Graph exporter
`acquired` output still needs independently supplied folder/page and destination
reconciliation evidence; it cannot be promoted by changing its status.

After the Power Automate backfill has closed and its sanitized evidence has
been exported to the approved evidence location, the workflow owner or analyst
can build the process-mining report with:

```powershell
$env:CAREOPS_PSEUDONYM_SECRET = '<local secret managed outside the repository>'
uv run python scripts/build-closed-run-report.py `
  --facts .\approved\minimized-facts.json `
  --evidence .\approved\backfill-evidence.json `
  --pilot-entry .\approved\pilot-entry.json `
  --output .\approved\process-report.json
```

The facts input may contain only the minimized contract fields. The command
fails closed if the evidence is not `closed`, pagination is incomplete, counts
are not reconciled, idempotent replay is unverified, or raw content storage is
not explicitly ruled out. Never commit the input exports, secret, or generated
report if it contains tenant-derived data; retain them only in the approved
evidence location.

The v2 report contains OCEL, candidate process families, operational patterns,
corpus quality and a coverage ledger from the same validated run. The ledger
keeps source-record counts separate from emitted-event counts, labels evidence
as synthetic/smoke-test/live, and leaves tenant-wide coverage unknown and owner
validation pending. It is a restricted analytical review artifact, not an
owner-validated executive decision. Validation diagnostics do not echo input
payloads, and validation failure leaves a previous report untouched.


Publication stages complete JSON in the approved output directory, flushes it to
disk and replaces the destination only after serialization succeeds. A failed
write or replacement leaves the previous report intact and reports a generic
error. Output cannot resolve to the facts, evidence or approval input path.
Caught failures remove staging files. After an abrupt process/host crash,
operators may find `.careops-report-*.json` stages in the approved directory:
confirm no publisher is running, verify the authoritative report, then dispose
of abandoned stages under the same approved retention policy. Never publish a
partial stage or use it as closure evidence.
