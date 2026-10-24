# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Exercise the real graph receipt checks without network calls or credentials."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

WORKFLOW = Path(".github/workflows/dependency-inventory.yml").read_text()


def python_block(name: str) -> str:
    """Select an exact checked-in workflow Python block."""
    step = WORKFLOW.split("      - name: " + name + "\n", 1)[1]
    step = step.split("      - name:", 1)[0]
    body = step.split("          python - <<'PYCODE'\n", 1)[1].split("          PYCODE", 1)[0]
    return textwrap.dedent(body)


@pytest.mark.parametrize(
    ("result", "accepted"),
    [
        ({"result": "SUCCESS", "id": 123}, True),
        ({"result": "FAILURE", "id": 123}, False),
        ({"result": "SUCCESS"}, False),
    ],
)
def test_snapshot_acceptance_requires_explicit_success_and_id(
    tmp_path: Path,
    result: dict[str, str | int],
    *,
    accepted: bool,
) -> None:
    """A response without an accepted handle cannot qualify a submission."""
    base = tmp_path / ".local/dependency-inventory"
    base.mkdir(parents=True)
    (base / "submission.json").write_text(json.dumps(result))
    run = subprocess.run(  # noqa: S603 - fixed repository receipt, no caller commands
        [sys.executable, "-I", "-c", python_block("Submit once and require server acceptance")],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert (run.returncode == 0) == accepted


@pytest.mark.parametrize(
    ("observed", "accepted"),
    [
        ("pkg:pypi/example@1.0", True),
        ("pkg:pypi/example@0.9", False),
        ("pkg:pypi/other@1.0", False),
    ],
)
def test_graph_readback_requires_every_exact_package(
    tmp_path: Path,
    observed: str,
    *,
    accepted: bool,
) -> None:
    """Missing and changed package identities fail without submitting again."""
    base = tmp_path / ".local/dependency-inventory"
    base.mkdir(parents=True)
    snapshot = {
        "manifests": {
            "uv.lock": {
                "resolved": {"pkg:pypi/example@1.0": {"package_url": "pkg:pypi/example@1.0"}}
            }
        }
    }
    graph = {
        "sbom": {
            "packages": [
                {"externalRefs": [{"referenceType": "purl", "referenceLocator": observed}]},
            ]
        }
    }
    (base / "snapshot.json").write_text(json.dumps(snapshot))
    (base / "graph.json").write_text(json.dumps(graph))
    run = subprocess.run(  # noqa: S603 - fixed repository receipt, no caller commands
        [sys.executable, "-I", "-c", python_block("Read back the current dependency graph")],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert (run.returncode == 0) == accepted


def test_submission_is_trusted_main_only_and_has_no_automatic_retry() -> None:
    """PRs cannot reach the write job; accepted submissions are never replayed."""
    assert "pull_request:" not in WORKFLOW
    assert "if: github.ref == 'refs/heads/main'" in WORKFLOW
    assert "cancel-in-progress: false" in WORKFLOW
    assert WORKFLOW.count("gh api --method POST") == 1
    assert "--frozen --all-extras --all-groups" in WORKFLOW
    assert "--no-emit-project" not in WORKFLOW  # Retain the graph root and direct edges.
    assert "git diff --exit-code -- uv.lock pyproject.toml" in WORKFLOW
    assert "233748d76e61d8e7c67131942c221cb96cdf2a32" in WORKFLOW
