# Python runtime inventory — 25 October 2026

Scope: active Python execution surfaces in the selected Process source at
`5c2cc222cc4cbb97e1f34bcf9f8c28404fdee8c5`, plus current setup guidance.
Historical receipts and synthetic test values are classified separately.

| Surface | Current state | Evidence |
| --- | --- | --- |
| Project interpreter pin | Python 3.15.1 | `.python-version` |
| Package support | `>=3.15,<3.16` | `pyproject.toml` |
| Frozen lock runtime | `==3.15.*` | `uv.lock` |
| Type-check target | 3.15 | `pyproject.toml` `[tool.pyright]` |
| Lint target | 3.15 | `pyproject.toml` `[tool.ruff]` (`py315`) |
| Local command entry | `.venv/bin/python` by default; `uv run` resolves the selected project environment | `Makefile`, `README.md` |
| Required CI | One stable matrix entry, Python 3.15.1 | `.github/workflows/ci.yml` |
| Optional PM4Py CI | Python 3.15.1 | `.github/workflows/ci.yml` |
| Dependency inventory CI | Python 3.15.1, including an isolated helper environment | `.github/workflows/dependency-inventory.yml` |
| Package/release CI | Python 3.15.1, including the wheel smoke environment | `.github/workflows/package-release.yml` |
| Development canary | Stable bootstrap 3.15.1; candidates are limited to the 3.15 line | `.github/workflows/development-canary.yml`, `tests/test_ci_canary.py` |
| Containers and alternate environment managers | None found | No Dockerfile, Compose, tox or nox configuration in the selected source |
| Repo-local environment readback | `.venv/bin/python -VV` reports Python 3.15.1 after `uv sync --locked --group dev` | Local checkpoint, 25 October 2026 |

The active Python-version tests use `3.14.8` as a negative candidate, `3.15.1`
as the accepted baseline, `3.15.2rc1` as an in-line preview, and `3.16.0a1`
as an out-of-line negative. Those values are synthetic inputs to
`tests/test_ci_canary.py`, not installed or executed compatibility runtimes.

Historical evidence retains its original versions: older Conductor receipts,
the 14 October mining dependency/coverage receipts, the 15 October blocker
checkpoint, and the pre-3.15.1 canary receipts in `docs/ci-delivery.md`.
Current executable setup instructions now use Python 3.15.1. The external
Dependabot UV graph updater still rejects the project's 3.15 range; that is
tracked in CareOps issue #175 and is not a reason to downgrade Python.
