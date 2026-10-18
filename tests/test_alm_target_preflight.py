"""Synthetic preflight boundary tests; mocks are not target acceptance evidence."""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404 - fixed Python test subprocess
import sys
import zipfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from careops_process import alm_target_preflight as preflight

if TYPE_CHECKING:
    from pathlib import Path

ORG = "11111111-1111-4111-8111-111111111111"
USER = "22222222-2222-4222-8222-222222222222"
ENV = "33333333-3333-4333-8333-333333333333"
REAL_OBSERVE = preflight._observe  # noqa: SLF001 - exercise internal I/O guards separately

_SDK_STUB = """
import sys,types
for name in ['PowerPlatform','PowerPlatform.Dataverse','PowerPlatform.Dataverse.client',
             'PowerPlatform.Dataverse.core','PowerPlatform.Dataverse.core.config',
             'azure','azure.identity']:
 sys.modules[name]=types.ModuleType(name)
class Records:
 def list(self,table,**kwargs):
  return [{'roleid':'synthetic','_businessunitid_value':'synthetic-bu'}]
 def retrieve(self,table,identifier,**kwargs):
  return {'name':'System Customizer'} if table=='roletemplate' else BUSINESS_UNIT
class Client:
 def __init__(self,*args,**kwargs): self.records=Records()
 def __enter__(self): return self
 def __exit__(self,*args): pass
sys.modules['PowerPlatform.Dataverse.client'].DataverseClient=Client
sys.modules['PowerPlatform.Dataverse.core.config'].OperationContext=lambda x:x
sys.modules['azure.identity'].AzureCliCredential=lambda:None
"""


@pytest.mark.parametrize(
    ("business_unit", "expected"),
    [
        ({}, False),
        ({"_parentbusinessunitid_value": None}, True),
        ({"_parentbusinessunitid_value": "synthetic-parent"}, False),
    ],
)
def test_embedded_sdk_requires_explicit_root_parent(
    business_unit: dict[str, str | None], *, expected: bool
) -> None:
    """Execute the real SDK subprocess body; missing selected fields are not root proof."""
    script = "BUSINESS_UNIT=" + repr(business_unit) + "\n" + _SDK_STUB + preflight._SDK  # noqa: SLF001
    result = subprocess.run(  # noqa: S603  # nosec B603
        [sys.executable, "-c", script],
        input=json.dumps(
            {"origin": "https://fixture.crm6.dynamics.com", "dependencies": [], "roles": [ORG]}
        ),
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert json.loads(result.stdout)["roles"][0]["root_business_unit"] is expected


@pytest.fixture
def evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    """Provide one fixed package and synthetic internal service observations."""
    artifact = tmp_path / "app.zip"
    with zipfile.ZipFile(artifact, "w") as package:
        package.writestr(
            "solution.xml",
            "<ImportExportXml><SolutionManifest>"
            "<UniqueName>fixture</UniqueName><Version>1.0.0.0</Version><Managed>0</Managed>"
            "<MissingDependencies/></SolutionManifest></ImportExportXml>",
        )
        package.writestr("customizations.xml", "<ImportExportXml/>")
    binding: dict[str, Any] = {
        "environment_url": "https://fixture.crm6.dynamics.com",
        "organization_id": ORG,
        "user_id": USER,
        "environment_id": ENV,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "decision": "retain-existing-restrictions",
        "reviewed_at": datetime.now(UTC).isoformat(),
    }

    def observation(*_args: object) -> dict[str, Any]:
        return {
            "organization_id": ORG,
            "user_id": USER,
            "environment_id": ENV,
            "dependencies": [],
            "roles": [],
        }

    monkeypatch.setattr(preflight, "_observe", observation)
    return artifact, binding


def test_report_never_grants_import(evidence: tuple[Path, dict[str, Any]]) -> None:
    """Report explicitly leaves import and recovery unverified."""
    artifact, binding = evidence
    result = preflight.assess_target(artifact, binding)
    assert result["status"] == "target-prerequisites-observed"
    assert result["import_rights"] == "unverified"
    assert result["recovery"] == "unverified"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("organization_id", "44444444-4444-4444-8444-444444444444"),
        ("environment_id", "44444444-4444-4444-8444-444444444444"),
        ("user_id", "44444444-4444-4444-8444-444444444444"),
        ("reviewed_at", "2020-01-01T00:00:00+00:00"),
        ("artifact_sha256", "0" * 64),
        ("decision", "approve-ordinary-users"),
    ],
)
def test_binding_drift_fails(evidence: tuple[Path, dict[str, Any]], field: str, value: str) -> None:
    """Reject cross-target, stale, changed artifact and widened-access sidecars."""
    artifact, binding = evidence
    binding[field] = value
    with pytest.raises(ValueError, match="preflight"):
        preflight.assess_target(artifact, binding)


