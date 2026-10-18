# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic, privacy-minimised triage and executive views without external connectors."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import Field, StrictBool, model_validator

from careops_process.hub_capabilities import (
    OpaqueReference,  # noqa: TC001 # Pydantic runtime schema.
)
from careops_process.hub_domain import (
    GovernanceMatter,
    MetadataRecord,
    State,
    TemplateId,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

Trigger = Literal[
    "district_threshold",
    "urgent_criteria_met",
    "executive_decision_required",
    "assurance_only",
    "operational_delegation",
]
Route = Literal[
    "district",
    "urgent_out_of_session",
    "scheduled_agenda",
    "assurance",
    "operational",
    "hold_for_triage",
]


class AttentionContext(MetadataRecord):
    """Carry explicit evaluated trigger flags, without copying evidence or narrative."""

    district_threshold: StrictBool = False
    urgent_criteria_met: StrictBool = False
    executive_decision_required: StrictBool = False
    assurance_only: StrictBool = False
    operational_delegation: StrictBool = False


class TriageRule(MetadataRecord):
    """Reference a configured authority for one explicitly evaluated trigger."""

    trigger: Trigger
    route: Route
    owner_role: OpaqueReference
    authority_ref: OpaqueReference


class RoutingPolicy(MetadataRecord):
    """Keep priority, roles and authorities as explicit synthetic configuration."""

    execution_mode: Literal["synthetic"] = "synthetic"
    scope_ref: OpaqueReference
    policy_ref: OpaqueReference
    rules: tuple[TriageRule, ...]

    @model_validator(mode="after")
    def require_distinct_triggers(self) -> Self:
        """Reject ambiguous duplicates in ordered triage rules."""
        if len({rule.trigger for rule in self.rules}) != len(self.rules):
            message = "routing triggers must be distinct"
            raise ValueError(message)
        return self


class TriageResult(MetadataRecord):
    """Return a scoped route and its provenance without claiming live authority."""

    execution_mode: Literal["synthetic"] = "synthetic"
    matter_id: OpaqueReference
    route: Route
    owner_role: OpaqueReference | None = None
    authority_ref: OpaqueReference | None = None
    policy_ref: OpaqueReference


def triage(
    matter: GovernanceMatter, context: AttentionContext, policy: RoutingPolicy
) -> TriageResult:
    """Select the first matched configured rule, or hold when no approved route applies."""
    if matter.scope_ref != policy.scope_ref:
        message = "routing policy scope does not permit this matter"
        raise ValueError(message)
    selected = next((rule for rule in policy.rules if getattr(context, rule.trigger)), None)
    if matter.classification == "unconfirmed" or selected is None:
        return TriageResult(
            matter_id=matter.matter_id, route="hold_for_triage", policy_ref=policy.policy_ref
        )
    return TriageResult(
        matter_id=matter.matter_id,
        route=selected.route,
        owner_role=selected.owner_role,
        authority_ref=selected.authority_ref,
        policy_ref=policy.policy_ref,
    )


class PortfolioItem(MetadataRecord):
    """Expose fixed attention reason codes and low-sensitivity identifiers only."""

    matter_id: OpaqueReference
    state: State
    template_id: TemplateId
    reasons: tuple[str, ...]
    overdue_action_count: int


def _scoped_unique(
    matters: Sequence[GovernanceMatter],
    scope_ref: str,
) -> tuple[GovernanceMatter, ...]:
    records = tuple(matter for matter in matters if matter.scope_ref == scope_ref)
    if len({matter.matter_id for matter in records}) != len(records):
        message = "duplicate canonical matter in selected scope"
        raise ValueError(message)
    return records


def build_portfolio(  # noqa: C901 # Evaluate independently specified attention reasons.
    matters: Sequence[GovernanceMatter],
    *,
    actor_scope_ref: str,
    now: datetime,
) -> tuple[PortfolioItem, ...]:
    """Return material and actionable exceptions for one authorised low-sensitivity scope."""
    if now.tzinfo is None or now.utcoffset() is None:
        message = "portfolio evaluation requires timezone-aware time"
        raise ValueError(message)
    items: list[PortfolioItem] = []
    records = _scoped_unique(matters, actor_scope_ref)
    dependency_states = {
        matter.matter_id: matter.state
        for matter in records
        if matter.classification == "low_sensitivity_metadata"
    }
    for matter in records:
        if (
            matter.scope_ref != actor_scope_ref
            or matter.classification != "low_sensitivity_metadata"
        ):
            continue
        if matter.state in {
            "closed",
            "archived",
            "withdrawn",
            "rejected",
            "cancelled",
            "superseded",
            "consolidated",
        }:
            continue
        reasons: list[str] = []
        overdue = sum(
            action.state in {"assigned", "in_progress"} and action.due_at < now
            for action in matter.actions
        )
        if matter.risk in {"material", "higher"}:
            reasons.append(f"{matter.risk}_risk")
        if matter.state == "decision_required":
            reasons.append("decision_required")
        if matter.state == "provisionally_decided":
            reasons.append("ratification_gap")
        if matter.state == "assurance_review":
            reasons.append("assurance_review")
        if overdue:
            reasons.append("overdue_actions")
        if any(
            link.relation == "depends_on"
            and dependency_states.get(link.matter_id) not in {"closed", "archived"}
            for link in matter.linked_matters
        ):
            reasons.append("dependencies")
        if reasons:
            items.append(
                PortfolioItem(
                    matter_id=matter.matter_id,
                    state=matter.state,
                    template_id=matter.template_id,
                    reasons=tuple(sorted(reasons)),
                    overdue_action_count=overdue,
                )
            )
    return tuple(sorted(items, key=lambda item: item.matter_id))


def build_secretariat_queue(
    matters: Sequence[GovernanceMatter],
    *,
    actor_scope_ref: str,
) -> tuple[PortfolioItem, ...]:
    """Keep routine intake, preparation and confirmation work in a separate scoped queue."""
    reasons = {
        "submitted": "intake_triage",
        "returned": "return_information",
        "decision_required": "agenda_preparation",
        "provisionally_decided": "decision_confirmation",
        "actions_open": "action_followup",
        "assurance_review": "assurance_review",
    }
    return tuple(
        PortfolioItem(
            matter_id=matter.matter_id,
            state=matter.state,
            template_id=matter.template_id,
            reasons=(reasons[matter.state],),
            overdue_action_count=0,
        )
        for matter in _scoped_unique(matters, actor_scope_ref)
        if (
            matter.scope_ref == actor_scope_ref
            and matter.classification == "low_sensitivity_metadata"
            and matter.state in reasons
        )
    )


class DigestPolicy(MetadataRecord):
    """Require explicit frequency and notification volume limits."""

    enabled: StrictBool
    maximum_items: Annotated[int, Field(strict=True, ge=1, le=100)]
    interval_days: Annotated[int, Field(strict=True, ge=1, le=31)]


class ExecutiveDigest(MetadataRecord):
    """Return one deduplicatable digest candidate; no notification is sent here."""

    execution_mode: Literal["synthetic"] = "synthetic"
    digest_key: str
    items: tuple[PortfolioItem, ...]
    omitted_count: int


def build_digest(
    matters: Sequence[GovernanceMatter],
    *,
    actor_scope_ref: str,
    policy: DigestPolicy,
    now: datetime,
    previous_digest_key: str | None = None,
) -> ExecutiveDigest | None:
    """Suppress disabled, empty and previously emitted intervals; cap each candidate's size."""
    if not policy.enabled:
        return None
    items = build_portfolio(matters, actor_scope_ref=actor_scope_ref, now=now)
    if not items:
        return None
    interval_seconds = policy.interval_days * 24 * 60 * 60
    interval = int(now.timestamp()) // interval_seconds
    digest_key = hashlib.sha256(
        f"{actor_scope_ref}:{interval}:{policy.model_dump_json()}".encode()
    ).hexdigest()
    if digest_key == previous_digest_key:
        return None
    return ExecutiveDigest(
        digest_key=digest_key,
        items=items[: policy.maximum_items],
        omitted_count=max(0, len(items) - policy.maximum_items),
    )


def render_decision_brief(matter: GovernanceMatter, *, actor_scope_ref: str) -> str:
    """Render a one-page brief scaffold without retrieving protected decision evidence."""
    if matter.scope_ref != actor_scope_ref:
        message = "brief requires authorised scope"
        raise ValueError(message)
    if matter.classification != "low_sensitivity_metadata":
        message = "brief requires approved low-sensitivity classification"
        raise ValueError(message)
    return (
        f"# Decision brief — {matter.matter_id}\n\n"
        f"Pathway: {matter.template_id}; state: {matter.state}; revision: {matter.revision}.\n\n"
        "| Brief field | Controlled record |\n| --- | --- |\n"
        "| Question | Approved brief reference required |\n"
        "| Recommendation | Approved recommendation reference required |\n"
        "| Alternatives | Approved options reference required |\n"
        "| Risks | Approved risk assessment reference required |\n"
        "| Authority | Existing delegation or terms-of-reference record required |\n"
        "| Conflicts | Current declarations and recusals record required |\n"
        "| Consultations | Protected consultation references required |\n"
        "| Proposed actions | Canonical action records required |\n"
    )
