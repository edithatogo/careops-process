# Credentialing acceptance and handover — 17 October 2026

The original track remains in progress. Local contracts and synthetic checks
do not establish CHHHS/Queensland Health clinical rules, approved source access,
silent-mode effectiveness or causal capacity release. The selected VUW sandbox
does not itself approve any credentialing source, policy or instrument.

## Executable synthetic example

From the repository, with the existing development environment:

```powershell
uv run --no-sync python examples/credentialing_acceptance.py
uv run --no-sync python -m pytest tests/test_credentialing_acceptance_example.py tests/test_credentialing_projection_schema.py --no-cov -q -p no:cacheprovider
```

The example uses fixed local fixtures, reads the ontology registry and prints
aggregate JSON. It performs no authentication, network/source acquisition,
deployment, file writes, AI calls or workflow mutation. Every grant, source
attestation, authority/reference, instrument and reviewer decision is synthetic.
Independent measurement populations must not be joined into person identities.
The floor of two is a fixture/technical floor, not an approved deployment policy.

Expected results are independently asserted in
`tests/test_credentialing_acceptance_example.py`:

| Evidence | Synthetic result |
| --- | --- |
| Eight renewal traces, 13 observed stages each, one inferred fact each | 104 observed + 8 inferred; exact replay stays 112 |
| Delete one observed reminder then replay | 111 retained; rare missing endpoint suppresses the whole timing report |
| Observed conformance | Eight routine matches and six independent supplied pathway models match; no compliance certificate |
| Request-to-completion / decision-to-register p95 | 11 / 3 elapsed hours |
| Work and comparison | 16 touches, 160 observed minutes; baseline-current difference 10 minutes PER CASE |
| Independent case-level evaluation | FP and FN rates both 0.5; not alert-level completeness |
| First-submission completeness / outstanding overdue renewal | Both observed rates 0.5 |
| Condition/supervision review completion / on-time | 0.5 / 0.25, including outstanding obligations in denominator |
| Temporary conversion / conversion by expiry | 0.5 / 0.25; two independently observed expiry transitions |
| Temporary review completion / on-time | 0.5 / 0.25; unconfirmed required population blocks the full rate |
| Experience | 8 invited, 6 responded, 4 item answers; response rate 0.75, with missingness distinct |
| Destination work | 100 TOTAL minutes, 60 in a supplied higher-value category; six joint-partitioned workers |
| Human improvement review | Fixture acceptance has `measurement_review_only` scope |
| One-case reports/proposals | Timing suppressed; no hypothesis emitted |

The example exposes no case/event/cohort identifiers, source instants, evidence
digests or protected attribution quantities. It deliberately leaves
`released_capacity_requirement` as `partial`. Its acceptance assertions are
repository evidence, not the maintainer's required real manual acceptance.

## Original outcome coverage and exact remaining granularity

This maps both the numbered specification and the broader original design-note
metrics. Existing minimum EVENT counters must not silently become case rates.

| Original outcome | Existing local evidence | Remaining capability or evidence |
| --- | --- | --- |
| Versioned ontology/projection, prohibited content, observed/inferred separation | `credentialing.py`, registry, strict schema and deep rejection tests | Approved source vocabulary/identity mapping and actual provenance; schema validation cannot authenticate source truth |
| Replay, deletion, watermarks, dead letters | `CredentialingLedger`, projection merge and local `SQLiteCredentialingStore` transactions, unbounded durable tombstones, restart/crash/concurrent-write tests | Actual deployed storage/hosting, approved retention and old-backup disaster-restore/deletion/revocation reconciliation remain open; local SQLite evidence is not Dataverse deployment |
| Routine renewal and separate pathways | `assess_routine_renewal`, source-linked `assess_pathway`; BPMN/SVG/PNG | Actual local applicability, authority, terminal/exception and roster/register mappings; later packs remain open |
| Request demand/pathway mix | Explicit granted-case population, missing classification and jointly suppressed case pathway mix in `credentialing_local_reporting` | Approved source-defined request population/window and classification mapping; case demand is not an arrival rate |
| First submission, touches, elapsed percentiles and decision/register intervals | Submission, workload and stage-time public reporters | Real-source completeness, cohort/endpoint applicability and baseline acceptance |
| Correction/further-information and deferral/exception rates by reason | Explicit case assessments, controlled process reasons, observed/population case and reason rates with missingness in `credentialing_local_reporting` | Approved criteria/reason vocabulary and complete source assessments; event absence is not a negative assessment |
| Queue time, professional review and committee preparation work | Explicit queue/active/unknown case-calendar partition; source-mapped professional-review/committee-preparation worker minutes and touches in `credentialing_stage_effort`; explicit per-interval stage calendar allocation in `credentialing_stage_calendar` | Actual source/span/stage mapping acceptance remains open; calendar active time is not worker effort and queue is never elapsed minus worker minutes |
| Temporary approval conversion/review/expiry; condition/supervision reviews; renewal overdue | Explicit episode/obligation snapshots and privacy-aware reporters | Approved deadline, extension, completion, censoring and complete obligation populations |
| Duplicate/register reconciliation exceptions | Validated registered activities and failure/duplicate event counters | Approved reconciliation semantics and source linkage; roster reconciliation and unauthorized-practice conclusions are not established |
| Conformance fitness and variant frequency | Per-case reference comparisons; protected case-scoped variants; optional pinned PM4Py weighted Petri alignment over retained observed traces with explicit markings/method and joint suppression | Alignment is distinct from positional/set scores, token replay and precision. Actual canonical model/source/authority/completeness acceptance, operational runtime and licence review remain open; no BPMN conversion or clinical compliance certificate |
| False alerts/missed requirements | Independently adjudicated CASE-level FP/FN reporters | Approved evaluation grain/reference and representative silent-mode adjudication; case rates cannot be relabelled alert/requirement rates |
| Practitioner/staff experience | Versioned instrument, frozen aggregate cohort and distinct-person response/missingness reporter | Source instrument/sampling/privacy acceptance, actual observations and interpretive validation |
| Higher-value capacity released | Observed destination work, recomputed effort difference, protected attributed claims/judgments | Credible causal evaluation, provenance and human appraisal remain necessary. The causal requirement stays partial |
| Explainable human-reviewed improvement, AI-disabled operation | Deterministic stage-delay hypotheses; local SQLite request authentication, server-stored grants, current-evidence recomputation and atomic/idempotent measurement-review persistence | Organisational identity/credential lifecycle, actual host/transport/access policy and real human acceptance remain open; local test identities are not VUW/Entra authentication; no automatic workflow mutation |

