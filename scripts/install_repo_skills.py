"""Expose pinned upstream skills to repository and independent user-level Codex."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


def read_manifest(root: Path) -> dict[str, Any]:
    """Read the repository's explicitly selected source and skill inventory."""
    data = json.loads((root / ".agents" / "skills-manifest.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        message = "Invalid skills manifest version or object"
        raise ValueError(message)
    for key, required in (
        ("sources", ("id", "path", "url", "commit", "license")),
        ("skills", ("name", "source", "path", "description")),
    ):
        records = data.get(key)
        if not isinstance(records, list) or any(
            not isinstance(record, dict)
            or any(not isinstance(record.get(field), str) for field in required)
            for record in records
        ):
            message = f"Invalid skills manifest {key} records"
            raise ValueError(message)
    return data


def within(root: Path, relative: str) -> Path:
    """Resolve a manifest path while rejecting escapes from the source root."""
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        message = f"Manifest path escapes its root: {relative}"
        raise ValueError(message)
    return path


def entrypoint(name: str, description: str, target: str) -> str:
    """Build a portable skill entrypoint without copying upstream instructions."""
    return (
        f"---\nname: {name}\ndescription: {json.dumps(description)}\n---\n\n"
        f"Read the upstream skill at [{name}]({target}/SKILL.md) before starting.\n\n"
        "Resolve upstream scripts, assets and supporting references relative to that\n"
        "upstream skill directory. Run project operations from the current project,\n"
        "using the Python executable available on this host. Installation alone does\n"
        "not configure CLI runtimes, credentials, MCP tools or platform access.\n"
    )


def install_skills(root: Path, *, user_home: Path | None) -> int:
    """Install repository entrypoints and optionally independent user-scope copies."""
    manifest = read_manifest(root)
    sources = {source["id"]: source for source in manifest["sources"]}
    selected = manifest["skills"]
    names = [skill["name"] for skill in selected]
    if len(names) != len(set(names)) or any(
        re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) is None for name in names
    ):
        message = "Skill names must be unique, safe lowercase identifiers"
        raise ValueError(message)
    for skill in selected:
        source = sources[skill["source"]]
        source_root = within(root, source["path"])
        upstream = within(source_root, skill["path"])
        if not (upstream / "SKILL.md").is_file():
            message = f"Missing upstream skill: {upstream}"
            raise ValueError(message)
    copied: dict[str, Path] = {}
    if user_home is not None:
        for source in sources.values():
            source_root = within(root, source["path"])
            target = (
                user_home
                / "skill-sources"
                / "careops"
                / (f"{source['id']}-{source['commit'][:12]}")
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                source_root,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            copied[source["id"]] = target
    for skill in selected:
        source = sources[skill["source"]]
        repo_target = f"../../plugins/{source['id']}/{skill['path']}"
        folder = root / ".agents" / "skills" / skill["name"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(
            entrypoint(skill["name"], skill["description"], repo_target), encoding="utf-8"
        )
        if user_home is not None:
            user_target = within(copied[source["id"]], skill["path"])
            user_folder = user_home / "skills" / skill["name"]
            user_folder.mkdir(parents=True, exist_ok=True)
            (user_folder / "SKILL.md").write_text(
                entrypoint(skill["name"], skill["description"], user_target.as_posix()),
                encoding="utf-8",
            )
    return len(selected)


def main() -> int:
    """Install selected skills without configuring any live platform connection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--user-home", type=Path, help="Codex home, such as ~/.codex")
    args = parser.parse_args()
    count = install_skills(args.root.resolve(), user_home=args.user_home)
    sys.stdout.write(
        f"Installed {count} repository skills"
        + (" and user-level skills" if args.user_home is not None else "")
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
