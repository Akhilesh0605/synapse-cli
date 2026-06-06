import time
import logging
import json
import uuid
from typing import Optional
from datetime import datetime,timezone

from app.llm.client import generate_command, generate_ai_response
from app.llm.shell_generator import generate_shell_command
from app.validator.command_validator import CommandValidator
from app.risk.policy_engine import PolicyEngine, PolicyDecision
from app.utils.os_detect import detect_os_context
from app.schemas.runtime_trace_schema import RuntimeStageTrace
from app.execution.executor import CommandExecutor
from app.execution.sandbox import SandboxExecutor
from app.semantic.semantic_validator import SemanticValidator
from app.execution.execution_policy import ExecutionPolicyEngine
from app.utils.windows_volume import apply_windows_volume_intent
from app.utils.windows_brightness import apply_windows_brightness_intent
from app.database.repository import save_command_history
from app.database.memory import update_memory, get_memory_context

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

def process_query(user_query: str, force_confirm: bool = False) -> dict:

    traces = []   # collect all stage traces
    runtime_context["last_query"] = user_query
    
    # Inject behavioral memory context into runtime query
    try:
        memory_context = get_memory_context()
        if memory_context:
            enriched_query = f"[MEMORY: {json.dumps(memory_context)}]\n{user_query}"
        else:
            enriched_query = user_query
    except Exception as e:
        logger.debug(f"Memory context injection failed: {str(e)}")
        enriched_query = user_query

    start         = time.time()
    intent_result = generate_command(enriched_query)

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

    if policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION and not force_confirm:
        return _response("require_confirmation", traces, reason=policy_result.reason,
                         intent=intent_result, policy=policy_result)

    if policy_result.decision == PolicyDecision.CLARIFY:
        return _response("clarify", traces, reason=policy_result.reason,
                         intent=intent_result, policy=policy_result)

    if intent_result.action_type == "ai_response":
        if intent_result.query_type == "realtime_data":
            import webbrowser
            query = intent_result.parameters.get("topic", user_query)
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return _response(
                "web_search",
                traces,
                intent=intent_result,
                message=f"Opened search for: {query}",
            )

        if intent_result.query_type == "static_knowledge":
            answer = generate_ai_response(user_query)
            return _response(
                "ai_response",
                traces,
                intent=intent_result,
                answer=answer,
            )

        return _response(
            "ai_response",
            traces,
            intent=intent_result,
            policy=policy_result,
        )

    if intent_result.action_type == "web_navigation":
        url = intent_result.parameters.get("url")

        if url and "watch?v=" in url:
    
            search_query = intent_result.parameters.get("search_query", user_query)
            url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"

        elif not url:
            url = f"https://www.google.com/search?q={user_query.replace(' ', '+')}"

    volume_intents = {
        "increase_volume",
        "decrease_volume",
        "set_volume",
        "adjust_volume",
        "mute_volume",
    }
    if intent_result.intent in volume_intents:
        if detect_os_context() != "windows":
            return _response(
                "blocked",
                traces,
                reason="Volume control is only implemented for Windows in this build.",
                intent=intent_result,
                policy=policy_result,
            )

        start = time.time()
        percent = int(intent_result.parameters.get("percent", 1) or 1)
        volume_result = apply_windows_volume_intent(intent_result.intent, percent)

        from app.schemas.execution_schema import ExecutionResult
        import uuid

        execution_result = ExecutionResult(
            request_id=str(uuid.uuid4()),
            success=volume_result.success,
            stdout=volume_result.message if volume_result.success else "",
            stderr="" if volume_result.success else volume_result.message,
            return_code=0 if volume_result.success else 1,
            execution_time_ms=int((time.time() - start) * 1000),
            timed_out=False,
            killed=False,
            command=f"{intent_result.intent}:{percent}",
            shell_type=intent_result.shell_type,
            retry_attempt=0,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            error_message=None if volume_result.success else volume_result.message,
        )

        traces.append(make_trace(
            stage_name="execution",
            stage_order=3,
            start=start,
            success=execution_result.success,
            error_message=execution_result.error_message,
            input_snapshot=intent_result.model_dump(mode="json"),
            output_snapshot=execution_result.model_dump(mode="json"),
        ))

        final_status = "success" if execution_result.success else "execution_failed"
        return _response(
            final_status,
            traces,
            intent=intent_result,
            policy=policy_result,
            execution=execution_result,
        )

    brightness_intents = {
        "increase_screen_brightness",
        "decrease_screen_brightness",
        "set_screen_brightness",
        "adjust_screen_brightness",
    }
    if intent_result.intent in brightness_intents:
        if detect_os_context() != "windows":
            return _response(
                "blocked",
                traces,
                reason="Screen brightness control is only implemented for Windows in this build.",
                intent=intent_result,
                policy=policy_result,
            )

        start = time.time()
        level = int(intent_result.parameters.get("level", 1) or 1)
        brightness_result = apply_windows_brightness_intent(intent_result.intent, level)

        from app.schemas.execution_schema import ExecutionResult
        import uuid

        execution_result = ExecutionResult(
            request_id=str(uuid.uuid4()),
            success=brightness_result.success,
            stdout=brightness_result.message if brightness_result.success else "",
            stderr="" if brightness_result.success else brightness_result.message,
            return_code=0 if brightness_result.success else 1,
            execution_time_ms=int((time.time() - start) * 1000),
            timed_out=False,
            killed=False,
            command=f"{intent_result.intent}:{level}",
            shell_type=intent_result.shell_type,
            retry_attempt=0,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            error_message=None if brightness_result.success else brightness_result.message,
        )

        traces.append(make_trace(
            stage_name="execution",
            stage_order=3,
            start=start,
            success=execution_result.success,
            error_message=execution_result.error_message,
            input_snapshot=intent_result.model_dump(mode="json"),
            output_snapshot=execution_result.model_dump(mode="json"),
        ))

        final_status = "success" if execution_result.success else "execution_failed"
        return _response(
            final_status,
            traces,
            intent=intent_result,
            policy=policy_result,
            execution=execution_result,
        )


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

    attempt = command_result.retry_attempt
    execution_result = None

    while True:
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
            return _response(
                "blocked",
                traces,
                reason=execution_policy_result.governance_reason,
                intent=intent_result,
                policy=policy_result,
                command=command_result,
                execution_policy=execution_policy_result,
            )

        # --- Username substitution for cross-platform compatibility ---
        import os
        username = os.environ.get("USERNAME") or os.environ.get("USER")
        if username:
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

        # --- Dynamic executable path resolution for all system/app launches ---
        from app.utils.find_executable import find_executable
        import re
        # Only attempt for commands that look like app launches (start, start-process, open, explorer, etc.)
        if hasattr(command_result, "command") and isinstance(command_result.command, str):
            cmd = command_result.command.strip()
            # Regex for launch patterns: e.g., start app, start 'C:\\Path\\App.exe', start-process -FilePath 'app', open app, explorer app
            launch_patterns = [
                r"^(start|open|explorer)\\s+['\"]?([^'\"]+)['\"]?",
                r"start-process\\s+-filepath\\s+['\"]?([^'\"]+)['\"]?",
            ]
            for pat in launch_patterns:
                m = re.search(pat, cmd, re.IGNORECASE)
                if m:
                    if pat.startswith("^(start"):
                        app_token = m.group(2)
                    else:
                        app_token = m.group(1)

                    # If a full path was provided but it doesn't exist, try resolving by basename
                    app_token_expanded = os.path.expandvars(os.path.expanduser(app_token))
                    if os.path.isabs(app_token_expanded) and not os.path.isfile(app_token_expanded):
                        app_base = os.path.splitext(os.path.basename(app_token_expanded))[0]
                    else:
                        app_base = os.path.splitext(os.path.basename(app_token_expanded))[0]

                    exe_path = find_executable(app_base)
                    if exe_path:
                        if pat.startswith("^(start"):
                            command_result.command = re.sub(pat, f"{m.group(1)} \"{exe_path}\"", cmd, flags=re.IGNORECASE)
                        else:
                            command_result.command = re.sub(r"-filepath\\s+['\"]?([^'\"]+)['\"]?", f"-FilePath '{exe_path}'", cmd, flags=re.IGNORECASE)
                    break

        start=time.time()
        if execution_policy_result.sandbox_required:
            execution_result = SandboxExecutor.execute(command_result, execution_policy_result)
        else:
            execution_result = CommandExecutor.execute(command_result, execution_policy_result)

        traces.append(make_trace(
                stage_name      = "execution",
                stage_order     = 7,
                start           = start,
                success         = execution_result.success,
                error_message   = execution_result.error_message,
                input_snapshot  = command_result.model_dump(mode="json"),
                output_snapshot = execution_result.model_dump(mode="json"),
            ))

        if execution_result.success:
            break

        if attempt >= 2:
            break

        attempt += 1
        retry_start = time.time()
        retry_command = generate_shell_command(
            intent_result,
            retry_attempt=attempt,
            stderr=execution_result.stderr,
            exit_code=execution_result.return_code,
        )
        traces.append(make_trace(
            stage_name      = "shell_generation",
            stage_order     = 3,
            start           = retry_start,
            success         = retry_command is not None,
            error_message   = None if retry_command else "LLM #2 returned None",
            input_snapshot  = intent_result.model_dump(mode="json"),
            output_snapshot = retry_command.model_dump(mode="json") if retry_command else None,
        ))
        if retry_command is None:
            return _response("error", traces, message="Failed to generate shell command.",
                             intent=intent_result)
        command_result = retry_command
        

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
    execution_policy=execution_policy_result,
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

    response = {
        "status": status,
        "trace": {
            "stages":       [t.model_dump(mode="json") for t in traces],
            "total_ms":     sum(t.latency_ms for t in traces),
            "stages_run":   len(traces),
            "failed_stage": next(
                (t.stage_name for t in traces if not t.success), None
            ),
        },
       **serialized,
    }

    execution_policy = serialized.get("execution_policy")
    policy = serialized.get("policy")
    active_policy = execution_policy if isinstance(execution_policy, dict) else policy
    if isinstance(active_policy, dict) and active_policy.get("execution_mode"):
        response["trace"]["execution_mode"] = active_policy.get("execution_mode")
        response["trace"]["sandbox_required"] = bool(active_policy.get("sandbox_required"))

    if "execution" in serialized and isinstance(serialized["execution"], dict):
        response.setdefault("request_id", serialized["execution"].get("request_id"))

    if not response.get("request_id"):
        response["request_id"] = serialized.get("request_id") or str(uuid.uuid4())
    if not response.get("query"):
        response["query"] = runtime_context.get("last_query", "")
    
    # Save to database (wrapped in try/except to never crash pipeline)
    try:
        # Add pipeline stages for tracing
        response["pipeline_stages"] = response["trace"]["stages"]
        
        # Save command history
        save_command_history(response)
        
        # Update behavioral memory if successful execution
        if status == "success" and "execution" in serialized:
            execution = serialized.get("execution", {})
            intent = serialized.get("intent", {})
            command = serialized.get("command", {})
            
            if intent.get("intent") and command.get("command"):
                update_memory(
                    intent=intent.get("intent"),
                    shell_type=intent.get("shell_type", "unknown"),
                    command=command.get("command"),
                )
    except Exception as e:
        logger.debug(f"Database operation failed (non-fatal): {str(e)}")
    
    return response