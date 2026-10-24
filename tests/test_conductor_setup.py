# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Verify local Conductor integrity without live platform access."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.install_repo_skills import install_skills
from scripts.validate_conductor import validate_conductor


def make_project(root: Path) -> Path:
    """Create a minimal coherent project with one pinned skill source."""
    conductor = root / "conductor"
    track = conductor / "tracks" / "example_20261013"
    track.mkdir(parents=True)
    for name in ("product", "product-guidelines", "tech-stack", "workflow"):
        (conductor / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    guides = conductor / "code_styleguides"
    guides.mkdir()
    for name in ("general", "python"):
        (guides / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    (conductor / "index.md").write_text(
        "# Context\n[Product](product.md)\n[Guides](code_styleguides/)\n"
        "[Tracks](tracks.md)\n[Directory](tracks/)\n",
        encoding="utf-8",
    )
    (conductor / "tracks.md").write_text(
        "# Tracks\n- [ ] **Track: Example**\n"
        "*Link: [example](./tracks/example_20261013/index.md)*\n",
        encoding="utf-8",
    )
    (track / "index.md").write_text(
        "# Example\nStatus: new\n[Spec](spec.md)\n[Plan](plan.md)\n[Metadata](metadata.json)\n",
        encoding="utf-8",
    )
    (track / "spec.md").write_text("# Example\n", encoding="utf-8")
    (track / "plan.md").write_text("# Plan\n- [ ] Task: Example\n", encoding="utf-8")
    (track / "metadata.json").write_text(
        json.dumps({"id": track.name, "status": "new", "created": "2026-10-13"}),
        encoding="utf-8",
    )
    source = root / ".agents" / "plugins" / "example"
    skill = source / "skills" / "example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: example\ndescription: Example skill.\n---\n"
        "Read [guide](references/guide.md).\n",
        encoding="utf-8",
    )
    (skill / "references").mkdir()
    (skill / "references" / "guide.md").write_text("Reference\n", encoding="utf-8")
    (source / "LICENSE").write_text("MIT\n", encoding="utf-8")
    commit = "a" * 40
    (root / ".gitmodules").write_text(
        '[submodule "example"]\n\tpath = .agents/plugins/example\n'
        "\turl = https://github.com/example/skills.git\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "sources": [
            {
                "id": "example",
                "path": ".agents/plugins/example",
                "commit": commit,
                "url": "https://github.com/example/skills.git",
                "license": "MIT",
            }
        ],
        "skills": [
            {
                "name": "careops-example",
                "source": "example",
                "path": "skills/example",
                "description": "Example skill.",
            }
        ],
    }
    (root / ".agents" / "skills-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    install_skills(root, user_home=None)
    return root


def test_coherent_project_and_existing_metadata_aliases_pass(tmp_path: Path) -> None:
    """Existing metadata names remain compatible."""
    assert validate_conductor(make_project(tmp_path), verify_git=False) == []


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("conductor/code_styleguides/python.md", "python.md"),
        ("conductor/tracks/example_20261013/plan.md", "plan.md"),
        (".agents/plugins/example/skills/example/SKILL.md", "SKILL.md"),
        (".agents/skills/careops-example/SKILL.md", "careops-example"),
    ],
)
def test_missing_required_artifact_fails(tmp_path: Path, relative: str, expected: str) -> None:
    """Missing configuration, plans and skill targets are reported."""
    root = make_project(tmp_path)
    (root / relative).unlink()
    assert any(expected in error for error in validate_conductor(root, verify_git=False))


@pytest.mark.parametrize("change", ["orphan", "duplicate", "broken", "json", "id", "status"])
def test_track_integrity_failures(tmp_path: Path, change: str) -> None:
    """Invalid registries and track metadata cannot report a healthy setup."""
    root = make_project(tmp_path)
    registry = root / "conductor" / "tracks.md"
    metadata = root / "conductor" / "tracks" / "example_20261013" / "metadata.json"
    match change:
        case "orphan":
            registry.write_text("# Tracks\n", encoding="utf-8")
        case "duplicate":
            registry.write_text(registry.read_text() * 2, encoding="utf-8")
        case "broken":
            (root / "conductor" / "index.md").write_text("[Bad](missing.md)\n")
        case "json":
            metadata.write_text("{broken", encoding="utf-8")
        case "id":
            metadata.write_text(json.dumps({"track_id": "wrong", "status": "new"}))
        case "status":
            metadata.write_text(json.dumps({"track_id": "example_20261013", "status": "completed"}))
        case _:
            pytest.fail(f"Unexpected test scenario: {change}")
    assert validate_conductor(root, verify_git=False)


