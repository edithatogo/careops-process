# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Every execution entry point rejects relabelled synthetic live artifacts."""

from __future__ import annotations

import json
import runpy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from careops_process.backfill_run import run_authorised_closed_backfill, run_closed_backfill
from careops_process.report import build_authorised_closed_run_report, build_closed_run_report
from tests.backfill_fixture import sealed_evidence
from tests.test_outlook_reconciliation import inputs


def candidate() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Relabel an internally consistent synthetic manifest without external proof."""
    facts = inputs()["destination_facts"]
    evidence = sealed_evidence(facts)
    evidence["evidence_class"] = "live_corpus"
    entry = {
        "source_owner_approved": True,
        "ig_approved": True,
        "configuration_frozen": True,
        "rollback_retention_approved": True,
        "authorised_source_partitions": evidence["configuration"]["authorised_source_partitions"],
        "configuration_hash": evidence["configuration_hash"],
        "evidence_reference": "synthetic-untrusted-test-only",
    }
    return facts, evidence, entry


@pytest.mark.parametrize(
    "entrypoint", ["runner", "authorised_runner", "report", "authorised_report"]
)
def test_direct_entrypoints_reject_caller_labelled_live_evidence(entrypoint: str) -> None:
    """Matching hashes and approval flags cannot replace a live-evidence validator."""
    facts, evidence, entry = candidate()
    with pytest.raises(ValueError, match=r"live.*verification"):
        _execute(entrypoint, facts, evidence, entry)


def _execute(
    entrypoint: str,
    facts: list[dict[str, Any]],
    evidence: dict[str, Any],
    entry: dict[str, Any],
) -> None:
    if entrypoint == "runner":
        run_closed_backfill(facts, evidence, pseudonym_secret="synthetic")  # noqa: S106
    elif entrypoint == "authorised_runner":
        run_authorised_closed_backfill(facts, evidence, entry, pseudonym_secret="synthetic")  # noqa: S106
    elif entrypoint == "report":
        build_closed_run_report(facts, evidence, pseudonym_secret="synthetic")  # noqa: S106
    else:
        build_authorised_closed_run_report(facts, evidence, entry, pseudonym_secret="synthetic")  # noqa: S106


def test_cli_rejects_live_label_without_publishing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The command cannot bypass the common gate by loading a prebuilt envelope."""
    facts, evidence, entry = candidate()
    paths = [tmp_path / name for name in ("facts.json", "evidence.json", "entry.json")]
    for path, value in zip(paths, (facts, evidence, entry), strict=True):
        path.write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "report.json"
    monkeypatch.setenv("CAREOPS_PSEUDONYM_SECRET", "synthetic-local-test-only")
    monkeypatch.setattr(
        "sys.argv",
        [
            "build-closed-run-report",
            "--facts",
            str(paths[0]),
            "--evidence",
            str(paths[1]),
            "--pilot-entry",
            str(paths[2]),
            "--output",
            str(output),
        ],
    )
    main = runpy.run_path("scripts/build-closed-run-report.py")["main"]
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2  # noqa: PLR2004
    assert not output.exists()
    assert "inputs failed validation" in capsys.readouterr().err
