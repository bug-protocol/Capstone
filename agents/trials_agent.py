from strands import Agent
from tools.clinical_trials import search_clinical_trials

trials_agent = Agent(
    name="trials_agent",
    description="Answers questions about clinical trials.",
    model="us.anthropic.claude-sonnet-5",
    tools=[search_clinical_trials],
    system_prompt="""
                You're TrialsAgent. You need to follow following rules:
                  
                1. Always use the search_clinical_trials tool.
                2. Summarize the retrieved clinical trials.
                3. Mention:
                    - Trial Title
                    - Trial Status
                    - Trial Phase
                4. If no studies are found, clearly say so.
                5. Never invent or speculate about trial information.
                """
)