import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class PipelineStage:
    def __init__(self, name: str, fn: Callable, required: bool = True):
        self.name = name
        self.fn = fn
        self.required = required

    def run(self, state: dict, trace: list[dict]) -> Any:
        start = time.monotonic()
        try:
            result = self.fn(state)
            elapsed = time.monotonic() - start
            trace.append(
                {
                    "step": self.name,
                    "status": "completed",
                    "duration_ms": round(elapsed * 1000, 2),
                }
            )
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            trace.append(
                {
                    "step": self.name,
                    "status": "failed",
                    "error": str(e),
                    "duration_ms": round(elapsed * 1000, 2),
                }
            )
            logger.error("Pipeline stage '%s' failed: %s", self.name, e, exc_info=True)
            if self.required:
                raise
            return None


class Pipeline:
    def __init__(self, stages: list[PipelineStage]):
        self.stages = stages

    def run(self, initial_state: dict) -> tuple[dict, list[dict]]:
        state = dict(initial_state)
        trace: list[dict] = []

        total_start = time.monotonic()
        for stage in self.stages:
            result = stage.run(state, trace)
            if result is not None:
                state[stage.name] = result

        total_elapsed = time.monotonic() - total_start
        trace.append(
            {
                "step": "pipeline_total",
                "status": "completed",
                "duration_ms": round(total_elapsed * 1000, 2),
                "stages_executed": len([t for t in trace if t.get("step") != "pipeline_total"]),
            }
        )

        return state, trace
