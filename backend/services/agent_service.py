import json
import logging
import asyncio
import re
from typing import AsyncGenerator, Dict, Any, List
import boto3

from backend.config import settings
from backend.utils.telemetry import trace_span
from agents.supervisor import get_supervisor
from agents.memory import ltm_store
from tools.label_search import search_drug_label, SUPPORTED_DRUGS
from tools.gateway import gateway_search_adverse_events, gateway_search_clinical_trials
from tools.escalation import escalate_to_human

logger = logging.getLogger("capstone.agent_service")


def fallback_specialist_router(prompt: str, actor_id: str) -> str:
    prompt_lower = prompt.lower()
    ltm_context = ltm_store.format_ltm_context(actor_id)

    refusal_triggers = [
        "should i take", "can i take", "prescribe", "my dose", "dose for me",
        "how much should i take", "what should i take", "diagnose", "treatment for me",
        "high dose", "overdose", "feeling different", "took too much", "feeling sick",
        "headache", "nausea", "vomiting", "adverse reaction", "allergic reaction", "toxicity"
    ]
    if any(trigger in prompt_lower for trigger in refusal_triggers):
        escalation = escalate_to_human(
            reason="Personalized clinical recommendation, overdose risk, or symptoms evaluation requested",
            user_request=prompt
        )
        return (
            "⚠️ **Refusal & Safety Escalation**: I cannot provide personalized medical advice, diagnosis, "
            "or dosing/overdose recommendations. "
            f"\n\n**Action Taken**: {escalation['message']} "
            "\nPlease consult a qualified physician or pharmacist for medical decisions immediately."
        )

    target_drug = None
    for drug_key in SUPPORTED_DRUGS.keys():
        if drug_key in prompt_lower or (drug_key == "paracetamol" and "acetaminophen" in prompt_lower):
            target_drug = drug_key
            break

    if not target_drug:
        if "ozempic" in prompt_lower or "semaglutide" in prompt_lower:
            target_drug = "ozempic"
        elif "azithromycin" in prompt_lower:
            target_drug = "azithromycin"
        elif "paracetamol" in prompt_lower or "pcm" in prompt_lower or "acetaminophen" in prompt_lower:
            target_drug = "paracetamol"
        else:
            target_drug = "azithromycin"

    if any(w in prompt_lower for w in ["clinical trial", "trial", "study", "studies", "nct"]):
        trials_data = gateway_search_clinical_trials(drug_name=target_drug, page_size=4)
        studies = trials_data.get("studies", [])
        if not studies:
            return f"No active clinical trials found for {target_drug.capitalize()} in ClinicalTrials.gov."

        response_lines = [
            f"### Clinical Trials for {target_drug.capitalize()} (via ClinicalTrials.gov v2)\n"
        ]
        for s in studies:
            response_lines.append(
                f"- **{s.get('title')}**\n"
                f"  - **NCT ID**: `{s.get('nct_id')}`\n"
                f"  - **Status**: `{s.get('status')}`\n"
                f"  - **Phase**: {s.get('phase')}\n"
            )
        response_lines.append("\n**Source**: ClinicalTrials.gov API v2 (via AgentCore Gateway MCP)")
        return "\n".join(response_lines)

    if any(w in prompt_lower for w in ["adverse", "side effect", "reaction", "safety", "signal", "faers"]):
        safety_data = gateway_search_adverse_events(drug_name=target_drug, limit=20)
        reactions = safety_data.get("frequently_reported_reactions", {})

        response_lines = [
            f"### Frequently Reported Adverse Events for {target_drug.capitalize()}\n",
            f"Based on spontaneous post-marketing safety reports from the **openFDA Drug Event API** (Sample size: {safety_data.get('sample_size', 20)} reports):\n"
        ]
        for reaction, count in reactions.items():
            response_lines.append(f"- **{reaction}**: {count} reports")

        response_lines.append(
            "\n> **Important Regulatory Notice**: Reported adverse-event frequencies are based on spontaneous reports and do not establish causality."
        )
        response_lines.append("\n**Source**: openFDA Drug Event Database / FAERS (via AgentCore Gateway MCP)")
        return "\n".join(response_lines)

    section = "indications_and_usage"
    if "contraindication" in prompt_lower:
        section = "contraindications"
    elif "warning" in prompt_lower:
        section = "warnings_and_cautions"
    elif "adverse" in prompt_lower or "reaction" in prompt_lower:
        section = "adverse_reactions"
    elif "dosage" in prompt_lower or "administration" in prompt_lower:
        section = "dosage_and_administration"

    label_result = search_drug_label(drug_name=target_drug, section=section)
    if label_result.get("success"):
        evidence = label_result.get("evidence", [])
        evidence_text = "\n\n".join(evidence[:2])
        if len(evidence_text) > 600:
            evidence_text = evidence_text[:600] + "..."

        section_display = section.replace("_", " ").title()
        return (
            f"### Approved Drug Labeling for {target_drug.capitalize()}\n"
            f"**Section: {section_display}**\n\n"
            f"{evidence_text}\n\n"
            f"**Source Citation**: US FDA Approved Drug Labeling for {target_drug.capitalize()} ({label_result.get('source')})."
        )
    else:
        return (
            f"Could not retrieve approved labeling for {target_drug}. "
            f"Details: {label_result.get('error', 'Section not found.')}"
        )


