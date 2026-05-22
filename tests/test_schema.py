from app.schemas.intent_schema import IntentSchema

def test_intent_schema_valid():
    data = {
        "action_type": "system_command",
        "intent": "list_docker_containers",
        "requires_shell": True,
        "shell_type": "powershell",
        "parameters": {
            "flags": ["-a"]
        },
        "risk_level": "LOW",
        "confidence": "HIGH",
        "explanation": "User wants to list Docker containers."
    }
    validated = IntentSchema(**data)
    # Assert that the validated object has expected attributes
    assert validated.action_type == "system_command"
    assert validated.intent == "list_docker_containers"
    assert validated.requires_shell is True
    assert validated.shell_type == "powershell"
    assert validated.parameters["flags"] == ["-a"]
    assert validated.risk_level == "LOW"
    assert validated.confidence == "HIGH"
    assert validated.explanation == "User wants to list Docker containers."
