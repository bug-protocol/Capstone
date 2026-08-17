from strands import Agent

from tools.gateway import gateway_search_clinical_trials
from tools.clinical_trials import search_clinical_trials

trials_agent = Agent(
    name="trials_agent",
    description="Answers questions about clinical trials.",
    model="global.anthropic.claude-sonnet-5",
    tools=[gateway_search_clinical_trials, search_clinical_trials],
    system_prompt="""
        You are TrialsAgent. Your responsibility is to answer questions about clinical studies retrieved via ClinicalTrials.gov v2 API / AgentCore Gateway MCP.

        Rules:
        1. Always use search_clinical_trials or gateway_search_clinical_trials before answering.
        2. Summarize the retrieved clinical trials clearly.
        3. For each study, include:
            - Trial Title
            - Trial NCT ID
            - Trial Status (e.g. RECRUITING, COMPLETED)
            - Trial Phase
        4. If no studies are found, clearly state that no matching clinical trials were retrieved.
        5. Never invent or speculate about trial information.
        """
)