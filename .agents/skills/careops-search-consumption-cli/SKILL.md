---
name: careops-search-consumption-cli
description: "Finds Fabric items across every workspace with the Catalog Search API when the workspace is unknown, locating an item by display name, inventorying one item type tenant-wide, and returning the workspace and item IDs later calls need. Dataflow Gen1 and Gen2 items are not supported. Use only to locate items; once found, query them with the owning item skill such as sqldw-cli, spark-cli, eventhouse-cli or fabriciq."
---

Read the upstream skill at [careops-search-consumption-cli](../../plugins/skills-for-fabric/skills/search-consumption-cli/SKILL.md) before starting.

Resolve upstream scripts, assets and supporting references relative to that
upstream skill directory. Run project operations from the current project,
using the Python executable available on this host. Installation alone does
not configure CLI runtimes, credentials, MCP tools or platform access.
