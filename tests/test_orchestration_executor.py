import pytest

from app.core.orchestrator import process_query


# ---------------------------------------------------------
# SAFE SUCCESSFUL EXECUTION
# ---------------------------------------------------------

def test_pipeline_executes_safe_command():

    result = process_query("show python version")

    assert result["status"] in ["success", "execution_failed"]

    trace = result["trace"]

    assert trace["stages_run"] >= 5

    stage_names = [s["stage_name"] for s in trace["stages"]]

    assert "execution" in stage_names

    execution_stage = next(
        s for s in trace["stages"]
        if s["stage_name"] == "execution"
    )

    assert execution_stage["success"] is True

    assert "execution" in result

    execution = result["execution"]

    assert execution["success"] is True
    assert execution["return_code"] == 0
    assert execution["timed_out"] is False


# ---------------------------------------------------------
# BLOCKED DANGEROUS COMMAND
# ---------------------------------------------------------

def test_pipeline_blocks_dangerous_command():

    result = process_query("delete system32 folder")

    assert result["status"] == "blocked"

    trace = result["trace"]

    stage_names = [s["stage_name"] for s in trace["stages"]]

    # should never reach execution
    assert "execution" not in stage_names

    if trace["failed_stage"] is not None:
        assert trace["failed_stage"] in {
            "command_validation",
            "semantic_validation",
            "policy_evaluation",
        }


# ---------------------------------------------------------
# EXECUTION FAILURE
# ---------------------------------------------------------

def test_pipeline_handles_execution_failure():

    result = process_query("run invalid nonexistent command")

    assert result["status"] in [
        "execution_failed",
        "blocked",
        "clarify",
    ]

    trace = result["trace"]

    stage_names = [s["stage_name"] for s in trace["stages"]]

    if "execution" in stage_names:

        execution = result["execution"]

        assert execution["success"] is False

        assert execution["return_code"] != 0


# ---------------------------------------------------------
# EXECUTION TRACE EXISTS
# ---------------------------------------------------------

def test_execution_trace_contains_runtime_data():

    result = process_query("show current directory")

    trace = result["trace"]

    execution_stage = next(
        s for s in trace["stages"]
        if s["stage_name"] == "execution"
    )

    assert execution_stage["latency_ms"] >= 0

    assert execution_stage["input_snapshot"] is not None

    assert execution_stage["output_snapshot"] is not None


# ---------------------------------------------------------
# TOTAL LATENCY INCLUDES EXECUTION
# ---------------------------------------------------------

def test_total_pipeline_latency():

    result = process_query("show python version")

    trace = result["trace"]

    total_stage_latency = sum(
        s["latency_ms"]
        for s in trace["stages"]
    )

    assert trace["total_ms"] >= total_stage_latency - 10


# ---------------------------------------------------------
# TIMEOUT HANDLING
# ---------------------------------------------------------

def test_pipeline_timeout_handling():

    result = process_query(
        "run a command that sleeps for 20 seconds"
    )

    if result["status"] == "execution_failed":

        execution = result["execution"]

        assert execution["timed_out"] is True

        assert execution["success"] is False


# ---------------------------------------------------------
# EXECUTION OUTPUT EXISTS
# ---------------------------------------------------------

def test_execution_output_returned():

    result = process_query("show python version")

    if result["status"] == "success":

        execution = result["execution"]

        assert execution["stdout"] != ""

        assert execution["stderr"] == ""


# ---------------------------------------------------------
# TRACE ORDER VALIDATION
# ---------------------------------------------------------

def test_trace_stage_order():

    result = process_query("show current directory")

    trace = result["trace"]

    orders = [
        s["stage_order"]
        for s in trace["stages"]
    ]

    assert orders == sorted(orders)

    assert orders[0] == 1


# ---------------------------------------------------------
# EXECUTION SHOULD NEVER RUN AFTER VALIDATION FAILURE
# ---------------------------------------------------------

def test_execution_not_triggered_when_validation_fails():

    result = process_query(
        "delete all files recursively"
    )

    trace = result["trace"]

    stage_names = [
        s["stage_name"]
        for s in trace["stages"]
    ]

    assert "execution" not in stage_names