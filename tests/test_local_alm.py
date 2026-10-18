"""Offline release safeguards with synthetic solution and package fixtures."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from careops_process import local_alm


@pytest.fixture
def solution(tmp_path: Path) -> Path:
    """Create a minimal portable unpacked solution."""
    source = tmp_path / "source"
    (source / "Other").mkdir(parents=True)
    (source / "Other/Solution.xml").write_text(
        "<ImportExportXml><SolutionManifest><UniqueName>fixture</UniqueName>"
        "<Version>1.0.0.0</Version><Managed>0</Managed>"
        "<Publisher><CustomizationPrefix>cop</CustomizationPrefix></Publisher>"
        "<RootComponents/><MissingDependencies/></SolutionManifest></ImportExportXml>",
        encoding="utf-8",
    )
    (source / "Other/Customizations.xml").write_text("<ImportExportXml/>", encoding="utf-8")
    return source


def test_structure_version_and_missing_references(solution: Path) -> None:
    """Reject malformed versions, missing source references and dependency declarations."""
    assert local_alm.validate_solution(solution).version == "1.0.0.0"
    manifest = solution / "Other/Solution.xml"
    original = manifest.read_text(encoding="utf-8")
    for broken in (
        original.replace("1.0.0.0", "1.0"),
        original.replace(
            "<RootComponents/>",
            '<RootComponents><RootComponent type="1" schemaName="cop_missing"/></RootComponents>',
        ),
        original.replace(
            "<MissingDependencies/>",
            "<MissingDependencies><MissingDependency/></MissingDependencies>",
        ),
        "<!DOCTYPE a [<!ENTITY x SYSTEM 'file:///private'>]><a>&x;</a>",
    ):
        manifest.write_text(broken, encoding="utf-8")
        with pytest.raises(ValueError, match=r"Invalid|missing|dependencies|unsafe"):
            local_alm.validate_solution(solution)
    manifest.write_text(original, encoding="utf-8")
    (solution / "Other/Customizations.xml").unlink()
    with pytest.raises(ValueError, match="required"):
        local_alm.validate_solution(solution)


@pytest.mark.parametrize(
    "value",
    [
        "https://tenant.crm.dynamics.com",
        "Bearer abc",
        '"client_secret": "hidden"',
        '"ConnectionId": "bound"',
    ],
)
def test_portability_diagnostics_do_not_echo_values(solution: Path, value: str) -> None:
    """Detect protected or bound content without copying it into errors."""
    (solution / "config.json").write_text(value, encoding="utf-8")
    with pytest.raises(ValueError, match="portable") as error:
        local_alm.validate_solution(solution)
    assert value not in str(error.value)


def fake_pac(command: list[str]) -> None:
    """Create a synthetic package as the injected offline PAC adapter."""
    target = Path(command[command.index("--zipfile") + 1])
    source = Path(command[command.index("--folder") + 1])
    with zipfile.ZipFile(target, "w") as archive:
        archive.write(source / "Other/Solution.xml", "solution.xml")
        archive.write(source / "Other/Customizations.xml", "customizations.xml")


@pytest.fixture
def app_solution(solution: Path) -> Path:
    """Build tenant-neutral PAC-shaped app, navigation, form and view sources."""
    files = {
        "Entities/cop_Intake/Entity.xml": "<Entity><Name>cop_intake</Name></Entity>",
        "Entities/cop_Intake/FormXml/main/{11111111-1111-1111-1111-111111111111}.xml": (
            "<forms><systemform><formid>{11111111-1111-1111-1111-111111111111}"
            "</formid></systemform></forms>"
        ),
        "Entities/cop_Intake/SavedQueries/{22222222-2222-2222-2222-222222222222}.xml": (
            "<savedqueries><savedquery><savedqueryid>{22222222-2222-2222-2222-222222222222}"
            "</savedqueryid></savedquery></savedqueries>"
        ),
        "AppModules/cop_app/AppModule.xml": (
            "<AppModule><UniqueName>cop_app</UniqueName><AppModuleComponents>"
            '<AppModuleComponent type="1" schemaName="cop_intake"/>'
            '<AppModuleComponent type="60" id="{11111111-1111-1111-1111-111111111111}"/>'
            '<AppModuleComponent type="26" id="{22222222-2222-2222-2222-222222222222}"/>'
            '<AppModuleComponent type="62" schemaName="cop_app"/>'
            "</AppModuleComponents><AppModuleRoleMaps/><appsettings>"
            '<appsetting settingdefinitionid.uniquename="AppChannel">'
            "<iscustomizable>1</iscustomizable><value>1</value>"
            "</appsetting></appsettings></AppModule>"
        ),
        "AppModuleSiteMaps/cop_app/AppModuleSiteMap.xml": (
            "<AppModuleSiteMap><SiteMapUniqueName>cop_app</SiteMapUniqueName><SiteMap>"
            '<Area Id="area"><Group Id="group"><SubArea Id="list" Entity="cop_intake"/>'
            "</Group></Area></SiteMap></AppModuleSiteMap>"
        ),
    }
    for name, content in files.items():
        path = solution / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    manifest = solution / "Other/Solution.xml"
    manifest.write_text(
        manifest.read_text().replace(
            "<RootComponents/>",
            '<RootComponents><RootComponent type="1" schemaName="cop_intake"/>'
            '<RootComponent type="62" schemaName="cop_app"/>'
            '<RootComponent type="80" schemaName="cop_app"/></RootComponents>',
        )
    )
    return solution


def test_pac_app_references_and_typed_setting(app_solution: Path) -> None:
    """A minimal app with fully resolved portable references is supported."""
    assert local_alm.validate_solution(app_solution).name == "fixture"


@pytest.mark.parametrize(
    ("tag", "identifier"), [("Area", "area"), ("Group", "group"), ("SubArea", "list")]
)
@pytest.mark.parametrize("invalid", ["empty", "missing", "duplicate"])
def test_navigation_identity_is_required_and_unique(
    app_solution: Path, tag: str, identifier: str, invalid: str
) -> None:
    """Sitemap identity collisions cannot silently select the wrong navigation node."""
    path = app_solution / "AppModuleSiteMaps/cop_app/AppModuleSiteMap.xml"
    text = path.read_text()
    if invalid == "empty":
        text = text.replace(f'Id="{identifier}"', 'Id=""')
    elif invalid == "missing":
        text = text.replace(f' Id="{identifier}"', "")
    elif tag == "SubArea":
        text = text.replace(
            '<SubArea Id="list" Entity="cop_intake"/>',
            '<SubArea Id="list" Entity="cop_intake"/>' * 2,
        )
    elif tag == "Group":
        text = text.replace("</Group>", '</Group><Group Id="group"/>')
    else:
        text = text.replace("</Area>", '</Area><Area Id="area"/>')
    path.write_text(text)
    with pytest.raises(ValueError, match="navigation identity"):
        local_alm.validate_solution(app_solution)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-root",
        "duplicate-component",
        "orphan-app",
        "missing-form",
        "duplicate-map",
        "secret-comment",
    ],
)
def test_app_duplicate_missing_and_secret_paths(app_solution: Path, mutation: str) -> None:
    """Reject ambiguous identities, orphan components and secrets hidden in XML comments."""
    app = app_solution / "AppModules/cop_app/AppModule.xml"
    manifest = app_solution / "Other/Solution.xml"
    if mutation == "duplicate-root":
        manifest.write_text(
            manifest.read_text().replace(
                '<RootComponent type="80" schemaName="cop_app"/>',
                '<RootComponent type="80" schemaName="cop_app"/>' * 2,
            )
        )
    elif mutation == "duplicate-component":
        app.write_text(
            app.read_text().replace(
                '<AppModuleComponent type="1" schemaName="cop_intake"/>',
                '<AppModuleComponent type="1" schemaName="cop_intake"/>' * 2,
            )
        )
    elif mutation == "orphan-app":
        manifest.write_text(manifest.read_text().replace('type="80"', 'type="62"'))
    elif mutation == "missing-form":
        next((app_solution / "Entities").glob("*/FormXml/*/*.xml")).unlink()
    elif mutation == "duplicate-map":
        path = app_solution / "AppModuleSiteMaps/cop_app/AppModuleSiteMap.xml"
        path.write_text(path.read_text().replace("</SiteMap>", "</SiteMap><SiteMap/>"))
    else:
        app.write_text(
            app.read_text().replace("<UniqueName>", "<!-- Bearer synthetic-secret --><UniqueName>")
        )
    with pytest.raises(ValueError, match=r"[Dd]uplicate|[Mm]issing|references|portable|single"):
        local_alm.validate_solution(app_solution)


@pytest.mark.parametrize(
    ("relative", "old", "new"),
    [
        ("Other/Solution.xml", 'type="80"', 'type="300"'),
        ("Other/Solution.xml", '<RootComponent type="80" schemaName="cop_app"/>', ""),
        ("AppModules/cop_app/AppModule.xml", "<UniqueName>cop_app", "<UniqueName>cop_wrong"),
        ("AppModules/cop_app/AppModule.xml", 'type="26"', 'type="999"'),
        ("AppModules/cop_app/AppModule.xml", 'id="{11111111', 'id="{99999999'),
        ("AppModules/cop_app/AppModule.xml", 'schemaName="cop_intake"', 'schemaName="cop_missing"'),
        (
            "AppModules/cop_app/AppModule.xml",
            "<AppModuleRoleMaps/>",
            '<AppModuleRoleMaps><Role id="synthetic-role"/></AppModuleRoleMaps>',
        ),
        (
            "AppModuleSiteMaps/cop_app/AppModuleSiteMap.xml",
            'Entity="cop_intake"',
            'Entity="cop_missing"',
        ),
        (
            "AppModuleSiteMaps/cop_app/AppModuleSiteMap.xml",
            'Entity="cop_intake"',
            'Url="https://example.org"',
        ),
        ("AppModules/cop_app/AppModule.xml", "<value>1</value>", "<value>secret</value>"),
        ("AppModules/cop_app/AppModule.xml", 'uniquename="AppChannel"', 'uniquename="Other"'),
        (
            "AppModules/cop_app/AppModule.xml",
            "</appsettings>",
            "<value>protected</value></appsettings>",
        ),
        (
            "Other/Solution.xml",
            "<MissingDependencies/>",
            "<MissingDependencies><MissingDependency/></MissingDependencies>",
        ),
    ],
)
def test_app_rejects_unresolved_or_bound_components(
    app_solution: Path, relative: str, old: str, new: str
) -> None:
    """Broken app references and sharing/settings/dependency gates fail closed."""
    path = app_solution / relative
    path.write_text(path.read_text().replace(old, new))
    with pytest.raises(ValueError, match=r"app|App|component|navigation|portable|dependencies"):
        local_alm.validate_solution(app_solution)


def test_package_integrity_dry_run_and_failure(solution: Path, tmp_path: Path) -> None:
    """Publish only complete verified releases and preserve earlier releases on failure."""
    destination = tmp_path / "release"
    local_alm.package_solution(solution, destination, runner=fake_pac, dry_run=True)
    assert not destination.exists()
    local_alm.package_solution(solution, destination, runner=fake_pac)
    release = local_alm.verify_release(destination)
    assert release.name == "fixture"
    with pytest.raises(ValueError, match="exists"):
        local_alm.package_solution(solution, destination, runner=fake_pac)

    def interrupted(_command: list[str]) -> None:
        raise subprocess.CalledProcessError(1, "pac", output="protected")

    with pytest.raises(RuntimeError, match="failed") as error:
        local_alm.package_solution(solution, tmp_path / "interrupted", runner=interrupted)
    assert "protected" not in str(error.value)
    assert not (tmp_path / "interrupted").exists()
    archive = next(destination.glob("*.zip"))
    archive.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        local_alm.verify_release(destination)


def test_prepare_requires_export_and_rollback_evidence(solution: Path, tmp_path: Path) -> None:
    """A deployment plan needs an intact pre-change release and never executes import."""
    release = tmp_path / "release"
    local_alm.package_solution(solution, release, runner=fake_pac)
    with pytest.raises(ValueError, match="backup"):
        local_alm.prepare_deployment(release, None, "test")
    plan = local_alm.prepare_deployment(release, release, "dev")
    assert plan["status"] == "prepared-offline"
    assert plan["rollback"] == "review-backup-and-forward-fix"
    assert json.loads(json.dumps(plan))["backup_sha256"] == plan["artifact_sha256"]
    with pytest.raises(ValueError, match="managed"):
        local_alm.prepare_deployment(release, release, "prod")


def test_settings_bound_values_and_interruption(solution: Path, tmp_path: Path) -> None:
    """Settings publication is atomic and bound values never enter a reusable template."""
    target = tmp_path / "settings.json"

    def generate(command: list[str]) -> None:
        Path(command[-1]).write_text(
            '{"EnvironmentVariables": [], "ConnectionReferences": []}', encoding="utf-8"
        )

    local_alm.generate_settings(solution, target, runner=generate)
    assert json.loads(target.read_text(encoding="utf-8"))["EnvironmentVariables"] == []
    with pytest.raises(ValueError, match="exists"):
        local_alm.generate_settings(solution, target, runner=generate)

    def bound(command: list[str]) -> None:
        Path(command[-1]).write_text(
            '{"EnvironmentVariables": [{"Value":"private"}], "ConnectionReferences": []}',
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="bound"):
        local_alm.generate_settings(solution, tmp_path / "bound.json", runner=bound)
    assert not (tmp_path / "bound.json").exists()

    def interrupted(_command: list[str]) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        local_alm.package_solution(solution, tmp_path / "interrupted", runner=interrupted)
    assert not (tmp_path / "interrupted").exists()
    assert not list(tmp_path.glob(".alm-*"))


@pytest.mark.parametrize(
    "replacement",
    [
        "<Other/>",
        "<ImportExportXml/>",
        '<RootComponents><RootComponent type="29"/></RootComponents>',
    ],
)
def test_missing_manifest_and_unsupported_components(solution: Path, replacement: str) -> None:
    """Unsupported components are rejected rather than silently declared validated."""
    path = solution / "Other/Solution.xml"
    value = path.read_text(encoding="utf-8")
    path.write_text(
        value.replace("<RootComponents/>", replacement)
        if "RootComponents" in replacement
        else replacement,
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"required|Unsupported"):
        local_alm.validate_solution(solution)


def test_binary_and_invalid_text(solution: Path) -> None:
    """Source scanning fails closed for unhandled assets and undecodable content."""
    (solution / "unknown.bin").write_bytes(b"asset")
    with pytest.raises(ValueError, match="Unsupported"):
        local_alm.validate_solution(solution)
    (solution / "unknown.bin").unlink()
    (solution / "bad.json").write_bytes(b"\xff")
    with pytest.raises(ValueError, match="Malformed"):
        local_alm.validate_solution(solution)


def test_malformed_json_has_sanitized_diagnostics(solution: Path) -> None:
    """Malformed JSON cannot pass validation or leak its contents in diagnostics."""
    malformed = "{invalid-json protected-content"
    (solution / "malformed.json").write_text(malformed, encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed") as error:
        local_alm.validate_solution(solution)
    assert malformed not in str(error.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"endpoint": "HTTPS://SYNTHETIC.CRM6.DYNAMICS.COM/api/data/v9.2"},
        {"clientSecret": "synthetic-forbidden-value"},
    ],
)
def test_portability_checks_ignore_endpoint_and_secret_key_case(
    solution: Path, payload: dict[str, str]
) -> None:
    """Case changes cannot bypass protected or environment-bound value rejection."""
    (solution / "settings.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="portable"):
        local_alm.validate_solution(solution)


def test_packaging_detects_source_mutation(solution: Path, tmp_path: Path) -> None:
    """Concurrent source edits cannot be labelled as the package's audited source."""

    def mutate(command: list[str]) -> None:
        fake_pac(command)
        (solution / "Other/Customizations.xml").write_text("<Changed/>", encoding="utf-8")

    with pytest.raises(ValueError, match="changed"):
        local_alm.package_solution(solution, tmp_path / "mutation", runner=mutate)
    assert not (tmp_path / "mutation").exists()
    with pytest.raises(ValueError, match="outside"):
        local_alm.package_solution(solution, solution / "release", dry_run=True)


