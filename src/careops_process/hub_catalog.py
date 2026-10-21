# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Bounded immutable synthetic catalog; no persistence or live approval verification.

Changes affect selection for future matters only. Existing matters continue to
resolve their pinned version and digest through the unchanged domain contract.
Opaque review references are evidence pointers, not authentication assertions.
"""

from typing import Literal, Self

from pydantic import Field, TypeAdapter, model_validator

from careops_process.hub_capabilities import OpaqueReference  # noqa: TC001
from careops_process.hub_domain import (
    MetadataRecord,
    Revision,
    TemplateId,
    Version,
    WorkflowTemplate,
    template_digest,
)


class CatalogCommand(MetadataRecord):
    """Supply synthetic review evidence and a compare-and-swap revision."""

    request_ref: OpaqueReference
    expected_revision: Revision
    template_id: TemplateId
    version: Version
    synthetic_approval_ref: OpaqueReference
    action: Literal["activate", "rollback"] = "activate"
    migration_ref: OpaqueReference | None = None
    rollback_approval_ref: OpaqueReference | None = None


class TemplateCatalog(MetadataRecord):
    """Keep all registered definitions and reviewed selections in bounded tuples."""

    execution_mode: Literal["synthetic"] = "synthetic"
    revision: Revision = 0
    templates: tuple[WorkflowTemplate, ...] = Field(default=(), max_length=128)
    selections: tuple[CatalogCommand, ...] = Field(default=(), max_length=256)

    @model_validator(mode="after")
    def validate_catalog(self) -> Self:
        """Reject duplicate identities and contradictory imported selections."""
        keys = {(item.template_id, item.version) for item in self.templates}
        if len(keys) != len(self.templates) or self.revision != len(self.templates) + len(
            self.selections
        ):
            message = "inconsistent catalog revision or definitions"
            raise ValueError(message)
        seen: set[str] = set()
        selected: dict[str, WorkflowTemplate] = {}
        previous_revision = -1
        for index, entry in enumerate(self.selections):
            registered_count = entry.expected_revision - index
            if (
                entry.request_ref in seen
                or entry.expected_revision >= self.revision
                or entry.expected_revision <= previous_revision
                or not 0 < registered_count <= len(self.templates)
            ):
                message = "inconsistent catalog selection history"
                raise ValueError(message)
            target = resolve_template(self, entry.template_id, version=entry.version)
            if target not in self.templates[:registered_count]:
                message = "selection precedes template registration"
                raise ValueError(message)
            _validate_selection(target, selected.get(entry.template_id), entry)
            selected[entry.template_id] = target
            seen.add(entry.request_ref)
            previous_revision = entry.expected_revision
        return self


def resolve_template(
    catalog: TemplateCatalog, template_id: str, *, version: str | None = None
) -> WorkflowTemplate:
    """Resolve an active future selection or an explicitly pinned old definition."""
    if version is None:
        version = next(
            (
                item.version
                for item in reversed(catalog.selections)
                if item.template_id == template_id
            ),
            None,
        )
    template = next(
        (
            item
            for item in catalog.templates
            if item.template_id == template_id and item.version == version
        ),
        None,
    )
    if template is None:
        message = "unknown template identity or version"
        raise ValueError(message)
    return template


def register_template(
    catalog: TemplateCatalog, template: WorkflowTemplate, *, expected_revision: int
) -> TemplateCatalog:
    """Register once; identical content replay preserves the original snapshot."""
    template = WorkflowTemplate.model_validate(template.model_dump())
    expected_revision = TypeAdapter[int](Revision).validate_python(expected_revision)
    for existing in catalog.templates:
        if (existing.template_id, existing.version) == (template.template_id, template.version):
            if template_digest(existing) != template_digest(template):
                message = "registered template content cannot change"
                raise ValueError(message)
            return catalog
    _check_revision(catalog, expected_revision)
    return TemplateCatalog.model_validate(
        {
            **catalog.model_dump(),
            "revision": catalog.revision + 1,
            "templates": (*catalog.templates, template),
        }
    )


def _check_revision(catalog: TemplateCatalog, expected_revision: int) -> None:
    if expected_revision != catalog.revision:
        message = "stale catalog expected revision"
        raise ValueError(message)


def _validate_selection(
    target: WorkflowTemplate, current: WorkflowTemplate | None, command: CatalogCommand
) -> None:
    if not (
        target.approval_ref
        and target.authority_source_ref
        and target.records_policy_ref
        and target.roles
        and target.rules
        and target.outcomes
    ):
        message = "activation requires an approved configured template"
        raise ValueError(message)
    if current is None:
        if command.action == "rollback":
            message = "rollback requires a previously active template"
            raise ValueError(message)
        return
    if target.template_id != current.template_id or target.schema_version != current.schema_version:
        message = "template identity or schema is incompatible"
        raise ValueError(message)
    before = tuple(map(int, current.version.split(".")))
    after = tuple(map(int, target.version.split(".")))
    if command.action == "rollback":
        if after >= before or not command.rollback_approval_ref:
            message = "rollback requires approval and a lower registered version"
            raise ValueError(message)
    elif after <= before:
        message = "lower or equal version requires explicit rollback"
        raise ValueError(message)
    if not command.migration_ref:
        message = "reviewed migration reference required"
        raise ValueError(message)


def activate_template(catalog: TemplateCatalog, command: CatalogCommand) -> TemplateCatalog:
    """Select a reviewed synthetic version without modifying any existing matter."""
    command = CatalogCommand.model_validate(command.model_dump())
    for recorded in catalog.selections:
        if recorded.request_ref == command.request_ref:
            if recorded != command:
                message = "catalog request reference collision"
                raise ValueError(message)
            return catalog
    _check_revision(catalog, command.expected_revision)
    target = resolve_template(catalog, command.template_id, version=command.version)
    current_version = next(
        (
            entry.version
            for entry in reversed(catalog.selections)
            if entry.template_id == command.template_id
        ),
        None,
    )
    current = (
        resolve_template(catalog, command.template_id, version=current_version)
        if current_version
        else None
    )
    _validate_selection(target, current, command)
    return TemplateCatalog.model_validate(
        {
            **catalog.model_dump(),
            "revision": catalog.revision + 1,
            "selections": (*catalog.selections, command),
        }
    )
