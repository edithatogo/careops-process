"""Offline Dataverse solution validation, atomic packaging and release preparation.

No function authenticates, exports from a tenant, checks online or imports a solution.
"""

import argparse
import hashlib
import json
import re
import shutil

# PAC is invoked without a shell through a resolved executable.
import subprocess  # nosec B404
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

if TYPE_CHECKING:
    from collections.abc import Callable

_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
_BOUND = re.compile(
    r"https?://[^\s\"<>]+\.(?:dynamics\.com|sharepoint\.com)|"
    r"(?i:Bearer\s+\S+|[\"']?(?:client_secret|password|access_token|refresh_token|"
    r"tenantid|environmentid|connectionid)[\"']?\s*[:=]\s*[\"']?[^\s\"'<>{}]+|"
    r"<(?:clientsecret|password|access_token|refresh_token|connectionid|tenantid|"
    r"environmentid|defaultvalue|value)>\s*[^\s<]+)"
)


@dataclass(frozen=True)
class SolutionInfo:
    """Validated local identity; managed denotes source provenance, not deployment evidence."""

    name: str
    version: str
    managed: bool


def _validate_files(source: Path) -> None:
    for relative in ("Other/Solution.xml", "Other/Customizations.xml"):
        if not (source / relative).is_file():
            msg = "Solution required source files are missing."
            raise ValueError(msg)
    try:
        for path in source.rglob("*"):
            if path.is_symlink():
                msg = "Solution symbolic links are unsupported."
                raise ValueError(msg)
            if path.is_file():
                if path.suffix.lower() not in {".xml", ".json", ".resx"}:
                    msg = "Unsupported solution file requires an explicit validation adapter."
                    raise ValueError(msg)
                text = path.read_text(encoding="utf-8-sig")
                if _BOUND.search(text):
                    msg = "Solution content is not portable; remove protected or bound values."
                    raise ValueError(msg)
                if path.suffix.lower() in {".xml", ".resx"}:
                    ElementTree.parse(path)
                else:
                    json.loads(text)
    except ElementTree.ParseError, UnicodeError, DefusedXmlException, json.JSONDecodeError:
        msg = "Malformed or unsafe solution XML/JSON/text."
        raise ValueError(msg) from None


def validate_solution(source: Path) -> SolutionInfo:
    """Check supported source structure, component references and portable content.

    Raises:
        ValueError: Source is incomplete, unsupported or contains bound/protected values.

    """
    _validate_files(source)
    root = ElementTree.parse(source / "Other/Solution.xml").getroot()
    if root is None:
        msg = "Solution XML root is required."
        raise ValueError(msg)
    manifest = root.find("SolutionManifest")
    if manifest is None:
        msg = "SolutionManifest is required."
        raise ValueError(msg)
    name = manifest.findtext("UniqueName", "")
    version = manifest.findtext("Version", "")
    managed = manifest.findtext("Managed", "")
    prefix = manifest.findtext("Publisher/CustomizationPrefix", "")
    if (
        not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name)
        or not _VERSION.fullmatch(version)
        or managed not in {"0", "1"}
        or not re.fullmatch(r"[a-z][a-z0-9]{1,7}", prefix)
        or prefix == "new"
    ):
        msg = "Invalid solution identity, four-part version, managed flag or publisher prefix."
        raise ValueError(msg)
    if manifest.findall("MissingDependencies/MissingDependency"):
        msg = "Declared missing dependencies require resolution before packaging."
        raise ValueError(msg)
    entity_names = {
        path.parent.name.casefold() for path in (source / "Entities").glob("*/Entity.xml")
    }
    for component in manifest.findall("RootComponents/RootComponent"):
        if component.get("type") != "1":
            msg = "Unsupported root component requires an explicit validation adapter."
            raise ValueError(msg)
        if component.get("schemaName", "").casefold() not in entity_names:
            msg = "Root component references missing entity source."
            raise ValueError(msg)
    return SolutionInfo(name, version, managed == "1")


