from strands import Agent

from agents.label_agent import label_agent
from agents.safety_agent import safety_agent
from agents.trials_agent import trials_agent
from agents.memory import get_short_term_session_manager, ltm_store
from tools.escalation import escalate_to_human
from strands import tool

BASE_SYSTEM_PROMPT = """
You are a supervisor agent in Capstone, an enterprise drug-safety and medical-information assistant.

You never answer clinical or factual questions directly yourself; you always route to the appropriate specialist agent or tool.

Rules to follow:
1. Intent Routing:
   - Use LabelAgent for approved drug label questions (indications, contraindications, warnings, approved labeling info).
   - Use SafetyAgent for adverse-event queries and spontaneous safety signal reports.
   - Use TrialsAgent for clinical trial queries from ClinicalTrials.gov.
2. Refusal Policy: If a user asks for diagnosis, personalized treatment, or personalized dosing advice, do NOT answer.
3. Escalation: Use escalate_to_human for personalized clinical recommendations or dosing decisions, and instruct the user to consult a qualified healthcare professional.
4. Memory & Patient Context:
   - Always verify and respect the user's Long-Term Memory (LTM) profile (e.g., known drug allergies, chronic conditions, clinical role) when assessing safety warnings and contraindications.
   - Maintain multi-turn conversational context (Short-Term Memory) across the consultation session.
   - If the user provides new persistent medical facts or allergy profile updates, acknowledge them clearly so they remain recorded in the patient safety context.
"""


def get_supervisor(session_id: str = "default-session", actor_id: str = "default-user") -> Agent:
    session_manager = get_short_term_session_manager(session_id=session_id, actor_id=actor_id)
    ltm_context = ltm_store.format_ltm_context(actor_id)
    
    full_prompt = BASE_SYSTEM_PROMPT.strip() + ltm_context

    @tool
    def save_patient_fact(key: str, value: str):
        """Saves a persistent medical fact or profile information about the current user to Long-Term Memory (LTM)."""
        ltm_store.set_actor_fact(actor_id=actor_id, key=key, value=value)
        return f"Successfully saved {key} = {value} to patient's LTM profile."
    
    return Agent(
        model="global.anthropic.claude-sonnet-5",
        tools=[label_agent, safety_agent, trials_agent, escalate_to_human, save_patient_fact],
        session_manager=session_manager,
        system_prompt=full_prompt,
    )


supervisor = get_supervisor()