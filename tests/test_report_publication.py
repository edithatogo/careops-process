# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Report publication must preserve prior artifacts across serialization and I/O failures."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from careops_process.report_publication import publish_report

if TYPE_CHECKING:
    from pathlib import Path


def test_report_is_published_as_one_complete_json_artifact(tmp_path: Path) -> None:
    """Successful replacement exposes complete deterministic JSON with no staging debris."""
    output = tmp_path / "report.json"
    output.write_text("old-report", encoding="utf-8")
    report = {"run_id": "synthetic-run", "evidence_class": "synthetic", "event_count": 1}
    publish_report(report, output)
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert not list(tmp_path.glob(".careops-report-*"))


def test_unserializable_report_cannot_replace_prior_output(tmp_path: Path) -> None:
    """A failed write removes its partial stage while retaining the authoritative report."""
    output = tmp_path / "report.json"
    output.write_text("old-report", encoding="utf-8")
    with pytest.raises(TypeError, match="JSON serializable"):
        publish_report({"invalid_value": object()}, output)
    assert output.read_text(encoding="utf-8") == "old-report"
    assert not list(tmp_path.glob(".careops-report-*"))
