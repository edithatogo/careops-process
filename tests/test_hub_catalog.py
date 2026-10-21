# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic catalog activation and immutable version regression tests."""

import pytest
from pydantic import ValidationError

from careops_process.hub_catalog import (
    CatalogCommand,
    TemplateCatalog,
    activate_template,
    register_template,
    resolve_template,
)
from careops_process.hub_domain import (
    TransitionRule,
    WorkflowTemplate,
    create_matter,
    draft_templates,
    template_digest,
)


def configured(version: str = "1.0.0") -> WorkflowTemplate:
    """Return a minimal explicitly synthetic policy fixture."""
    return WorkflowTemplate(
        template_id="review_action",
        version=version,
        authority_source_ref="synthetic-authority",
        approval_ref="synthetic-approval",
        records_policy_ref="synthetic-records",
        roles=("synthetic-role",),
        outcomes=("noting",),
        rules=(
            TransitionRule(
                from_state="draft", to_state="submitted", allowed_roles=("synthetic-role",)
            ),
        ),
    )


def command(revision: int, version: str = "1.0.0", **changes: object) -> CatalogCommand:
    """Construct a validated activation command."""
    return CatalogCommand.model_validate(
        {
            "request_ref": f"synthetic-request-{revision}",
            "expected_revision": revision,
            "template_id": "review_action",
            "version": version,
            "synthetic_approval_ref": "synthetic-approval",
            **changes,
        }
    )


def test_register_and_activate() -> None:
    """Registration is immutable, content checked and replay safe."""
    empty = TemplateCatalog()
    template = configured()
    catalog = register_template(empty, template, expected_revision=0)
    assert empty.templates == ()
    assert register_template(catalog, template, expected_revision=0) is catalog
    active = activate_template(catalog, command(1))
    assert activate_template(active, command(1)) is active
    assert resolve_template(active, "review_action") == template
    assert resolve_template(active, "review_action", version="1.0.0") == template
    with pytest.raises(ValueError, match="content"):
        register_template(
            catalog, template.model_copy(update={"approval_ref": "changed"}), expected_revision=1
        )
    with pytest.raises(ValueError, match="revision"):
        register_template(catalog, configured("2.0.0"), expected_revision=0)


def test_upgrade_and_rollback() -> None:
    """Reviewed changes preserve every pinned definition."""
    catalog = register_template(TemplateCatalog(), configured(), expected_revision=0)
    catalog = activate_template(catalog, command(1))
    catalog = register_template(catalog, configured("2.0.0"), expected_revision=2)
    with pytest.raises(ValueError, match="migration"):
        activate_template(catalog, command(3, "2.0.0"))
    catalog = activate_template(catalog, command(3, "2.0.0", migration_ref="reviewed-migration"))
    with pytest.raises(ValueError, match="rollback"):
        activate_template(catalog, command(4))
    with pytest.raises(ValueError, match="migration"):
        activate_template(
            catalog, command(4, action="rollback", rollback_approval_ref="synthetic-rollback")
        )
    catalog = activate_template(
        catalog,
        command(
            4,
            action="rollback",
            migration_ref="reviewed-migration",
            rollback_approval_ref="synthetic-rollback",
        ),
    )
    assert resolve_template(catalog, "review_action").version == "1.0.0"
    assert resolve_template(catalog, "review_action", version="2.0.0").version == "2.0.0"


def test_drafts_unknown_and_protected_payloads() -> None:
    """Unapproved drafts and narrative payloads fail closed."""
    catalog = register_template(TemplateCatalog(), draft_templates()[-1], expected_revision=0)
    with pytest.raises(ValueError, match="configured"):
        activate_template(catalog, command(1, "0.1.0"))
    with pytest.raises(ValueError, match="unknown"):
        resolve_template(catalog, "missing")
    with pytest.raises(ValueError, match="unknown"):
        activate_template(catalog, command(1))
    with pytest.raises(ValidationError):
        command(1, patient_notes="protected")
    with pytest.raises(ValidationError):
        TemplateCatalog.model_validate({"patient_notes": "protected"})


def test_collision_and_stale_activation() -> None:
    """A request cannot be reused with different content or stale revisions."""
    catalog = register_template(TemplateCatalog(), configured(), expected_revision=0)
    active = activate_template(catalog, command(1))
    with pytest.raises(ValueError, match="collision"):
        activate_template(active, command(1, synthetic_approval_ref="changed"))
    with pytest.raises(ValueError, match="revision"):
        activate_template(active, command(1, request_ref="other-request"))
    with pytest.raises(ValueError, match="rollback"):
        activate_template(active, command(2, request_ref="other-request"))


def test_pinned_matter_survives_selection_changes() -> None:
    """Selection changes leave canonical matter provenance untouched."""
    original = configured()
    matter = create_matter(
        matter_id="synthetic-matter",
        scope_ref="synthetic-scope",
        classification="low_sensitivity_metadata",
        source_ref="synthetic-source",
        template=original,
    )
    catalog = register_template(TemplateCatalog(), original, expected_revision=0)
    catalog = activate_template(catalog, command(1))
    catalog = register_template(catalog, configured("2.0.0"), expected_revision=2)
    catalog = activate_template(catalog, command(3, "2.0.0", migration_ref="reviewed"))
    assert matter.template_version == "1.0.0"
    assert matter.template_digest == template_digest(
        resolve_template(catalog, matter.template_id, version=matter.template_version)
    )


@pytest.mark.parametrize("field", ["authority_source_ref", "records_policy_ref", "approval_ref"])
def test_incomplete_policy_denied(field: str) -> None:
    """Approval pointers alone cannot activate incomplete policy."""
    template = WorkflowTemplate.model_validate({**configured().model_dump(), field: None})
    catalog = register_template(TemplateCatalog(), template, expected_revision=0)
    with pytest.raises(ValueError, match="configured"):
        activate_template(catalog, command(1))


@pytest.mark.parametrize("field", ["rules", "roles", "outcomes"])
def test_empty_configuration_denied(field: str) -> None:
    """Missing executable rules or decision semantics cannot be selected."""
    values = {**configured().model_dump(), field: ()}
    if field == "roles":
        values["rules"] = ()
    template = WorkflowTemplate.model_validate(values)
    catalog = register_template(TemplateCatalog(), template, expected_revision=0)
    with pytest.raises(ValueError, match="configured"):
        activate_template(catalog, command(1))


def test_validated_boundaries_and_history() -> None:
    """Reject schema tampering, missing fields, malformed refs and forged history."""
    with pytest.raises(ValidationError):
        CatalogCommand.model_validate({})
    with pytest.raises(ValidationError):
        command(0, migration_ref="https://example.invalid/patient narrative")
    with pytest.raises(ValidationError):
        register_template(
            TemplateCatalog(),
            configured().model_copy(update={"schema_version": 2}),
            expected_revision=0,
        )
    catalog = register_template(TemplateCatalog(), configured(), expected_revision=0)
    with pytest.raises(ValueError, match="unknown"):
        activate_template(catalog, command(1, template_id="clinical_risk"))
    with pytest.raises(ValueError, match="unknown"):
        resolve_template(catalog, "review_action", version="9.0.0")
    with pytest.raises(ValueError, match="rollback"):
        activate_template(catalog, command(1, action="rollback"))
    with pytest.raises(ValidationError):
        TemplateCatalog(revision=2, templates=catalog.templates, selections=(command(0),))
    with pytest.raises(ValidationError):
        catalog.revision = 9
