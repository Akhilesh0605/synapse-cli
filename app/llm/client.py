import json
import ollama
from app.schemas.intent_schema import IntentSchema
from pydantic import ValidationError

from app.llm.prompts import LLM_1_PROMPT

def generate_command(user_query: str):
    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "system",
                "content": LLM_1_PROMPT
            },
            {
                "role": "user",
                "content": user_query
            }
        ]
    )

    content = response["message"]["content"]

    try:
        parsed = json.loads(content)
        validated = IntentSchema(**parsed)
        return validated
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}\nContent: {content}")
        return None
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None