@pytest.mark.parametrize("contents", [b"broken", b"<ImportExportXml/>"])
def test_invalid_packaged_content(solution: Path, tmp_path: Path, contents: bytes) -> None:
    """Successful process exit does not substitute for valid solution ZIP content."""

    def invalid(command: list[str]) -> None:
        archive = Path(command[command.index("--zipfile") + 1])
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("solution.xml", contents)
            package.writestr("customizations.xml", "<Customizations/>")

    with pytest.raises(ValueError, match="Invalid"):
        local_alm.package_solution(solution, tmp_path / "invalid", runner=invalid)


def test_metadata_and_backup_identity(solution: Path, tmp_path: Path) -> None:
    """Metadata path traversal and mismatched backup identity cannot prepare deployment."""
    release = tmp_path / "release"
    local_alm.package_solution(solution, release, runner=fake_pac)
    metadata = release / "release.json"
    original = metadata.read_text(encoding="utf-8")
    value = json.loads(original)
    value["artifact"] = "../outside.zip"
    metadata.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="path"):
        local_alm.verify_release(release)
    value = json.loads(original)
    value["solution"]["version"] = "2.0.0.0"
    metadata.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata"):
        local_alm.verify_release(release)
    metadata.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="Stage"):
        local_alm.prepare_deployment(release, release, "unknown")
    manifest = solution / "Other/Solution.xml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("fixture", "different"), encoding="utf-8"
    )
    backup = tmp_path / "different"
    local_alm.package_solution(solution, backup, runner=fake_pac)
    with pytest.raises(ValueError, match="identity"):
        local_alm.prepare_deployment(release, backup, "dev")


