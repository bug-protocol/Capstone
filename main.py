from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agents.supervisor import get_supervisor

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt")
    session_id = payload.get("session_id", "default-session")
    actor_id = payload.get("actor_id", "default-user")

    if not prompt:
        return {
            "error": "Missing 'prompt' in request"
        }

    agent = get_supervisor(session_id=session_id, actor_id=actor_id)
    result = agent(prompt)

    return {
        "response": str(result),
        "session_id": session_id,
        "actor_id": actor_id
    }


if __name__ == "__main__":
    app.run()