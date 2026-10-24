# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic ontology compatibility tests."""

import json
from pathlib import Path

import pytest

from careops_process.ontology import OntologyError, assert_compatible_versions, validate_terms


def load_ontology() -> dict[str, object]:
    """Load the repository-owned ontology registry."""
    return json.loads(Path("schemas/careops-ontology.registry.json").read_text(encoding="utf-8"))


def test_registered_terms_and_version_are_accepted() -> None:
    """Known CareOps terms pass compatibility checks."""
    ontology = {**load_ontology(), "objects": ["approval_request"], "events": ["request_received"]}
    assert_compatible_versions(ontology)
    validate_terms(ontology, object_types=["approval_request"], event_types=["request_received"])


def test_unknown_terms_and_versions_fail_closed() -> None:
    """Ontology drift cannot silently enter the canonical log."""
    ontology = {**load_ontology(), "objects": ["approval_request"], "events": ["request_received"]}
    with pytest.raises(OntologyError, match="unknown event"):
        validate_terms(ontology, object_types=[], event_types=["unregistered"])
    with pytest.raises(OntologyError, match="incompatible"):
        assert_compatible_versions(ontology, expected="2.0.0")
