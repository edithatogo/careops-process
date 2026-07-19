# Corpus reconstruction validation - 2026-07-19

## Live delegated Planner validation

The local, non-repository Planner corpus was reconstructed into an OCEL 2.0 log
using only pseudonymous lifecycle metadata.

- 38 events
- 35 objects across task, plan and bucket types
- 18 objects linked to only one observed event
- 20 objects with a creation event but no observed completion event
- one source system

These are data-quality and lifecycle observations for the delegated Planner
endpoint only. They are not findings about IHG's main processes. The live corpus
and identifiers remain outside Git.

## Determinism and scale validation

- Reordered equivalent facts produce the same canonical corpus fingerprint.
- A synthetic benchmark reconstructed 10,000 events and 10,001 objects in
  approximately 0.261 seconds on the validation workstation.
- Object type conflicts, unsafe identifiers, duplicate events, missing object
  references, completion-before-creation anomalies and incomplete lifecycles fail
  closed or remain explicit in the quality report.

The benchmark is implementation evidence, not a production capacity guarantee.
Real corpus sizing and partition boundaries must be revisited after additional
source lanes become accessible.
