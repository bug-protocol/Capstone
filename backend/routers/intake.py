from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.db_models import User
from backend.models.schemas import IntakeRequest, IntakeResponse
from backend.auth.dependencies import get_current_user
from backend.utils.telemetry import generate_correlation_id
from backend.services.intake_service import process_intake_narrative

router = APIRouter(prefix="/intake", tags=["Adverse Event Intake"])


@router.post("", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
async def submit_adverse_event_intake(
    request: IntakeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    correlation_id = generate_correlation_id()

    triage_case, structured_case = await process_intake_narrative(
        raw_narrative=request.narrative,
        user=current_user,
        correlation_id=correlation_id,
        db=db,
    )

    return IntakeResponse(
        case_id=triage_case.id,
        structured_case=structured_case,
        narrative_redacted=triage_case.narrative_redacted,
        status=triage_case.status,
        correlation_id=correlation_id,
        created_at=triage_case.created_at,
    )
