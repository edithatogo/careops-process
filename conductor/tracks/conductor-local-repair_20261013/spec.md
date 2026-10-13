# Conductor and Microsoft skills local setup

Repair the local Conductor configuration and make relevant Microsoft and PnP
skills reproducible in this repository and available to Codex across projects.

## Requirements

- Preserve existing product, privacy, workflow and manual-verification rules.
- Add general and Python style guides compatible with Ruff and strict Pyright.
- Register every existing track and migrate legacy inline plans without losing
  requirements, completion markers, evidence or external gates.
- Reconcile credentialing progress only where implementation and tests support it.
- Pin Conductor and five Microsoft/PnP source repositories as Git submodules.
- Expose selected skills through repository and independent user-level Codex
  entrypoints, retaining upstream resources, source commits and licences.
- Add read-only validation of configuration, tracks, links, metadata, skills and
  source pins. Test failures with synthetic temporary repositories.
- Run the validator in CI after initialising the pinned submodules.

## Acceptance

All eleven tracks are registered once, contain linked spec, plan and metadata
documents, and can be read by Conductor. Selected skills resolve their upstream
instructions and resources in both repository and user scope. Validation,
formatting, lint, typing, tests and security checks pass. Local commits preserve
the work. Human verification is required before this track is marked complete.

## Boundaries

Do not change application behavior, push commits, open PRs, authenticate VUW,
register live connectors, deploy solutions or change platform resources. Skill
installation does not prove that CLI, MCP, account or environment access works.
VUW CLI setup and live verification are a separate subsequent track.
