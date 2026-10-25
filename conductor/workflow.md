# Workflow

1. Read [CareOps absorption and work tracking](careops-absorption.md); the track
   registry is a historical snapshot, not the active queue.
2. Use the linked CareOps successor issue as the source of scope, owner, status
   and acceptance. Do not create a replacement issue or track here.
3. If that successor needs a source change before archival, keep the change in
   this repository, cite the parent issue in the PR, and report the exact child
   commit and checks back to the parent record.
4. Use synthetic fixtures and test-first implementation. Run the checks required
   by the applicable parent issue and this repository's contributor guidance.
5. Separate repository evidence from live tenant evidence and external gates;
   source PR checks do not qualify native or operational acceptance.

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
