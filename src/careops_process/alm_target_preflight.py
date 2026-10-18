"""Read-only artifact/target prerequisites; never an import or portable-release gate."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil

# Fixed executable and argument arrays; no shell.
import subprocess  # nosec B404
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn, cast
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from defusedxml import ElementTree

if TYPE_CHECKING:
    # Annotation only; runtime parsing uses defusedxml.
    from xml.etree.ElementTree import Element  # nosec B405

_TARGET = re.compile(r"https://[a-z0-9-]+\.crm[0-9]*\.dynamics\.com/?\Z")
_FIELDS = {
    "environment_url",
    "organization_id",
    "user_id",
    "environment_id",
    "artifact_sha256",
    "decision",
    "reviewed_at",
}
_LIMIT = 1_048_576
_MAX_FILES = 5000
_ICON_ID = "953b9fac-1e5e-e611-80d6-00155ded156f"
_SDK = """
import json,sys
from PowerPlatform.Dataverse.client import DataverseClient
from PowerPlatform.Dataverse.core.config import OperationContext
from azure.identity import AzureCliCredential
try:
 a=json.load(sys.stdin)
 with DataverseClient(a['origin'],AzureCliCredential(),context=OperationContext(
  'app=dataverse-skills/1.16.0;skill=dv-solution;agent=codex')) as c:
  def rows(table,flt,cols):
   return [dict(r) for r in c.records.list(table,filter=flt,select=cols,top=3)]
  def solution(name,version):
   rs=rows('solution',"uniquename eq '"+name+"'",['solutionid','version','ismanaged'])
   return rs if len(rs)==1 and rs[0]['ismanaged'] and rs[0]['version']==version else []
  out={'dependencies':[],'roles':[]}
  for name in sorted(a['dependencies']):
   if name=='icon':
    ss=solution('AppModuleWebResources','2.5')
    rr=rows('webresource',"name eq 'msdyn_/Images/AppModule_Default_Icon.png'",['webresourceid'])
    if len(rr)==1 and rr[0]['webresourceid']!='953b9fac-1e5e-e611-80d6-00155ded156f': rr=[]
    typ=61;key='webresourceid'
   else:
    ss=solution('msdyn_AppFrameworkInfraExtensions','1.0.0.20')
    anchor=solution('PowerAppsAppFramework_Anchor','1.0.0.26')
    if not anchor: ss=[]
    rr=rows('settingdefinition',"uniquename eq 'AppChannel'",['settingdefinitionid'])
    typ=10094;key='settingdefinitionid'
   members=[]
   if len(rr)==1 and len(ss)==1:
    members=rows('solutioncomponent','objectid eq '+rr[0][key]+
     ' and componenttype eq '+str(typ)+' and _solutionid_value eq '+ss[0]['solutionid'],
     ['objectid','componenttype','_solutionid_value'])
   out['dependencies'].append({'name':name,'count':len(rr),'matched':len(rr)==1,
    'version_ok':len(ss)==1,'membership':len(members)==1})
  for tid in sorted(a['roles']):
   template=c.records.retrieve('roletemplate',tid,select=['name'])
   rs=rows('role','_roletemplateid_value eq '+tid,['roleid','_businessunitid_value'])
   root=False
   if len(rs)==1:
    bu=c.records.retrieve('businessunit',rs[0]['_businessunitid_value'],
     select=['_parentbusinessunitid_value'])
    root=bu is not None and bu.get('_parentbusinessunitid_value') is None
   out['roles'].append({'template_id':tid,'name':template['name'] if template else '',
    'count':len(rs),'root_business_unit':root})
 print(json.dumps(out,allow_nan=False))
except Exception:
 sys.exit(1)