The remaining local aggregation/decomposition work above is identified precisely,
not declared blocked merely by absent approvals. Source definitions are needed
before its operational interpretation can be accepted. Do not mark the track,
later packs or all named mathematical outcomes complete from this example.

The subsequent [local reporting implementation and synthetic example](credentialing-local-reporting.md)
cover the four explicitly authorised local reporting outcomes. They use a separate
source-assessment contract, not guessed clinical mappings or event-counter rates.
The [local stage-effort reporter](credentialing-stage-effort.md) adds explicit
professional/committee worker-effort granularity. The
[stage-calendar reporter](credentialing-stage-calendar.md) adds explicit local
queue attribution and reconciled denominators. Actual source/stage mapping,
causal capacity and every real-source/acceptance gate below remain open.
The [local store adapter](credentialing-store.md) provides local durable state and
authenticated atomic review, without claiming a deployed VUW identity/backend.
The [optional model-alignment adapter](credentialing-model-alignments.md) adds
canonical weighted Petri alignment fitness with explicit backend semantics;
it does not admit an operational source model or establish causal effects.
The [authenticated local route](credentialing-authenticated-alignment.md) binds
that reporter to stored reader grants/privacy policy and exact retained evidence,
then rechecks access and state after computation. It supplies local request
authentication, not VUW identity, source/model acceptance or anti-rollback recovery.
VUW-only live work and deferred
Queensland Health integration are unchanged by tenant-neutral local arithmetic.

## Minimal real-source/authority/instrument acceptance checklist

Each item needs a named accountable owner, dated version/reference, actual
evidence and explicit disposition. All are currently **pending**, not inferred
from a successful example or sandbox selection.

- [ ] **Source and access:** approve the purpose/environment, permitted sources,
  minimized fields, stable case/episode/obligation mapping, pseudonymisation and
  server-resolved role/grants. Verify source completeness/replay/deletion semantics
  and durable retention/recovery; preserve raw sensitive evidence outside this pack.
- [ ] **Authority and pathway:** accept current delegation/policy references,
  applicability and branching, stages/terminal states, deadline/timezone/extension
  rules and controlled exception/reconciliation meaning. Record who may accept
  each model; a reference match is not policy compliance.
- [ ] **Measurement and instrument:** accept population/windows, units,
  denominators, endpoints, independent evaluation grain/reference and survey
  instrument/sampling/categories. Establish required-review enumeration and
  source-computed distinct-person/joint aggregation. Never substitute case,
  worker, episode and obligation denominators for one another.
- [ ] **Privacy and governance:** approve cell thresholds, inferable joint and
  complement cells, repeated releases, protected claim/reviewer evidence,
  retention/records, security, architecture, support and continuity. Client
  attestations or stored hashes do not authenticate themselves.
- [ ] **Baseline and pilot:** obtain complete accepted baseline data; execute
  approved de-identified retrospective cases, then prospective silent mode with
  no source writes. Reconcile false/missed findings, variants, workload,
  experience and privacy effects. Collect actual causal study evidence before
  accepting any released-capacity outcome.
- [ ] **Human and release acceptance:** maintainer verifies the generic model's
  limits and the current revision's required checks; accountable reviewers record
  real dispositions. Track acceptance includes all original requirements and
  remaining local work, not just the implemented component receipts.

## Schema boundary repair

Eight independent lexical regressions reproduced a terminal-newline bypass in
the published EVENT projection's `$`-terminated code/version patterns. Full
Draft 2020-12 validation also admitted mutated event/source IDs before the fix.
Patterns now require the true end of input. The pathway-reference schema was
already protected by separate `not` guards and was deliberately left unchanged.
Runtime normalization/source mapping and external approval remain separate concerns.

## Local verification receipt

The focused projection/assurance/pathway/acceptance suite passes 125 tests with
ordinary assertion rewriting, including eight lexical regressions and two
independent end-to-end expectations. The example CLI runs successfully. Scoped
Ruff formatting/lint, strict Pyright including the example, Bandit, Conductor
validation and whitespace checks pass. Full Draft 2020-12 validation accepts the
runtime-exported projection and rejects nine newline-mutated identifier/source/
qualifier fields. The unchanged pathway schema separately rejects four such
mutations through its existing guards. Schema checking used a disposable
environment with active date-time validation; project dependencies are unchanged.

Independent read-only schema/example/handover review found no actionable issues.
This is focused local evidence, not the final combined revision's hosted checks,
host repair, real-source authority/instrument acceptance or completion of the
remaining original outcomes above.
