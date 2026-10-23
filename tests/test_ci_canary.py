# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Execute the real workflow receipt on bootstrap and compatibility failures."""

import json
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("failed_stage", "expected_state"),
    [
        ("source", "setup-blocked"),
        ("bootstrap", "setup-blocked"),
        ("prepare", "preparation-failure"),
        ("resolve", "executed-failure"),
        ("install", "executed-failure"),
        ("tests", "executed-failure"),
        (None, "qualified-source-only"),
    ],
)
def test_real_receipt_classifies_every_stage(
    tmp_path: Path,
    failed_stage: str | None,
    expected_state: str,
) -> None:
    """Early failures retain a receipt and cannot look like successful tests."""
    workflow = Path(".github/workflows/development-canary.yml").read_text()
    step = workflow.split("      - name: Record actual qualification and lock integrity\n", 1)[1]
    step = step.split("      - name: Preserve candidate evidence", 1)[0]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1])
    if sys.platform == "win32":
        # The workflow wrapper contains only this Python heredoc. Execute its
        # unchanged body locally; Linux continues to check the actual Bash step.
        opening = "python - <<'PY'\n"
        assert script.startswith(opening)
        assert script.endswith("\nPY\n")
        command = [sys.executable, "-c", script[len(opening) : -len("\nPY\n")]]
    else:
        script = script.replace("python", shlex.quote(sys.executable), 1)
        command = ["/bin/bash", "-euc", script]
    names = ["source", "bootstrap", "prepare", "resolve", "install", "tests"]
    outcomes = dict.fromkeys(names, "success")
    if failed_stage:
        position = names.index(failed_stage)
        outcomes.update(dict.fromkeys(names[position + 1 :], "skipped"))
        outcomes[failed_stage] = "failure"
    environment = {
        **{name.upper() + "_OUTCOME": value for name, value in outcomes.items()},
    }
    environment.update(
        CANARY_ROOT=str(tmp_path / "evidence"),
        SOURCE_COMMIT="a" * 40,
        CANDIDATE_PYTHON="3.15.1",
        TEST_OUTCOME=outcomes["tests"],
    )
    # Execute only the checked-in workflow receipt with an explicit no-credential environment.
    subprocess.run(  # noqa: S603 - fixed repository CI receipt; no caller command input
        command,
        check=True,
        env=environment,
        capture_output=True,
    )
    receipt = json.loads((tmp_path / "evidence/qualification.json").read_text())
    assert receipt["state"] == expected_state
    assert receipt["failedStage"] == failed_stage
    assert receipt["testsExecuted"] == (outcomes["tests"] in {"success", "failure"})
    assert receipt["promoted"] is False
    assert receipt["nativeWrites"] is False
    assert receipt["optionalProviderScope"] == (
        "synthetic alignment/store tests and dependency load; no production deployment"
        if failed_stage is None
        else "not qualified; inspect stage outcomes"
    )


@pytest.mark.parametrize(
    ("candidate", "accepted"),
    [("3.14.8", False), ("3.15.1", True), ("3.15.2rc1", True), ("3.16.0a1", False)],
)
def test_candidate_preparation_preserves_supported_runtime_range(
    tmp_path: Path,
    candidate: str,
    *,
    accepted: bool,
) -> None:
    """Execute real preparation: candidates stay in the selected Python line."""
    workflow = Path(".github/workflows/development-canary.yml").read_text()
    step = workflow.split(
        "      - name: Prepare committed source in an isolated candidate workspace\n", 1
    )[1]
    step = step.split("      - name: Resolve preview dependencies", 1)[0]
    shell = textwrap.dedent(step.split("        run: |\n", 1)[1])
    script = shell.split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    source = Path("pyproject.toml").read_text()
    target = tmp_path / "pyproject.toml"
    target.write_text(source)
    result = subprocess.run(  # noqa: S603 - actual checked-in preparation with synthetic environment
        [sys.executable, "-c", script],
        check=False,
        env={"CANARY_ROOT": str(tmp_path), "CANDIDATE_PYTHON": candidate},
        capture_output=True,
    )
    assert (result.returncode == 0) is accepted
    assert target.read_text() == source
    assert Path("pyproject.toml").read_text() == source


def test_runtime_setup_failure_retains_receipt_without_python(tmp_path: Path) -> None:
    """Run the real shell fallback with no interpreter available in PATH."""
    if sys.platform == "win32":
        pytest.skip("The actual workflow fallback runs on Linux Bash")
    workflow = Path(".github/workflows/development-canary.yml").read_text()
    step = workflow.split(
        "      - name: Retain setup failure without a fallback Python runtime\n", 1
    )[1].split("      - name: Record actual qualification", 1)[0]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1])
    subprocess.run(  # noqa: S603 - exact repository fallback, fixed Bash, no user command
        ["/bin/bash", "-euc", script],
        env={"CANARY_ROOT": str(tmp_path), "PATH": "/not-an-interpreter-directory"},
        check=True,
        capture_output=True,
    )
    result = json.loads((tmp_path / "qualification.json").read_text())
    assert result["state"] == "setup-blocked"
    assert result["failedStage"] == "python"
    assert result["testsExecuted"] is False
    assert result["promoted"] is False
