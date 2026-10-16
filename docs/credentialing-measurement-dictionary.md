# Credentialing metric dictionary addendum

This adds local executable definitions to the minimum event-counter dictionary
in `contracts/credentialing-assurance-measures.json`. It does not replace those
counters, approve deployment parameters or establish a live baseline.

| Measure | Unit and denominator | Missingness and interpretation |
| --- | --- | --- |
| Stage elapsed median/p75/p90/p95 | Hours between exactly one observed start and end per granted case; median and nearest-rank percentiles across eligible cases | Controlled exclusions reconcile to the case population; no eligible samples means unavailable; overlapping intervals cannot be summed as work |
| Decision-to-register elapsed | Observed delegated decision to observed register activation, using the stage-time rules | Delay is not proof of unauthorized practice or the cause of delay |
| Manual touches | Sum of explicit observed touch deltas, exact replay counted once | Process events are not touches; absence is unknown, explicit observed zero is zero |
| Active working minutes | Sum of explicit observed minute deltas; mean divides by distinct observed cases | Does not infer staff effort from elapsed process time; completeness is separately attested |
| Effort coverage | Distinct granted cases observed/missing and complete/partial | Latest timestamp requires all work observations there to attest measurement complete; case approval/completion is a separate concept |
| Observed effort difference | Baseline mean minutes per case minus current mean | Available only for compatible source/cohort versions, ordered nonoverlapping windows, source completeness and complete coverage of every granted case; no causal or released-capacity claim |
| False-positive rate | Independently adjudicated case-level FP/(FP+TN) at one controlled evaluation reference version | Repeated consistent labels count once; conflicting labels fail; zero denominator unavailable |
| False-negative rate | Independently adjudicated case-level FN/(FN+TP) at the same controlled reference version | Does not certify that all clinical requirements or alert units were evaluated |
| Observed first-submission completeness | Distinct complete cases / distinct assessed cases under one explicit source-defined assessment version | Missing assessments are unknown; contradictory case labels fail; no assessed cases means unavailable |
| Source-attested population first-submission completeness | Same numerator/rate, released only with assessments for every granted case and explicit source-coverage attestation | Missing assessments or unconfirmed source coverage make this rate unavailable; attestation does not prove source truth |
| Observed outstanding overdue renewal prevalence | Pending obligations with supplied effective deadline before explicit as-of / matured completed plus matured outstanding obligations | Missing/unknown/censored/not-yet-due cells reconcile separately; no matured denominator means unavailable; historical late completion is a different measure |
| Source-attested population overdue renewal prevalence | Same fraction only with complete case evidence, attested source coverage and nonzero matured denominator | Explicitly accounted censoring/not-yet-due cases are exclusions; missing evidence or unconfirmed coverage prevents a population rate |
| Observed review completion and on-time rates | Completed (on-time plus late) / matured obligations; on-time completed / the same matured denominator including outstanding | One kind/definition/as-of; missing, unknown, censored and future obligations remain separate; privacy counts distinct contributing cases, not obligations |
| Source-attested population review completion and on-time rates | Same fractions only with complete obligation evidence, attested source coverage and nonzero matured denominator | Source-owner definitions and deadlines remain explicit inputs; administrative completion does not establish clinical-condition satisfaction |
| Stage-delay investigation candidate | Released p95 strictly above a finite positive versioned threshold | Bound to current observed evidence, case grants, authority and policy; alternatives preserve uncertainty; human acceptance is measurement review only |

Every nonzero released case cell must meet the configured approved threshold,
with a technical minimum of two; otherwise suppress the entire report. A report
omits source IDs/times. Observation records and human-review actor references
remain protected operational metadata. Cross-release privacy protection and
trusted source/unit mapping are adapter/governance requirements.

First-submission assessment semantics and boundaries are documented in
[the first-submission manual](credentialing-submission-quality.md). This local
capability does not establish an approved first-time-complete baseline.

Still unimplemented or unproven by this extension:
temporary conversion/expiry rates,
practitioner/staff experience measures and causal capacity
released to higher-value work. Later pathway references alone cannot establish
these measures. Actual approved baseline, retrospective and silent-mode evidence
and governance/manual acceptance remain necessary.

[Outstanding overdue renewal semantics](credentialing-renewal-quality.md) require
source-owner acceptance of effective deadline, cycle, state and denominator
mapping. Local executable arithmetic is not an approved renewal baseline.

[Review-completion semantics](credentialing-review-quality.md) preserve separate
obligation denominators and distinct-case privacy. Local completion/on-time
rates do not establish approved condition/supervision definitions or a baseline.