def test_pac_prerequisite_and_private_failure(
    solution: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing executable and process failures have actionable, protected diagnostics."""

    def missing(_name: str) -> None:
        return None

    def installed(_name: str) -> str:
        return "pac.exe"

    monkeypatch.setattr(local_alm.shutil, "which", missing)
    with pytest.raises(RuntimeError, match="prerequisite"):
        local_alm.package_solution(solution, tmp_path / "missing")
    monkeypatch.setattr(local_alm.shutil, "which", installed)

    def fail(*_args: object, **_kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, "pac", output="secret")

    monkeypatch.setattr(local_alm.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="failed"):
        local_alm.generate_settings(solution, tmp_path / "failed.json")


@pytest.mark.parametrize(
    "settings",
    [
        "{}",
        '{"EnvironmentVariables": null, "ConnectionReferences": []}',
        '{"EnvironmentVariables": [], "ConnectionReferences": [null]}',
        '{"EnvironmentVariables": [], "ConnectionReferences": [], "CopilotAgents": [1]}',
    ],
)
def test_unsupported_settings(solution: Path, tmp_path: Path, settings: str) -> None:
    """Unknown schemas and malformed entries cannot publish a template."""

    def generate(command: list[str]) -> None:
        Path(command[-1]).write_text(settings, encoding="utf-8")

    with pytest.raises((ValueError, TypeError), match=r"schema|collection|bound|adapter"):
        local_alm.generate_settings(solution, tmp_path / "invalid.json", runner=generate)
    assert not (tmp_path / "invalid.json").exists()


def test_cli_review_outputs_and_failures(
    solution: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """All offline operator entry points report verified facts or a failed exit."""
    release = tmp_path / "release"
    local_alm.package_solution(solution, release, runner=fake_pac)
    for arguments in (
        ["validate", str(solution)],
        ["pack", str(solution), str(tmp_path / "dry"), "--dry-run"],
        ["verify", str(release)],
        ["prepare", str(release), str(release), "dev"],
    ):
        monkeypatch.setattr(sys, "argv", ["local-alm", *arguments])
        local_alm.main()
        assert isinstance(json.loads(capsys.readouterr().out), dict)
    monkeypatch.setattr(sys, "argv", ["local-alm", "validate", str(tmp_path / "absent")])
    with pytest.raises(SystemExit) as error:
        local_alm.main()
    assert error.value.code == 1


def test_portable_entity_and_empty_settings_entries(solution: Path, tmp_path: Path) -> None:
    """Actual table references and empty connection settings are accepted without tenant binding."""
    (solution / "Entities/cop_Example").mkdir(parents=True)
    (solution / "Entities/cop_Example/Entity.xml").write_text("<Entity/>", encoding="utf-8")
    manifest = solution / "Other/Solution.xml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "<RootComponents/>",
            '<RootComponents><RootComponent type="1" schemaName="cop_example"/></RootComponents>',
        ),
        encoding="utf-8",
    )
    assert local_alm.validate_solution(solution).name == "fixture"

    def generate(command: list[str]) -> None:
        Path(command[-1]).write_text(
            '{"EnvironmentVariables":[{"SchemaName":"cop_Endpoint","Value":""}],'
            '"ConnectionReferences":[{"LogicalName":"cop_Connection","ConnectionId":""}],'
            '"CopilotAgents":[]}',
            encoding="utf-8",
        )

    local_alm.generate_settings(solution, tmp_path / "settings.json", runner=generate)
    assert (tmp_path / "settings.json").is_file()


def test_package_identity_mismatch(solution: Path, tmp_path: Path) -> None:
    """A package for a different solution cannot be published under the audited identity."""

    def different(command: list[str]) -> None:
        target = Path(command[command.index("--zipfile") + 1])
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr(
                "solution.xml",
                (solution / "Other/Solution.xml")
                .read_text(encoding="utf-8")
                .replace("fixture", "different"),
            )
            archive.writestr("customizations.xml", "<Customizations/>")

    with pytest.raises(ValueError, match="differs"):
        local_alm.package_solution(solution, tmp_path / "different", runner=different)


def test_cli_settings_adapter(
    solution: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI settings reports generation only after the adapter has succeeded."""

    def generate(source: Path, destination: Path) -> None:
        assert source == solution
        destination.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(local_alm, "generate_settings", generate)
    monkeypatch.setattr(
        sys, "argv", ["local-alm", "settings", str(solution), str(tmp_path / "cli-settings.json")]
    )
    local_alm.main()
    assert json.loads(capsys.readouterr().out)["status"] == "generated-local-settings"


def test_managed_promotion_requires_version_increase(solution: Path, tmp_path: Path) -> None:
    """Managed downstream preparation rejects version reuse and accepts a newer fixture."""
    backup = tmp_path / "backup"
    local_alm.package_solution(solution, backup, runner=fake_pac)
    manifest = solution / "Other/Solution.xml"
    value = manifest.read_text(encoding="utf-8").replace("<Managed>0", "<Managed>1")
    manifest.write_text(value, encoding="utf-8")
    unchanged = tmp_path / "unchanged"
    local_alm.package_solution(solution, unchanged, runner=fake_pac)
    with pytest.raises(ValueError, match="increase"):
        local_alm.prepare_deployment(unchanged, backup, "test")
    manifest.write_text(value.replace("1.0.0.0", "1.0.1.0"), encoding="utf-8")
    candidate = tmp_path / "candidate"
    local_alm.package_solution(solution, candidate, runner=fake_pac)
    assert local_alm.prepare_deployment(candidate, backup, "test")["version"] == "1.0.1.0"
