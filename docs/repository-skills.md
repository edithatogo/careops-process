# Repository and user-level Codex skills

The selected upstream skills are pinned as submodules under `.agents/plugins/`.
[The manifest](../.agents/skills-manifest.json) records each URL, full commit,
licence, selected skill and runtime prerequisites. Codex discovers the small
entrypoints in `.agents/skills/`; resources remain with their upstream source.
Microsoft maintains the Microsoft sources; PnP maintains CLI for Microsoft 365
as a community project. Conductor remains a separate upstream source.

## Clone and validate

```powershell
git clone --recurse-submodules https://github.com/edithatogo/careops-process.git
cd careops-process
uv sync --frozen --group dev
uv run python scripts/validate_conductor.py
```

For an existing clone, run `git submodule update --init` first. Source updates
are deliberate: inspect upstream changes, update the gitlink and manifest SHA
together, then run validation. Do not use automatic submodule tracking updates
as a substitute for reviewing an update.

## Install skills generally for Codex

```powershell
uv run python scripts/install_repo_skills.py --user-home "$env:USERPROFILE/.codex"
```

If Codex uses a custom `CODEX_HOME`, pass that directory instead. The installer
creates entrypoints in that home's `skills/` and independent, versioned copies
of complete upstream sources in `skill-sources/careops/`. Moving or deleting
this project does not remove the user-level skills. Existing unrelated skills
are preserved. Repeating installation is supported. Skill discovery occurs on
the next turn; reload Codex if an updated skill is not visible.

## Live prerequisites remain unverified

These installations provide instructions and references. They do not install
or authenticate PAC, Dataverse CLI, Microsoft 365 CLI, Azure CLI, Node.js,
Fabric CLI, FlowAgent, or MCP servers. They do not grant environment permissions,
consent, licences or capacity. Some upstream skills assume other agent tool
names; use available Codex equivalents and verify the actual prerequisite.

VUW account setup is the next stage: establish the intended account and CLI
profiles, confirm environment access, then verify each required live capability.
Keep credentials, tenant-specific configuration and live data outside public
Git. Repository completion must not be reported as platform deployment.
