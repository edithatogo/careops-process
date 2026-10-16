# Synthetic brief, agenda, minute and urgent-decision records

`hub_meetings.py` assembles immutable meeting metadata from explicitly supplied
approved references. It does not retrieve protected brief contents, publish a
meeting, authenticate participants or mutate the canonical governance matter.
Every root record is synthetic. Approval-reference authenticity remains a
controlled-store responsibility, not an inference from local tests.

`BriefReferences` binds question, recommendation, alternatives, risk, authority,
conflicts, consultations and proposed-action references to one matter, scope,
template version and full collective-rule fingerprint. The renderer produces a
compact one-page reference brief; it deliberately does not copy clinical or
executive narrative into collaboration text.

`add_agenda_entry` checks current matter classification/scope, configured
secretariat/chair, expected meeting revision and agenda deadline. Late additions
need a chair-exception reference. Entries retain the canonical matter revision,
review cycle, current decision IDs, template digest and original addition time.
Exact duplicate retry preserves the original entry even after its deadline;
changed case or brief snapshots require `replace_agenda_entry`.

The synthetic replacement command requires an existing entry, strict expected
revision (booleans rejected), opaque replacement ID, configured actor, current
canonical matter and newly supplied brief references. It returns a new meeting
with one active entry per matter and append-only `replacements` history. Every
receipt retains its previous/new snapshots, complete synthetic canonical-matter
request, actor, expected revision and command digest. The digest also binds the
exact meeting context. This is controlled governance metadata, not a public
brief or proof of reference authenticity.

Replacements must advance content, preserve the pinned template/version and
collective-policy fingerprint, and never move canonical revision/review cycle
backward. An unchanged snapshot is rejected without consuming a replacement ID;
a changed chair-exception pointer alone is not a content refresh. Policy/template
rebinding needs a separate governed operation. Every new add, replacement and
minute must follow retained event chronology. A late pre-meeting replacement
needs the existing explicit chair-exception reference. Replacement is refused
at/after the scheduled meeting and after that matter has been minuted, including
backdated requests. Existing minute records are never rewritten.

Exact historical replay includes the original request timestamp and expected
revision, returns the current meeting unchanged, and cannot undo a later refresh
or minute. Changed content under the same replacement ID is a collision. Timestamps
are normalized to UTC. Restoration validates receipt digests, meeting-context
binding, predecessor/successor chains, active snapshots, deadlines, chronology and
revision counts. The default empty replacement history preserves the meaning of
old serialized meetings with no replacement records. Original inputs remain
unchanged, and retained inputs are revalidated before mutation.

`record_minutes` requires the current canonical matter as well as the scoped
agenda, rule and voting session. Matter, decision, review cycle, revision,
classification, template/version, authority and rule fingerprint must agree.
The session's `meeting_ref` must identify the exact meeting, and actor/participant,
chair and minute references must match the configured context. Responses remain
provisional when the collective evaluator reports an unresolved gate.

Loaded minutes are validated against their agenda entries, meeting/policy,
decision/cycle/template context, chronological order and confirmation/gap
consistency. Normalized UTC response/expiry timestamps make equivalent-instant
session replay idempotent. Minute recording returns a new meeting record; final
canonical lifecycle changes still go through `apply_transition` and its common
collective controls.

`UrgentDecisionLedger` keeps urgency evidence, provisional decision, expiry and
later ratification separate. It pins the original authority, template version,
review cycle, original response references and approved ratification-policy
fingerprint. Expiry preserves a ratification gap rather than deleting the
decision. A later ratification must use a distinct session, matching decision,
scope/authority/version/cycle/reference and ratification semantics. Its responses
must be later than the provisional decision and use distinct evidence references.
An original approval card, changed quorum or unbound ratification pointer cannot
turn the status into ratified.

Five important review findings had failing regression cases before the fixes:
canonical decision/cycle binding, cross-meeting reuse, imported-minute
consistency, urgent policy pinning and timestamp-equivalent replay. Additional
cases check current classification and after-deadline duplicate replay. Tests,
lint and strict typing pass before this slice's scoped commit.

Remaining implementation work includes authenticated protected-record resolution,
approved deadline/cadence/urgency configuration, persistent meeting event storage
and calendar/Teams delivery. The
IHG authority/quorum/conflict/ratification model and pilot scope remain pending;
these synthetic records are not live meeting or policy verification.

The agenda-refresh follow-up has 33 new cases plus 20 existing meeting cases
passing locally. Categories include exact replay/collisions, unchanged refresh,
strict revisions, full history restoration, recomputed-digest chain tampering,
interleaved additions/replacements, cutoff/deadline controls, stale minutes and
input immutability. This focused receipt does not replace final shared integration
checks or resolve the independently observed host/runtime reliability problem.
