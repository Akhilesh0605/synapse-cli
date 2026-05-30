import json
import ollama
from app.schemas.intent_schema import IntentSchema
from pydantic import ValidationError
from app.utils.json_utils import extract_json_object
from app.utils.os_detect import detect_os_context

from app.llm.intent_prompt import INTENT_SYSTEM_PROMPT

INTENT_MODEL="llama3"


def generate_ai_response(user_query: str) -> str:
    response = ollama.chat(
        model   = INTENT_MODEL,
        options = {"temperature": 0.7, "seed": 42},
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer clearly and concisely.",
            },
            {"role": "user", "content": user_query},
        ]
    )
    return response.message.content

def generate_command(user_query: str):
    runtime_prompt = f"[OS: {detect_os_context()}]\n{user_query}"
    response = ollama.chat(
        model=INTENT_MODEL,
        format="json",
        options={
            "temperature":0.1,
            "top_p":0.9,
            "seed":42
        },
        messages=[
            {
                "role": "system",
                "content": INTENT_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": runtime_prompt
            }
        ]
    )

    content = response["message"]["content"]

    try:
        parsed = extract_json_object(content)
        validated = IntentSchema(**parsed)
        return validated
    except (json.JSONDecodeError,ValueError) as e:
        print(f"JSON decode error/ValueError: {e}\nContent: {content}")
        return None
    except ValidationError as e:
        print(f"Validation error: {e}")
        print(f"Raw parsed output was:",parsed)
        return None
