# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Explicit versioned references for independent credentialing pathways.

These comparisons report observed process evidence against a caller-supplied
reference. They neither supply clinical rules nor certify approval or compliance.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, get_args

from careops_process.credentialing import (
    Activity,
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)

if TYPE_CHECKING:
    from careops_process.credentialing import CredentialingFact

PATHWAY_CODES = frozenset(
    {
        "routine-renewal",
        "changed-scope",
        "mutual-recognition",
        "temporary-approval",
        "conditions-supervision",
        "review-appeal",
        "register-reconciliation",
    }
)
_ACTIVITIES = frozenset(str(term) for term in get_args(Activity))
_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_FIELDS = frozenset(
    {
        "reference_id",
        "version",
        "pathway_code",
        "authority_mapping_version",
        "source_reference",
        "required_stages",
        "permitted_activities",
        "terminal_activities",
    }
)


def _fail(message: str) -> None:
    raise CredentialingContractError(message)


def _code(value: object) -> str:
    if not isinstance(value, str) or _CODE.fullmatch(value) is None:
        message = "Pathway references require bounded non-sensitive codes"
        raise CredentialingContractError(message)
    return value


def _stage_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not value:
        message = "Pathway activities require a nonempty immutable tuple"
        raise CredentialingContractError(message)
    stages = cast("tuple[object, ...]", value)
    if any(not isinstance(stage, str) or stage not in _ACTIVITIES for stage in stages):
        message = "Pathway contains an unregistered activity"
        raise CredentialingContractError(message)
    result = cast("tuple[str, ...]", stages)
    if len(result) != len(set(result)):
        message = "Pathway reference activities must be unique"
        raise CredentialingContractError(message)
    return result


