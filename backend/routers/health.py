from datetime import datetime, timezone
from fastapi import APIRouter
from backend.models.schemas import HealthResponse
from backend.config import settings

router = APIRouter(tags=["Health & System"])


@router.get("/health", response_model=HealthResponse)
@router.get("/ping", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        agentcore_runtime_arn=settings.AGENTCORE_RUNTIME_ARN,
        database="connected",
        timestamp=datetime.now(timezone.utc),
    )
