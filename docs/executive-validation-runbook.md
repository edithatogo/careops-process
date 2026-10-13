# Governance and Executive validation

Technical completion of a backfill is not approval to use its findings. Before
an IHG Executive decision, store the sanitized structure in
`config/executive-validation.example.json` at the approved evidence location.

The record must identify the closed run and external evidence reference, and
must separately record mailbox scope approval, information-governance approval,
operational-owner validation of process families, and the Executive decision.

Validate it with:

```powershell
uv run python scripts/validate-executive-validation.py .\approved\executive-validation.json
```

The validator allows a pending record while the gates are open. It rejects any
non-pending Executive decision unless scope and IG approval and operational-owner
validation are all complete. Do not commit approvals, names, UPNs, mailbox
identifiers, screenshots, clinical content, or meeting records to the public
repository.
