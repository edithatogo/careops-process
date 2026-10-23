# Workflow

1. Implement one track at a time from `conductor/tracks.md`.
2. Mark work in progress before changing code.
3. Use synthetic fixtures and test-first implementation.
4. Run formatting, lint, typing, unit, property, privacy, dependency, workflow,
   and secret checks before completion.
5. Separate repository evidence from live tenant evidence and external gates.
6. Require manual verification at the end of every track.

## Local setup validation

Run `uv run python scripts/validate_conductor.py` before declaring Conductor
ready. This checks required guides, every track registration and document,
metadata/status consistency, local links, skill entrypoints and pinned source
commits. The upstream setup helper's index-exists check is not sufficient.

After cloning on Windows, run `git -c core.longpaths=true submodule update --init` and
`uv run python scripts/install_repo_skills.py` to refresh repository entrypoints.
For user-level Codex installation and prerequisites, see
[Repository skills](../docs/repository-skills.md).


## Targeted test cadence

Follow AGENTS.md targeted-test guidance during edits. Preserve full integration,
coverage and release gates at coherent milestones. Cached or zero-test results
are not complete acceptance evidence.
