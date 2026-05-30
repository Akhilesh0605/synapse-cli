import time
import logging
from typing import Optional
from datetime import datetime,timezone

from app.llm.client import generate_command
from app.llm.shell_generator import generate_shell_command
from app.validator.command_validator import CommandValidator
from app.risk.policy_engine import PolicyEngine, PolicyDecision
from app.utils.os_detect import detect_os_context
from app.schemas.runtime_trace_schema import RuntimeStageTrace
from app.execution.executor import CommandExecutor
from app.semantic.semantic_validator import SemanticValidator
from app.execution.execution_policy import ExecutionPolicyEngine

logger = logging.getLogger(__name__)



def make_trace(
    stage_name:      str,
    stage_order:     int,
    start:           float,
    success:         bool,
    error_message:   Optional[str]   = None,
    input_snapshot:  Optional[dict]  = None,
    output_snapshot: Optional[dict]  = None,
) -> RuntimeStageTrace:
    end = time.time()
    return RuntimeStageTrace(
        stage_name      = stage_name,
        stage_order     = stage_order,
        started_at      = start,
        completed_at    = end,
        started_at_utc   = datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
        completed_at_utc = datetime.fromtimestamp(end,   tz=timezone.utc).isoformat(),
        latency_ms      = int((end - start) * 1000),
        success         = success,
        error_message   = error_message,
        input_snapshot  = input_snapshot,
        output_snapshot = output_snapshot,
    )


import os
import getpass

runtime_context = {
    "os":       detect_os_context(),
    "username": getpass.getuser(),
    "home":     os.path.expanduser("~"),
    "desktop":  os.path.join(os.path.expanduser("~"), "Desktop"),
}

