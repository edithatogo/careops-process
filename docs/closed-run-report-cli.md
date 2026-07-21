# Closed-run report command

After the Power Automate backfill has closed and its sanitized evidence has
been exported to the approved evidence location, the workflow owner or analyst
can build the process-mining report with:

```powershell
$env:CAREOPS_PSEUDONYM_SECRET = '<local secret managed outside the repository>'
uv run python scripts/build-closed-run-report.py `
  --facts .\approved\minimized-facts.json `
  --evidence .\approved\backfill-evidence.json `
  --output .\approved\process-report.json
```

The facts input may contain only the minimized contract fields. The command
fails closed if the evidence is not `closed`, pagination is incomplete, counts
are not reconciled, idempotent replay is unverified, or raw content storage is
not explicitly ruled out. Never commit the input exports, secret, or generated
report if it contains tenant-derived data; retain them only in the approved
evidence location.
