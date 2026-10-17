"""Mocked service-boundary checks, never actual Dataverse acceptance evidence."""

# Unit tests exercise the private I/O adapters independently of network access.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from typing import Any, Self, cast

import pytest

from careops_process import dataverse_provenance as provenance
from careops_process.backfill_evidence import close_reconciled_run
from careops_process.outlook_dataverse_destination import PRIMARY_KEY, row_id, serialize_fact
from careops_process.outlook_reconciliation import CanonicalMailFact, reconcile_outlook_evidence
from careops_process.report import build_closed_run_report
from tests.test_backfill_outlook_integration import configuration
from tests.test_outlook_reconciliation import inputs

ORG = "11111111-1111-4111-8111-111111111111"
USER = "22222222-2222-4222-8222-222222222222"
RUN = "33333333-3333-4333-8333-333333333333"
URL = "https://synthetic.crm6.dynamics.com"
FACT = CanonicalMailFact(
    id="mail_" + "a" * 64,
    activity="email_received",
    timestamp_utc="2026-01-01T00:00:00Z",
    source_system="outlook",
    object_ids=["conversation_" + "b" * 64],
)


def setup_service(monkeypatch: pytest.MonkeyPatch) -> tuple[list[str], dict[str, Any]]:
    """Replace only the internal I/O boundary with explicit synthetic responses."""
    calls: list[str] = []
    row = {**serialize_fact(FACT), PRIMARY_KEY: row_id(ORG, RUN, FACT.id), "@odata.etag": 'W/"1"'}
    replies: dict[str, Any] = {"identity": {"OrganizationId": ORG, "UserId": USER}, "row": row}

    def token(_url: str) -> str:
        return "synthetic-token"

    monkeypatch.setattr(provenance, "_access_token", token)

    def read(url: str, _token: str) -> dict[str, Any]:
        calls.append(url)
        return replies["identity"]

    monkeypatch.setattr(provenance, "_read_json", read)

    def retrieve(origin: str, identifier: str) -> dict[str, Any]:
        calls.append(origin + "/cop_processevents(" + identifier + ")")
        return replies["row"]

    monkeypatch.setattr(provenance, "_retrieve_row", retrieve)
    return calls, replies


def verify() -> provenance.SyntheticDestinationVerification:
    """Invoke the public API with pinned synthetic identity and expected data."""
    return provenance.verify_synthetic_destination(
        environment_url=URL, organization_id=ORG, user_id=USER, run_id=RUN, facts=[FACT]
    )


def test_verifier_reads_identity_and_exact_row_before_returning_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A supplied row list or boolean is not the service verification boundary."""
    calls, _replies = setup_service(monkeypatch)
    result = verify()
    assert len(calls) == 2  # noqa: PLR2004
    assert calls[0] == URL + "/api/data/v9.2/WhoAmI"
    assert row_id(ORG, RUN, FACT.id) in calls[1]
    assert result.row_count == 1
    assert result.evidence_class == "synthetic_service_readback"
    assert not hasattr(result, "dataverse_reconciled")


@pytest.mark.parametrize(
    "defect", ["organization", "user", "row_id", "row_org", "content", "nextlink", "extra"]
)
def test_service_identity_or_row_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
) -> None:
    """Reject mismatched context, content and collection-shaped responses."""
    _calls, replies = setup_service(monkeypatch)
    if defect == "organization":
        replies["identity"]["OrganizationId"] = RUN
    elif defect == "user":
        replies["identity"]["UserId"] = RUN
    elif defect == "row_id":
        replies["row"][PRIMARY_KEY] = RUN
    elif defect == "row_org":
        replies["row"]["_organizationid_value"] = RUN
    elif defect == "content":
        replies["row"]["cop_eventkey"] = "mail_" + "c" * 64
    else:
        replies["row"]["@odata.nextLink" if defect == "nextlink" else "secret"] = "protected"
    with pytest.raises(ValueError, match="destination verification failed") as error:
        verify()
    assert "protected" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "http://synthetic.crm6.dynamics.com",
        "https://example.com",
        URL + "/unexpected",
        URL + "?x=1",
        URL + ":443",
    ],
)
def test_invalid_target_is_rejected_before_auth(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    """No credential acquisition is attempted for an unbound endpoint."""

    def unexpected_auth(_url: str) -> str:
        pytest.fail("unexpected auth")

    monkeypatch.setattr(provenance, "_access_token", unexpected_auth)
    with pytest.raises(ValueError, match="destination verification failed"):
        provenance.verify_synthetic_destination(
            environment_url=url, organization_id=ORG, user_id=USER, run_id=RUN, facts=[FACT]
        )


def test_fixed_command_boundaries_use_explicit_target_and_sanitize_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Credentials remain in memory and child SDK input contains no bearer token."""
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((command, kwargs))
        return SimpleNamespace(stdout="synthetic-token\n" if len(calls) == 1 else '{"row":1}')

    def executable(_name: str) -> str:
        return "az.cmd"

    monkeypatch.setattr(provenance.shutil, "which", executable)
    monkeypatch.setattr(provenance.subprocess, "run", run)
    assert provenance._access_token(URL) == "synthetic-token"  # noqa: SLF001
    assert provenance._retrieve_row(URL, RUN) == {"row": 1}  # noqa: SLF001
    assert calls[0][0][4] == URL + "/"
    assert json.loads(cast("str", calls[1][1]["input"]))["origin"] == URL
    assert "synthetic-token" not in str(calls[1][1]["input"])
    assert all(call[1]["check"] is True for call in calls)

    def fail(_url: str) -> str:
        raise subprocess.CalledProcessError(1, ["secret-command"], stderr="protected-detail")

    monkeypatch.setattr(provenance, "_access_token", fail)
    with pytest.raises(ValueError, match="destination verification failed") as error:
        verify()
    assert "protected-detail" not in str(error.value)


