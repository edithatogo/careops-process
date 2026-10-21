# Technology Stack

- Python 3.14 and `uv` lockfiles
- Polars and Arrow for tabular processing
- OCEL 2.0 for object-centric interchange
- PM4Py 2.7.23.8 as an optional AGPL/licence-reviewed dependency
- Mojo nightly on Linux/WSL only for benchmarked acceleration experiments
- Power Automate, Dataverse, Fabric/OneLake, and Power BI when permissions allow
- Microsoft Teams and Power Apps as user-facing surfaces, with Dataverse as the
  preferred canonical governance store
- Existing Teams, SharePoint/Microsoft Lists, Approvals, and Planner as a
  restricted low-sensitivity fallback when verified user-scoped access permits
- Windows-native PAC, PowerShell, and delegated APIs for user-scoped deployment;
  no required Entra app registration, service principal, tenant-admin access,
  WSL, or Linux for the governance hub
- pytest, Hypothesis, Ruff, Pyright, Bandit, pip-audit, CodeQL, Zizmor, and OSSF Scorecard
