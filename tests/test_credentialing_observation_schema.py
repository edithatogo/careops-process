# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Independent lexical fixtures for published observation-schema patterns."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


@pytest.mark.parametrize("branch", [0, 1])
@pytest.mark.parametrize(
    ("field", "valid"),
    [
        ("observation_id", "synthetic-event"),
        ("case_id", "synthetic-case"),
        ("source_system", "synthetic"),
        ("recorded_at_utc", "2026-06-01T00:00:00.123456+00:00"),
    ],
)
def test_schema_patterns_require_the_true_end_of_input(branch: int, field: str, valid: str) -> None:
    """A terminal newline must not turn uncontrolled values into valid wire tokens."""
    schema_path = (
        Path(__file__).resolve().parents[1] / "contracts/credentialing-observation.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    pattern = schema["oneOf"][branch]["properties"][field]["pattern"]
    assert re.search(pattern, valid) is not None
    assert re.search(pattern, valid + "\n") is None


def test_evaluation_reference_pattern_rejects_terminal_newline() -> None:
    """The independently versioned evaluation mapping uses the same strict boundary."""
    schema_path = (
        Path(__file__).resolve().parents[1] / "contracts/credentialing-observation.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    pattern = schema["oneOf"][1]["properties"]["evaluation_reference_version"]["pattern"]
    assert re.search(pattern, "mapping-v1") is not None
    assert re.search(pattern, "mapping-v1\n") is None
