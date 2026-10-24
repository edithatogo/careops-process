# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Report command privacy and approved-manifest integration checks."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from tests.backfill_fixture import sealed_evidence
from tests.test_backfill_evidence import FACTS


@pytest.mark.parametrize(
    "mode", ["valid", "invalid_timestamp", "acquired", "unapproved", "output_alias"]
)
def test_report_command_enforces_closed_inputs_and_safe_diagnostics(
    tmp_path: Path, mode: str
) -> None:
    """Only approved closed input replaces a report; failures never echo protected values."""
    protected_value = "synthetic-protected-protected_value"
    facts = [dict(FACTS[0])]
    if mode == "invalid_timestamp":
        facts[0]["timestamp_utc"] = protected_value
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
    facts_before = (tmp_path / "facts.json").read_text(encoding="utf-8")
    destination = tmp_path / "facts.json" if mode == "output_alias" else output
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
            str(destination),
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
    assert protected_value not in completed.stderr
    assert protected_value not in completed.stdout
    assert "Traceback" not in completed.stderr
    assert output.read_text(encoding="utf-8") == "previous-valid-output"
    assert (tmp_path / "facts.json").read_text(encoding="utf-8") == facts_before


def test_interrupted_publication_preserves_report_and_sanitizes_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A disk or rename failure must leave the prior authoritative report intact."""
    facts = [dict(FACTS[0])]
    evidence = sealed_evidence(facts)
    entry = {
        "source_owner_approved": True,
        "ig_approved": True,
        "configuration_frozen": True,
        "rollback_retention_approved": True,
        "authorised_source_partitions": ["outlook-authorised-mailbox"],
        "configuration_hash": evidence["configuration_hash"],
        "evidence_reference": "synthetic-reference",
    }
    for name, value in (("facts", facts), ("evidence", evidence), ("entry", entry)):
        (tmp_path / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "report.json"
    previous = "previous-authoritative-report"
    output.write_text(previous, encoding="utf-8")
    main = runpy.run_path("scripts/build-closed-run-report.py")["main"]
    monkeypatch.setenv("CAREOPS_PSEUDONYM_SECRET", "synthetic-key")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build-closed-run-report",
            "--facts",
            str(tmp_path / "facts.json"),
            "--evidence",
            str(tmp_path / "evidence.json"),
            "--pilot-entry",
            str(tmp_path / "entry.json"),
            "--output",
            str(output),
        ],
    )
    original_write = Path.write_text
    original_replace = Path.replace
    protected_value = "synthetic-protected-disk-error"

    def failed_write(
        path: Path,
        text: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if path == output:
            original_write(path, "partial-report", encoding="utf-8")
            raise OSError(protected_value)
        return original_write(path, text, encoding=encoding, errors=errors, newline=newline)

    def failed_replace(path: Path, destination: Path) -> Path:
        if destination == output:
            raise OSError(protected_value)
        return original_replace(path, destination)

    monkeypatch.setattr(Path, "write_text", failed_write)
    monkeypatch.setattr(Path, "replace", failed_replace)
    with pytest.raises(SystemExit):
        main()
    assert output.read_text(encoding="utf-8") == previous
    assert protected_value not in capsys.readouterr().err
    assert not list(tmp_path.glob(".careops-report-*"))