def test_global_install_survives_repository_source_removal(tmp_path: Path) -> None:
    """General Codex availability does not depend on the project checkout."""
    root = make_project(tmp_path / "project")
    user = tmp_path / "user"
    install_skills(root, user_home=user)
    source = root / ".agents" / "plugins" / "example"
    source.rename(source.with_name("moved"))
    entry = user / "skills" / "careops-example" / "SKILL.md"
    content = entry.read_text(encoding="utf-8")
    copied = user / "skill-sources" / "careops" / f"example-{'a' * 12}"
    assert (copied / "skills" / "example" / "SKILL.md").is_file()
    assert (copied / "skills" / "example" / "references" / "guide.md").is_file()
    assert (copied / "LICENSE").is_file()
    assert copied.as_posix() in content


def test_install_is_idempotent(tmp_path: Path) -> None:
    """Repeating installation leaves entrypoints stable."""
    root = make_project(tmp_path)
    entry = root / ".agents" / "skills" / "careops-example" / "SKILL.md"
    before = entry.read_bytes()
    install_skills(root, user_home=None)
    assert entry.read_bytes() == before


def test_repeated_install_repairs_an_incomplete_user_source(tmp_path: Path) -> None:
    """An interrupted or incomplete copy can be restored by rerunning installation."""
    root = make_project(tmp_path / "project")
    user = tmp_path / "user"
    install_skills(root, user_home=user)
    copied = user / "skill-sources" / "careops" / f"example-{'a' * 12}"
    reference = copied / "skills" / "example" / "references" / "guide.md"
    reference.unlink()
    install_skills(root, user_home=user)
    assert reference.is_file()


def test_malformed_manifest_is_an_actionable_error(tmp_path: Path) -> None:
    """Malformed source records cannot crash the setup gate."""
    root = make_project(tmp_path)
    manifest = root / ".agents" / "skills-manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "sources": [{}], "skills": []}))
    assert any("manifest" in error for error in validate_conductor(root, verify_git=False))


@pytest.mark.parametrize("record", ["sources", "skills"])
def test_manifest_path_escape_has_actionable_diagnostic(tmp_path: Path, record: str) -> None:
    """Invalid source and skill paths fail without exposing a traceback."""
    root = make_project(tmp_path)
    path = root / ".agents/skills-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest[record][0]["path"] = "../../outside"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    errors = validate_conductor(root, verify_git=False)
    assert any("escapes" in error for error in errors)


def test_damaged_entrypoint_fails_validation(tmp_path: Path) -> None:
    """An existing file without skill metadata and upstream instructions is unusable."""
    root = make_project(tmp_path)
    entry = root / ".agents" / "skills" / "careops-example" / "SKILL.md"
    entry.write_text("arbitrary text without a skill or link\n", encoding="utf-8")
    assert validate_conductor(root, verify_git=False)


def test_missing_upstream_reference_fails_validation(tmp_path: Path) -> None:
    """Required upstream resource links must resolve."""
    root = make_project(tmp_path)
    reference = root / ".agents/plugins/example/skills/example/references/guide.md"
    reference.unlink()
    assert validate_conductor(root, verify_git=False)


def test_inline_markdown_examples_are_not_resource_dependencies(tmp_path: Path) -> None:
    """Documented examples must not be mistaken for required upstream resources."""
    root = make_project(tmp_path)
    instructions = root / ".agents/plugins/example/skills/example/SKILL.md"
    instructions.write_text(
        instructions.read_text() + "\nExample: `[new track](<relative example path>)`\n"
    )
    assert validate_conductor(root, verify_git=False) == []


def test_modified_pinned_resource_fails_normal_git_validation(tmp_path: Path) -> None:
    """Git pins do not excuse changes in the source working tree."""
    root = make_project(tmp_path)
    source = root / ".agents/plugins/example"
    executable = shutil.which("git")
    assert executable is not None

    def git(directory: Path, *arguments: str) -> str:
        result = subprocess.run(  # noqa: S603
            [executable, "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    git(source, "init")
    git(source, "add", ".")
    git(
        source,
        "-c",
        "user.name=Setup Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "Synthetic source",
    )
    commit = git(source, "rev-parse", "HEAD")
    git(root, "init")
    git(root, "update-index", "--add", "--cacheinfo", f"160000,{commit},.agents/plugins/example")
    manifest_path = root / ".agents/skills-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["commit"] = commit
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert validate_conductor(root) == []
    (source / "skills/example/references/guide.md").write_text("Changed\n", encoding="utf-8")
    assert validate_conductor(root)


def test_validator_does_not_change_project_files(tmp_path: Path) -> None:
    """Validation only reads its target repository."""
    root = make_project(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    validate_conductor(root, verify_git=False)
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_cli_reports_failure_and_exit_code(tmp_path: Path) -> None:
    """The command-line gate fails with an actionable missing configuration error."""
    script = Path(__file__).resolve().parents[1] / "scripts" / "validate_conductor.py"
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "conductor" in result.stdout
