from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ExecutionMode(str, Enum):
    """
    Runtime execution modes.

    NORMAL
        Direct execution with minimal restrictions.

    RESTRICTED
        Governed execution with limited permissions.

    SANDBOXED
        Isolated execution environment required.

    DRY_RUN
        Validate and simulate only — never execute.
    """

    NORMAL     = "normal"
    RESTRICTED = "restricted"
    SANDBOXED  = "sandboxed"
    DRY_RUN    = "dry_run"




class ExecutionPolicyResult(BaseModel):
    """
    Deterministic runtime execution contract.

    This object defines:
    - whether execution is allowed
    - runtime restrictions
    - execution isolation requirements
    - operational governance constraints
    """


    allowed: bool

    execution_mode: ExecutionMode

    timeout_seconds: int = Field(..., ge=1, le=300)

    requires_confirmation: bool = False


    allow_network: bool = False

    allow_filesystem_write: bool = False

    allow_process_spawn: bool = False



    sandbox_required: bool = False

    dry_run: bool = False

    max_stdout_bytes: int = 1024 * 1024   # 1MB

    max_stderr_bytes: int = 1024 * 512    # 512KB



    governance_reason: Optional[str] = None

    risk_level: Optional[str] = None

    capability: Optional[str] = None

    policy_source: Optional[str] = None



    @model_validator(mode="after")
    def validate_policy_consistency(self):



        if not self.allowed and not self.governance_reason:
            raise ValueError(
                "governance_reason is required when allowed=False"
            )

        if (
            self.execution_mode == ExecutionMode.SANDBOXED
            and not self.sandbox_required
        ):
            raise ValueError(
                "sandbox_required must be True in SANDBOXED mode"
            )
        if self.execution_mode == ExecutionMode.DRY_RUN:

            if any([
                self.allow_network,
                self.allow_filesystem_write,
                self.allow_process_spawn,
            ]):
                raise ValueError(
                    "DRY_RUN mode cannot allow network, "
                    "filesystem writes, or process spawning"
                )

            if not self.dry_run:
                raise ValueError(
                    "dry_run flag must be True in DRY_RUN mode"
                )
        if not self.allowed:

            if any([
                self.allow_network,
                self.allow_filesystem_write,
                self.allow_process_spawn,
            ]):
                raise ValueError(
                    "Permission flags must all be False "
                    "when allowed=False"
                )

        return self

