import re
import logging
import asyncio
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db_models import TriageCase, User
from backend.models.schemas import IntakeResponse
from backend.utils.pii import redact_pii
from backend.utils.telemetry import trace_span
from models.adverse_event import AdverseEventCase
from agents.intake_agent import process_adverse_event

logger = logging.getLogger("capstone.intake_service")


def fallback_extract_case(redacted_text: str) -> AdverseEventCase:
    text_lower = redacted_text.lower()

    drug_name = None
    if "ozempic" in text_lower or "semaglutide" in text_lower:
        drug_name = "Ozempic"
    elif "azithromycin" in text_lower or "zithromax" in text_lower:
        drug_name = "Azithromycin"
    elif "paracetamol" in text_lower or "acetaminophen" in text_lower or "pcm" in text_lower:
        drug_name = "Paracetamol"

    dose_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml))\b', redacted_text, re.IGNORECASE)
    dose = dose_match.group(1) if dose_match else None

    reactions = []
    reaction_keywords = [
        "nausea", "vomiting", "diarrhea", "rash", "hives", "dizziness",
        "headache", "liver injury", "hepatotoxicity", "hypoglycemia",
        "abdominal pain", "pruritus", "anaphylaxis", "pancreatitis", "dyspnea"
    ]
    for kw in reaction_keywords:
        if kw in text_lower:
            reactions.append(kw.title())
    reaction = ", ".join(reactions) if reactions else "Unspecified adverse reaction"

    serious_keywords = ["hospital", "emergency", "fatal", "death", "icu", "severe", "anaphylaxis", "life-threatening", "hepatotoxicity"]
    is_serious = any(kw in text_lower for kw in serious_keywords)

    action_taken = None
    if "discontinued" in text_lower or "stopped" in text_lower:
        action_taken = "Drug Discontinued"
    elif "dose reduced" in text_lower or "reduced dose" in text_lower:
        action_taken = "Dose Reduced"

    outcome = None
    if "recovered" in text_lower or "resolved" in text_lower:
        outcome = "Recovered"
    elif "improving" in text_lower:
        outcome = "Improving"
    elif "fatal" in text_lower or "died" in text_lower:
        outcome = "Fatal"

    return AdverseEventCase(
        patient_name="[REDACTED]",
        drug_name=drug_name,
        reaction=reaction,
        dose=dose,
        seriousness=is_serious,
        action_taken=action_taken,
        outcome=outcome,
    )


async def process_intake_narrative(
    raw_narrative: str,
    user: User,
    correlation_id: str,
    db: AsyncSession
) -> Tuple[TriageCase, AdverseEventCase]:
    redacted_narrative = redact_pii(raw_narrative)

    with trace_span("intake.extract_structured_case", {
        "correlation_id": correlation_id,
        "user_id": user.id,
        "narrative_length": len(redacted_narrative),
    }):
        loop = asyncio.get_running_loop()

        def _extract():
            try:
                extracted = process_adverse_event(redacted_narrative)
                if isinstance(extracted, AdverseEventCase):
                    return extracted
                elif isinstance(extracted, dict):
                    return AdverseEventCase(**extracted)
                return fallback_extract_case(redacted_narrative)
            except Exception as e:
                logger.warning(f"LLM structured intake extraction failed: {e}. Using rule extractor.")
                return fallback_extract_case(redacted_narrative)

        structured_case = await loop.run_in_executor(None, _extract)

    with trace_span("db.save_triage_case", {
        "correlation_id": correlation_id,
        "drug_name": structured_case.drug_name,
        "seriousness": structured_case.seriousness,
    }):
        case_status = "ESCALATED" if structured_case.seriousness else "PENDING_REVIEW"
        
        triage_case = TriageCase(
            user_id=user.id,
            correlation_id=correlation_id,
            raw_narrative=raw_narrative,
            narrative_redacted=redacted_narrative,
            patient_name=structured_case.patient_name,
            drug_name=structured_case.drug_name,
            reaction=structured_case.reaction,
            dose=structured_case.dose,
            seriousness=structured_case.seriousness,
            action_taken=structured_case.action_taken,
            outcome=structured_case.outcome,
            status=case_status,
        )
        db.add(triage_case)
        await db.commit()
        await db.refresh(triage_case)

    return triage_case, structured_case
