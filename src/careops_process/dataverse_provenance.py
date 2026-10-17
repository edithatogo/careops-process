"""Explicit-target synthetic service readback; never a live-corpus approval gate."""

from __future__ import annotations

import json
import re
import shutil

# Fixed local commands use argument arrays, no shell.
import subprocess  # nosec B404
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from careops_process.backfill_evidence import evidence_digest
from careops_process.outlook_dataverse_destination import (
    FIELD_MAPPING,
    PRIMARY_KEY,
    parse_readback,
    row_id,
    serialize_fact,
)

if TYPE_CHECKING:
    from careops_process.outlook_reconciliation import CanonicalMailFact

_TARGET = re.compile(r"https://[a-z0-9-]+\.crm[0-9]*\.dynamics\.com/?\Z")
_MAX_RESPONSE = 1_048_576
_CONTEXT = "app=dataverse-skills/1.16.0;skill=dv-query;agent=codex"
_SDK_READ = """
import json,sys
from PowerPlatform.Dataverse.client import DataverseClient
from PowerPlatform.Dataverse.core.config import OperationContext
from azure.identity import AzureCliCredential
try:
    args=json.load(sys.stdin)
    with DataverseClient(args['origin'],AzureCliCredential(),
                        context=OperationContext(args['context'])) as client:
        row=client.records.retrieve('cop_processevent',args['id'],select=args['columns'])
        result=dict(row)
    print(json.dumps(result,allow_nan=False))
except Exception:
    sys.exit(1)
"""


@dataclass(frozen=True, slots=True)
class SyntheticDestinationVerification:
    """Run-bound summary of actual reads, with no live acceptance or raw rows."""

    organization_id: str
    run_id: str
    row_count: int
    content_hash: str
    evidence_class: str = "synthetic_service_readback"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        """Do not carry a bearer credential through redirects."""
        return


def _access_token(origin: str) -> str:
    executable = shutil.which("az")
    if executable is None:
        raise ValueError
    result = subprocess.run(  # noqa: S603  # nosec B603
        [
            executable,
            "account",
            "get-access-token",
            "--resource",
            origin + "/",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    token = result.stdout.strip()
    if not token or any(character.isspace() for character in token):
        raise ValueError
    return token


def _read_json(url: str, token: str) -> dict[str, Any]:
    request = Request(  # noqa: S310 - URL constructed from validated HTTPS origin
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "User-Agent": "CareOps/1.0 (" + _CONTEXT + ")",
        },
    )
    with build_opener(_NoRedirect()).open(request, timeout=30) as response:
        if response.status != 200 or response.geturl() != url:  # noqa: PLR2004
            raise ValueError
        payload = response.read(_MAX_RESPONSE + 1)
    if len(payload) > _MAX_RESPONSE:
        raise ValueError
    result = json.loads(payload)
    if not isinstance(result, dict):
        raise TypeError
    return cast("dict[str, Any]", result)


def _retrieve_row(origin: str, identifier: str) -> dict[str, Any]:
    runtime = Path(__file__).resolve().parents[2] / "artifacts/alm/sdk-venv/Scripts/python.exe"
    result = subprocess.run(  # noqa: S603  # nosec B603
        [str(runtime), "-c", _SDK_READ],
        input=json.dumps(
            {
                "origin": origin,
                "id": identifier,
                "context": _CONTEXT,
                "columns": [PRIMARY_KEY, *[column for _, column in FIELD_MAPPING]],
            }
        ),
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )
    if len(result.stdout) > _MAX_RESPONSE:
        raise ValueError
    row = json.loads(result.stdout)
    if not isinstance(row, dict):
        raise TypeError
    return cast("dict[str, Any]", row)


def _invalid() -> None:
    raise ValueError


def _verified_row(
    row: dict[str, Any],
    identifier: str,
    organization_id: str,
) -> CanonicalMailFact:
    permitted = {
        PRIMARY_KEY,
        "@odata.context",
        "@odata.etag",
        "_organizationid_value",
        *[column for _, column in FIELD_MAPPING],
    }
    if not set(row).issubset(permitted) or row.get(PRIMARY_KEY) != identifier:
        _invalid()
    if row.get("_organizationid_value", organization_id) != organization_id:
        _invalid()
    return parse_readback({column: row[column] for _, column in FIELD_MAPPING})


def verify_synthetic_destination(
    *,
    environment_url: str,
    organization_id: str,
    user_id: str,
    run_id: str,
    facts: list[CanonicalMailFact],
) -> SyntheticDestinationVerification:
    """Requery WhoAmI and exact SDK primary keys with existing Azure CLI auth.

    No caller-supplied receipt, boolean or destination rows bypass these reads.
    This Developer-only adapter does not enable live closure. Its runtime is the
    existing ALM SDK environment; unavailable/expired auth fails without login.
    """
    try:
        if type(environment_url) is not str or _TARGET.fullmatch(environment_url) is None:
            _invalid()
        for identifier in (organization_id, user_id, run_id):
            if (
                type(identifier) is not str
                or str(UUID(identifier)) != identifier
                or not UUID(identifier).int
            ):
                _invalid()
        if not facts or len({fact.id for fact in facts}) != len(facts):
            _invalid()
        expected = [(fact, serialize_fact(fact)) for fact in facts]
        origin = environment_url.rstrip("/")
        token = _access_token(origin)
        identity = _read_json(origin + "/api/data/v9.2/WhoAmI", token)
        if identity.get("OrganizationId") != organization_id or identity.get("UserId") != user_id:
            _invalid()
        normalized: list[dict[str, Any]] = []
        for fact, values in expected:
            identifier = row_id(organization_id, run_id, fact.id)
            row = _retrieve_row(origin, identifier)
            actual = _verified_row(row, identifier, organization_id)
            if serialize_fact(actual) != values:
                _invalid()
            normalized.append(actual.model_dump())
        return SyntheticDestinationVerification(
            organization_id,
            run_id,
            len(normalized),
            evidence_digest(sorted(normalized, key=lambda item: item["id"])),
        )
    except (
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        OSError,
        subprocess.SubprocessError,
        HTTPError,
    ):
        message = "destination verification failed"
        raise ValueError(message) from None
