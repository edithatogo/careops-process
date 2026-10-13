# CareOps Process

CareOps Process provides privacy-preserving, object-centric process intelligence
for administrative and clinical-governance workflows.

The repository contains versioned schemas, synthetic fixtures, analytical code,
process models, tests, and deployment automation. It must never contain mailbox
exports, message content, patient or practitioner information, credentials,
tenant identifiers, production event logs, or generated operational findings.

## Core capabilities

- OCEL 2.0 event and object contracts;
- low-privilege Microsoft 365 and Dataverse fact projection;
- replay-safe checkpoints, deduplication, tombstones, and minimized dead-letter
  records;
- deterministic process-family and variant discovery;
- conformance, delay, deviation, rework, and quality measures;
- governed semantic projections; and
- explainable, human-reviewable improvement recommendations.

The module observes and analyses processes. It never changes a workflow,
approves a request, or makes a clinical, credentialing, employment, review, or
appeal decision.

## Modular domain packs

The generic core is extended through versioned domain ontologies and event
projection contracts. Domain packs are disabled or disconnected until an
approved deployment profile supplies the source mapping, privacy classification,
retention, access, and acceptance evidence.

The first credentialing pack is documented in
[`docs/credentialing-process-assurance.md`](docs/credentialing-process-assurance.md).
It models credentialing requests, evidence, professional review, committee
recommendations, delegated decisions, conditions, expiry, review, appeal, and
register activation through privacy-minimised identifiers and events.

The pack receives event facts from `careops-approve` and `careops-decisions`. It
does not ingest raw credentials, CVs, referee reports, complaints, investigation
records, patient records, committee papers, or decision free text.

## AI and process mining

AI or NLP may assist with process-family labels, event-classification proposals,
anomaly summaries, root-cause hypotheses, and improvement drafts. These outputs
must remain labelled as inferred, retain confidence and model provenance, and be
reviewed by a human. Observed events and inferred hypotheses remain separate.

No AI output may alter a source event, certify conformance, change a case,
reassign work, or implement a recommendation automatically.

## Architecture

- Python 3.14 is the canonical runtime.
- Polars is the default dataframe engine.
- OCEL 2.0 is the portable event contract.
- PM4Py is an optional, licence-gated process-mining engine.
- Mojo is an experimental Linux/WSL acceleration lane and must pass parity
  tests against the Python implementation.
- Power Automate and Dataverse provide the low-privilege ingestion path.
- Fabric, OneLake, or another managed analytical target may be used only after
  deployment-specific access, governance, and security gates pass.

## Bootstrap

```powershell
uv sync --locked --group dev
uv run pytest
uv run python scripts/check_coverage.py
uv run ruff check .
uv run pyright
pwsh -NoProfile -File tests/powershell/test_graph_mailbox_backfill.ps1
pwsh -NoProfile -File tests/powershell/test_planner_export.ps1
```

See [Conductor](conductor/index.md), the
[feasibility evidence](docs/feasibility.md), and the
[live pilot runbook](docs/live-pilot.md).

Current hardening runbooks cover [Planner exports](docs/planner-export-reliability.md),
[independent mining/coverage assurance](docs/mining-assurance.md),
[CI and dependency ownership](docs/dependency-and-ci-operations.md), and
[local solution ALM](docs/local-alm.md). Local tests and packaging do not establish
hosted CodeQL/SARIF execution, live tenant permissions, or promotion approval.

## Licence

Original material in this repository is licensed under the MIT License.
Third-party dependencies retain their own terms.
