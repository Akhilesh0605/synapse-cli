"""Docker-backed sandboxed command execution."""
import logging
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

from app.execution.process_monitor import ProcessMonitor
from app.execution.timeout_manager import TimeoutManager
from app.schemas.command_schema import ShellCommandSchema
from app.schemas.execution_policy_schema import ExecutionPolicyResult
from app.schemas.execution_schema import ExecutionResult

logger = logging.getLogger(__name__)


class SandboxExecutor:
    """Execute shell commands inside a locked-down Docker container."""

    IMAGE_NAME = ProcessMonitor.SANDBOX_IMAGE
    DOCKERFILE_NAME = "Dockerfile.sandbox"

    @classmethod
    def _project_root(cls) -> Path:
        return Path(__file__).resolve().parents[2]

    @classmethod
    def _blocked_result(
        cls,
        schema: ShellCommandSchema,
        started_at: datetime,
        start_time: float,
        message: str,
        timed_out: bool = False,
        killed: bool = False,
    ) -> ExecutionResult:
        end_time = time.time()
        return ExecutionResult(
            request_id=str(uuid.uuid4()),
            success=False,
            stdout="",
            stderr=message,
            return_code=-1,
            execution_time_ms=int((end_time - start_time) * 1000),
            timed_out=timed_out,
            killed=killed,
            command=schema.command,
            shell_type=schema.shell_type,
            retry_attempt=schema.retry_attempt,
            error_message=message,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    @classmethod
    def _ensure_image(cls) -> tuple[bool, str | None]:
        if ProcessMonitor.is_sandbox_image_built():
            return True, None

        logger.info("Building sandbox image - first run only")
        project_root = cls._project_root()
        dockerfile = project_root / cls.DOCKERFILE_NAME

        try:
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "-f",
                    str(dockerfile),
                    "-t",
                    cls.IMAGE_NAME,
                    str(project_root),
                ],
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=600,
            )
        except FileNotFoundError:
            return False, "Docker is not installed or not available on PATH."
        except subprocess.TimeoutExpired:
            return False, "Sandbox image build timed out."

        if result.returncode != 0:
            details = (result.stderr or result.stdout or "Sandbox image build failed.").strip()
            return False, details

        return True, None

    @classmethod
    def _build_docker_command(cls, schema: ShellCommandSchema) -> list[str]:
        shell_type = schema.shell_type.lower()
        if shell_type == "powershell":
            return ["pwsh", "-Command", schema.command]
        if shell_type == "cmd":
            return ["bash", "-c", schema.command]
        return ["bash", "-c", schema.command]

    @classmethod
    def execute(cls, schema: ShellCommandSchema, policy: ExecutionPolicyResult) -> ExecutionResult:
        start_time = time.time()
        started_at = datetime.now()

        if not ProcessMonitor.is_docker_available():
            return cls._blocked_result(
                schema,
                started_at,
                start_time,
                "Docker is not available on this host.",
            )

        image_ready, build_error = cls._ensure_image()
        if not image_ready:
            return cls._blocked_result(schema, started_at, start_time, build_error or "Sandbox image unavailable.")

        timeout = TimeoutManager.resolve_timeout(policy)
        workspace = cls._project_root()
        inner_command = cls._build_docker_command(schema)
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--memory=256m",
            "--cpus=0.5",
            "--read-only",
            "--tmpfs",
            "/tmp:size=64m",
            "-v",
            f"{str(workspace)}:/workspace:ro",
            "--user",
            "sandbox",
            "-w",
            "/workspace",
            cls.IMAGE_NAME,
            *inner_command,
        ]

        logger.info("Executing sandboxed command: %s", schema.command)

        try:
            result = subprocess.run(
                docker_cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )

            end_time = time.time()
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            success = result.returncode == 0
            oom_killed = result.returncode == 137 or "OOMKilled" in stdout or "OOMKilled" in stderr

            if oom_killed:
                stderr = stderr or "Sandbox container was OOM killed."

            return ExecutionResult(
                request_id=str(uuid.uuid4()),
                success=success and not oom_killed,
                stdout=stdout,
                stderr=stderr,
                return_code=result.returncode,
                execution_time_ms=int((end_time - start_time) * 1000),
                timed_out=False,
                killed=oom_killed,
                command=schema.command,
                shell_type=schema.shell_type,
                retry_attempt=schema.retry_attempt,
                error_message=None if success and not oom_killed else (stderr or f"Sandbox execution failed with exit code {result.returncode}."),
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except subprocess.TimeoutExpired:
            return cls._blocked_result(
                schema,
                started_at,
                start_time,
                f"Sandbox execution timed out after {timeout}s.",
                timed_out=True,
            )
        except FileNotFoundError:
            return cls._blocked_result(
                schema,
                started_at,
                start_time,
                "Docker is not available on this host.",
            )
        except Exception as exc:
            logger.exception("Sandbox execution failed")
            return cls._blocked_result(
                schema,
                started_at,
                start_time,
                f"Unexpected sandbox error: {exc}",
            )