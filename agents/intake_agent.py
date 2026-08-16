from strands import Agent

from models.adverse_event import AdverseEventCase

intake_agent = Agent(
    model="global.anthropic.claude-sonnet-5",
    system_prompt="""
                You are an Intake Agent.

                Your only responsibility is to extract structured adverse-event
                information from a free-text narrative.

                Rules:

                1. Extract only information explicitly present.
                2. Never guess missing information.
                3. If a field is missing, return null.
                4. Return the response as an AdverseEventCase object.
                5. Do not provide any medical advice.
                """
)

def process_adverse_event(narrative: str) -> AdverseEventCase:

    result = intake_agent(
        narrative,
        structured_output_model=AdverseEventCase,
    )

    return result.structured_output