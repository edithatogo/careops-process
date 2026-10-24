# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Exercise the real graph receipt checks without network calls or credentials."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

WORKFLOW = Path(".github/workflows/dependency-inventory.yml").read_text()
VERIFIER = Path(".local/graph-tools/portfolio-scripts/dependency_snapshot.py")
VERIFIER_SHA256 = "80768b650d8f5b9a1cb32b8eeace3e5cf8478f90349e964284b322c2149defa3"


def run_readback(
    tmp_path: Path, snapshot: dict[str, Any], graph: dict[str, Any]
) -> subprocess.CompletedProcess[bytes]:
    """Execute the actual shell step with only its remote graph read replaced."""
    assert VERIFIER.is_file(), "Prepare the pinned verifier using README's offline-test setup."
    assert hashlib.sha256(VERIFIER.read_bytes()).hexdigest() == VERIFIER_SHA256
    base = tmp_path / ".local/dependency-inventory"
    base.mkdir(parents=True)
    (base / "snapshot.json").write_text(json.dumps(snapshot))
    (tmp_path / "response.json").write_text(json.dumps(graph))
    helper = tmp_path / VERIFIER
    helper.parent.mkdir(parents=True)
    shutil.copyfile(VERIFIER, helper)
    step = WORKFLOW.split("      - name: Read back the current dependency graph\n", 1)[1]
    script = textwrap.dedent(step.split("      - name:", 1)[0].split("        run: |\n", 1)[1])
    stub = """gh() {
      [ "$#" = 2 ] && [ "$1" = api ] &&
        [ "$2" = repos/fictional/repo/dependency-graph/sbom ] || return 99
      cat response.json
    }
    python() { "$TEST_PYTHON" "$@"; }
    """
    bash = shutil.which("bash")
    assert bash is not None
    return subprocess.run(  # noqa: S603 - exact source step; network command is a local stub
        [bash, "-e", "-c", stub + script],
        cwd=tmp_path,
        env=dict(os.environ, TEST_PYTHON=sys.executable, REPOSITORY="fictional/repo"),
        capture_output=True,
        check=False,
    )


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
    snapshot: dict[str, Any] = {
        "detector": {"name": "careops-uv-cyclonedx"},
        "manifests": {
            "uv.lock": {
                "resolved": {
                    "pkg:pypi/example@1.0": {
                        "package_url": "pkg:pypi/example@1.0",
                        "dependencies": [],
                    }
                }
            }
        },
    }
    graph: dict[str, Any] = {
        "sbom": {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": "example",
                    "externalRefs": [{"referenceType": "purl", "referenceLocator": observed}],
                },
            ],
            "relationships": [],
        }
    }
    run = run_readback(tmp_path, snapshot, graph)
    assert (run.returncode == 0) == accepted
    assert (base / "readback.json").exists() == accepted


@pytest.mark.parametrize("edge", ["DEPENDS_ON", "DEPENDENCY_OF", "missing", "reversed"])
def test_graph_readback_requires_relationships_with_all_packages_present(
    tmp_path: Path, edge: str
) -> None:
    """Node-only graph success cannot conceal a missing or reversed dependency."""
    alpha, beta = "pkg:pypi/alpha@1.0", "pkg:pypi/beta@1.0"
    snapshot: dict[str, Any] = {
        "detector": {"name": "careops-uv-cyclonedx"},
        "manifests": {
            "uv.lock": {
                "resolved": {
                    alpha: {"package_url": alpha, "dependencies": [beta]},
                    beta: {"package_url": beta, "dependencies": []},
                }
            }
        },
    }
    graph: dict[str, Any] = {
        "sbom": {
            "spdxVersion": "SPDX-2.3",
            "packages": [
                {
                    "SPDXID": name,
                    "externalRefs": [{"referenceType": "purl", "referenceLocator": purl}],
                }
                for name, purl in (("alpha", alpha), ("beta", beta))
            ],
            "relationships": [],
        }
    }
    if edge != "missing":
        source, target = (
            ("beta", "alpha") if edge in ("DEPENDENCY_OF", "reversed") else ("alpha", "beta")
        )
        graph["sbom"]["relationships"] = [
            {
                "spdxElementId": source,
                "relatedSpdxElement": target,
                "relationshipType": "DEPENDENCY_OF" if edge == "DEPENDENCY_OF" else "DEPENDS_ON",
            }
        ]
    run = run_readback(tmp_path, snapshot, graph)
    accepted = edge in ("DEPENDS_ON", "DEPENDENCY_OF")
    assert (run.returncode == 0) == accepted, run.stderr
    receipt = tmp_path / ".local/dependency-inventory/readback.json"
    assert receipt.exists() == accepted
    if accepted:
        assert json.loads(receipt.read_text())["dependencyRelationshipsVerified"] == 1


def test_submission_is_trusted_main_only_and_has_no_automatic_retry() -> None:
    """PRs cannot reach the write job; accepted submissions are never replayed."""
    assert "pull_request:" not in WORKFLOW
    assert "if: github.ref == 'refs/heads/main'" in WORKFLOW
    assert "cancel-in-progress: false" in WORKFLOW
    assert WORKFLOW.count("gh api --method POST") == 1
    assert "--frozen --all-extras --all-groups" in WORKFLOW
    assert "--no-emit-project" not in WORKFLOW  # Retain the graph root and direct edges.
    assert "git diff --exit-code -- uv.lock pyproject.toml" in WORKFLOW
    assert "8080acfb3549849408c35295b9b939711c90775e" in WORKFLOW
    assert "--snapshot .local/dependency-inventory/snapshot.json" in WORKFLOW
    assert "readback.json" in WORKFLOW