"""


def _fail() -> NoReturn:
    msg = "Target preflight failed; inspect prerequisites privately."
    raise ValueError(msg)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return


def _token(resource: str) -> str:
    exe = shutil.which("az")
    if exe is None:
        _fail()
    result = subprocess.run(  # noqa: S603  # nosec B603
        [
            str(exe),
            "account",
            "get-access-token",
            "--resource",
            resource,
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=40,
    )
    token = result.stdout.strip()
    if not token or any(c.isspace() for c in token):
        _fail()
    return token


def _read(url: str, token: str) -> dict[str, Any]:
    request = Request(  # noqa: S310 - fixed management or validated Dynamics HTTPS origin
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "User-Agent": "CareOps/1.0 (app=dataverse-skills/1.16.0;skill=dv-solution;agent=codex)",
        },
    )
    with build_opener(_NoRedirect()).open(request, timeout=30) as response:
        if response.status != 200 or response.geturl() != url:  # noqa: PLR2004
            _fail()
        payload = response.read(_LIMIT + 1)
    if len(payload) > _LIMIT:
        _fail()
    result = json.loads(payload)
    if not isinstance(result, dict):
        _fail()
    return cast("dict[str, Any]", result)


def _dependency_key(dependency: Element) -> str:
    if [child.tag for child in dependency] != ["Required", "Dependent"]:
        _fail()
    if len(dependency.findall("Required")) != 1 or len(dependency.findall("Dependent")) != 1:
        _fail()
    required = dependency.findall("Required")[0]
    if (
        dependency.attrib
        or (dependency.text or "").strip()
        or [child.tag for child in required] != ["package"]
        or len(dependency.findall("Dependent")[0])
    ):
        _fail()
    if (
        required.get("type") == "61"
        and required.get("schemaName") == ("msdyn_/Images/AppModule_Default_Icon.png")
        and required.get("solution") == "AppModuleWebResources (2.5)"
    ):
        key = "icon"
        package_version = "2.5"
    elif (
        required.get("type") == "SettingDefinition"
        and required.get("id.uniquename") == "AppChannel"
        and required.get("solution") == "msdyn_AppFrameworkInfraExtensions (1.0.0.20)"
    ):
        key = "channel"
        package_version = "1.0.0.25"
    else:
        _fail()
    packages = required.findall("package")
    if len(packages) != 1 or packages[0].get("version") != package_version:
        _fail()
    return key


def _container(
    parent: Element, name: str, child_tag: str, *, optional: bool = False
) -> list[Element]:
    """Validate a prerequisite container before extracting its known child nodes."""
    matches = parent.findall(name)
    if not matches and optional:
        return []
    if len(matches) != 1:
        _fail()
    container = matches[0]
    if container.attrib or (container.text or "").strip():
        _fail()
    children = list(container)
    if any(child.tag != child_tag or (child.tail or "").strip() for child in children):
        _fail()
    return children


def _declared_roles(customizations: Element) -> set[str]:
    roles: set[str] = set()
    for app in _container(customizations, "AppModules", "AppModule", optional=True):
        for role in _container(app, "AppModuleRoleMaps", "Role"):
            if set(role.attrib) != {"id"} or len(role) or (role.text or "").strip():
                _fail()
            identifier = str(UUID(role.get("id", "").strip("{}")))
            if identifier in roles:
                _fail()
            roles.add(identifier)
    return roles


def _requirements(snapshot: bytes) -> tuple[set[str], set[str]]:
    with zipfile.ZipFile(io.BytesIO(snapshot)) as package:
        if (
            len(package.infolist()) > _MAX_FILES
            or sum(x.file_size for x in package.infolist()) > 16 * _LIMIT
        ):
            _fail()
        if package.testzip() is not None:
            _fail()
        for name in ("solution.xml", "customizations.xml"):
            if package.namelist().count(name) != 1 or package.getinfo(name).file_size > _LIMIT:
                _fail()
        manifest = ElementTree.fromstring(package.read("solution.xml"))
        customizations = ElementTree.fromstring(package.read("customizations.xml"))
    dependencies: set[str] = set()
    manifests = manifest.findall("SolutionManifest")
    if (
        manifest.tag != "ImportExportXml"
        or customizations.tag != "ImportExportXml"
        or len(manifests) != 1
    ):
        _fail()
    for dependency in _container(manifests[0], "MissingDependencies", "MissingDependency"):
        key = _dependency_key(dependency)
        if key in dependencies:
            _fail()
        dependencies.add(key)
    roles = _declared_roles(customizations)
    if "icon" in dependencies and {
        node.text for node in customizations.findall("AppModules/AppModule/WebResourceId")
    } != {_ICON_ID}:
        _fail()
    return dependencies, roles


def _identity(snapshot: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(snapshot)) as package:
        root = ElementTree.fromstring(package.read("solution.xml"))
    manifests = root.findall("SolutionManifest")
    if len(manifests) != 1:
        _fail()
    manifest = manifests[0]
    result = {key: manifest.findtext(key, "") for key in ("UniqueName", "Version", "Managed")}
    if (
        not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", result["UniqueName"])
        or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", result["Version"])
        or result["Managed"] not in {"0", "1"}
        or any(len(manifest.findall(key)) != 1 for key in result)
    ):
        _fail()
    return result


def _observe(binding: dict[str, Any], dependencies: set[str], roles: set[str]) -> dict[str, Any]:
    origin = binding["environment_url"].rstrip("/")
    identity = _read(origin + "/api/data/v9.2/WhoAmI", _token(origin + "/"))
    if identity.get("OrganizationId") != binding["organization_id"] or (
        identity.get("UserId") != binding["user_id"]
    ):
        _fail()
    management = _read(
        "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/environments/"
        + binding["environment_id"]
        + "?api-version=2020-10-01",
        _token("https://service.powerapps.com/"),
    )
    linked = management["properties"]["linkedEnvironmentMetadata"]["instanceUrl"].rstrip("/")
    if linked != origin or management["name"] != binding["environment_id"]:
        _fail()
    runtime = Path(__file__).resolve().parents[2] / "artifacts/alm/sdk-venv/Scripts/python.exe"
    result = subprocess.run(  # noqa: S603  # nosec B603
        [str(runtime), "-c", _SDK],
        input=json.dumps(
            {"origin": origin, "dependencies": sorted(dependencies), "roles": sorted(roles)}
        ),
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    if len(result.stdout) > _LIMIT:
        _fail()
    observed = json.loads(result.stdout)
    observed.update(
        organization_id=identity["OrganizationId"],
        user_id=identity["UserId"],
        environment_id=management["name"],
    )
    return observed


def _check_observations(
    observed: dict[str, Any], binding: dict[str, Any], dependencies: set[str], roles: set[str]
) -> None:
    if any(observed[k] != binding[k] for k in ("organization_id", "user_id", "environment_id")):
        _fail()
    facts = observed["dependencies"]
    if len(facts) != len(dependencies) or {x["name"] for x in facts} != dependencies:
        _fail()
    for fact in facts:
        if fact["count"] != 1 or not all(
            fact[k] is True for k in ("matched", "membership", "version_ok")
        ):
            _fail()
    role_facts = observed["roles"]
    if len(role_facts) != len(roles) or {x["template_id"] for x in role_facts} != roles:
        _fail()
    for role in role_facts:
        if (
            role["count"] != 1
            or role["root_business_unit"] is not True
            or role["name"] not in {"System Administrator", "System Customizer"}
        ):
            _fail()


def assess_target(artifact: Path, binding: dict[str, Any]) -> dict[str, Any]:
    """Requery target prerequisites; private binding JSON never supplies service evidence.

    Requires an exact reviewed artifact digest and a private pinned target sidecar.
    Observations are point-in-time only. No credentials are stored or login attempted.
    """
    try:
        if set(binding) != _FIELDS or _TARGET.fullmatch(binding["environment_url"]) is None:
            _fail()
        for key in ("organization_id", "user_id", "environment_id"):
            if str(UUID(binding[key])) != binding[key] or not UUID(binding[key]).int:
                _fail()
        when = datetime.fromisoformat(binding["reviewed_at"])
        age = datetime.now(UTC) - when
        if age < timedelta(0) or age > timedelta(minutes=15):
            _fail()
        if artifact.is_symlink() or artifact.stat().st_size > 16 * _LIMIT:
            _fail()
        snapshot = artifact.read_bytes()
        digest = hashlib.sha256(snapshot).hexdigest()
        if (
            digest != binding["artifact_sha256"]
            or binding["decision"] != "retain-existing-restrictions"
        ):
            _fail()
        dependencies, roles = _requirements(snapshot)
        identity = _identity(snapshot)
        _check_observations(_observe(binding, dependencies, roles), binding, dependencies, roles)
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != digest or (
            datetime.now(UTC) - when > timedelta(minutes=15)
        ):
            _fail()
        return {
            "status": "target-prerequisites-observed",
            "artifact_sha256": digest,
            "target_binding_sha256": hashlib.sha256(
                json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "solution": identity,
            "observed_at": datetime.now(UTC).isoformat(),
            "dependency_count": len(dependencies),
            "role_count": len(roles),
            "import_rights": "unverified",
            "recovery": "unverified",
            "portable_validation": "unchanged-strict-default",
        }
    except Exception:  # noqa: BLE001 - public boundary suppresses protected service diagnostics
        _fail()
