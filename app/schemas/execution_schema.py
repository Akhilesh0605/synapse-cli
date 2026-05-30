from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ExecutionResult(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    request_id:str

    # core result
    success:            bool
    stdout:             str  = ""
    stderr:             str  = ""
    return_code:        int

    # timing
    execution_time_ms:  int  = Field(..., ge=0)

    # termination flags
    timed_out:          bool = False
    killed:             bool = False

    # context
    command:            str                  # what was actually executed
    shell_type:         str                  # powershell / bash / cmd
    retry_attempt:      int  = Field(0, ge=0, le=2)

    started_at: datetime
    completed_at: datetime

    # failure reason (populated when success=False)
    error_message:      Optional[str] = None