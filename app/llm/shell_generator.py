import json
import os 
import logging
from typing import Optional

from groq import Groq
from pydantic import ValidationError
from dotenv import load_dotenv

from app.schemas.intent_schema import IntentSchema
from app.schemas.command_schema import ShellCommandSchema
from app.llm.shell_prompt import SHELL_SYSTEM_PROMPT
from app.utils.os_detect import detect_os_context
from app.utils.json_utils import strip_json_fences

logger = logging.getLogger(__name__)


SHELL_MODEL = "openai/gpt-oss-120b"
load_dotenv()

client=Groq(api_key=os.getenv("GROQ_API_KEY"))

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
        response   = client.chat.completions.create(
            model    = SHELL_MODEL,
            temperature=0.1,
            seed=42,
            top_p=0.9,
            messages = [
                {"role": "system", "content": SHELL_SYSTEM_PROMPT},
                {"role": "user",   "content": runtime_prompt},
            ]
        )
        raw_output = response.choices[0].message.content

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