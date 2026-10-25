# Technology Stack

- Python 3.15.1 and `uv` lockfiles; newer 3.15 patches are qualified in isolation before promotion
- Polars and Arrow for tabular processing
- OCEL 2.0 for object-centric interchange
- local deterministic variant and sequence comparisons as the default mining route
- PM4Py 2.7.23.11 as an optional, licence-gated dependency for separately
  selected model-based analysis
- Power Automate Process Mining as an optional paid service, never a baseline
  dependency
- Mojo nightly on Linux/WSL only for benchmarked acceleration experiments
- Power Automate with user-scoped Outlook/SharePoint connectors for the selected
  ingestion design; Dataverse, Fabric/OneLake, and Power BI remain separate
  options gated by their own contracts and permissions
- Microsoft Teams and Power Apps as user-facing surfaces, with Dataverse as the
  preferred canonical governance store
- Existing Teams, SharePoint/Microsoft Lists, Approvals, and Planner as a
  restricted low-sensitivity fallback when verified user-scoped access permits
- Windows-native PAC, PowerShell, and delegated APIs for user-scoped deployment;
  no required Entra app registration, service principal, tenant-admin access,
  WSL, or Linux for the governance hub
- pytest, Hypothesis, Ruff, Pyright, Bandit, pip-audit, CodeQL, Zizmor, and OSSF Scorecard

Project-owned code uses Apache-2.0 under the user-selected portfolio standard.
Preserve third-party terms, attribution, historical evidence and private-source
rights; qualify source/package changes without changing native authority.
