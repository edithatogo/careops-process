# careops-process

Privacy-preserving, object-centric process intelligence for CareOps.

This repository contains schemas, synthetic fixtures, analytical code, and
deployment automation. It must never contain mailbox exports, message content,
personal information, credentials, tenant identifiers, or production event
logs.

## Architecture

- Python 3.14 is the canonical runtime.
- Polars is the default dataframe engine.
- OCEL 2.0 is the portable event contract.
- PM4Py is an optional, licence-gated process-mining engine.
- Mojo is an experimental Linux/WSL acceleration lane and must pass parity
  tests against the Python implementation.
- Power Automate and Dataverse provide the low-privilege ingestion path.
- Fabric/OneLake is the preferred managed-compute target when access is proven.

## Bootstrap

```powershell
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run pyright
```

See [Conductor](conductor/index.md) for the executable roadmap and
[feasibility evidence](docs/feasibility.md) for current platform gates.

