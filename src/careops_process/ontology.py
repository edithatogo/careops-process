# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Versioned CareOps ontology registry and compatibility validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class OntologyError(ValueError):
    """Raised when a fact uses an unregistered ontology term."""


def validate_terms(
    ontology: Mapping[str, object], *, object_types: Sequence[str], event_types: Sequence[str]
) -> None:
    """Ensure source terms are present in the versioned registry."""
    registered_objects = ontology.get("objects")
    registered_events = ontology.get("events")
    if not isinstance(registered_objects, list) or not isinstance(registered_events, list):
        message = "ontology objects and events must be lists"
        raise OntologyError(message)
    object_terms = cast("list[str]", registered_objects)
    event_terms = cast("list[str]", registered_events)
    unknown_objects = set(object_types) - set(object_terms)
    unknown_events = set(event_types) - set(event_terms)
    if unknown_objects:
        message = f"unknown object types: {', '.join(sorted(unknown_objects))}"
        raise OntologyError(message)
    if unknown_events:
        message = f"unknown event types: {', '.join(sorted(unknown_events))}"
        raise OntologyError(message)


def assert_compatible_versions(ontology: Mapping[str, object], expected: str = "1.0.0") -> None:
    """Reject incompatible ontology versions before mining or projection."""
    if ontology.get("version") != expected:
        message = f"incompatible ontology version: expected {expected}"
        raise OntologyError(message)
