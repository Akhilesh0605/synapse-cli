import time
import subprocess
import logging
from typing import Optional

from app.schemas.execution_schema import ExecutionResult
from app.schemas.command_schema import ShellCommandSchema
from app.execution.timeout_manager import TimeoutManager
from app.schemas.execution_policy_schema import ExecutionPolicyResult

logger = logging.getLogger(__name__)




class CommandExecutor:

    @classmethod
    def _build_cmd_list(cls, schema: ShellCommandSchema) -> list:
        """Never use shell=True — always invoke shell explicitly."""
        if schema.shell_type == "powershell":
            return ["powershell", "-NoProfile", "-Command", schema.command]
        elif schema.shell_type == "cmd":
            return ["cmd", "/c", schema.command]
        else:  # bash
            return ["bash", "-c", schema.command]

    @classmethod
    def execute(cls, schema: ShellCommandSchema,policy:ExecutionPolicyResult) -> ExecutionResult:
        import uuid
        from datetime import datetime

        timeout   = TimeoutManager.resolve_timeout(policy)
        cmd_list  = cls._build_cmd_list(schema)
        start     = time.time()
        started_at = datetime.now()

        logger.info("Executing: '%s' | shell: %s | timeout: %ss",
                    schema.command, schema.shell_type, timeout)

        try:
            result = subprocess.run(
                cmd_list,
                shell          = False,
                capture_output = True,
                text           = True,
                timeout        = timeout,
                encoding="utf-8",
                errors="replace",
            )

            end        = time.time()
            completed_at = datetime.now()
            success    = result.returncode == 0

            logger.info("Exit code: %d | latency: %dms",
                        result.returncode, int((end - start) * 1000))

            return ExecutionResult(
                request_id         = str(uuid.uuid4()),
                success            = success,
                stdout             = result.stdout.strip(),
                stderr             = result.stderr.strip(),
                return_code        = result.returncode,
                execution_time_ms  = int((end - start) * 1000),
                timed_out          = False,
                killed             = False,
                command            = schema.command,
                shell_type         = schema.shell_type,
                retry_attempt      = schema.retry_attempt,
                error_message      = result.stderr.strip() if not success else None,
                started_at         = started_at,
                completed_at       = completed_at,
            )

        except subprocess.TimeoutExpired:
            end = time.time()
            completed_at = datetime.now()
            logger.warning("Command timed out after %ss: '%s'", timeout, schema.command)
            return ExecutionResult(
                request_id         = str(uuid.uuid4()),
                success           = False,
                stdout            = "",
                stderr            = f"Command timed out after {timeout}s.",
                return_code       = -1,
                execution_time_ms = int((end - start) * 1000),
                timed_out         = True,
                killed            = False,   # ← timeout ≠ killed
                command           = schema.command,
                shell_type        = schema.shell_type,
                retry_attempt     = schema.retry_attempt,
                error_message     = f"Execution timeout exceeded ({timeout}s).",
                started_at        = started_at,
                completed_at      = completed_at,
            )

        except Exception as e:
            end = time.time()
            completed_at = datetime.now()
            logger.error("Unexpected executor error: %s", e)
            return ExecutionResult(
                request_id         = str(uuid.uuid4()),
                success           = False,
                stdout            = "",
                stderr            = str(e),
                return_code       = -1,
                execution_time_ms = int((end - start) * 1000),
                timed_out         = False,
                killed            = False,
                command           = schema.command,
                shell_type        = schema.shell_type,
                retry_attempt     = schema.retry_attempt,
                error_message     = f"Unexpected error: {e}",
                started_at        = started_at,
                completed_at      = completed_at,
            )