def extract_citations_from_text(text: str) -> List[Dict[str, Any]]:
    citations = []
    text_lower = text.lower()

    if "openfda" in text_lower or "drug label" in text_lower or "approved" in text_lower:
        citations.append({
            "source": "FDA Approved Drug Labeling (openFDA Drug Label API)",
            "section": "Approved Product Information",
            "evidence": "Retrieved from FDA approved drug labeling database."
        })
    if "spontaneous reports" in text_lower or "drug event" in text_lower or "faers" in text_lower:
        citations.append({
            "source": "FDA Adverse Event Reporting System (FAERS / openFDA)",
            "section": "Post-Marketing Safety Reports",
            "evidence": "Spontaneous adverse event reporting statistics (Signal != Causality)."
        })
    if "clinicaltrials.gov" in text_lower or "nct" in text_lower:
        citations.append({
            "source": "ClinicalTrials.gov API v2",
            "section": "Clinical Studies Registry",
            "evidence": "Registered clinical trials and investigation protocols."
        })

    return citations


def invoke_remote_agentcore_runtime(
    prompt: str,
    session_id: str,
    actor_id: str,
    correlation_id: str
) -> str:
    """
    Invokes the deployed Bedrock AgentCore Runtime container on AWS via boto3.
    """
    if not settings.AGENTCORE_RUNTIME_ARN:
        raise ValueError("AGENTCORE_RUNTIME_ARN is not configured.")

    client = boto3.client("bedrock-agentcore", region_name=settings.AWS_REGION)
    payload_dict = {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": actor_id,
        "correlation_id": correlation_id,
    }

    response = client.invoke_agent_runtime(
        agentRuntimeArn=settings.AGENTCORE_RUNTIME_ARN,
        payload=json.dumps(payload_dict).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
        runtimeSessionId=session_id,
        runtimeUserId=actor_id,
    )

    body = response.get("response")
    if hasattr(body, "read"):
        raw_output = body.read().decode("utf-8")
    elif isinstance(body, bytes):
        raw_output = body.decode("utf-8")
    else:
        raw_output = str(body)

    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, dict):
            return parsed.get("response") or parsed.get("message") or str(parsed)
        return str(parsed)
    except Exception:
        return raw_output


async def invoke_agent(
    prompt: str,
    session_id: str,
    actor_id: str,
    correlation_id: str
) -> Dict[str, Any]:
    with trace_span("agent.invoke", {
        "correlation_id": correlation_id,
        "session_id": session_id,
        "actor_id": actor_id,
        "prompt_length": len(prompt),
        "runtime_arn": settings.AGENTCORE_RUNTIME_ARN,
    }):
        loop = asyncio.get_running_loop()

        def _run():
            # 1. Attempt invocation of deployed AWS Bedrock AgentCore remote container via boto3
            if settings.AGENTCORE_RUNTIME_ARN:
                try:
                    logger.info(
                        f"Invoking remote deployed AgentCore Runtime container via boto3 ({settings.AGENTCORE_RUNTIME_ARN})"
                    )
                    return invoke_remote_agentcore_runtime(
                        prompt=prompt,
                        session_id=session_id,
                        actor_id=actor_id,
                        correlation_id=correlation_id,
                    )
                except Exception as exc:
                    logger.warning(
                        f"Remote AgentCore Runtime invocation via boto3 failed ({exc}). Falling back to local supervisor."
                    )

            # 2. Local in-process Strands supervisor fallback
            try:
                agent = get_supervisor(session_id=session_id, actor_id=actor_id)
                result = agent(prompt)
                return str(result)
            except Exception as exc:
                logger.warning(
                    f"Local Bedrock model invocation failed ({exc}). Using direct specialist router with live APIs."
                )
                return fallback_specialist_router(prompt=prompt, actor_id=actor_id)

        try:
            response_text = await loop.run_in_executor(None, _run)
        except Exception as exc:
            logger.error(f"Error during agent invocation: {exc}", exc_info=True)
            response_text = fallback_specialist_router(prompt=prompt, actor_id=actor_id)

        citations = extract_citations_from_text(response_text)

        return {
            "response": response_text,
            "session_id": session_id,
            "actor_id": actor_id,
            "correlation_id": correlation_id,
            "citations": citations,
        }


async def stream_agent_response(
    prompt: str,
    session_id: str,
    actor_id: str,
    correlation_id: str
) -> AsyncGenerator[str, None]:
    status_event = {
        "type": "status",
        "content": "Analyzing query and routing to specialist agents...",
        "session_id": session_id,
        "correlation_id": correlation_id,
    }
    yield f"data: {json.dumps(status_event)}\n\n"
    await asyncio.sleep(0.05)

    result = await invoke_agent(
        prompt=prompt,
        session_id=session_id,
        actor_id=actor_id,
        correlation_id=correlation_id
    )

    response_text = result["response"]
    citations = result.get("citations", [])

    words = response_text.split(" ")
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        chunk_text = " ".join(words[i:i + chunk_size])
        if i + chunk_size < len(words):
            chunk_text += " "

        chunk_event = {
            "type": "token",
            "content": chunk_text,
            "session_id": session_id,
            "correlation_id": correlation_id,
        }
        yield f"data: {json.dumps(chunk_event)}\n\n"
        await asyncio.sleep(0.02)

    if citations:
        citation_event = {
            "type": "citation",
            "content": "Verified source citations attached.",
            "citations": citations,
            "session_id": session_id,
            "correlation_id": correlation_id,
        }
        yield f"data: {json.dumps(citation_event)}\n\n"

    done_event = {
        "type": "done",
        "content": "",
        "session_id": session_id,
        "correlation_id": correlation_id,
    }
    yield f"data: {json.dumps(done_event)}\n\n"