def process_query(user_query: str) -> dict:

    traces = []   # collect all stage traces

    start         = time.time()
    intent_result = generate_command(user_query)

    traces.append(make_trace(
        stage_name      = "intent_generation",
        stage_order     = 1,
        start           = start,
        success         = intent_result is not None,
        error_message   = None if intent_result else "LLM #1 returned None",
        input_snapshot  = {"query": user_query},
        output_snapshot = intent_result.model_dump() if intent_result else None,
    ))

    if intent_result is None:
        return _response("error", traces, message="Failed to generate intent schema.")

    start         = time.time()
    engine        = PolicyEngine(os_context=detect_os_context())
    policy_result = engine.evaluate(intent_result)

    traces.append(make_trace(
        stage_name      = "policy_evaluation",
        stage_order     = 2,
        start           = start,
        success         = True,   # engine always returns a result
        input_snapshot  = intent_result.model_dump(mode="json"),
        output_snapshot = policy_result.model_dump(mode="json"),
    ))

    if policy_result.decision == PolicyDecision.BLOCK:
        return _response("blocked", traces, reason=policy_result.reason,
                         intent=intent_result, policy=policy_result)

    if policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION:
        return _response("require_confirmation", traces, reason=policy_result.reason,
                         intent=intent_result, policy=policy_result)

    if policy_result.decision == PolicyDecision.CLARIFY:
        return _response("clarify", traces, reason=policy_result.reason,
                         intent=intent_result, policy=policy_result)

    if intent_result.action_type == "ai_response":
        return _response("ai_response", traces,
                         intent=intent_result, policy=policy_result)

    if intent_result.action_type == "web_navigation":
        return _response("web_navigation", traces,
                         intent=intent_result, policy=policy_result,
                         url=intent_result.parameters.get("url"))


    start          = time.time()
    command_result = generate_shell_command(intent_result)

    traces.append(make_trace(
        stage_name      = "shell_generation",
        stage_order     = 3,
        start           = start,
        success         = command_result is not None,
        error_message   = None if command_result else "LLM #2 returned None",
        input_snapshot  = intent_result.model_dump(mode="json"),
        output_snapshot = command_result.model_dump(mode="json") if command_result else None,
    ))

    if command_result is None:
        return _response("error", traces, message="Failed to generate shell command.",
                         intent=intent_result)

    start      = time.time()
    validation = CommandValidator.validate(command_result)

    traces.append(make_trace(
        stage_name      = "command_validation",
        stage_order     = 4,
        start           = start,
        success         = validation.safe,
        error_message   = (
            "; ".join(v.reason for v in validation.violations)
            if not validation.safe else None
        ),
        input_snapshot  = command_result.model_dump(mode="json"),
        output_snapshot = validation.model_dump(mode="json"),
    ))

    if not validation.safe:
        return _response("blocked", traces, reason="Command failed static validation.",
                         intent=intent_result, policy=policy_result,
                         command=command_result, violations=validation.violations)
    
    start = time.time()

    semantic_result=SemanticValidator.validate(
        intent_result,
        command_result
    )

    traces.append(make_trace(

        stage_name="semantic_validation",
        stage_order=5,
        start=start,
        success=semantic_result.safe,
        error_message=(
                "; ".join(v.reason for v in semantic_result.violations)
                if not semantic_result.safe else None
            ),
        input_snapshot=command_result.model_dump(mode="json"),
        output_snapshot=semantic_result.model_dump(mode="json"),
    ))
    
    if not semantic_result.safe:
        return _response(
            "blocked",
            traces,
            reason="Semantic validation failed.",
            intent=intent_result,
            policy=policy_result,
            command=command_result,
            semantic=semantic_result,
        )
    start=time.time()
    execution_policy_result = (
    ExecutionPolicyEngine.derive_policy(
        risk_level=command_result.expected_risk,
        capability=semantic_result.capability,
    )
    )
    traces.append(make_trace(
        stage_name="execution_policy",
        stage_order=6,
        start=start,
        success=execution_policy_result.allowed,
        error_message=None if execution_policy_result.allowed else execution_policy_result.governance_reason,
        input_snapshot={
            "risk_level": command_result.expected_risk,
            "capability": semantic_result.capability,
        },
        output_snapshot=execution_policy_result.model_dump(),
    ))
    
    if not execution_policy_result.allowed:
        raise RuntimeError(
            execution_policy_result.governance_reason
        )

    # --- Username substitution for cross-platform compatibility ---
    import os
    username = os.environ.get("USERNAME") or os.environ.get("USER")
    if username:
        # Replace {username}, $USER, $USERNAME in command string and parameters
        if hasattr(command_result, "command") and isinstance(command_result.command, str):
            command_result.command = (
                command_result.command
                .replace("{username}", username)
                .replace("$USER", username)
                .replace("$USERNAME", username)
            )
        if hasattr(command_result, "parameters") and isinstance(command_result.parameters, dict):
            for k, v in command_result.parameters.items():
                if isinstance(v, str):
                    command_result.parameters[k] = (
                        v.replace("{username}", username)
                         .replace("$USER", username)
                         .replace("$USERNAME", username)
                    )

    start=time.time()
    execution_result = CommandExecutor.execute(command_result,execution_policy_result)

    traces.append(make_trace(
            stage_name      = "execution",
            stage_order     = 7,
            start           = start,
            success         = execution_result.success,
            error_message   = execution_result.error_message,
            input_snapshot  = command_result.model_dump(mode="json"),
            output_snapshot = execution_result.model_dump(mode="json"),
        ))
        

    logger.info(
        "Pipeline complete | stages: %d | total_ms: %d",
        len(traces),
        sum(t.latency_ms for t in traces),
    )

    final_status = (
    "success"
    if execution_result.success
    else "execution_failed"
    )

    return _response(
    final_status,
    traces,
    intent=intent_result,
    policy=policy_result,
    command=command_result,
    execution=execution_result,
    )



def _response(status: str, traces: list, **kwargs) -> dict:

    # serialize any pydantic models in kwargs
    serialized = {}
    for key, value in kwargs.items():
        if hasattr(value, "model_dump"):
            serialized[key] = value.model_dump(mode="json")
        elif isinstance(value, list):
            serialized[key] = [
                v.model_dump(mode="json") if hasattr(v, "model_dump") else v
                for v in value
            ]
        else:
            serialized[key] = value

    return {
        "status": status,
        "trace": {
            "stages":       [t.model_dump(mode="json") for t in traces],
            "total_ms":     sum(t.latency_ms for t in traces),
            "stages_run":   len(traces),
            "failed_stage": next(
                (t.stage_name for t in traces if not t.success), None
            ),
        },
       **serialized,}