from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from models.adverse_event import AdverseEventCase


class UserSignup(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username_or_email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Clinical query or patient question")
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID")
    stream: bool = Field(default=False, description="Whether to stream response via Server-Sent Events (SSE)")


class CitationItem(BaseModel):
    source: str
    section: Optional[str] = None
    drug: Optional[str] = None
    evidence: Optional[Any] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    citations: List[CitationItem] = []
    correlation_id: str
    agent_used: Optional[str] = None
    created_at: datetime


class ChatStreamChunk(BaseModel):
    type: str
    content: str
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    citations: Optional[List[CitationItem]] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    correlation_id: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    agentcore_session_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class IntakeRequest(BaseModel):
    narrative: str = Field(..., min_length=10, description="Raw adverse event narrative text")


class IntakeResponse(BaseModel):
    case_id: str
    structured_case: AdverseEventCase
    narrative_redacted: str
    status: str
    correlation_id: str
    created_at: datetime


class CaseResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    narrative_redacted: str
    patient_name: Optional[str] = None
    drug_name: Optional[str] = None
    reaction: Optional[str] = None
    dose: Optional[str] = None
    seriousness: bool
    action_taken: Optional[str] = None
    outcome: Optional[str] = None
    status: str
    reviewer_notes: Optional[str] = None
    assigned_reviewer: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseUpdateStatusRequest(BaseModel):
    status: str = Field(..., description="Updated status: PENDING_REVIEW, TRIAGED, ESCALATED, RESOLVED")
    reviewer_notes: Optional[str] = None
    assigned_reviewer: Optional[str] = None


class CaseListResponse(BaseModel):
    total: int
    cases: List[CaseResponse]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    agentcore_runtime_arn: str
    database: str
    timestamp: datetime
