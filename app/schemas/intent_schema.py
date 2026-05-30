from typing import Literal, Dict, Any
from pydantic import BaseModel, Field, model_validator


class IntentSchema(BaseModel):

    action_type: Literal[
        "system_command",
        "ai_response",
        "web_navigation",
        "unknown"
    ]

    intent: str = Field(
        ...,
        pattern=r'^[a-z][a-z0-9_]*$',
        description="Machine-readable intent in snake_case"
    )
    query_type: Literal["static_knowledge", "realtime_data", "none"] = "none"

    requires_shell: bool

    shell_type: Literal["powershell", "cmd", "bash", "none"]

    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured extracted parameters"
    )

    risk_level: Literal["LOW", "MEDIUM", "HIGH"]

    confidence: Literal["LOW", "MEDIUM", "HIGH"]

    explanation: str = Field(..., min_length=10)

    @model_validator(mode="after")
    def validate_consistency(self):
        if self.action_type in ("ai_response", "web_navigation", "unknown"):
            if self.requires_shell:
                raise ValueError(f"{self.action_type} must have requires_shell=false")
            if self.shell_type != "none":
                raise ValueError(f"{self.action_type} must have shell_type='none'")

        if self.action_type == "web_navigation" and "url" not in self.parameters:
            raise ValueError("web_navigation must include 'url' in parameters")

        if self.action_type == "unknown" and self.parameters:
            raise ValueError("unknown action_type must have empty parameters")

        if self.action_type == "system_command" and not self.requires_shell:
            raise ValueError("system_command must have requires_shell=true")

        return self