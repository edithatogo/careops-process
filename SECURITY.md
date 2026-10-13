# Security and secret scanning

Run the repository-local Gitleaks scan before committing:

```powershell
gitleaks git --config .gitleaks.toml --redact --no-banner
```

The GitHub Actions `Secret scan` workflow performs a full-history scan on pull
requests and pushes to `main`. Do not add credentials, mailbox exports, tenant
configuration, personal identifiers or clinical content. If a secret is
detected, revoke or rotate it first, then remove it from the working tree and
history through the repository security process.
