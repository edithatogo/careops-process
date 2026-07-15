# Managed PM4Py, Mojo experiments, and conformance analytics

- GitHub issue: https://github.com/edithatogo/careops-process/issues/5
- GHE issue: https://nswhealth.ghe.com/60217257/careops-process/issues/5
- GitHub Project: https://github.com/users/edithatogo/projects/26

## Specification

Run reproducible object-centric discovery, variants, conformance, performance,
and drift analytics in approved managed compute. PM4Py licensing is a release
gate. Mojo kernels are experimental and require Python parity.

## Plan

- [x] Record PM4Py licensing as a release gate.
- [x] Package a pinned Python 3.14/Polars/PM4Py environment.
- [x] Add deterministic trace variants and conformance metrics.
- [x] Define Linux Mojo benchmarks only for proven hot paths.
- [x] Keep numerical, semantic, privacy, and failure parity tests in Python.
- [x] Record Fabric unavailability and preserve a local/CI fallback.
- [x] Conductor - User Manual Verification.
