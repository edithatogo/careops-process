# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Read-only hub deployment preparation must expose actual artifact and live gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from careops_process.hub_release import HubReleaseRequest, main, prepare_hub_release


def test_neutral_blueprint_is_blocked_without_human_lane_and_artifacts() -> None:
    """Local assets never invent a publisher, target, approval or packaged application."""
    result = prepare_hub_release(HubReleaseRequest())
    assert result.deployment_authorized is False
    assert result.mode == "dry_run_only"
    assert "pilot_lane_unselected" in result.gaps
    assert "operating_model_missing" in result.gaps
    assert "publisher_confirmation_missing" in result.gaps
    assert "capability_verification_missing" in result.gaps


def test_preferred_lane_reuses_shared_alm_with_prechange_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preparation uses the shared validator but still exposes app/flow and live gates."""
    observed: list[tuple[Path, Path | None, str]] = []

    def prepared(release: Path, backup: Path | None, stage: str) -> dict[str, str]:
        observed.append((release, backup, stage))
        return {"status": "prepared-offline", "solution": "SyntheticHub", "version": "1.0.0.0"}

    monkeypatch.setattr("careops_process.hub_release.local_alm.prepare_deployment", prepared)
    request = HubReleaseRequest(lane="dataverse", stage="dev")
    result = prepare_hub_release(request, release=tmp_path / "release", backup=tmp_path / "backup")
    assert observed == [(tmp_path / "release", tmp_path / "backup", "dev")]
    assert result.artifact_prepared is True
    assert "hub_app_flow_validation_pending" in result.gaps
    assert result.deployment_authorized is False


def test_shared_alm_failure_is_sanitized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Private tool diagnostics or paths cannot enter a release report."""

    def rejected(_release: Path, _backup: Path | None, _stage: str) -> dict[str, str]:
        message = "synthetic-private-diagnostic-with-token"
        raise ValueError(message)

    monkeypatch.setattr("careops_process.hub_release.local_alm.prepare_deployment", rejected)
    result = prepare_hub_release(
        HubReleaseRequest(lane="dataverse"), release=tmp_path, backup=tmp_path
    )
    assert "release_or_backup_invalid_or_unsupported" in result.gaps
    assert "private-diagnostic" not in result.model_dump_json()


def test_fallback_requires_low_metadata_and_verified_configuration_export() -> None:
    """The no-admin fallback is not a substitute for unverified privacy or audit controls."""
    result = prepare_hub_release(
        HubReleaseRequest(lane="restricted_fallback", classification="protected")
    )
    assert "fallback_classification_incompatible" in result.gaps
    assert "fallback_configuration_export_missing" in result.gaps
    assert result.deployment_authorized is False


def test_release_configuration_rejects_bound_urls_tokens_and_unknown_fields() -> None:
    """Only opaque review references may enter the neutral release request."""
    for value in (
        {"token": "synthetic-secret"},
        {"publisher_confirmation_ref": "https://example.com"},
    ):
        with pytest.raises(ValidationError):
            HubReleaseRequest.model_validate(value)


