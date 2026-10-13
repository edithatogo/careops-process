"""Report command privacy and approved-manifest integration checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from tests.backfill_fixture import sealed_evidence
from tests.test_backfill_evidence import FACTS


@pytest.mark.parametrize("mode", ["valid", "invalid_timestamp", "acquired", "unapproved"])
def test_report_command_enforces_closed_inputs_and_safe_diagnostics(
    tmp_path: Path, mode: str
) -> None:
    """Only approved closed input replaces a report; failures never echo protected values."""
    sentinel = "synthetic-protected-sentinel"
    facts = [dict(FACTS[0])]
    if mode == "invalid_timestamp":
        facts[0]["timestamp_utc"] = sentinel
    evidence = sealed_evidence(facts)
    if mode == "acquired":
        evidence["status"] = "acquired"
    entry = {
        "source_owner_approved": True,
        "ig_approved": True,
        "configuration_frozen": True,
        "rollback_retention_approved": True,
        "authorised_source_partitions": ["outlook-authorised-mailbox"],
        "configuration_hash": evidence["configuration_hash"],
        "evidence_reference": "synthetic-reference",
    }
    if mode == "unapproved":
        entry["ig_approved"] = False
    for name, value in (("facts", facts), ("evidence", evidence), ("entry", entry)):
        (tmp_path / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "report.json"
    output.write_text("previous-valid-output", encoding="utf-8")
    completed = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "scripts/build-closed-run-report.py",
            "--facts",
            str(tmp_path / "facts.json"),
            "--evidence",
            str(tmp_path / "evidence.json"),
            "--pilot-entry",
            str(tmp_path / "entry.json"),
            "--output",
            str(output),
        ],
        env={**os.environ, "CAREOPS_PSEUDONYM_SECRET": "synthetic-key"},
        capture_output=True,
        text=True,
        check=False,
    )
    if mode == "valid":
        assert completed.returncode == 0, completed.stderr
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["evidence"]["content_hash"] == evidence["content_hash"]
        assert report["coverage_ledger"]["evidence_class"] == "synthetic"
        assert report["corpus_quality"]["event_count"] == len(facts)
        return
    assert completed.returncode != 0
    assert sentinel not in completed.stderr
    assert sentinel not in completed.stdout
    assert "Traceback" not in completed.stderr
    assert output.read_text(encoding="utf-8") == "previous-valid-output"
