# Optional canonical-model alignment evidence

`credentialing_alignment.py` provides a bounded local adapter for cost-based
Petri-net trace alignment using the existing optional PM4Py **2.7.23.8** runtime.
`credentialing_alignment_reporting.py` selects observed case traces from a retained
credentialing ledger and protects the aggregate release. The base profile imports
no PM4Py and reports unavailable mining explicitly.

This is model-based **alignment fitness**, separate from the existing positional
and activity-set comparisons. It is neither token-replay fitness, model precision,
a probability of clinical compliance nor evidence of released capacity. A fitting
trace means the observed activity order can be explained by the supplied model
under the stated cost policy. It cannot establish that the model is appropriate,
the facts are complete or authentic, or an intervention caused a benefit.

## Model and method binding

`AlignmentModel` pins the actual PNML bytes with SHA-256, model version, activity
mapping version, pathway code, authority mapping version, initial/final token
markings and the fixed method policy `pm4py-2.7.23.8-default-alignment-v1`.
These are protected service configuration, not public clinical approval flags.
Constructors validate structure and consistency only; they do not resolve source
documents or authenticate an approver.

The admitted **canonical subset** has one unnamespaced PNML P/T net and page,
plain positive weighted arcs connecting places/transitions, unique bounded IDs,
and registered credentialing activity names on visible transitions. An unnamed
transition is silent. Start/final markings are separate explicit place/token
bindings; embedded markings are rejected. Namespaced documents, nested pages,
inhibitor/reset/data/colour/tool-specific extensions, unknown labels and other
unsupported elements fail closed. This intentionally narrower interchange format
is not a claim to support every PNML export. No marking is guessed and no semantic
extension is discarded during loading.

The adapter builds a Petri net using public backend APIs from this validated
topology. There is no bespoke alignment algorithm or positional-score substitute.
There is **no BPMN converter** in this tranche. The repository's generic routine
renewal BPMN is not automatically admitted, clinically approved or proved to have
semantics-preserving conversion. A source owner must approve any separate
canonicalisation and activity/authority mapping before operational use.

The worker explicitly supplies a visible model move cost of 10,000, log move cost
of 10,000, synchronous move cost zero and silent model move cost one. It retains
the pinned backend's own reported fitness normalization. Do not substitute
`1 - raw_cost / best_worst_cost`: a valid parallel execution with two silent
moves has raw cost two and fitness one. The synthetic arithmetic checks establish
the selected backend behavior, not a universal normalization for other methods.

`align_traces` returns ordered **restricted trace diagnostics**. Its positional
fitness/cost arrays can identify an individual case when joined with inputs.
They must remain behind case-authorised service/storage access and must not be
published as a broad aggregate.

## Retained trace selection and denominators

`report_alignments` requires a consistent trusted ledger snapshot, server-resolved
`report_reader` scope, case-classified grants, an approved case privacy threshold
and an explicit subset of complete observed cases. Role strings and completeness
sets do not authenticate themselves. The storage service must lock/snapshot the
ledger while supplying it and preserve tombstones across recovery.

The function reconstructs the ledger, applies deletion memory and validates the
projection before selecting traces. Exact source replay is not counted twice.
Only observed facts enter alignments; inference remains separately counted and
cannot supply a missing observed step. Unrelated/ungranted objects never grant
case access. Events are ordered by source timestamp. Timestamp ties are excluded
as ambiguous; event-ID order is not treated as evidence of execution order.

Each granted case has exactly one primary trace category, in this order:

1. No observed trace.
2. Partial/censored trace, based on the supplied coverage definition.
3. Model pathway/authority binding mismatch on an observed fact.
4. Ambiguous source timestamp order.
5. Trace exceeds the bounded event limit.
6. Eligible complete observed trace.

Complete means the accepted observation window covers a full trace. It does not
mean the trace reached a model final state or conformed. A missing or reordered
step in an explicitly complete trace is a scored deviation, never conveniently
excluded. A partial trace is excluded rather than penalised for future work.

Population cases = eligible cases + sum of primary exclusion counts. Aligned
cases equals eligible cases only after a successful backend response. An
unavailable backend leaves aligned cases zero, fit/deviation counts and mean
fitness unavailable; it does not turn unavailable fitness into zero. On success,
fit + deviating = aligned. Mean fitness is the equal-weight **case mean** across
aligned cases, not an event-weighted or population-complete estimate. There is no
implicit extrapolation from observed cases to excluded cases.

Retained source-event count deduplicates source identities across granted cases.
Observed/inferred case-event occurrence counts expand event-to-case links. One
event linked to two granted cases is one source event and two case occurrences.
Worker counts/minutes and causal capacity amounts are separate measurement units.

The release checks joint case cells combining primary category, observed-presence,
inference-presence and fit/deviation outcome. Every nonempty joint cell must meet
the case floor, technically at least two. Suppression removes all counts, labels
and fitness from the report. No case IDs, timestamps, source references, model
identities or raw alignments appear in the public aggregate. Deployment privacy
review must still address longitudinal differencing and repeated releases; this
is not a person-level privacy guarantee.

## Optional runtime and resources

The trusted service configures an absolute interpreter path. It is not a client
request parameter. A fixed repository worker runs with Python isolated mode,
without a shell or multiprocessing; vendor stdout/stderr is discarded. Model/
trace payloads and output use temporary local files removed after execution;
host ACLs, disk encryption and protected working storage remain deployment duties.
No AI call, source write, dependency installation or CI opt-in is performed.

Limits are 128 KiB model bytes, 128 places, 128 transitions, 512 distinct arcs,
32 initial/final tokens per marked place, 64 traces per call, 128 activities per
trace, 32 KiB reply and a configurable wall-clock timeout up to 60 seconds
(default 30). Oversized batches are unavailable, never silently sampled. The
parent consumes at most 65 incoming traces before rejecting an oversized batch.
Timeout kills and waits for the direct worker. These limits are **not an OS
memory/CPU quota** or proof that all unbounded Petri nets terminate. Operational
use still requires an accepted resource/isolation policy.

Missing interpreter, absent/wrong package version, timeout, malformed/oversized
reply, unsupported model or backend failure never creates a synthetic fitness
score. Contract/model errors raise `CredentialingContractError`; execution
failures return controlled unavailable statuses. The pinned optional dependency's
existing licence/adoption gate remains open for production use.

## Local evidence and remaining outcomes

Synthetic tests exercise independently expected sequence insertion/deletion/
reordering arithmetic, choice, repeated loops, both legal parallel interleavings,
silent-move normalization and a missing parallel branch against the actual
already-installed pinned runtime. Boundary tests cover malformed models/replies,
real child timeout, replay/deletion, partial traces, inference exclusion,
case/event grain, qualifier/order exclusions and whole-report suppression.

This local component does not close source-model acceptance, retrospective or
prospective validation, operational deployment, governance sign-off, model
precision or the original causal released-capacity outcome. Credible actual
capacity evidence still needs an accepted counterfactual study, complete and
comparable work measurements, same-workforce redeployment records, quality
outcomes and appraisal of alternative causes. A pure silent-mode run that changes
no practice can validate measurement but cannot prove capacity caused by a
workflow intervention.
