# Specification: Authorised M365 corpus-scale process discovery

## Overview

Discover the principal operational and governance processes evidenced across the
complete Microsoft 365 and Power Platform corpus available through authorised
user-scoped access. The work must begin with corpus and coverage discovery, not
with a predefined approval workflow. It must reconstruct candidate processes,
variants, hand-offs, delays, loops, escalations and incomplete cases, then expose
privacy-controlled evidence suitable for validation and IHG Executive review.

The four-record Dataverse approval run is a connectivity smoke test only. It is
not representative evidence and cannot satisfy this track's pilot, discovery or
completion criteria.

## Objectives

1. Inventory the full accessible evidence boundary across Exchange/Outlook,
   Teams, SharePoint, Microsoft Lists, Planner, Approvals, Power Automate and
   Dataverse, including time range, accessible containers, record counts and
   known blind spots.
2. Acquire all approved in-scope metadata through Windows-native, user-scoped
   interfaces, sanctioned exports or existing resource-owner connections without
   requiring Entra application registration or tenant-admin consent.
3. Transform heterogeneous source facts into a provenance-bearing OCEL 2.0 event
   corpus with stable replay, deletion, uncertainty and access-boundary semantics.
4. Discover process families empirically and rank them by evidence volume,
   recurrence, organisational reach, executive relevance and confidence.
5. Validate discovered families and correlations with operational owners before
   presenting findings or recommending changes.
6. Produce an executive process landscape and drill-down views that show coverage,
   uncertainty, variants, bottlenecks, hand-offs and improvement opportunities.

## Functional requirements

### 1. Corpus boundary and coverage ledger

- Enumerate every authorised source, container and acquisition route that can be
  inspected using existing delegated permissions.
- Record accessible and inaccessible sources separately; absence of permission
  must never be interpreted as absence of activity.
- Capture observation period, source count, candidate record count, successfully
  acquired count, rejected count, duplicate count, deletion/tombstone count and
  extraction timestamp for every source partition.
- Calculate coverage against the discoverable authorised denominator and label
  tenant-wide or organisational coverage as unknown unless independently proven.
- Support incremental checkpoints and repeatable historical backfill.

### 2. Privacy-preserving acquisition

- Use Windows-native PowerShell, Azure CLI, PAC CLI, delegated Microsoft APIs,
  Power Platform connectors and approved exports only.
- Default the persistent event corpus to minimised metadata. Raw narrative,
  attachments, credentials, personal identifiers and clinical content must not be
  committed to Git or copied into unapproved stores.
- Permit transient local feature extraction from approved narrative only when an
  information-handling assessment explicitly authorises it; persist only approved
  derived features and provenance.
- Apply keyed pseudonymisation, least-privilege filtering, access-boundary labels,
  retention controls and a deletion/rebuild procedure.
- Fail closed when classification, authority, provenance or destination controls
  cannot be verified.

### 3. Event and object reconstruction

- Normalize source facts into versioned activity, object and relationship
  contracts while preserving source identifiers, timestamps and provenance.
- Correlate cases and objects using explainable deterministic evidence first,
  followed by confidence-scored hypotheses where deterministic linkage is absent.
- Preserve one-to-many and many-to-many relationships rather than forcing every
  event into a single case identifier.
- Detect identity collisions, clock anomalies, missing lifecycle events,
  out-of-order events, duplicates, loops and incomplete cases.
- Keep observed facts distinct from inferred process-family labels and links.

### 4. Unsupervised and weakly supervised discovery

- Discover candidate activity vocabularies and process families across sources
  before applying IHG-specific names or governance templates.
- Produce frequency-ranked variants, directly-follows relationships, object-centric
  models, hand-off maps, cycle-time distributions and exception patterns.
- Quantify family confidence, assignment ambiguity, temporal stability and source
  dependence; route low-confidence classifications to human review.
- Test sensitivity to source exclusions, time windows, correlation thresholds and
  activity-label mappings so artefacts of access or preprocessing are visible.
- Maintain deterministic baselines; tenant-approved embedding or LLM enrichment is
  optional and must not be required for useful discovery.

### 5. Validation and executive interpretation

- Provide a review workbench/export containing representative evidence references,
  candidate labels, uncertainty and proposed merges/splits without exposing
  protected narrative.
- Require operational-owner confirmation before a discovered family is described
  as an organisational process.
- Show IHG executives a process landscape, top families, cross-service hand-offs,
  bottlenecks, rework, escalation, ageing, incomplete cases and data-quality gaps.
- Every visual must display observation period, coverage boundary, population,
  exclusions, sample size and confidence; no four-record or synthetic view may be
  presented as operational evidence.
- Separate descriptive findings from governed improvement experiments. No workflow
  or authority rule may change automatically.

### 6. Repeatability and operation

- Support checkpointed refreshes, idempotent replay, backfill, dead-letter repair,
  source withdrawal and deterministic rebuilds.
- Generate machine-readable run manifests, coverage reports, quality reports,
  model versions and hashes for all executive artefacts.
- Provide low-privilege runbooks, resource-owner hand-offs and continuity steps for
  multiple authorised operators.
- Keep repository validation, live extraction, human validation and executive
  acceptance as separate status gates.

## Non-functional requirements

- No required Entra application registration, service principal, tenant-admin
  consent, Azure subscription, WSL or Linux workstation.
- At least 90% line and branch coverage for executable repository code.
- Bounded-memory or partitioned processing for the measured corpus; performance
  targets must be based on the inventory rather than an assumed corpus size.
- Re-runs over unchanged inputs and configuration must produce equivalent event
  identities, counts and discovered baseline outputs.
- Protected content and live event corpora must remain outside Git and outside
  public GitHub/GitHub Actions artefacts.
- PM4Py use remains subject to licence review; an engine-neutral event corpus and
  deterministic analytics fallback must remain available.

## Acceptance criteria

1. A signed-off coverage ledger identifies all authorised source surfaces,
   observation periods, accessible populations, extraction counts and blind spots.
2. At least one approved historical acquisition route processes the complete
   accessible population for each source family admitted to the pilot, not a
   convenience sample.
3. Reconciliation proves source-to-event counts, rejection reasons, duplicates,
   checkpoints and privacy controls for every included partition.
4. The combined corpus produces empirically discovered process families and
   variants with confidence, coverage and stability statistics.
5. Results include cross-source/object correlations and explicitly quantify
   unresolved or ambiguous links.
6. Operational owners validate, reject, merge or split the highest-ranked families;
   their decisions and rationale are recorded.
7. Executive visualisations identify the main validated processes and material
   exceptions while displaying coverage and uncertainty prominently.
8. Synthetic, smoke-test and live corpus results are visibly separated in all
   outputs and status records.
9. A repeat run demonstrates idempotency and a controlled incremental refresh.
10. Privacy, security, dependency, quality, licence and records-governance gates
    pass, or unresolved external gates are recorded without a completion claim.
11. IHG Executive representatives explicitly decide whether the evidence is fit
    for operational improvement planning and define any authorised next stage.

## Out of scope

- Circumventing permissions or claiming tenant-wide completeness from delegated
  access.
- Persisting mailbox bodies, Teams message bodies, attachments, clinical content
  or direct personal identifiers in the repository.
- Surveillance, individual productivity scoring or automated performance action.
- Automated changes to clinical, governance, delegation or approval workflows.
- Production deployment or source expansion without information-governance and
  post-pilot approval.

