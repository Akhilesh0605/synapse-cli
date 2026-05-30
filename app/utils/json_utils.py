import re
import json
import logging

logger = logging.getLogger(__name__)


def extract_json_object(text: str) -> dict :
    """
    Extracts and parses the first valid JSON object from LLM output.

    Handles:
    - Markdown fences (```json ... ```)
    - Leading/trailing prose around the JSON block
    - Nested objects and arrays
    - Validates parse before returning

    Returns parsed dict. Raises ValueError with context on failure.
    """

    if not text or not text.strip():
        raise ValueError("Input text is empty")

    # Step 1 — strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    # Step 2 — try parsing the whole cleaned string first (happy path)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3 — scan for the first balanced { } block
    start = cleaned.find("{")
    if start == -1:
        logger.debug("Raw LLM output: %s", text)
        raise ValueError("No JSON object found in LLM output")

    depth   = 0
    in_str  = False
    escape  = False

    for i, ch in enumerate(cleaned[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as e:
                    logger.debug("Candidate JSON invalid: %s | raw: %s", e, candidate)
                    raise ValueError(
                        f"Found JSON-like block but it failed to parse: {e}"
                    ) from e

    logger.debug("Raw LLM output: %s", text)
    raise ValueError("Found opening brace but no matching closing brace")


def strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()