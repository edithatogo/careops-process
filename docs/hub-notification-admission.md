# Synthetic notification admission

`hub_notifications.py` adds pure recipient/channel admission proposals around the
existing `build_digest` candidate. It does not send notifications, authenticate
recipients, persist state or change `DigestPolicy` or its wire/API. Governance
operating-model confirmation remains pending. This is partial evidence for hub
notification volume controls, not deployed Phase 3 or Phase 5 completion.

## API and integration

1. A trusted adapter resolves tenant, recipient, channel and authorized scope;
   loads the complete durable `NotificationLedger`; and builds an approved
   low-sensitivity candidate with `build_digest`. A `None` candidate needs no
   admission. Existing item limits remain separate from delivery quotas.
2. Construct `ReserveCommand` with a command ID, expected ledger revision,
   evaluation time, binding, logical message ID, reservation ID, provider
   idempotency intent ID, policy reference, enabled flag, pinned window and
   candidate. Call `reserve_notification(ledger, command)`.
3. Atomically compare-and-swap the proposal against its original expected
   revision, committing the complete ledger and receipt together **before** an
   outbound attempt. Only the committed winner may use a non-replay
   `attempt_permitted` result, subject to all external gates below. Pure calls
   on the same old ledger can both propose admission; they cannot establish a
   persistent winner.
4. Reconcile trusted provider evidence with `ReconcileCommand` and
   `reconcile_notification`. Persist its proposal with the same atomic rule.

Each result contains the latest proposed ledger, original command receipt and
`replayed`. Exact command replay returns that original receipt alongside the
current ledger, sets `replayed=True` and never permits another attempt. It does
not restore an old ledger snapshot. The fingerprint includes operation kind and
every normalized command field, including expected revision and time. Reusing a
command ID with changed fields is a collision; a new command with a stale
revision or evaluation time fails without mutation.

## Accounting and identity

A ledger has one immutable tenant/recipient/channel/scope binding and trusted
history origin. It retains multiple immutable, half-open UTC windows plus global
reservation and command history. The first window starts at the origin; later
windows must be adjacent. Gaps, overlaps, changed bounds and changed pinned
limits fail. A new reservation must fall within its supplied window. Skipped
windows require a separately approved continuity mechanism; this API refuses
to silently skip them. No retention/pruning/reset operation is provided.

Policy references and the builder's policy-dependent digest keys do not define
quota identity. Policy changes cannot enlarge or repartition a retained window.
Every evaluated window is retained atomically with its receipt, including
disabled or empty intervals. Those intervals create no reservations, but pin
their window and limit so the next adjacent interval can proceed.

Message, reservation and provider intent IDs are globally unique within the
ledger. An existing message may retry only with the same reservation, provider
intent, full candidate fingerprint, original window and policy reference.
Retries across rollover remain charged to the original window. Retries cannot
change content or create another charge. Another recipient/channel requires a
separate trusted ledger namespace and matching command binding.

| State | Consumes original-window capacity | New attempt eligibility |
| --- | --- | --- |
| reserved | Yes | Same idempotent intent, after committed admission |
| delivery_unknown | Yes | Same idempotent intent, after committed admission |
| delivered | Yes | Terminal; no retry |
| confirmed_not_delivered | No | Terminal; no retry |

Unknown may become delivered or definitively not delivered. Reserved may become
any of the three evidence outcomes. Timeouts, cancellations, expired leases and
missing acknowledgements never release capacity. Both terminal states reject
new reconciliation; only exact command replay is accepted. Once released, the
same logical message cannot authorize an uncharged retry. No re-admission
protocol is implemented.

Evidence binds its unique reference and observed time to the reservation's
provider idempotency intent. Observations cannot precede reservation creation
or the previous observation, or exceed reconciliation time. Duplicate evidence
references and contradictory terminal evidence fail. `complete_attempts=True`
is mandatory for definitive non-delivery; it is a **trusted adapter assertion**,
not locally verified proof that every possible attempt failed.

## Validation, privacy and external gates

Public operations reconstruct exact concrete records, including all nested
history, windows, receipts, evidence, digest and portfolio items. Unsupported
subclasses and forced mutations cannot bypass validation. Strict booleans,
bounded integer/code metadata, unique identities, reconciled revisions,
continuous windows and capacity totals are checked. Each window must have a
receipt binding its fingerprint. Each reservation must have exactly one earlier
admission receipt binding all immutable reservation fields (including frozen
content and provider identity); each evidence item must have one ordered reconciliation
receipt binding its reference and fingerprint. Retained retry/terminal decisions
are checked against the state derived at that receipt revision, including quota
usage at every historical admission rather than only final released totals. Candidates accept only the
executive portfolio's fixed attention-reason vocabulary. Ledger history stores
candidate fingerprints, not digest items, matter narrative or message bodies.

The adapter must authenticate roles and recipients, resolve grants and source
scope/classification, approve policies/windows/history origins, verify provider
evidence and complete-attempt coverage, enforce provider idempotency, and retain
the authoritative ledger and receipts durably. The candidate itself has no
recipient or scope provenance; the command's scope declaration cannot prove
authorization. Never create a new empty ledger after a missing/corrupt load or
change its namespace/origin to bypass prior history. Structural validation can
detect inconsistent partial history; it cannot distinguish a completely forged
or rolled-back but internally consistent ledger from genuine persisted state.
Command and effect fingerprints are consistency checks, not signatures. Original
command payloads are not retained, so a coordinated rewrite of state and receipts
(or a changed command-result assertion with all structural links preserved)
cannot be authenticated locally; trusted tamper-resistant persistence is required.

No provider, scheduler, delivery adapter, source writer, dependency or live
tenant configuration is added. Actual notification dispatch, persistent CAS,
identity/evidence authenticity, retention approval and manual pilot acceptance
remain external gates.

## Verification scope

Test-first synthetic examples and generated admission/release sequences check
pinned quotas, policy changes, window boundaries/history, terminal states,
ambiguous retries, full-command replay and collisions, independent namespaces,
stale revisions/evidence, approved metadata, and concrete subclass/mutation
rejection. Integration accepts the existing `build_digest` output unchanged.
Focused notification and existing digest-view tests pass together (60 tests).
These checks do not prove persistent concurrency, provider behavior, host
reliability or live delivery.
