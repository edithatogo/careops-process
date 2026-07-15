# Feasibility baseline - 2026-07-15

## Confirmed

- GitHub CLI is authenticated to `github.com` as `edithatogo` with private
  repository, workflow, and project scopes.
- GitHub CLI is authenticated to `nswhealth.ghe.com` as `60217257` with private
  repository and workflow scopes.
- PAC CLI has a live user-scoped NSW Health Dataverse connection and can list
  four accessible Power Platform environments.
- Python 3.14.6 is installed through `uv` without administrator access.
- PM4Py 2.7.23.1 declares Python 3.14 support.
- Polars, Arrow, and synthetic event-contract testing are viable locally and in
  GitHub Actions.

## Gated or degraded

- Fabric redirected to interactive sign-in in both available browser surfaces;
  Fabric capacity/workspace permissions are therefore unverified.
- Graph Data Connect remains Entra application and Global Administrator gated.
- Mojo requires Linux or WSL and is not a native-Windows runtime. It is suitable
  only for experimental Linux CI kernels with Python parity tests.
- PACX is installed but cannot currently start because the x64 .NET 8 runtime
  is missing; only x64 .NET 10 and x86 .NET 8 are present.
- The existing Azure CLI installation is obsolete/broken and is not required
  for the initial Power Platform pilot.
- Microsoft 365 CLI is not installed.

## Decision

Proceed with the repository, schemas, synthetic harness, Dataverse/Power
Automate adapter design, and GitHub/GHE automation. Do not claim Fabric,
Graph Data Connect, Azure deployment, Mojo production parity, or live mailbox
ingestion until their dedicated track gates pass.

