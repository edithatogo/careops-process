# Credentialing assurance completion — design for review

Repository implementation design, 2026-10-14. The user's "Address the blocker"
authorises continuing the independent repository extension and its implementation
plan. No production policy, authority rule, threshold or live pilot is approved
by this document. The existing track remains in progress.

## Intended outcome

Complete the organisation-neutral pack's measurement and human-review interfaces
so it can describe conformance, delay, rework, exceptions, observed workload and
quality evidence from privacy-minimised inputs. Retain AI-disabled operation,
explainable calculations, explicit exclusions and suppressed small cohorts.
Human acceptance of a hypothesis permits measurement only; operational changes
still require a separate owning-system change and approval.

## Approaches

1. Recommended: extend the deterministic credentialing pack with explicit
   measurement and evaluation contracts. Reuse existing projection validation,
   case-grant and whole-report suppression rules. This supplies inspectable
   calculations without requiring a live connector or language model.
2. Adapt the generic improvement/experiment APIs directly. Those APIs accept
   unrestricted narrative and do not establish credentialing privacy boundaries;
   substantial validation wrappers would still be required.
3. Wait for a live CHHHS source before implementing measurement. This would
   postpone synthetic validation of interfaces that can be specified now.

## Measurement contract

The trusted adapter supplies the authorised case population, approved source
mapping, pathway and authority version. Object links alone do not establish
that an object is a case. No identity resolution or person-level ranking occurs.

Elapsed time uses observed event endpoints. Each measurement requires exactly
one start and one finish for the same explicitly mapped case, pathway and
authority version. Missing endpoints, repeated endpoints, tied or reversed times,
and qualifier mismatch are separate exclusion reasons. Inferred events never
substitute for observed endpoints. Stage intervals can overlap and must not be
summed as staff effort or queue time.

Initial pairs: request to completion; each adjacent routine-renewal reference
stage; recommendation to delegated decision; decision to communication;
communication to register activation; decision to register activation. Durations
are UTC elapsed hours, with median and nearest-rank 75th/90th/95th percentiles.
Each pair reconciles eligible cases plus excluded cases to the supplied case
population. These are administrative elapsed times, not clinical quality scores
or policy deadlines.

Workload uses a separate versioned strict observation contract: safe observation
ID, mapped case reference, approved source code, UTC recording time, observed
manual-touch count and observed active-work minutes. Raw evidence, staff identity
and free text are excluded. Duplicate replay is idempotent; conflicting replay
fails closed. Missing effort observations are unknown, not zero. Counts of process
events are never relabelled as manual touches or work minutes.

Capacity comparison requires matched, explicitly defined baseline and evaluation
cohorts, reporting windows and denominators. Report observed work minutes per
eligible case and the arithmetic difference; mark comparability failures and
missing observations. Do not infer causal benefit or released staff capacity from
timestamp gaps. Capacity deployment claims remain dependent on evaluation evidence.

Quality uses independently reviewed evaluation observations with controlled
outcomes: alert/no-alert crossed with requirement-present/absent. Define false
positive and false negative numerators and denominators explicitly; undefined
denominators yield unavailable results. Separate administrative first-pass
completeness from professional competence. A first-pass proxy is released only
when the approved source mapping confirms submission/completeness semantics and
source completeness; otherwise it is unavailable.

## Privacy and access

Case-level evidence remains restricted to trusted case grants. Broader reports
contain no case IDs, event IDs, exact timestamps, staff identifiers or run details.
Every nonzero measurement or exclusion cell must meet the approved distinct-case
threshold; otherwise suppress the entire report, including totals, percentiles
and hypotheses. Empty populations are suppressed. Deployment approval must cover
overlapping cohorts and successive releases; a single-report threshold does not
solve differencing attacks.

Code-shaped tokens alone cannot prove pseudonymisation. Approved vocabularies,
source minimisation and trusted grant resolution remain external prerequisites.

## Explainable improvement review

Add a credentialing-specific hypothesis record using controlled categories,
measurement-set version, evidence snapshot digest, triggering metric, approved
threshold version and controlled uncertainty/alternative-explanation codes.
Examples include investigating duplicate requests or a long decision-to-register
interval. Threshold breaches are hypotheses, not causal findings or compliance
certificates. Do not emit proposals from suppressed or unavailable evidence.

Review records contain a safe review reference, trusted reviewer-role reference,
UTC decision time and accepted/rejected/needs-more-evidence outcome. The caller's
trusted authorisation layer must establish the reviewer role. Reviewed records
retain the original evidence digest; evidence changes require a new review.
Acceptance changes measurement-review state only. There is no connector, workflow
write, automatic approval, clinical recommendation or deployment action.

AI is optional and disabled by default. Deterministic proposals and manual
review must work end to end with no model installed or called. Any later AI
proposal needs separate run provenance and the same privacy and review boundary.

## Pathways and storage

Keep routine renewal as the tested generic reference. Other pathways require
separate versioned models backed by approved source requirements; do not turn the
routine model into assumed mutual-recognition, temporary, condition, review or
appeal rules. Their current plan tasks remain open until mapped and tested.

Ledger state is currently in memory. Production readiness additionally requires
durable atomic projection/provenance/tombstone/watermark persistence, transaction
and concurrency tests, retention migration approval and recovery verification.
The design does not silently substitute an in-memory demo for those requirements.

## Proposed execution and evidence

Implement sequentially in this chat under the recorded execution ruling:

1. Stage-time calculations and reconciled exclusions, then reporting suppression.
2. Strict workload/evaluation schemas, replay-safe observations, effort and quality
   calculations with missing-data handling.
3. Evidence-bound deterministic hypotheses and authorised human-review transitions.
4. Synthetic end-to-end fixtures with AI disabled, privacy/adversarial/property
   tests and independent review of calculation and suppression boundaries.
5. Update metric dictionary, manual verification instructions, track evidence and
   the formal Conductor review report.

For every stage, test first with hand-calculated expectations, run the repository
suite and all required quality checks, and preserve at least 90% line and branch
coverage. Do not mark the overall track complete until the existing manual,
source-mapping, later-pathway and silent-mode gates have authoritative evidence.

## Current verified checkpoint

Ledger input isolation, projection ingestion revalidation and atomic deletion
preparation were committed as 289dc3e. Follow-up assessment/report boundary and
restored-deleted-inference regression fixes passed 77 scoped tests and an earlier
664-test full run. Further direct merge/summary regression fixes pass 81 scoped
tests, with 100% line and branch coverage in both credentialing modules. The latest
full run crashed with a native access violation. A standalone nested-model
reproducer and matched native dump preserve that unresolved failure. This design
does not assume a runtime fix or pilot effectiveness.
