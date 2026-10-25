# CareOps absorption and work tracking

**Status as of source commit `035021965d2776778b521a836a52331715234ec1`**

CareOps Process remains the public source repository and is consumed by the
CareOps suite as a pinned Git submodule. CareOps (the parent repository) now
owns active issue tracking, Conductor status, acceptance records and operational
handoffs. See the [parent migration ledger](https://github.com/edithatogo/careops/blob/main/conductor/tracks/suite_process_migration_20261018/plan.md).

The checkboxes in this repository's `tracks.md` and the detailed track folders
are preserved source history. An in-progress marker means the work was unfinished
at the transfer snapshot; it is not a claim of completion and it is no longer
the authoritative current work queue. The actionable successors are:

| Historical Process track | Current CareOps work |
| --- | --- |
| Credentialing privacy-minimised event and assurance pack | [CareOps #177](https://github.com/edithatogo/careops/issues/177) |
| Authorised M365 corpus-scale process discovery | [CareOps #171](https://github.com/edithatogo/careops/issues/171), [#173](https://github.com/edithatogo/careops/issues/173), [#174](https://github.com/edithatogo/careops/issues/174) |
| Cloud-only complete historical Outlook mailbox backfill | [CareOps #171](https://github.com/edithatogo/careops/issues/171), [#172](https://github.com/edithatogo/careops/issues/172), [#173](https://github.com/edithatogo/careops/issues/173), [#174](https://github.com/edithatogo/careops/issues/174) |
| Teams clinical-governance workflows | [CareOps #178](https://github.com/edithatogo/careops/issues/178) |
| Local reliability and ALM hardening | [CareOps #167](https://github.com/edithatogo/careops/issues/167), [#168](https://github.com/edithatogo/careops/issues/168), [#170](https://github.com/edithatogo/careops/issues/170) |
| Suite CI dependency, canary and release qualification | [CareOps #167](https://github.com/edithatogo/careops/issues/167), [#170](https://github.com/edithatogo/careops/issues/170) |
| Python 3.15 migration and qualification | The active CareOps absorption and suite qualification records; the child P3.3 goal-status item remains open until the full migration goal is complete. |

Do not create new Process issues or Conductor tracks for these ongoing scopes.
Update the CareOps successor with evidence, owner and acceptance state. If a
successor requires a Process source change before this repository is archived,
make the source PR here and record its exact commit and checks in the CareOps
successor and parent submodule pin. Source CI does not establish tenant,
provider, governance or operational acceptance.

The source repository is not archived yet. Reconcile any generated bot issue
that reappears into the CareOps dashboard before archive readiness is assessed.
