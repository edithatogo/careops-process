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
    script = script.replace("/usr/bin/python3", shlex.quote(sys.executable), 1)
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
        CANDIDATE_PYTHON="3.15.0",
        TEST_OUTCOME=outcomes["tests"],
    )
    # Execute only the checked-in workflow receipt with an explicit no-credential environment.
    subprocess.run(  # noqa: S603 - fixed repository CI receipt; no caller command input
        ["/bin/bash", "-euc", script],
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
