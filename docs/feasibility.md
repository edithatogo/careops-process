# Feasibility baseline - 2026-07-15

## Confirmed

- GitHub CLI is authenticated to `github.com` as `edithatogo` with private
  repository, workflow, and project scopes.
- An enterprise Git hosting mirror is configured separately from the public
  GitHub repository; its host, account and permissions are not recorded here.
- PAC CLI has a live user-scoped NSW Health Dataverse connection and can list
  four accessible Power Platform environments.
- Python 3.14.6 is installed through `uv` without administrator access.
- PM4Py 2.7.23.1 declares Python 3.14 support.
- Polars, Arrow, and synthetic event-contract testing are viable locally and in
  GitHub Actions.

## Gated or degraded

- Azure CLI 2.88 can authenticate as the NSW Health user and acquire a Power BI
  API token, but the API returns zero accessible workspaces and zero dedicated
  capacities. Fabric is therefore unavailable under current permissions.
- Graph Data Connect remains Entra application and Global Administrator gated.
- Mojo requires Linux or WSL and is not a native-Windows runtime. It is suitable
  only for experimental Linux CI kernels with Python parity tests.
- PACX starts after installing the user-scoped x64 .NET 8.0.29 runtime. Its
  previous encrypted credential store was corrupt and has been preserved in a
  timestamped local backup. A replacement `careops-owner` OAuth profile is now
  connected and `pacx auth ping` succeeds against Dataverse 9.2. PAC CLI also
  remains connected and usable.
- Azure CLI 2.88 is installed through `uv` on Python 3.13 and is tenant-level
  authenticated. No Azure subscription is exposed to the account.
- Microsoft 365 CLI 11.9.0 can be installed under Node 24, but the global Node
  26/npm installation produces incomplete dependency trees and the isolated
  CLI does not complete startup. Azure CLI, Microsoft Graph REST, PAC CLI, and
  Power Platform connectors are the supported automation surfaces until the
  upstream Node/tool interaction is resolved.
- WSL is not installed and its installation requires a Windows feature change;
  Mojo therefore remains a Linux GitHub Actions experiment rather than a local
  runtime requirement.
- GHE Actions jobs fail before the first step, indicating that no compatible
  `ubuntu-latest` runner is available to this repository. GitHub.com Actions is
  the execution mirror until an enterprise runner is assigned.
- GitHub Advanced Security is not purchased for the private personal repo.
  Secret scanning is unavailable there and is enterprise-policy-blocked on
  GHE. Repository-local secret scanning and fail-closed CI are required.

## Decision

Proceed with repository, schemas, synthetic harness, Dataverse/Power Automate
adapter design, and GitHub.com CI mirrored to GHE. Do not claim Fabric, Graph
Data Connect, Azure resource deployment, Mojo production parity, GHE runner
execution, or live mailbox ingestion until their dedicated gates pass.