@dataclass(frozen=True, slots=True, kw_only=True)
class PathwayReference:
    """A source-linked reference with no implicit approval or operational rule."""

    reference_id: str
    version: str
    pathway_code: str
    authority_mapping_version: str
    source_reference: str
    required_stages: tuple[str, ...]
    permitted_activities: tuple[str, ...]
    terminal_activities: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject reference drift and require an explicit independent event model."""
        for value in (self.reference_id, self.authority_mapping_version, self.source_reference):
            _code(value)
        if _code(self.pathway_code) not in PATHWAY_CODES:
            _fail("Unknown credentialing pathway")
        if _VERSION.fullmatch(_code(self.version)) is None:
            _fail("Pathway model version must use semantic version syntax")
        required = _stage_tuple(self.required_stages)
        permitted = _stage_tuple(self.permitted_activities)
        terminal = _stage_tuple(self.terminal_activities)
        if not set(required).issubset(permitted) or not set(terminal).issubset(permitted):
            _fail("Required and terminal activities must be permitted by the reference")


def pathway_reference_payload(reference: PathwayReference) -> dict[str, object]:
    """Export only strict source-reference codes and registered activity arrays."""
    return {
        "reference_id": reference.reference_id,
        "version": reference.version,
        "pathway_code": reference.pathway_code,
        "authority_mapping_version": reference.authority_mapping_version,
        "source_reference": reference.source_reference,
        "required_stages": list(reference.required_stages),
        "permitted_activities": list(reference.permitted_activities),
        "terminal_activities": list(reference.terminal_activities),
    }


def _wire_stages(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        message = "Pathway wire activities must be arrays"
        raise CredentialingContractError(message)
    return _stage_tuple(tuple(cast("list[object]", value)))


def parse_pathway_reference(payload: Mapping[str, object]) -> PathwayReference:
    """Load an exact reference envelope; free text and unknown fields fail closed."""
    if frozenset(payload) != _FIELDS:
        message = "Pathway fields do not match the strict reference contract"
        raise CredentialingContractError(message)
    return PathwayReference(
        reference_id=_code(payload["reference_id"]),
        version=_code(payload["version"]),
        pathway_code=_code(payload["pathway_code"]),
        authority_mapping_version=_code(payload["authority_mapping_version"]),
        source_reference=_code(payload["source_reference"]),
        required_stages=_wire_stages(payload["required_stages"]),
        permitted_activities=_wire_stages(payload["permitted_activities"]),
        terminal_activities=_wire_stages(payload["terminal_activities"]),
    )


@dataclass(frozen=True, slots=True)
class PathwayAssessment:
    """Restricted case evidence with controlled deviations and no source content."""

    reference_id: str
    reference_version: str
    status: str
    deviations: tuple[str, ...]
    excluded_inferred_count: int
    observed_event_count: int


def _stage_deviations(
    observed: list[CredentialingFact],
    reference: PathwayReference,
) -> list[str]:
    deviations: list[str] = []
    previous = None
    for stage in reference.required_stages:
        matches = [fact for fact in observed if fact.activity == stage]
        if not matches:
            deviations.append(f"missing:{stage}")
            continue
        if len(matches) > 1:
            deviations.append(f"repeated:{stage}")
        timestamp = matches[0].timestamp_utc
        if previous is not None and timestamp <= previous:
            deviations.append(f"order:{stage}")
        previous = timestamp
    return deviations


def _deviations(observed: list[CredentialingFact], reference: PathwayReference) -> tuple[str, ...]:
    deviations = _stage_deviations(observed, reference)
    if any(fact.qualifiers.pathway_code != reference.pathway_code for fact in observed):
        deviations.append("pathway_mismatch")
    if any(
        fact.qualifiers.authority_mapping_version != reference.authority_mapping_version
        for fact in observed
    ):
        deviations.append("authority_mismatch")
    deviations.extend(
        f"unexpected:{fact.activity}"
        for fact in observed
        if fact.activity not in reference.permitted_activities
    )
    if len({fact.timestamp_utc for fact in observed}) != len(observed):
        deviations.append("ambiguous_event_order")
    if observed[-1].activity not in reference.terminal_activities:
        deviations.append("terminal_not_observed")
    if any(fact.activity in reference.terminal_activities for fact in observed[:-1]):
        deviations.append("activity_after_terminal")
    return tuple(sorted(set(deviations)))


def _assert_case_access(role: str, case_id: str, grants: object) -> None:
    if role != "case_analyst":
        _fail("Pathway assessment requires a trusted case_analyst role")
    _code(case_id)
    if not isinstance(grants, AbstractSet):
        _fail("Pathway case grants must be a set")
    granted = cast("AbstractSet[object]", grants)
    for item in granted:
        _code(item)
    if case_id not in granted:
        _fail("Pathway case is outside the trusted grant scope")


def assess_pathway(
    projection: CredentialingProjection,
    reference: PathwayReference,
    *,
    case_id: str,
    role: str,
    granted_case_ids: object,
) -> PathwayAssessment:
    """Compare one authorised case against its explicitly supplied pathway model.

    Trusted adapters must resolve role/grants, source mapping, reference authority
    and provenance before calling. A match describes this event sequence only.
    It does not approve a policy, infer clinical competence or mutate a source.
    """
    _assert_case_access(role, case_id, granted_case_ids)
    reference = parse_pathway_reference(pathway_reference_payload(reference))
    projection = validate_credentialing_projection(projection)
    linked = [fact for fact in projection.facts if case_id in fact.object_ids]
    observed = [fact for fact in linked if fact.observed_or_inferred == "observed"]
    excluded = len(linked) - len(observed)
    if not observed:
        return PathwayAssessment(
            reference.reference_id,
            reference.version,
            "insufficient_evidence",
            ("no_observed_evidence",),
            excluded,
            0,
        )
    deviations = _deviations(observed, reference)
    return PathwayAssessment(
        reference.reference_id,
        reference.version,
        "review_required" if deviations else "matches_reference",
        deviations,
        excluded,
        len(observed),
    )
