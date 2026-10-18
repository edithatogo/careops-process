# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Read-only, privacy-safe Windows probe orchestration with synthetic responses."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from careops_process.hub_probe import (
    ProbeConfig,
    ProbeResponse,
    build_probe_calls,
    collect_capabilities,
    main,
    run_cli,
)

NOW = datetime(2026, 10, 14, tzinfo=UTC)
ENV_ID = "00000000-0000-0000-0000-000000000001"
TARGETS: dict[str, Any] = {
    "environment_url": "https://synthetic.crm.dynamics.com",
    "environment_id": ENV_ID,
    "team_id": "00000000-0000-0000-0000-000000000002",
    "site_url": "https://synthetic.sharepoint.com/sites/synthetic",
    "list_id": "00000000-0000-0000-0000-000000000003",
    "planner_plan_id": "synthetic-plan",
    "app_id": "00000000-0000-0000-0000-000000000004",
    "governance_table": "ihg_governancematter",
}


def test_only_explicit_scope_is_probed() -> None:
    """Default discovery never examines an implicit org, site, plan or app."""
    calls = build_probe_calls(ProbeConfig())
    assert {call.name for call in calls} == {"pac_identity", "m365_identity", "environments"}


def test_all_scoped_read_operations_and_no_admin_prerequisite() -> None:
    """A fully configured probe reads metadata only through cached user tools."""
    calls = build_probe_calls(ProbeConfig.model_validate(TARGETS))
    names = {call.name for call in calls}
    assert names >= {
        "dataverse",
        "roles",
        "solutions",
        "audit_settings",
        "tables",
        "connectors",
        "app_permissions",
        "team",
        "list_controls",
        "planner",
    }
    args = [arg.lower() for call in calls for arg in call.arguments]
    assert not set(args) & {
        "--asadmin",
        "admin",
        "create",
        "add",
        "import",
        "grant",
        "login",
        "--clientsecret",
        "--applicationid",
        "--grantadminconsent",
        "--debug",
    }
    for call in calls:
        if call.tool == "pac" and call.name not in {"pac_identity", "environments"}:
            assert "--environment" in call.arguments
            assert TARGETS["environment_url"] in call.arguments
    roles = next(call for call in calls if call.name == "roles")
    assert "eq-userid" in " ".join(roles.arguments)
    assert 'top="100"' in " ".join(roles.arguments)


@pytest.mark.parametrize("field", ["environment_url", "site_url"])
@pytest.mark.parametrize(
    "url", ["http://example.com", "https://u:p@example.com", "https://example.com/?token=x"]
)
def test_rejects_unsafe_scope_urls(field: str, url: str) -> None:
    """A configured URL cannot carry credentials, queries or insecure transport."""
    with pytest.raises(ValidationError):
        ProbeConfig.model_validate({field: url})


def test_resource_dependencies_and_unknown_config_rejected() -> None:
    """A list cannot be probed without a site; arbitrary configuration is rejected."""
    for value in (
        {"list_id": TARGETS["list_id"]},
        {"governance_table": "patient"},
        {"token": "secret"},
    ):
        with pytest.raises(ValidationError):
            ProbeConfig.model_validate(value)


def test_successful_reads_are_observations_never_verified_controls() -> None:
    """Even universal read success leaves deployment and sharing gates closed."""

    def runner(_tool: str, arguments: tuple[str, ...]) -> ProbeResponse:
        if arguments == ("auth", "who"):
            return ProbeResponse("success", "Type: User\n")
        if arguments[0] == "status":
            return ProbeResponse("success", json.dumps({"authType": "DeviceCode"}))
        return ProbeResponse("success", "synthetic-sensitive-raw-output")

    result = collect_capabilities(ProbeConfig.model_validate(TARGETS), runner=runner, now=NOW)
    assert result.assessment.lane == "fail_closed"
    assert result.probes["roles"] == "observed"
    assert result.snapshot.checks["dataverse_access"].status == "observed"
    rendered = result.model_dump_json()
    assert "synthetic-sensitive-raw-output" not in rendered
    assert "synthetic.crm" not in rendered
    assert "sharepoint.com" not in rendered
    assert "app_sharing_rights" in result.assessment.gaps["dataverse"]
    assert result.snapshot.co_owner_count == 0


@pytest.mark.parametrize("auth_type", ["Certificate", "Secret", "ManagedIdentity", "unknown"])
def test_application_authentication_prevents_resource_probes(auth_type: str) -> None:
    """Application identities are not a shortcut around user-scoped discovery."""
    invoked: list[tuple[str, ...]] = []

    def runner(tool: str, arguments: tuple[str, ...]) -> ProbeResponse:
        invoked.append(arguments)
        if tool == "pac":
            return ProbeResponse("success", "Type: ServicePrincipal\n")
        return ProbeResponse("success", json.dumps({"authType": auth_type}))

    result = collect_capabilities(ProbeConfig.model_validate(TARGETS), runner=runner, now=NOW)
    assert len(invoked) == 2  # noqa: PLR2004
    assert result.probes["dataverse"] == "unavailable"
    assert result.probes["team"] == "unavailable"
    assert result.assessment.lane == "fail_closed"


