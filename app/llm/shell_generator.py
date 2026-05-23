import json
import logging
import platform
import re
from typing import Optional

import ollama
from pydantic import ValidationError

from app.schemas.intent_schema import IntentSchema
from app.schemas.command_schema import ShellCommandSchema
from app.llm.shell_prompt import SHELL_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

SHELL_MODEL = "llama3"


def detect_os_context() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    return "linux"


def strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_shell_command(
    intent:        IntentSchema,
    retry_attempt: int           = 0,
    stderr:        Optional[str] = None,
    exit_code:     Optional[int] = None,
) -> Optional[ShellCommandSchema]:

    os_context = detect_os_context()

    # Build runtime prompt
    lines = [
        f"[OS: {os_context}]",
        f"[INTENT: {intent.model_dump_json()}]",
    ]
    if retry_attempt > 0 and stderr:
        lines.append(
            f'[RETRY: attempt={retry_attempt}, stderr="{stderr}", exit_code={exit_code}]'
        )
    runtime_prompt = "\n".join(lines)

    # LLM call
    try:
        response   = ollama.chat(
            model    = SHELL_MODEL,
            options={
            "temperature":0.1,
            "top_p":0.9,
            "seed":42
        },
            messages = [
                {"role": "system", "content": SHELL_SYSTEM_PROMPT},
                {"role": "user",   "content": runtime_prompt},
            ]
        )
        raw_output = response.message.content

    except Exception as e:
        logger.error("Ollama call failed: %s", e)
        return None

    # Parse
    try:
        parsed = json.loads(strip_json_fences(raw_output))
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed: %s | raw: %s", e, raw_output)
        return None

    # Null command = LLM flagged it unsafe
    if parsed.get("command") is None:
        logger.warning("LLM returned null command — %s", parsed.get("explanation"))
        return None

    # Schema validation
    try:
        if "shell_type" in parsed:
            parsed["shell_type"] = parsed["shell_type"].lower()

        if "expected_risk" in parsed:
            parsed["expected_risk"] = parsed["expected_risk"].upper()

        if "confidence" in parsed:
            parsed["confidence"] = parsed["confidence"].upper()
        return ShellCommandSchema(**parsed)     
    except ValidationError as e:
        logger.warning("Schema validation failed: %s", e)
        return None