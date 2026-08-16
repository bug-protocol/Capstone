from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agents.supervisor import supervisor

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt")

    if not prompt:
        return {
            "error": "Missing 'prompt' in request"
        }

    result = supervisor(prompt)

    return {
        "response": str(result)
    }


if __name__ == "__main__":
    app.run()   