def test_logged_out_and_expired_connection_fail_closed_without_retry() -> None:
    """A missing cached sign-in does not launch an interactive authentication loop."""
    invoked: list[str] = []

    def runner(tool: str, _arguments: tuple[str, ...]) -> ProbeResponse:
        invoked.append(tool)
        return ProbeResponse("error", '"Logged out"')

    result = collect_capabilities(ProbeConfig.model_validate(TARGETS), runner=runner, now=NOW)
    assert invoked == ["pac", "m365"]
    assert result.probes["m365_identity"] == "failed"
    assert result.assessment.lane == "fail_closed"


@pytest.mark.parametrize("state", ["timeout", "unavailable", "error"])
def test_partial_failure_is_sanitized_and_other_probes_continue(state: str) -> None:
    """One failed resource does not prevent an independent safe capability check."""

    def runner(tool: str, arguments: tuple[str, ...]) -> ProbeResponse:
        if tool == "pac":
            return ProbeResponse("success", "Type: User\n")
        if arguments[0] == "status":
            return ProbeResponse("success", '{"authType":"Browser"}')
        return ProbeResponse(state, "sensitive-diagnostic-that-must-not-leak")  # type: ignore[arg-type]

    result = collect_capabilities(ProbeConfig.model_validate(TARGETS), runner=runner, now=NOW)
    assert result.probes["team"] in {"failed", "unavailable"}
    assert "sensitive-diagnostic" not in result.model_dump_json()
    assert result.probes["solutions"] == "observed"


def test_cli_dry_run_never_executes_tools(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dry run validates configuration and exports only fixed probe names."""
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(TARGETS), encoding="utf-8")
    assert main(["--config", str(path), "--dry-run"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "dry_run"
    assert "list_controls" in output["probes"]
    assert "sharepoint.com" not in json.dumps(output)


def test_cli_invalid_input_never_echoes_payload(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Configuration validation errors cannot echo private URLs or arbitrary fields."""
    path = tmp_path / "scope.json"
    path.write_text('{"token":"sensitive-secret"}', encoding="utf-8")
    assert main(["--config", str(path)]) == 2  # noqa: PLR2004
    output = capsys.readouterr()
    assert "invalid_probe_configuration" in output.err
    assert "sensitive-secret" not in output.err


def test_cli_writes_sanitized_report_and_handles_output_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Persist collected evidence without leaking output failure paths."""

    def fake_collect(_config: ProbeConfig, *, now: datetime) -> Any:  # noqa: ANN401
        def absent(_tool: str, _arguments: tuple[str, ...]) -> ProbeResponse:
            return ProbeResponse("unavailable", "")

        return collect_capabilities(ProbeConfig(), runner=absent, now=now)

    monkeypatch.setattr("careops_process.hub_probe.collect_capabilities", fake_collect)
    path = tmp_path / "reports" / "report.json"
    assert main(["--output", str(path)]) == 0
    assert json.loads(path.read_text(encoding="utf-8"))["assessment"]["lane"] == "fail_closed"
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["assessment"]["pilot_authorized"] is False
    invalid_path = tmp_path / "file-not-directory"
    invalid_path.write_text("", encoding="utf-8")
    assert main(["--output", str(invalid_path / "report.json")]) == 2  # noqa: PLR2004
    error = capsys.readouterr().err
    assert "report_write_failed" in error
    assert str(invalid_path) not in error


def test_optional_targets_and_null_urls_can_be_omitted() -> None:
    """Environment-level discovery does not require an app or table to exist."""
    config = ProbeConfig(environment_id=ENV_ID, environment_url=None, site_url=None)
    names = {call.name for call in build_probe_calls(config)}
    assert {"tables", "apps", "connectors"} <= names
    assert "app_permissions" not in names
    names = {call.name for call in build_probe_calls(ProbeConfig(site_url=TARGETS["site_url"]))}
    assert "lists" in names
    assert "list_controls" not in names


@pytest.mark.parametrize(
    "raw",
    [
        '"Logged out"',
        "invalid-json",
        '{"authType":"Secret"}',
        '{"authType":[]}',
        '{"authType":{}}',
        '{"authType":null}',
    ],
)
def test_malformed_or_nondelegated_status_suppresses_m365_reads(raw: str) -> None:
    """CLI exit zero is insufficient without a recognised delegated identity."""

    def runner(tool: str, _arguments: tuple[str, ...]) -> ProbeResponse:
        return ProbeResponse("success", raw if tool == "m365" else "no recognised identity")

    report = collect_capabilities(ProbeConfig.model_validate(TARGETS), runner=runner, now=NOW)
    assert report.probes["m365_identity"] == "failed"
    assert report.probes["tables"] == "unavailable"


def test_pac_universal_profile_requires_a_user() -> None:
    """PAC's general profile type alone cannot prove a user-scoped session."""

    def runner(tool: str, arguments: tuple[str, ...]) -> ProbeResponse:
        if tool == "pac" and arguments == ("auth", "who"):
            return ProbeResponse("success", "Type: UNIVERSAL\nUser: synthetic@example.invalid\n")
        return ProbeResponse("unavailable", "")

    report = collect_capabilities(ProbeConfig(), runner=runner, now=NOW)
    assert report.probes["pac_identity"] == "observed"


def test_cli_module_entrypoint_supports_safe_dry_run() -> None:
    """The documented module command works without invoking live CLI probes."""
    command = ["uv", "run", "python", "-m", "careops_process.hub_probe", "--dry-run"]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)  # noqa: S603
    assert result.returncode == 0
    assert json.loads(result.stdout)["mode"] == "dry_run"


