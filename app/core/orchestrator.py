from app.llm.client import generate_command
from app.llm.shell_generator import generate_shell_command

from app.risk.policy_engine import(
    PolicyEngine
)

def process_query(user_query:str):
    #intent genration
    intent_result=generate_command(user_query)

    if intent_result is None:
        return{
            "status":"error",
            "message":"Failed to Generate valid intent schema."
        }

    #Policy Evaluation

    engine=PolicyEngine(
        os_context="windows"
    )

    policy_result=engine.evaluate(intent_result)

    if not policy_result.safe_to_proceed:

        return {
            "status": "blocked",
            "intent": intent_result,
            "policy": policy_result
        }

    command_result = None

    if intent_result.requires_shell:

        command_result = generate_shell_command(intent_result)

    return {
        "status": "success",
        "intent": intent_result,
        "policy": policy_result,
        "command": command_result
    }

    
