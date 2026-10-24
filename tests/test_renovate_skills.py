# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Keep both pin managers on real, identical upstream branch names."""

import configparser
import json
from pathlib import Path


def test_skill_pin_managers_resolve_the_same_named_branch() -> None:
    """Reject unresolved HEAD and mismatched gitlink/manifest tracking branches."""
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "renovate.json").read_text())
    manifest = json.loads((root / ".agents/skills-manifest.json").read_text())
    modules = configparser.ConfigParser()
    modules.read(root / ".gitmodules")
    manager = next(
        item for item in config["customManagers"] if item.get("datasourceTemplate") == "git-refs"
    )
    branch = manager["currentValueTemplate"]
    # git-refs.getDigest(value) searches heads/tags, so literal HEAD is not valid.
    assert branch == "main"
    expected_sources = 6
    assert len(manifest["sources"]) == expected_sources
    for source in manifest["sources"]:
        module = modules[f'submodule "{source["path"]}"']
        assert module["branch"] == branch
        assert module["url"] == source["url"]
