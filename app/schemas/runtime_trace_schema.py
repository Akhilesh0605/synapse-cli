from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from datetime import datetime


class RuntimeStageTrace(BaseModel):

    # identity
    stage_name:   Literal[
        "intent_generation",
        "policy_evaluation",
        "shell_generation",
        "command_validation",
        "execution",
    ]
    stage_order:  int = Field(..., ge=1, le=5)  # position in pipeline

    # timing
    started_at:   float = Field(..., ge=0)       # unix timestamp
    completed_at: float = Field(..., ge=0)        # unix timestamp
    latency_ms:   int   = Field(..., ge=0)

    started_at_utc:   str
    completed_at_utc: str
    # result
    success:      bool
    error_message: Optional[str] = None

    # optional payload snapshot (for debugging)
    input_snapshot:  Optional[Dict[str, Any]] = None  # what entered the stage
    output_snapshot: Optional[Dict[str, Any]] = None  # what left the stage

    @model_validator(mode="after")
    def validate_timing(self):
        # completed must be after started
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be before started_at")

        # latency must match timestamps
        expected_ms = int((self.completed_at - self.started_at) * 1000)
        if abs(self.latency_ms - expected_ms) > 5:   # 5ms tolerance
            raise ValueError(
                f"latency_ms {self.latency_ms} doesn't match "
                f"timestamps (expected ~{expected_ms}ms)"
            )

        # failed stage must have error_message
        if not self.success and not self.error_message:
            raise ValueError("error_message is required when success=False")

        return self