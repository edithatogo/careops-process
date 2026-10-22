# Repository and user-level Codex skills

The selected upstream skills are pinned as submodules under `.agents/plugins/`.
[The manifest](../.agents/skills-manifest.json) records each URL, full commit,
licence, selected skill and runtime prerequisites. Codex discovers the small
entrypoints in `.agents/skills/`; resources remain with their upstream source.
Microsoft maintains the Microsoft sources; PnP maintains CLI for Microsoft 365
as a community project. Conductor remains a separate upstream source.

## Clone and validate

```powershell
git -c core.longpaths=true clone --recurse-submodules https://github.com/edithatogo/careops-process.git
cd careops-process
uv sync --frozen --group dev
uv run python scripts/validate_conductor.py
```

For an existing Windows clone, run
`git -c core.longpaths=true submodule update --init` first. PnP's upstream test
fixtures include long paths; the per-command setting avoids Windows checkout
failures without changing global Git configuration. Source updates
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

For live work, reuse the existing qualified account/client/environment route and
current target evidence. A skill installation or source update is not a reason
to start a new login, replace a profile or infer new platform permissions.
Verify only changed prerequisites for the selected operation.
Keep credentials, tenant-specific configuration and live data outside public
Git. Repository completion must not be reported as platform deployment.


## Review submodule and manifest updates together

A bot's gitlink-only update intentionally fails pinned-source validation until
`.agents/skills-manifest.json` names the same reviewed commit. Check the selected
upstream skill paths, supporting resources and licence at the old/new commits;
retain unchanged local entrypoints when their content and mapping are unchanged.
Update only that source's manifest commit, initialize its exact gitlink, and run
`validate_conductor.py` plus the setup tests before fresh current-head CI. Keep
other pending source updates separate. Do not bypass checkout/manifest/resource
checks, regenerate aliases for unrelated sources, configure native tools or copy
credentials as part of this source-only update.


The reviewed Power Platform source at `e67e459ac316e9c0bc8b972d11c955a1d84c3097`
changes one selected skill: Canvas MCP configuration recognises host-specific
`connect` names and confirms configuration only after a successful connection.
Its local discovery description now matches that upstream selection. The other
11 selected Power Platform skill directories and upstream licence are unchanged.
Unselected upstream runtime/server changes are not installed or qualified here.

The upstream 404 recovery suggestions are generic. In this suite, a 404 alone
does not identify the wrong account or authorize account/flow substitution.
Preserve the user-selected VS Code provider, client, account, tenant, resource
and current target; distinguish a missing object, expired session, transport
failure and an actual policy denial before choosing a supported recovery.
Do not force account selection, request consent or start a different login flow
merely because a newly installed skill suggests it. Installation is source
availability, not a connected Canvas session or deployment result.
