import time
import subprocess
import logging
from typing import Optional

from app.schemas.execution_schema import ExecutionResult
from app.schemas.command_schema import ShellCommandSchema
from app.execution.timeout_manager import TimeoutManager
from app.schemas.execution_policy_schema import ExecutionPolicyResult

logger = logging.getLogger(__name__)


class PolicyViolationError(RuntimeError):
    pass




class CommandExecutor:

    @classmethod
    def _enforce_policy(cls, schema: ShellCommandSchema, policy: ExecutionPolicyResult) -> None:
        base_command = schema.command.strip().split()[0].lower()

        network_commands = {
            "curl", "wget", "ping", "nslookup", "netstat", "ipconfig", "ifconfig", "ip"
        }
        write_commands = {
            "new-item", "mkdir", "copy-item", "move-item", "cp", "mv"
        }
        launch_commands = {"start", "start-process", "open", "explorer"}

        if not policy.allow_network and base_command in network_commands:
            raise PolicyViolationError("Network access is not allowed by policy.")

        if not policy.allow_filesystem_write and base_command in write_commands:
            raise PolicyViolationError("Filesystem write is not allowed by policy.")

        if not policy.allow_process_spawn and base_command in launch_commands:
            raise PolicyViolationError("Process spawn is not allowed by policy.")

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
            cls._enforce_policy(schema, policy)
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

        except PolicyViolationError as e:
            end = time.time()
            completed_at = datetime.now()
            logger.warning("Policy violation: %s", e)
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
                error_message     = str(e),
                started_at        = started_at,
                completed_at      = completed_at,
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