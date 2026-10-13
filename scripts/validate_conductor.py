"""Validate local Conductor records and pinned skill installations without writes."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import unquote

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.install_repo_skills import entrypoint, read_manifest, within

MARKS = {" ": "new", "~": "in_progress", "x": "completed"}
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ENTRY = re.compile(r"(?:^## |^- )\[([ x~])\].*?\*Link:.*?\]\(([^)]+)\)", re.MULTILINE | re.DOTALL)


def _links(path: Path, root: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    errors = []
    for link in LINK.findall(text):
        if "://" in link or link.startswith(("#", "mailto:")):
            continue
        target = unquote(link.split("#", maxsplit=1)[0])
        if target and not (path.parent / target).exists():
            errors.append(f"{path.relative_to(root)}: missing link target {link}")
    return errors


def _git(root: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        message = "Git is required to verify pinned skill sources"
        raise ValueError(message)
    # Fixed local rev-parse and ls-files argument lists; no shell or network.
    result = subprocess.run(  # noqa: S603 # nosec B603
        [executable, "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        message = f"Git verification failed at {root}: {result.stderr.strip()}"
        raise ValueError(message)
    return result.stdout.strip()


def _registrations(conductor: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    registry = (conductor / "tracks.md").read_text(encoding="utf-8")
    errors = []
    entries: list[tuple[str, Path]] = []
    for mark, link in ENTRY.findall(registry):
        target = (conductor / link).resolve()
        if not target.is_relative_to((conductor / "tracks").resolve()):
            errors.append(f"conductor/tracks.md: track link escapes tracks directory: {link}")
            continue
        folder = target if target.is_dir() else target.parent
        entries.append((mark, folder))
    counts = Counter(folder.name for _, folder in entries)
    for name, count in counts.items():
        if count != 1:
            errors.append(f"conductor/tracks.md: duplicate registration for {name}")
    return entries, errors


def _metadata_errors(folder: Path, entries: list[tuple[str, Path]], root: Path) -> list[str]:
    metadata = folder / "metadata.json"
    if not metadata.is_file():
        return []
    try:
        data = json.loads(metadata.read_text(encoding="utf-8-sig"))
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return [f"{metadata.relative_to(root)}: invalid JSON object"]
    errors = []
    if data.get("track_id", data.get("id")) != folder.name:
        errors.append(f"{metadata.relative_to(root)}: track ID differs from directory")
    status = data.get("status")
    if status not in MARKS.values():
        errors.append(f"{metadata.relative_to(root)}: invalid status {status}")
    for mark, registered in entries:
        if registered == folder.resolve() and MARKS[mark] != status:
            errors.append(f"{metadata.relative_to(root)}: registry/status mismatch")
    index = folder / "index.md"
    if index.is_file():
        recorded = re.search(r"^Status: (.+)$", index.read_text(encoding="utf-8"), re.MULTILINE)
        if recorded and recorded[1].replace(" ", "_") != status:
            errors.append(f"{index.relative_to(root)}: index/status mismatch")
    return errors


def _tracks(root: Path) -> list[str]:
    conductor = root / "conductor"
    required = (
        "index.md",
        "product.md",
        "product-guidelines.md",
        "tech-stack.md",
        "workflow.md",
        "tracks.md",
        "code_styleguides/general.md",
        "code_styleguides/python.md",
    )
    errors = [
        f"conductor/{name}: required file missing"
        for name in required
        if not (conductor / name).is_file()
    ]
    if not (conductor / "tracks.md").is_file():
        return errors
    entries, entry_errors = _registrations(conductor)
    errors.extend(entry_errors)
    registered = {folder.name for _, folder in entries}
    tracks_dir = conductor / "tracks"
    if not tracks_dir.is_dir():
        return [*errors, "conductor/tracks: required directory missing"]
    for folder in sorted(p for p in tracks_dir.iterdir() if p.is_dir()):
        if folder.name not in registered:
            errors.append(f"conductor/tracks/{folder.name}: unregistered track")
        errors.extend(
            f"conductor/tracks/{folder.name}/{name}: required file missing"
            for name in ("index.md", "spec.md", "plan.md", "metadata.json")
            if not (folder / name).is_file()
        )
        errors.extend(_metadata_errors(folder, entries, root))
    for path in conductor.rglob("*.md"):
        errors.extend(_links(path, root))
    return errors


def _source_errors(root: Path, source: dict[str, Any], *, verify_git: bool) -> list[str]:
    errors = []
    path = within(root, source["path"])
    commit = source["commit"]
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        errors.append(f"{source['path']}: invalid commit SHA")
    modules = root / ".gitmodules"
    module_text = modules.read_text(encoding="utf-8") if modules.is_file() else ""
    if source["path"] not in module_text or source["url"] not in module_text:
        errors.append(f"{source['path']}: submodule mapping missing")
    if not path.is_dir():
        return [*errors, f"{source['path']}: submodule not initialised"]
    if not any(path.glob("LICENSE*")):
        errors.append(f"{source['path']}: upstream licence missing")
    if verify_git:
        try:
            if _git(path, "rev-parse", "HEAD") != commit:
                errors.append(f"{source['path']}: checkout differs from pinned commit")
            staged = _git(root, "ls-files", "--stage", "--", source["path"])
            if not staged.startswith(f"160000 {commit} "):
                errors.append(f"{source['path']}: Git submodule pointer differs from manifest")
            if _git(path, "status", "--porcelain", "--untracked-files=no"):
                errors.append(f"{source['path']}: pinned source resources are modified or missing")
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def _skill_errors(root: Path, skill: dict[str, Any], source: dict[str, Any]) -> list[str]:
    errors = []
    upstream = within(within(root, source["path"]), skill["path"])
    instructions = upstream / "SKILL.md"
    if not instructions.is_file():
        errors.append(f"{skill['name']}: upstream SKILL.md missing")
    else:
        errors.extend(_links(instructions, root))
    entry = root / ".agents" / "skills" / skill["name"] / "SKILL.md"
    if not entry.is_file():
        return [*errors, f"{skill['name']}: repository entrypoint missing"]
    expected = entrypoint(
        skill["name"],
        skill["description"],
        f"../../plugins/{source['id']}/{skill['path']}",
    )
    if entry.read_text(encoding="utf-8") != expected:
        errors.append(
            f"{skill['name']}: entrypoint metadata or upstream mapping differs from manifest"
        )
    errors.extend(_links(entry, root))
    return errors


def _skills(root: Path, *, verify_git: bool) -> list[str]:
    try:
        manifest = read_manifest(root)
        sources = manifest["sources"]
        skills = manifest["skills"]
    except OSError, ValueError, KeyError, TypeError:
        return [".agents/skills-manifest.json: missing or invalid manifest"]
    errors = []
    source_map = {source["id"]: source for source in sources}
    if len(source_map) != len(sources):
        errors.append(".agents/skills-manifest.json: duplicate source IDs")
    names = [skill["name"] for skill in skills]
    if len(set(names)) != len(names):
        errors.append(".agents/skills-manifest.json: duplicate skill names")
    for source in sources:
        errors.extend(_source_errors(root, source, verify_git=verify_git))
    for skill in skills:
        if skill["source"] not in source_map:
            errors.append(f"{skill['name']}: unknown skill source")
            continue
        source = source_map[skill["source"]]
        errors.extend(_skill_errors(root, skill, source))
    return errors


def validate_conductor(root: Path, *, verify_git: bool = True) -> list[str]:
    """Return actionable setup errors without contacting platforms or writing files."""
    root = root.resolve()
    errors = _tracks(root)
    try:
        errors.extend(_skills(root, verify_git=verify_git))
    except (OSError, ValueError) as exc:
        errors.append(f".agents/skills-manifest.json: {exc}")
    return sorted(set(errors))


def main() -> int:
    """Expose the read-only setup gate with stable success/failure exit codes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_conductor(args.root)
    if errors:
        for error in errors:
            sys.stdout.write(error + "\n")
        return 1
    sys.stdout.write("Conductor configuration, tracks and pinned skill entrypoints are valid.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
