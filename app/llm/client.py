import json
import ollama
from app.schemas.intent_schema import IntentSchema
from pydantic import ValidationError
from app.utils.json_utils import extract_json_object

from app.llm.intent_prompt import INTENT_SYSTEM_PROMPT

INTENT_MODEL="llama3"

def generate_command(user_query: str):
    response = ollama.chat(
        model=INTENT_MODEL,
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
                "content": user_query
            }
        ]
    )

    content = response["message"]["content"]

    try:
        parsed = extract_json_object(content)
        validated = IntentSchema(**parsed)
        return validated
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}\nContent: {content}")
        return None
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None
