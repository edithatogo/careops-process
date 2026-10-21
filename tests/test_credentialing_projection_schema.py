# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Independent JSON Schema lexical boundary fixtures for credentialing projection."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

_FACT = "$defs.fact.properties."
_QUALIFIER = _FACT + "qualifiers.properties."


@pytest.mark.parametrize(
    ("path", "valid"),
    [
        ("$defs.safe_id", "event-1"),
        (_FACT + "source_system", "synthetic"),
        (_QUALIFIER + "pathway_code", "routine-renewal"),
        (_QUALIFIER + "professional_stream", "synthetic-stream"),
        (_QUALIFIER + "facility_or_service_type", "synthetic-service"),
        (_QUALIFIER + "exception_code", "synthetic-exception"),
        (_QUALIFIER + "feature_pack_version", "0.1.0"),
        (_QUALIFIER + "authority_mapping_version", "synthetic-v1"),
    ],
)
def test_projection_schema_patterns_reject_terminal_newlines(path: str, valid: str) -> None:
    """JSON Schema uses search semantics, so a trailing dollar anchor alone is unsafe."""
    schema_path = (
        Path(__file__).resolve().parents[1] / "contracts/credentialing-event-projection.json"
    )
    node: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    for component in path.split("."):
        node = node[component]
    assert re.search(node["pattern"], valid) is not None
    assert re.search(node["pattern"], valid + "\n") is None
