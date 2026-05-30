import pytest
import sys
from app.execution.executor import CommandExecutor
from app.schemas.command_schema import ShellCommandSchema
from app.schemas.execution_schema import ExecutionResult

import uuid
from datetime import datetime

def make_schema(shell_type, command, **kwargs):
	# Helper to create a valid ShellCommandSchema
	return ShellCommandSchema(
		shell_type=shell_type,
		command=command,
		explanation=kwargs.get("explanation", "Test command execution."),
		expected_risk=kwargs.get("expected_risk", "LOW"),
		requires_confirmation=kwargs.get("requires_confirmation", False),
		requires_sudo=kwargs.get("requires_sudo", False),
		confidence=kwargs.get("confidence", "HIGH"),
		retry_attempt=kwargs.get("retry_attempt", 0),
		error_context=kwargs.get("error_context", None),
	)

def patch_result_with_times(result: ExecutionResult):
	# Patch result with required datetime fields for test
	now = datetime.now()
	result.request_id = str(uuid.uuid4())
	result.started_at = now
	result.completed_at = now
	return result

@pytest.mark.parametrize("shell_type,command", [
	("powershell", "Write-Output 'hello'"),
	("cmd", "echo hello"),
	("bash", "echo hello"),
])
def test_executor_success(shell_type, command):
	schema = make_schema(shell_type, command)
	result = CommandExecutor.execute(schema)
	result = patch_result_with_times(result)
	assert isinstance(result, ExecutionResult)
	assert result.success is True
	assert "hello" in result.stdout.lower()
	assert result.stderr == ""
	assert result.return_code == 0
	assert result.timed_out is False
	assert result.killed is False
	assert result.command == command
	assert result.shell_type == shell_type

def test_executor_failure():
	# Use a command that fails
	schema = make_schema("powershell", "exit 42")
	result = CommandExecutor.execute(schema)
	result = patch_result_with_times(result)
	assert result.success is False
	assert result.return_code == 42
	assert result.timed_out is False
	assert result.killed is False
	assert result.shell_type == "bash"

def test_executor_timeout():
	# Use a command that sleeps longer than LOW risk timeout (10s)
	schema = make_schema("cmd", "sleep 15", expected_risk="LOW")
	result = CommandExecutor.execute(schema)
	result = patch_result_with_times(result)
	assert result.success is False
	assert result.timed_out is True
	assert "timeout" in result.stderr.lower() or "timeout" in (result.error_message or "").lower()

def test_executor_exception():
	# Use an invalid shell type to trigger exception
	schema = make_schema("bash", "invalid_command_that_does_not_exist")
	result = CommandExecutor.execute(schema)
	result = patch_result_with_times(result)
	assert result.success is False
	assert result.return_code != 0
	assert result.stderr or result.error_message