@pytest.mark.parametrize("kind", ["ok", "redirect", "status", "oversized", "array"])
def test_identity_http_boundary_is_bounded_and_rejects_redirects(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """WhoAmI uses a fixed HTTPS request with redirects disabled and bounded JSON."""

    class Response:
        status = 403 if kind == "status" else 200

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def geturl(self) -> str:
            return "https://other.crm6.dynamics.com" if kind == "redirect" else URL

        def read(self, limit: int) -> bytes:
            assert limit == provenance._MAX_RESPONSE + 1  # noqa: SLF001
            if kind == "oversized":
                return b" " * limit
            return b"[]" if kind == "array" else b'{"OrganizationId":"synthetic"}'

    class Opener:
        def open(self, _request: object, *, timeout: int) -> Response:
            assert timeout == 30  # noqa: PLR2004
            return Response()

    def opener(handler: object) -> Opener:
        assert isinstance(handler, provenance._NoRedirect)  # noqa: SLF001
        return Opener()

    monkeypatch.setattr(provenance, "build_opener", opener)
    if kind == "ok":
        assert provenance._read_json(URL, "synthetic-token") == {"OrganizationId": "synthetic"}  # noqa: SLF001
    else:
        with pytest.raises((ValueError, TypeError)):
            provenance._read_json(URL, "synthetic-token")  # noqa: SLF001


def test_missing_credentials_and_malformed_sdk_output_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unavailable auth never starts login; malformed child results are rejected."""

    def missing(_name: str) -> None:
        return None

    monkeypatch.setattr(provenance.shutil, "which", missing)
    with pytest.raises(ValueError, match=r"^$"):
        provenance._access_token(URL)  # noqa: SLF001

    def run(_command: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout="[]")

    monkeypatch.setattr(provenance.subprocess, "run", run)
    with pytest.raises(TypeError):
        provenance._retrieve_row(URL, RUN)  # noqa: SLF001


@pytest.mark.parametrize("changes", [{"run_id": "invalid"}, {"facts": []}, {"facts": [FACT, FACT]}])
def test_invalid_run_or_expected_population_never_authenticates(
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, Any],
) -> None:
    """An explicit nonempty unique expected population precedes any credential read."""

    def unexpected(_url: str) -> str:
        pytest.fail("unexpected credential access")

    monkeypatch.setattr(provenance, "_access_token", unexpected)
    arguments: dict[str, Any] = {
        "environment_url": URL,
        "organization_id": ORG,
        "user_id": USER,
        "run_id": RUN,
        "facts": [FACT],
        **changes,
    }
    with pytest.raises(ValueError, match="destination verification failed"):
        provenance.verify_synthetic_destination(**arguments)


def test_token_whitespace_sdk_size_and_redirect_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed credentials and oversized child output cannot become a receipt."""

    def executable(_name: str) -> str:
        return "az.cmd"

    def run(_command: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout="bad token")

    monkeypatch.setattr(provenance.shutil, "which", executable)
    monkeypatch.setattr(provenance.subprocess, "run", run)
    with pytest.raises(ValueError, match=r"^$"):
        provenance._access_token(URL)  # noqa: SLF001

    def oversized(_command: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(stdout=" " * (provenance._MAX_RESPONSE + 1))  # noqa: SLF001

    monkeypatch.setattr(provenance.subprocess, "run", oversized)
    with pytest.raises(ValueError, match=r"^$"):
        provenance._retrieve_row(URL, RUN)  # noqa: SLF001
    assert provenance._NoRedirect().redirect_request() is None  # noqa: SLF001


def test_verified_expected_content_binds_synthetic_discovery_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mocked service verification and real discovery share one canonical fact digest."""
    setup_service(monkeypatch)
    verified = verify()
    fixture = inputs()
    old_identity = fixture["collector_facts"][0]["id"]
    fixture["collector_facts"][0].update(FACT.model_dump())
    fixture["destination_facts"] = [FACT.model_dump()]
    for page in fixture["pages"]:
        page["fact_ids"] = [FACT.id if key == old_identity else key for key in page["fact_ids"]]
    initial = reconcile_outlook_evidence(**fixture)
    replay = reconcile_outlook_evidence(**fixture)
    closed = close_reconciled_run(
        initial,
        replay,
        configuration(initial),
        run_id="synthetic-service-test",
        evidence_class="synthetic",
    )
    report = build_closed_run_report(
        initial["facts"],
        closed,
        pseudonym_secret="synthetic-test-key",  # noqa: S106
    )
    assert report["evidence"]["content_hash"] == verified.content_hash
    assert report["process_landscape"]["included_event_count"] == verified.row_count
    assert initial["dataverse_reconciled"] is False
    assert report["coverage_ledger"]["owner_validation_status"] == "pending"