def _run_pac(command: list[str]) -> None:
    executable = shutil.which("pac")
    if executable is None:
        msg = "PAC prerequisite missing: install Microsoft Power Platform CLI and retry."
        raise RuntimeError(msg)
    # Only fixed local PAC verbs and individually passed paths; no shell interpolation.
    subprocess.run(  # noqa: S603  # nosec B603
        [executable, *command[1:]], check=True, capture_output=True
    )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_identity(archive: Path) -> SolutionInfo:
    try:
        with zipfile.ZipFile(archive) as package:
            if package.testzip() is not None:
                msg = "Package CRC integrity failure."
                raise ValueError(msg)
            root = ElementTree.fromstring(package.read("solution.xml"))
            package.getinfo("customizations.xml")
            name = root.findtext("SolutionManifest/UniqueName", "")
            version = root.findtext("SolutionManifest/Version", "")
            managed = root.findtext("SolutionManifest/Managed", "")
            if not name or not _VERSION.fullmatch(version) or managed not in {"0", "1"}:
                msg = "Invalid package solution identity."
                raise ValueError(msg)
            return SolutionInfo(name, version, managed == "1")
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, DefusedXmlException) as error:
        msg = "Invalid solution package structure."
        raise ValueError(msg) from error


def package_solution(
    source: Path,
    destination: Path,
    *,
    runner: Callable[[list[str]], None] = _run_pac,
    dry_run: bool = False,
) -> list[str]:
    """Pack with PAC and publish a new release directory only after integrity checks.

    Existing releases are immutable. Staging is removed if PAC fails or is interrupted.
    Dry-run validates source and returns the command without creating files or invoking PAC.
    """
    info = validate_solution(source)
    if destination.resolve().is_relative_to(source.resolve()):
        msg = "Release destination must be outside solution source."
        raise ValueError(msg)
    if destination.exists():
        msg = "Release destination already exists; select a new versioned directory."
        raise ValueError(msg)
    filename = f"{info.name}_{info.version}_{'managed' if info.managed else 'unmanaged'}.zip"
    command = [
        "pac",
        "solution",
        "pack",
        "--folder",
        str(source.resolve()),
        "--zipfile",
        str(destination / filename),
        "--packagetype",
        "Managed" if info.managed else "Unmanaged",
    ]
    if dry_run:
        return command
    sources = {
        path.relative_to(source).as_posix(): _hash(path)
        for path in sorted(source.rglob("*"))
        if path.is_file()
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".alm-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        archive = staging / filename
        command[command.index("--zipfile") + 1] = str(archive)
        try:
            runner(command)
        except subprocess.CalledProcessError:
            msg = "PAC packaging failed; no release published. Inspect PAC diagnostics privately."
            raise RuntimeError(msg) from None
        if _package_identity(archive) != info:
            msg = "Packed solution identity differs from validated source."
            raise ValueError(msg)
        after = {
            str(path.relative_to(source)).replace("\\", "/"): _hash(path)
            for path in sorted(source.rglob("*"))
            if path.is_file()
        }
        if sources != after:
            msg = "Source changed during packaging; no release published."
            raise ValueError(msg)
        manifest = {
            "schema_version": 1,
            "solution": asdict(info),
            "artifact": filename,
            "sha256": _hash(archive),
            "source_sha256": sources,
            "status": "packaged-offline",
            "solution_check": "not-run",
        }
        (staging / "release.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        verify_release(staging)
        staging.rename(destination)
    command[command.index("--zipfile") + 1] = str(destination / filename)
    return command


def verify_release(release: Path) -> SolutionInfo:
    """Reject altered packages and metadata, including artifact paths outside the release."""
    metadata = json.loads((release / "release.json").read_text(encoding="utf-8"))
    filename = metadata["artifact"]
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or not filename.endswith(".zip")
    ):
        msg = "Invalid release artifact path."
        raise ValueError(msg)
    archive = release / filename
    if archive.is_symlink() or _hash(archive) != metadata["sha256"]:
        msg = "Release artifact integrity mismatch."
        raise ValueError(msg)
    info = _package_identity(archive)
    if metadata["schema_version"] != 1 or asdict(info) != metadata["solution"]:
        msg = "Release metadata identity mismatch."
        raise ValueError(msg)
    return info


def prepare_deployment(release: Path, backup: Path | None, stage: str) -> dict[str, str]:
    """Prepare an offline review record requiring an exported pre-change release.

    Backup provenance, timestamp and target identity still require operator verification.
    A prior managed import is not a guaranteed downgrade or data restore operation.
    """
    info = verify_release(release)
    if backup is None:
        msg = "Verified pre-change export backup is required."
        raise ValueError(msg)
    prior = verify_release(backup)
    if prior.name != info.name:
        msg = "Backup solution identity does not match release."
        raise ValueError(msg)
    if stage not in {"dev", "test", "prod"}:
        msg = "Stage must be dev, test or prod."
        raise ValueError(msg)
    if stage != "dev" and not info.managed:
        msg = "Downstream promotion requires a managed source/export; do not relabel unmanaged XML."
        raise ValueError(msg)
    if stage != "dev" and tuple(map(int, info.version.split("."))) <= tuple(
        map(int, prior.version.split("."))
    ):
        msg = "Downstream release version must increase over the pre-change backup."
        raise ValueError(msg)
    current = json.loads((release / "release.json").read_text(encoding="utf-8"))
    previous = json.loads((backup / "release.json").read_text(encoding="utf-8"))
    return {
        "status": "prepared-offline",
        "stage": stage,
        "solution": info.name,
        "version": info.version,
        "artifact_sha256": current["sha256"],
        "backup_sha256": previous["sha256"],
        "rollback": "review-backup-and-forward-fix",
        "external_gates": "target-and-backup-provenance,settings,checker,approval,restore-test",
    }


def generate_settings(
    source: Path, destination: Path, *, runner: Callable[[list[str]], None] = _run_pac
) -> None:
    """Generate tenant-neutral deployment settings through supported local PAC tooling."""
    validate_solution(source)
    if destination.exists():
        msg = "Settings destination already exists; existing bindings will not be overwritten."
        raise ValueError(msg)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".alm-settings-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "deployment-settings.json"
        command = [
            "pac",
            "solution",
            "create-settings",
            "--solution-folder",
            str(source.resolve()),
            "--settings-file",
            str(staging),
        ]
        try:
            runner(command)
        except subprocess.CalledProcessError:
            msg = "PAC settings generation failed; no settings published."
            raise RuntimeError(msg) from None
        content = staging.read_text(encoding="utf-8")
        if _BOUND.search(content):
            msg = "Generated settings contain protected or bound values."
            raise ValueError(msg)
        settings = json.loads(content)
        required = {"EnvironmentVariables", "ConnectionReferences"}
        if not required.issubset(settings) or set(settings) - required - {"CopilotAgents"}:
            msg = "Unsupported deployment settings schema."
            raise ValueError(msg)
        if settings.get("CopilotAgents"):
            msg = "Copilot agent settings require an explicit validation adapter."
            raise ValueError(msg)
        for group, key in (
            ("EnvironmentVariables", "Value"),
            ("ConnectionReferences", "ConnectionId"),
        ):
            if not isinstance(settings[group], list):
                msg = "Invalid deployment settings collection."
                raise TypeError(msg)
            for item in settings[group]:
                if not isinstance(item, dict) or item.get(key):
                    msg = "Generated settings contain bound values; keep them outside Git."
                    raise ValueError(msg)
        staging.rename(destination)


def main() -> None:
    """Expose local validate, pack, verify and deployment preparation commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("source", type=Path)
    pack = subparsers.add_parser("pack")
    pack.add_argument("source", type=Path)
    pack.add_argument("destination", type=Path)
    pack.add_argument("--dry-run", action="store_true")
    verify = subparsers.add_parser("verify")
    verify.add_argument("release", type=Path)
    settings = subparsers.add_parser("settings")
    settings.add_argument("source", type=Path)
    settings.add_argument("destination", type=Path)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("release", type=Path)
    prepare.add_argument("backup", type=Path)
    prepare.add_argument("stage", choices=("dev", "test", "prod"))
    args = parser.parse_args()
    try:
        if args.action == "validate":
            result = asdict(validate_solution(args.source))
        elif args.action == "pack":
            result = {
                "command": package_solution(args.source, args.destination, dry_run=args.dry_run)
            }
        elif args.action == "verify":
            result = asdict(verify_release(args.release))
        elif args.action == "settings":
            generate_settings(args.source, args.destination)
            result = {"status": "generated-local-settings"}
        else:
            result = prepare_deployment(args.release, args.backup, args.stage)
    except ValueError, TypeError, RuntimeError, OSError, KeyError:
        parser.exit(
            1, "Local ALM operation failed; check source, integrity and prerequisites privately.\n"
        )
    sys.stdout.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
