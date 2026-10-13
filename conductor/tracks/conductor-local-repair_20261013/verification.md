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