def test_cli_generates_only_read_only_dry_run_report(capsys: pytest.CaptureFixture[str]) -> None:
    """The public module prepares a review report and offers no live import operation."""
    assert main([]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "dry_run_only"
    assert output["deployment_authorized"] is False


def test_cli_invalid_request_never_echoes_private_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A malformed review request yields one safe fixed error code."""
    request = tmp_path / "request.json"
    request.write_text('{"token":"synthetic-private-secret"}', encoding="utf-8")
    assert main(["--request", str(request)]) == 2  # noqa: PLR2004
    error = capsys.readouterr().err
    assert "invalid_release_request" in error
    assert "synthetic-private-secret" not in error


def test_actual_malformed_shared_manifest_is_sanitized(tmp_path: Path) -> None:
    """The real ALM lookup failure must produce a gap rather than an uncaught traceback."""
    release = tmp_path / "release"
    release.mkdir()
    (release / "release.json").write_text("{}", encoding="utf-8")
    result = prepare_hub_release(
        HubReleaseRequest(lane="dataverse"), release=release, backup=tmp_path / "backup"
    )
    assert result.artifact_prepared is False
    assert "release_or_backup_invalid_or_unsupported" in result.gaps


def test_report_cannot_overwrite_request_release_or_backup_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dry-run reports cannot destroy the evidence they are meant to review."""
    request = tmp_path / "request.json"
    request.write_text("{}", encoding="utf-8")
    release = tmp_path / "release"
    backup = tmp_path / "backup"
    release.mkdir()
    backup.mkdir()
    manifest = backup / "release.json"
    manifest.write_text("{}", encoding="utf-8")
    unsafe_destination_exit = 2
    for output in (request, manifest, release / "new-report.json"):
        assert (
            main(
                [
                    "--request",
                    str(request),
                    "--release",
                    str(release),
                    "--backup",
                    str(backup),
                    "--output",
                    str(output),
                ]
            )
            == unsafe_destination_exit
        )
        assert "unsafe_release_report_destination" in capsys.readouterr().err
    assert request.read_text(encoding="utf-8") == "{}"
    assert manifest.read_text(encoding="utf-8") == "{}"


def test_safe_output_is_created_once_and_existing_alias_is_preserved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Create a new report without allowing subsequent calls to overwrite existing evidence."""
    output = tmp_path / "reports" / "plan.json"
    assert main(["--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["deployment_authorized"] is False
    prior = output.read_text(encoding="utf-8")
    assert main(["--output", str(output)]) == 2  # noqa: PLR2004
    assert "unsafe_release_report_destination" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == prior


def test_all_declared_refs_do_not_remove_actual_app_flow_and_access_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unsigned review pointers cannot become deployment permission or component verification."""
    data = {
        name: "synthetic-review" for name in HubReleaseRequest.model_fields if name.endswith("_ref")
    }
    request = HubReleaseRequest.model_validate(
        {**data, "lane": "dataverse", "classification": "low_sensitivity_metadata"}
    )
    without_artifacts = prepare_hub_release(request)
    assert "solution_export_missing" in without_artifacts.gaps
    assert "prechange_backup_missing" in without_artifacts.gaps

    def unsupported(_release: Path, _backup: Path | None, _stage: str) -> dict[str, str]:
        return {"status": "not-prepared"}

    monkeypatch.setattr("careops_process.hub_release.local_alm.prepare_deployment", unsupported)
    checked = prepare_hub_release(request, release=tmp_path, backup=tmp_path)
    assert checked.artifact_prepared is False
    assert "release_or_backup_invalid_or_unsupported" in checked.gaps
    fallback = HubReleaseRequest.model_validate(
        {**data, "lane": "restricted_fallback", "classification": "low_sensitivity_metadata"}
    )
    assert "publisher_confirmation_missing" not in prepare_hub_release(fallback).gaps
    assert prepare_hub_release(fallback).deployment_authorized is False


def test_output_resolution_and_write_errors_are_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Filesystem failures cannot leak private paths or destroy an existing report."""

    def failed_resolve(_path: Path) -> Path:
        message = "synthetic-private-path"
        raise OSError(message)

    monkeypatch.setattr(Path, "resolve", failed_resolve)
    assert main(["--output", str(tmp_path / "new.json")]) == 2  # noqa: PLR2004
    assert "unsafe_release_report_destination" in capsys.readouterr().err
    monkeypatch.undo()

    def failed_open(_path: Path, *_args: object, **_kwargs: object) -> None:
        message = "synthetic-private-path"
        raise OSError(message)

    monkeypatch.setattr(Path, "open", failed_open)
    assert main(["--output", str(tmp_path / "new.json")]) == 2  # noqa: PLR2004
    errors = capsys.readouterr().err
    assert "release_report_write_failed" in errors
    assert "synthetic-private-path" not in errors
