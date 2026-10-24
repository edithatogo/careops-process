# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Windows-native read-only capability discovery using existing user sign-ins.

No raw tool response, identity, resource title, URL or error text is exported.
Probes never create authentication profiles, grant consent or modify resources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, Self, cast
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from careops_process.hub_capabilities import (
    CapabilityAssessment,
    CapabilityCheck,
    CapabilitySnapshot,
    CheckName,
    CheckStatus,
    assess_capabilities,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

ResourceId = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")]
Guid = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")]
ResponseState = Literal["success", "error", "timeout", "unavailable"]
CLI_TIMEOUT_SECONDS = 30
ROLES_XML = (
    '<fetch top="100" distinct="true"><entity name="role"><attribute name="roleid"/>'
    '<link-entity name="systemuserroles" from="roleid" to="roleid" intersect="true">'
    '<filter><condition attribute="systemuserid" operator="eq-userid"/></filter>'
    "</link-entity></entity></fetch>"
)
TEAM_ROLES_XML = (
    '<fetch top="100" distinct="true"><entity name="role"><attribute name="roleid"/>'
    '<link-entity name="teamroles" from="roleid" to="roleid" intersect="true">'
    '<link-entity name="teammembership" from="teamid" to="teamid" intersect="true">'
    '<filter><condition attribute="systemuserid" operator="eq-userid"/></filter>'
    "</link-entity></link-entity></entity></fetch>"
)
AUDIT_XML = (
    '<fetch top="1"><entity name="organization"><attribute name="isauditenabled"/></entity></fetch>'
)


class ProbeConfig(BaseModel):
    """Explicit target selection; configuration stays outside exported reports."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_url: str | None = None
    environment_id: Guid | None = None
    team_id: Guid | None = None
    site_url: str | None = None
    list_id: Guid | None = None
    planner_plan_id: ResourceId | None = None
    app_id: Guid | None = None
    governance_table: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")] | None = None

    @field_validator("environment_url", "site_url")
    @classmethod
    def require_safe_https(cls, value: str | None) -> str | None:
        """Reject credentials, queries, fragments and insecure resource URLs."""
        if value is None:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or any(char.isspace() for char in value)
        ):
            message = "scope URLs require plain HTTPS without credentials or query strings"
            raise ValueError(message)
        return value.rstrip("/")

    @model_validator(mode="after")
    def require_resource_context(self) -> Self:
        """Reject target IDs lacking their corresponding environment or site."""
        if self.list_id and not self.site_url:
            message = "list requires explicit site URL"
            raise ValueError(message)
        if (self.app_id or self.governance_table) and not self.environment_id:
            message = "app and table require explicit environment ID"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class ProbeCall:
    """One fixed, read-only CLI operation with a structured argument array."""

    name: str
    tool: Literal["pac", "m365"]
    arguments: tuple[str, ...]


@dataclass(frozen=True)
class ProbeResponse:
    """Internal tool response; output must never enter a report or exception."""

    state: ResponseState
    output: str


class ProbeReport(BaseModel):
    """Sanitized probe statuses plus fail-closed deployment assessment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot: CapabilitySnapshot
    assessment: CapabilityAssessment
    probes: dict[str, CheckStatus]


def build_probe_calls(config: ProbeConfig) -> list[ProbeCall]:
    """Build metadata-only probes, never defaulting to an unselected resource."""
    calls = [
        ProbeCall("pac_identity", "pac", ("auth", "who")),
        ProbeCall("m365_identity", "m365", ("status", "--output", "json")),
        ProbeCall("environments", "pac", ("env", "list")),
    ]
    if config.environment_url:
        scope = ("--environment", config.environment_url)
        calls.extend(
            [
                ProbeCall("dataverse", "pac", ("env", "who", *scope)),
                ProbeCall("roles", "pac", ("env", "fetch", *scope, "--xml", ROLES_XML)),
                ProbeCall("team_roles", "pac", ("env", "fetch", *scope, "--xml", TEAM_ROLES_XML)),
                ProbeCall("solutions", "pac", ("solution", "list", *scope)),
                ProbeCall("audit_settings", "pac", ("env", "fetch", *scope, "--xml", AUDIT_XML)),
            ]
        )
    if config.environment_id:
        scope = ("--environmentName", config.environment_id, "--output", "json")
        calls.extend(
            [
                ProbeCall("tables", "m365", ("pp", "dataverse", "table", "list", *scope)),
                ProbeCall("connectors", "m365", ("pa", "connector", "list", *scope)),
                ProbeCall("apps", "m365", ("pa", "app", "list", *scope)),
            ]
        )
        if config.app_id:
            calls.append(
                ProbeCall(
                    "app_permissions",
                    "m365",
                    (
                        "pa",
                        "app",
                        "permission",
                        "list",
                        "--appName",
                        config.app_id,
                        *scope,
                    ),
                )
            )
        if config.governance_table:
            calls.append(
                ProbeCall(
                    "table_auditing",
                    "m365",
                    (
                        "pp",
                        "dataverse",
                        "table",
                        "get",
                        "--name",
                        config.governance_table,
                        *scope,
                    ),
                )
            )
    if config.team_id:
        calls.append(
            ProbeCall(
                "team",
                "m365",
                (
                    "teams",
                    "team",
                    "get",
                    "--id",
                    config.team_id,
                    "--output",
                    "json",
                ),
            )
        )
    if config.site_url:
        calls.append(
            ProbeCall(
                "lists",
                "m365",
                (
                    "spo",
                    "list",
                    "list",
                    "--webUrl",
                    config.site_url,
                    "--properties",
                    "Id,BaseTemplate,Hidden",
                    "--output",
                    "json",
                ),
            )
        )
        if config.list_id:
            calls.append(
                ProbeCall(
                    "list_controls",
                    "m365",
                    (
                        "spo",
                        "list",
                        "get",
                        "--webUrl",
                        config.site_url,
                        "--id",
                        config.list_id,
                        "--properties",
                        "Id,EnableVersioning,ReadSecurity,WriteSecurity,HasUniqueRoleAssignments",
                        "--withPermissions",
                        "--output",
                        "json",
                    ),
                )
            )
    if config.planner_plan_id:
        calls.append(
            ProbeCall(
                "planner",
                "m365",
                (
                    "planner",
                    "plan",
                    "get",
                    "--id",
                    config.planner_plan_id,
                    "--output",
                    "json",
                ),
            )
        )
    return calls


def run_cli(tool: str, arguments: tuple[str, ...]) -> ProbeResponse:  # noqa: PLR0911
    """Run a cached-sign-in CLI with a 30-second timeout and no shell interpolation."""
    if tool == "m365":
        npm_entry = shutil.which("m365.cmd")
        if not npm_entry:
            return ProbeResponse("unavailable", "")
        npm_directory = Path(npm_entry).parent
        script = npm_directory / "node_modules" / "@pnp" / "cli-microsoft365" / "dist" / "index.js"
        local_node = npm_directory / "node.exe"
        node = str(local_node) if local_node.is_file() else shutil.which("node")
        if not script.is_file() or not node:
            return ProbeResponse("unavailable", "")
        # Invoke the installed CLI itself, not a shim spawning Node with inherited pipes.
        command = [node, str(script), *arguments]
    elif tool == "pac":
        executable = shutil.which("pac")
        if not executable:
            return ProbeResponse("unavailable", "")
        command = [executable, *arguments]
    else:
        return ProbeResponse("unavailable", "")
    try:
        # Resolved local executables; fixed read-only operations, no shell.
        result = subprocess.run(  # noqa: S603 # nosec B603
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=CLI_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ProbeResponse("timeout", "")
    except OSError:
        return ProbeResponse("unavailable", "")
    if result.returncode:
        return ProbeResponse("error", "")
    return ProbeResponse("success", result.stdout)


def _delegated(tool: str, result: ProbeResponse) -> bool:
    if result.state != "success":
        return False
    if tool == "pac":
        user_type = re.search(r"^Type\s*:\s*User\s*$", result.output, re.MULTILINE | re.IGNORECASE)
        universal = re.search(
            r"^Type\s*:\s*UNIVERSAL\s*$", result.output, re.MULTILINE | re.IGNORECASE
        )
        user = re.search(r"^User\s*:\s*[^\s]+@[^\s]+\s*$", result.output, re.MULTILINE)
        return bool(user_type or (universal and user))
    try:
        status: object = json.loads(result.output)
    except ValueError:
        return False
    if not isinstance(status, dict):
        return False
    auth_type = cast("dict[str, object]", status).get("authType")
    return isinstance(auth_type, str) and auth_type in {"DeviceCode", "Browser"}


def collect_capabilities(
    config: ProbeConfig,
    *,
    runner: Callable[[str, tuple[str, ...]], ProbeResponse] = run_cli,
    now: datetime,
) -> ProbeReport:
    """Collect sanitized read observations; leave reviewed and human gates unresolved."""
    scope_ref = "scope-" + hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:24]
    probes: dict[str, CheckStatus] = {}
    checks: dict[CheckName, CapabilityCheck] = {}
    delegated: dict[str, bool] = {}
    mappings: dict[str, CheckName] = {
        "dataverse": "dataverse_access",
        "team": "existing_team_access",
        "list_controls": "sharepoint_list_access",
        "planner": "planner_access",
    }
    for call in build_probe_calls(config):
        identity = call.name in {"pac_identity", "m365_identity"}
        if not identity and not delegated.get(call.tool, False):
            status: CheckStatus = "unavailable"
        else:
            response = runner(call.tool, call.arguments)
            status = (
                "observed"
                if response.state == "success"
                else ("unavailable" if response.state == "unavailable" else "failed")
            )
            if identity:
                delegated[call.tool] = _delegated(call.tool, response)
                if not delegated[call.tool] and response.state == "success":
                    status = "failed"
        probes[call.name] = status
        check_name = mappings.get(call.name)
        if check_name:
            checks[check_name] = CapabilityCheck(
                status=status,
                scope_ref=scope_ref,
                observed_at=now,
            )
    checks["delegated_identity"] = CapabilityCheck(
        status="observed" if any(delegated.values()) else "unavailable",
        scope_ref=scope_ref,
        observed_at=now,
    )
    snapshot = CapabilitySnapshot(
        schema_version=1,
        scope_ref=scope_ref,
        collected_at=now,
        checks=checks,
    )
    return ProbeReport(
        snapshot=snapshot, assessment=assess_capabilities(snapshot, now=now), probes=probes
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Validate configuration, dry-run or export a sanitized live capability report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = (
            ProbeConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
            if args.config
            else ProbeConfig()
        )
    except OSError, ValueError, ValidationError:
        sys.stderr.write('{"error":"invalid_probe_configuration"}\n')
        return 2
    if args.dry_run:
        sys.stdout.write(
            json.dumps(
                {"mode": "dry_run", "probes": [call.name for call in build_probe_calls(config)]}
            )
            + "\n"
        )
        return 0
    report = collect_capabilities(config, now=datetime.now(UTC))
    rendered = report.model_dump_json(indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        except OSError:
            sys.stderr.write('{"error":"report_write_failed"}\n')
            return 2
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
