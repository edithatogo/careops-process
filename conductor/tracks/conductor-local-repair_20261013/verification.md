# Local implementation evidence

## Decisions and execution record

- Worked on the local branch `codex/conductor-local-repair`, preserving the
  original main branch and the previously installed Conductor checkout.
- Preserved historical completion markers during legacy migration. No live
  tenant capability was newly verified or marked complete.
- Split credentialing checklist items where existing tests support only part
  of the original requirement. Unsupported requirements remain pending.
- Preserved complete upstream source trees for skill resource resolution.
  Third-party source code is excluded from this project's Ruff checks; local
  entrypoints and installer/validator code remain in scope.
- Generated only Codex-compatible entrypoint frontmatter. Upstream agent-specific
  tool declarations remain upstream references, not configured local tools.
- User-level installations use independent versioned copies, not project paths.
- Retained the existing application's dependency lock; this track does not
  update application dependencies.

## Test-first evidence

The initial new tests failed because the installer and validator modules did
not exist. The first implementation passed 14 tests and failed its command-line
entry test; resolving imports made all 15 pass. Two further tests reproduced
an incomplete-copy retry failure and a malformed-manifest crash before fixes.
All 17 setup tests then passed, and strict typing reported no errors.

## Manual checkpoints

- [ ] Human review of project configuration and guides.
- [ ] Human review of migrated history and reconciled progress.
- [ ] Human review of selected skill sources and prerequisites.
- [ ] Final human verification of local implementation.

The track stays in progress until these reviews are recorded. VUW account
authentication and live platform verification remain a separate next stage.

## Final review and checks

The independent final review found one important validation gap: damaged skill
entrypoints and missing or modified upstream resources could pass. Three tests
reproduced the issue before the fix; an additional test covers inline Markdown
examples so they are not mistaken for resource dependencies. The validator now
checks generated entrypoint mappings, actual resource links and clean pinned
source working trees. All 21 setup tests and the 177-test suite pass.

Formatting, Ruff, strict typing, Bandit and dependency auditing pass. All 38
selected repository and user-level skills have valid frontmatter and supporting
source files. Frozen environment synchronisation also passes.

A recursive Windows clone exposed PnP fixture paths longer than the default
Git limit. Per-command `core.longpaths=true` restores a full checkout; the
installation instructions now include it. Repository code uses Python 3.14
through `uv`, not the older system Python.

The fresh recursive clone of the committed branch passes setup validation and
all 177 tests in an independently created, frozen Python 3.14 environment.
The original checkout also passes frozen environment synchronisation. Final
user-level verification resolves all 38 entrypoints to independent source copies.
Hosted Actions have not run because this work has not been pushed.

Final: fixed entrypoint/resource validation gap — three regression tests
RED to GREEN; full suite 177 passed.

Final: minor (deferred): malformed manifest path escapes fail with a traceback
rather than a polished diagnostic; the valid installed manifest is unaffected.
Final: minor (deferred): historical Outlook title includes a duplicated Track
label; its links, status and metadata are valid.

Ruling: preserved third-party sources unchanged and validated their real
resource links while excluding inline examples — avoids interpreting templates
as dependencies; cost if wrong: a nonstandard inline resource link may need
explicit classification. Git working-tree checks still detect tracked deletion.
