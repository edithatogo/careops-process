---
name: careops-spark-cli
description: "Manages Fabric Spark work, including notebook cell code with %%configure, %%sql, PySpark and notebookutils, named notebook runs, Livy sessions, triage of failed or OOM notebook and pipeline Spark runs, and the Materialized Lake View (MLV) lifecycle. Load it before writing MLV SQL, since CREATE MATERIALIZED LAKE VIEW and its CONSTRAINT clause are Fabric-only. KQL materialized views belong to eventhouse-cli."
---

Read the upstream skill at [careops-spark-cli](../../plugins/skills-for-fabric/skills/spark-cli/SKILL.md) before starting.

Resolve upstream scripts, assets and supporting references relative to that
upstream skill directory. Run project operations from the current project,
using the Python executable available on this host. Installation alone does
not configure CLI runtimes, credentials, MCP tools or platform access.