def test_receipt_cannot_replace_service(
    evidence: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caller receipts and service failures cannot produce readiness."""
    artifact, binding = evidence
    binding["observations"] = {"approved": True}
    with pytest.raises(ValueError, match="preflight"):
        preflight.assess_target(artifact, binding)
    binding.pop("observations")

    def unavailable(*_args: object) -> dict[str, Any]:
        msg = "private service failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(preflight, "_observe", unavailable)
    with pytest.raises(ValueError, match="preflight") as error:
        preflight.assess_target(artifact, binding)
    assert "private service failure" not in str(error.value)


@pytest.mark.parametrize("bad", ["missing", "duplicate", "membership", "version"])
def test_dependency_proof_required(
    evidence: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    """Require unique exact membership and pinned version evidence."""
    artifact, binding = evidence
    observation = {
        "organization_id": ORG,
        "user_id": USER,
        "environment_id": ENV,
        "dependencies": [
            {
                "name": "icon",
                "matched": bad != "missing",
                "count": 2 if bad == "duplicate" else 1,
                "membership": bad != "membership",
                "version_ok": bad != "version",
            }
        ],
        "roles": [],
    }

    def requirements(*_args: object) -> tuple[set[str], set[str]]:
        return {"icon"}, set()

    def observed(*_args: object) -> dict[str, Any]:
        return observation

    monkeypatch.setattr(preflight, "_requirements", requirements)
    monkeypatch.setattr(preflight, "_observe", observed)
    with pytest.raises(ValueError, match="preflight"):
        preflight.assess_target(artifact, binding)


@pytest.mark.parametrize("bad", ["duplicate", "child-bu", "widened", "wrong-template"])
def test_role_proof_is_restricted(
    evidence: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    """Target role facts must preserve one exact restricted root-role candidate."""
    artifact, binding = evidence

    def requirements(*_args: object) -> tuple[set[str], set[str]]:
        return set(), {ORG}

    def observation(*_args: object) -> dict[str, Any]:
        return {
            "organization_id": ORG,
            "user_id": USER,
            "environment_id": ENV,
            "dependencies": [],
            "roles": [
                {
                    "template_id": USER if bad == "wrong-template" else ORG,
                    "name": "Basic User" if bad == "widened" else "System Customizer",
                    "count": 2 if bad == "duplicate" else 1,
                    "root_business_unit": bad != "child-bu",
                }
            ],
        }

    monkeypatch.setattr(preflight, "_requirements", requirements)
    monkeypatch.setattr(preflight, "_observe", observation)
    with pytest.raises(ValueError, match="preflight"):
        preflight.assess_target(artifact, binding)


def test_artifact_changed_during_reads(
    evidence: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No report is emitted if the artifact changed while service reads ran."""
    artifact, binding = evidence

    def observation(*_args: object) -> dict[str, Any]:
        artifact.write_bytes(b"changed")
        return {
            "organization_id": ORG,
            "user_id": USER,
            "environment_id": ENV,
            "dependencies": [],
            "roles": [],
        }

    monkeypatch.setattr(preflight, "_observe", observation)
    with pytest.raises(ValueError, match="preflight"):
        preflight.assess_target(artifact, binding)


@pytest.mark.parametrize("bad", ["principal", "environment", "origin"])
def test_live_identity_guards_precede_sdk_reads(
    evidence: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    """Stop before dependency/role reads when actual principal or environment drifts."""
    _, binding = evidence

    def token(_resource: str) -> str:
        return "synthetic"

    def read(url: str, _token: str) -> dict[str, Any]:
        if url.endswith("WhoAmI"):
            return {"OrganizationId": ORG, "UserId": ORG if bad == "principal" else USER}
        return {
            "name": ORG if bad == "environment" else ENV,
            "properties": {
                "linkedEnvironmentMetadata": {
                    "instanceUrl": "https://other.crm6.dynamics.com"
                    if bad == "origin"
                    else binding["environment_url"]
                }
            },
        }

    monkeypatch.setattr(preflight, "_token", token)
    monkeypatch.setattr(preflight, "_read", read)
    # This invokes the real I/O orchestration, not the fixture's observation replacement.
    with pytest.raises(ValueError, match="preflight"):
        REAL_OBSERVE(binding, set(), set())


@pytest.mark.parametrize("bad", ["dependency-shape", "unknown-dependency", "duplicate-manifest"])
def test_package_requirements_fail_closed(evidence: tuple[Path, dict[str, Any]], bad: str) -> None:
    """Malformed and unsupported declarations cannot become a readiness report."""
    artifact, binding = evidence
    with zipfile.ZipFile(artifact) as archive:
        xml = archive.read("solution.xml").decode()
    if bad == "dependency-shape":
        xml = xml.replace(
            "<MissingDependencies/>",
            '<MissingDependencies><MissingDependency><Required type="61"/>'
            "</MissingDependency></MissingDependencies>",
        )
    elif bad == "unknown-dependency":
        xml = xml.replace(
            "<MissingDependencies/>",
            '<MissingDependencies><MissingDependency><Required type="999"/>'
            "<Dependent/></MissingDependency></MissingDependencies>",
        )
    else:
        xml = xml.replace("</ImportExportXml>", "<SolutionManifest/></ImportExportXml>")
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("solution.xml", xml)
        archive.writestr("customizations.xml", "<ImportExportXml/>")
    binding["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="preflight"):
        preflight.assess_target(artifact, binding)


@pytest.mark.parametrize(
    "bad",
    [
        "unknown-dependency-child",
        "duplicate-dependencies",
        "missing-dependencies",
        "unknown-role-child",
        "duplicate-role-maps",
        "missing-role-maps",
        "unknown-app-child",
        "duplicate-app-container",
        "nested-role",
    ],
)
def test_unknown_or_ambiguous_prerequisite_containers(
    evidence: tuple[Path, dict[str, Any]], bad: str
) -> None:
    """Unknown tags cannot erase declared prerequisite or sharing obligations."""
    artifact, binding = evidence
    with zipfile.ZipFile(artifact) as archive:
        manifest = archive.read("solution.xml").decode()
    customizations = "<ImportExportXml/>"
    if bad == "unknown-dependency-child":
        manifest = manifest.replace(
            "<MissingDependencies/>",
            "<MissingDependencies>"
            '<UnexpectedDependency><Required type="999"/><Dependent/></UnexpectedDependency>'
            "</MissingDependencies>",
        )
    elif bad == "duplicate-dependencies":
        manifest = manifest.replace("<MissingDependencies/>", "<MissingDependencies/>" * 2)
    elif bad == "missing-dependencies":
        manifest = manifest.replace("<MissingDependencies/>", "")
    else:
        role_maps = "<AppModuleRoleMaps/>"
        if bad == "unknown-role-child":
            role_maps = '<AppModuleRoleMaps><UnexpectedRole id="synthetic"/></AppModuleRoleMaps>'
        elif bad == "duplicate-role-maps":
            role_maps *= 2
        elif bad == "missing-role-maps":
            role_maps = ""
        elif bad == "nested-role":
            role_maps = (
                f'<AppModuleRoleMaps><Role id="{ORG}"><Unexpected/></Role></AppModuleRoleMaps>'
            )
        app = f"<AppModule><UniqueName>fixtureapp</UniqueName>{role_maps}</AppModule>"
        if bad == "unknown-app-child":
            app += "<UnexpectedApp/>"
        container = f"<AppModules>{app}</AppModules>"
        if bad == "duplicate-app-container":
            container *= 2
        customizations = f"<ImportExportXml>{container}</ImportExportXml>"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("solution.xml", manifest)
        archive.writestr("customizations.xml", customizations)
    binding["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="preflight"):
        preflight._requirements(artifact.read_bytes())  # noqa: SLF001
