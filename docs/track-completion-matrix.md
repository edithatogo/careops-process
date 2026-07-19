# CareOps process track completion matrix

This matrix records repository completion separately from tenant execution. A
track is complete when its contracts, tests, documentation, and automation
boundaries are present and verified in both repository mirrors. Tenant-gated
execution is deliberately not represented as a repository-side success.

| Track | Repository evidence | Verification | External residual gate |
| --- | --- | --- | --- |
| OCEL 2.0 and ontology | `src/careops_process/ocel.py`, `schemas/ocel2-careops.schema.json`, `schemas/careops-ontology.registry.json`, `sql/ocel2-careops.sql` | contract, privacy, reference, and relation tests | none for synthetic data |
| M365/Dataverse ingestion | `src/careops_process/ingest.py`, `src/careops_process/reliability.py`, `contracts/m365-fact-projection.json` | watermark, replay, tombstone, and raw-content rejection tests | corpus-scale source inventory and complete-population acquisition |
| NLP discovery | `src/careops_process/discover.py`, `src/careops_process/evaluate.py` | deterministic discovery, active-learning, drift, and leakage tests | tenant-approved model/LLM access |
| PM4Py and conformance | `src/careops_process/mine.py`, optional `mining` extra | deterministic variants and conformance tests | PM4Py licence review; Mojo requires Linux/WSL |
| Semantic projection and improvement | `src/careops_process/projection.py`, `src/careops_process/improve.py`, `schemas/semantic-projection.schema.json` | projection privacy and recommendation guardrail tests | Fabric/Power BI capacity and workspace access |
| Process model representations | `docs/process-models/careops-process-mining.bpmn`, `docs/process-models/careops-process-mining.mmd` | secure BPMN parse and structural test | none |
| End-to-end execution seam | `src/careops_process/pipeline.py` | 50-test suite exercises ingestion through projection | live connector execution remains tenant-gated |
| Authorised M365 corpus discovery | `contracts/m365-corpus-coverage.schema.json`, `src/careops_process/coverage.py`, `docs/corpus-inventory-20260719.md` | coverage and evidence-claim safeguards | source-owner access, complete accessible-population extraction, owner validation, and IHG Executive decision |

The four-record Dataverse approval run is classified as a connectivity smoke
test. It does not complete the authorised M365 corpus discovery track.

## Common verification

The canonical local gate is:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
uv run bandit -q -r src
```

GitHub additionally runs full-history secret scanning and a GitHub Actions
security audit. The GitHub and GHE `main` trees are synchronized after each
published tranche.
