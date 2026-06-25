import json
import os

from groq import Groq
from dotenv import load_dotenv
from pydantic import ValidationError

from app.schemas.intent_schema import IntentSchema
from app.utils.json_utils import extract_json_object
from app.utils.os_detect import detect_os_context
from app.llm.intent_prompt import INTENT_SYSTEM_PROMPT

load_dotenv()

INTENT_MODEL="openai/gpt-oss-120b"

client=Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_ai_response(user_query: str) -> str:
    response = client.chat.completions.create(
        model=INTENT_MODEL,
        temperature=0.7,
        seed=42,
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer clearly and concisely.",
            },
            {"role": "user", "content": user_query},
        ],
    )
    return response.choices[0].message.content

def generate_command(user_query: str):
    runtime_prompt = f"[OS: {detect_os_context()}]\n{user_query}"
    response = client.chat.completions.create(
        model=INTENT_MODEL,
        response_format={"type":"json_object"},
        temperature=0.7,
        seed=42,
        messages=[
            {
                "role": "system",
                "content": INTENT_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": runtime_prompt
            },
        ],
    )

    content = response.choices[0].message.content

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