def test_run_cli_handles_unavailable_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    """An absent runtime becomes a safe missing capability."""

    def absent(_name: str) -> None:
        return None

    monkeypatch.setattr("careops_process.hub_probe.shutil.which", absent)
    assert run_cli("pac", ("auth", "who")).state == "unavailable"
    assert run_cli("m365", ("status", "--output", "json")).state == "unavailable"


def test_run_cli_uses_bounded_shell_free_windows_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """Launch the actual Node CLI directly so the timeout kills the CLI process."""

    def available(name: str) -> str:
        return f"C:/synthetic/{name}"

    def exists(_path: Path) -> bool:
        return True

    monkeypatch.setattr("careops_process.hub_probe.shutil.which", available)
    monkeypatch.setattr(Path, "is_file", exists)
    invocations: list[list[str]] = []

    def execute(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        invocations.append(command)
        assert kwargs["timeout"] == 30  # noqa: PLR2004
        assert kwargs.get("shell", False) is False
        return subprocess.CompletedProcess(command, 0, stdout="safe", stderr="private")

    monkeypatch.setattr("careops_process.hub_probe.subprocess.run", execute)
    assert run_cli("m365", ("status", "--output", "json")).state == "success"
    assert invocations[0][0].endswith("node.exe")
    assert Path(invocations[0][1]).as_posix().endswith("cli-microsoft365/dist/index.js")
    assert "-File" not in invocations[0]
    assert run_cli("pac", ("auth", "who")).state == "success"


def test_run_cli_discards_failure_diagnostics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeouts and operating-system failures never return exception contents."""

    def available(_name: str) -> str:
        return "pac.exe"

    monkeypatch.setattr("careops_process.hub_probe.shutil.which", available)

    def timeout(*_args: object, **_kwargs: object) -> None:
        command = "sensitive-command"
        raise subprocess.TimeoutExpired(command, 30)

    monkeypatch.setattr("careops_process.hub_probe.subprocess.run", timeout)
    assert run_cli("pac", ("auth", "who")) == ProbeResponse("timeout", "")

    def failure(*_args: object, **_kwargs: object) -> None:
        message = "sensitive-path"
        raise OSError(message)

    monkeypatch.setattr("careops_process.hub_probe.subprocess.run", failure)
    assert run_cli("pac", ("auth", "who")) == ProbeResponse("unavailable", "")


def test_run_cli_rejects_unknown_tools_missing_entrypoint_and_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsafe tools, broken npm entrypoints and tool errors yield no raw diagnostics."""

    def available(name: str) -> str:
        return f"C:/synthetic/{name}"

    def missing(_path: Path) -> bool:
        return False

    def rejected(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="private-diagnostic", stderr="secret")

    monkeypatch.setattr("careops_process.hub_probe.shutil.which", available)
    monkeypatch.setattr(Path, "is_file", missing)
    monkeypatch.setattr("careops_process.hub_probe.subprocess.run", rejected)
    assert run_cli("unknown", ()) == ProbeResponse("unavailable", "")
    assert run_cli("m365", ()) == ProbeResponse("unavailable", "")
    assert run_cli("pac", ("auth", "who")) == ProbeResponse("error", "")


def test_timeout_bounds_real_node_cli_lifetime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Terminate a hanging synthetic Node CLI without a wrapper retaining its pipes."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is not installed")
    entry = tmp_path / "node_modules" / "@pnp" / "cli-microsoft365" / "dist" / "index.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("setTimeout(() => {}, 4000);", encoding="utf-8")

    def executable(name: str) -> str | None:
        return str(tmp_path / "m365.cmd") if name == "m365.cmd" else node

    monkeypatch.setattr("careops_process.hub_probe.shutil.which", executable)
    monkeypatch.setattr("careops_process.hub_probe.CLI_TIMEOUT_SECONDS", 0.1, raising=False)
    start = time.monotonic()
    assert run_cli("m365", ("status", "--output", "json")) == ProbeResponse("timeout", "")
    assert time.monotonic() - start < 2  # noqa: PLR2004
