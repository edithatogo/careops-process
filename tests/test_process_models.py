"""Validate versioned process-model artifacts."""

from pathlib import Path
from typing import TYPE_CHECKING, cast

from defusedxml import ElementTree

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

MODEL = Path(__file__).parents[1] / "docs" / "process-models" / "careops-process-mining.bpmn"
TASK_COUNT = 7
FLOW_COUNT = 8


def test_bpmn_model_is_well_formed_and_has_linear_pipeline() -> None:
    """Ensure the BPMN model contains the complete governed pipeline."""
    root = cast("Element", ElementTree.parse(MODEL).getroot())
    namespace = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
    process = root.find(f"{namespace}process")
    assert process is not None
    assert len(process.findall(f"{namespace}task")) == TASK_COUNT
    assert len(process.findall(f"{namespace}sequenceFlow")) == FLOW_COUNT
    assert process.find(f"{namespace}startEvent") is not None
    assert process.find(f"{namespace}endEvent") is not None
