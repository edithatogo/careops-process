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

- Python 3.15.1 is required for active development, builds, tests and CI. Qualify newer patches within the 3.15 line before promotion.
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

Original material in this repository is licensed under Apache-2.0.
Third-party dependencies retain their own terms.

## Frozen dependency graph submission

The main-only `Frozen dependency graph` workflow uses pinned uv 0.13.5 and a
verified repo-local Python 3.15.1 helper. It exports the existing frozen lock with
all declared groups and extras, then uses the immutable CareOps snapshot adapter.
This includes optional mining and diagnostic dependencies as security inventory;
it does not install, activate or licence-approve those providers, resolve a new
lock, or change the application runtime.

The trusted job submits once, requires GitHub's explicit acceptance and snapshot
ID, and checks all exact package identities in the returned dependency graph.
Retained payload edges describe the frozen export; package readback alone does
not prove that GitHub reproduced every edge or active runtime scope. Submission
and graph receipts are retained on failure. Reconcile an accepted ID before any
manual retry; never resubmit solely because readback is temporarily incomplete.
The existing automatic provider's Python-version limitation is separate from
this supported explicit snapshot route; no security setting is changed.

Retain [LICENSE](LICENSE) and [NOTICE](NOTICE) with project-owned source distributions.
