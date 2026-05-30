from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional


class ShellCommandSchema(BaseModel):

    shell_type: Literal["powershell", "cmd", "bash"]

    command: str = Field(
        ...,
        min_length=2,
        description="Single shell command — no && or ; chaining"
    )

    explanation: str = Field(..., min_length=10)

    expected_risk: Literal["LOW", "MEDIUM", "HIGH"]

    requires_confirmation: bool

    requires_sudo: bool = False

    confidence: Literal["LOW", "MEDIUM", "HIGH"]


    retry_attempt: int = Field(
        default=0,
        ge=0,
        le=2,
        description="0 = first attempt, 1-2 = retry after execution failure"
    )

    error_context: Optional[str] = Field(
        default=None,
        description="stderr from previous failed attempt, passed in on retry"
    )

    @model_validator(mode="after")
    def validate_consistency(self):
        # Block command chaining
        if any(op in self.command for op in ["&&", "||", ";;", ">>", "$(", "\n"]):
            raise ValueError(
                "command must be a single command — chaining operators not allowed"
            )

        # Semicolons allowed in PowerShell/CMD but not bash pipelines
        if self.shell_type == "bash" and ";" in self.command:
            raise ValueError(
                "bash command must not contain semicolons — use single commands only"
            )

        # Sudo only valid in bash
        if self.requires_sudo and self.shell_type != "bash":
            raise ValueError(
                f"requires_sudo=True is only valid for bash, not '{self.shell_type}'"
            )

        # retry_attempt > 0 must carry error_context
        if self.retry_attempt > 0 and not self.error_context:
            raise ValueError(
                "error_context is required when retry_attempt > 0"
            )

        # HIGH risk must require confirmation
        if self.expected_risk == "HIGH" and not self.requires_confirmation:
            raise ValueError(
                "HIGH risk commands must have requires_confirmation=True"
            )

        return self