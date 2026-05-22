from app.llm.client import generate_command

from app.risk.policy_engine import(
    PolicyEngine,
    PolicyDecision
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

    return {
        "status":"success",
        "intent":intent_result,
        "policy":policy_result
    }
