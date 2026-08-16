from strands import Agent

from agents.label_agent import label_agent
from agents.safety_agent import safety_agent
from agents.trials_agent import trials_agent
from tools.escalation import escalate_to_human

supervisor = Agent(
    model="global.anthropic.claude-sonnet-5",
    tools=[
        label_agent, safety_agent, trials_agent, escalate_to_human
    ], # agents can be used as tools
    
    system_prompt="""
        You are a supervisor agent.     
        
        You never answer questions yourself.

        Rules to follow:

        1. Use LabelAgent for approved drug label questions.

        2. Use SafetyAgent for adverse-event questions.

        3. Use TrialsAgent for clinical trial questions.

        4. If a question asks for diagnosis, treatment, or dosing advice,
        do not answer.
        
        5. Use escalate_to_human for diagnosis, personalized treatment recommendations, personalized dosing decision.
        Tell the user to consult a healthcare professional.
    """  
)

print(supervisor.tool_names)