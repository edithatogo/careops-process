# Feasibility baseline

Last reviewed: 2026-08-29

For 14 October 2026 local assurance evidence, see
[mining and independent coverage](mining-assurance.md),
[CI and dependency controls](dependency-and-ci-operations.md), and
[local ALM](local-alm.md). The dated feasibility boundary below is preserved;
current tenant capabilities still require a new authorised receipt.

This document records the reusable feasibility boundary for CareOps Process.
Deployment-specific permissions and tool availability must be captured in a
separate, non-sensitive environment receipt and reverified before each pilot.
Historical organisation, account, host, and tenant details are not part of the
product contract.

## Repository-confirmed capabilities

- Python, Polars, Arrow, and synthetic event-contract testing are viable in a
  local or hosted CI environment.
- OCEL 2.0, privacy-minimised fact projection, replay, tombstone, dead-letter,
  conformance, semantic-projection, and recommendation contracts are present.
- Power Automate and Dataverse adapters can be designed and tested with
  synthetic data without tenant-wide permissions.
- PM4Py may be used as an optional process-mining engine after licence and
  deployment review.
- GitHub or an approved enterprise Git host can run credential-free validation
  where an appropriate runner is available.

## Deployment-gated capabilities

The following must not be claimed until the selected environment provides and
evidences them:

- accessible Power Platform development, test, and production environments;
- approved user-scoped or workload-identity connections;
- Dataverse tables and security roles;
- Power BI or Fabric workspace and capacity;
- Microsoft Graph or Graph Data Connect permissions;
- Azure subscription and approved resource deployment;
- hosted or self-hosted CI runners;
- secret scanning and code-security services;
- live mailbox, Teams, SharePoint, or source-system ingestion;
- local or hosted AI/LLM access for NLP or process-family discovery; and
- production support, monitoring, retention, backup, recovery, and continuity.

## Supported low-privilege baseline

The preferred initial path uses:

- a narrow, approved source such as a Dataverse or SharePoint status row;
- only event ID, activity, timestamp, source system, and pseudonymous object
  references;
- no message body, subject, sender, recipient, attachment, practitioner,
  patient, or clinical narrative fields;
- replay-safe checkpoints and idempotency;
- synthetic or approved minimised pilot data;
- no production writes; and
- a documented human governance decision before live execution.

## Tooling fallbacks

- Use Power Automate and standard connectors before requesting tenant-wide app
  permissions.
- Use Dataverse operational views before making Power BI or Fabric a dependency.
- Use local or hosted Python only for analytical work that cannot be safely or
  maintainably expressed in Power Platform.
- Treat Mojo, preview Copilot features, Dataverse MCP, and other emerging tools
  as optional experiments behind feature flags and parity tests.
- If enterprise-hosted CI is unavailable, another approved runner may execute
  credential-free validation against the same commit; this is supporting
  evidence, not proof of equivalent enterprise controls.

## Pilot decision

Proceed with schemas, synthetic fixtures, event projections, adapters, tests,
and privacy-safe reporting. Do not claim live ingestion, Fabric, Graph, Azure,
AI production use, or operating effectiveness until the deployment-specific
gates are passed and evidenced.

Repository completion, environment deployment, successful pilot execution, and
operating effectiveness are separate statuses.
