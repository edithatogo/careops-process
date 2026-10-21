# Credentialing process assurance pack

Status: blueprint; disconnected by default

Repository reference implementation and manual verification instructions:
[Routine-renewal reference evidence](credentialing-renewal-reference.md).

## Purpose

This pack extends CareOps Process with an organisation-neutral credentialing and
scope-of-clinical-practice ontology. It supports process conformance, delay,
rework, exception, capacity, and quality analysis without copying sensitive
credentialing content into the analytical layer.

It receives privacy-minimised event facts from `careops-approve`,
`careops-decisions`, and, after separate approval, an authoritative register or
other source system. It does not manage cases, route approvals, recommend scope,
make decisions, or alter operational systems.

## Privacy boundary

The event projection contains stable pseudonymous or source-local references,
activity, timestamp, source system, and bounded qualifiers. It excludes:

- names, email addresses, registration numbers, dates of birth, and addresses;
- CVs, certificates, referee reports, evidence documents, and correspondence;
- complaints, incident, investigation, patient, or clinical narratives;
- committee deliberation and decision reasons;
- raw AI prompts and outputs; and
- individual performance rankings.

Small cohorts must be suppressed or aggregated before wider reporting. Access to
case-level event sequences must remain role restricted.

## Process objects

The ontology includes credentialing case, practitioner reference, application
pathway, requested scope, facility or service, evidence manifest, verification
summary, professional assessment, service-capability attestation, committee,
recommendation, delegated decision, condition, supervision, temporary approval,
register activation, review, and appeal.

Objects are linked by stable identifiers. The analytical layer should not
reverse-resolve a practitioner reference unless a separately authorised
operational investigation requires it.

## Core questions

The pack can answer:

- Where is time spent across intake, correction, professional review, committee,
  delegate, communication, and activation?
- How often is a request incomplete at first submission?
- Which evidence or pathway rules generate repeat requests or deferrals?
- How often are committee packets deferred because of quorum, conflicts,
  relevant-peer, service-capability, authority, or fairness gaps?
- What is the decision-to-register delay?
- Are temporary approvals converted, reviewed, or allowed to expire on time?
- Where do conditions, supervision, renewal, review, and appeal actions become
  overdue?
- Which variants depart from the approved process and why?
- Does a new feature reduce administrative effort without increasing errors,
  false alerts, missed requirements, or user burden?

## Metrics

Initial metrics should include:

- request demand and pathway mix;
- complete-at-first-submission rate;
- correction and further-information rate;
- manual touches per case;
- median, 75th, 90th, and 95th percentile lead time;
- queue time by stage;
- professional-review and committee-preparation time;
- deferral and exception rate by reason;
- recommendation-to-decision and decision-to-communication time;
- communication-to-register time;
- temporary-approval conversion, review, and expiry exceptions;
- condition and supervision review status;
- duplicate and reconciliation exceptions;
- conformance fitness and variant frequency;
- false-positive and false-negative alerts in silent mode; and
- staff capacity released to exception management, practitioner support, and
  quality assurance.

No metric should rank individual practitioners, peers, committee members, or
staff. Workload reporting must be used for service improvement and capacity
planning, not covert performance management.

## Conformance model

The first reference model should cover routine renewal:

1. request received;
2. pathway confirmed;
3. deterministic validation;
4. correction or further information where needed;
5. credentialing-officer review;
6. professional and service review where required;
7. committee scheduling and readiness;
8. recommendation;
9. separate delegated decision;
10. communication;
11. register activation and reconciliation; and
12. completion and future renewal reminder.

Changed scope, mutual recognition, temporary pathways, conditions, review, and
appeal are separate models and should be added as later capability packs.

## AI and NLP

AI or NLP may propose activity labels, group variants, summarise exceptions,
identify likely bottlenecks, and draft improvement hypotheses. It must:

- distinguish observed events from inferred events;
- retain confidence, model/provider, prompt or agent version, and run evidence;
- preserve source event IDs;
- avoid raw sensitive content;
- route low-confidence outputs for human review; and
- never certify conformance or change a process automatically.

A recommendation such as “reduce duplicate evidence requests” remains a human-
reviewable hypothesis. Implementation requires the owning module, current
policy, risk assessment, testing, approval, feature flag, and rollback.

## MVP and evaluation

The CHHHS MVP should begin with synthetic routine-renewal events, then approved
de-identified retrospective events, followed by prospective silent mode. The
pack remains disconnected from production decision or register writes.

Acceptance evidence includes schema validation, replay and duplicate tests,
tombstone tests, raw-field rejection, small-cohort suppression, stage and metric
reconciliation, conformance against synthetic golden paths and deviations, AI-
disabled operation, and documented human review of improvement outputs.
