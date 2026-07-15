"""CareOps object-centric process intelligence."""

from careops_process.events import EventFrameError, validate_events
from careops_process.pipeline import PipelineResult, run_pipeline

__all__ = ["EventFrameError", "PipelineResult", "run_pipeline", "validate_events"]
