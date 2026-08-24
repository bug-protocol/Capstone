import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.db_models import User, ChatSession, ChatMessage
from backend.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    CitationItem,
)
from backend.auth.dependencies import get_current_user
from backend.utils.telemetry import generate_correlation_id, trace_span
from backend.services.agent_service import invoke_agent, stream_agent_response

router = APIRouter(prefix="/chat", tags=["Chat & Consultation"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    correlation_id = generate_correlation_id()

    session = None
    if request.session_id:
        stmt = select(ChatSession).where(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()

    if not session:
        agentcore_session_id = f"ac-sess-{uuid.uuid4().hex[:8]}"
        session = ChatSession(
            user_id=current_user.id,
            title=request.message[:40] + ("..." if len(request.message) > 40 else ""),
            agentcore_session_id=agentcore_session_id,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message,
        correlation_id=correlation_id,
    )
    db.add(user_msg)
    await db.commit()

    if request.stream:
        async def stream_and_save():
            full_response_text = ""
            citations_data = []
            
            async for chunk_str in stream_agent_response(
                prompt=request.message,
                session_id=session.id,
                actor_id=current_user.username,
                correlation_id=correlation_id,
            ):
                yield chunk_str
                
                if chunk_str.startswith("data: "):
                    try:
                        data_str = chunk_str[6:].strip()
                        if data_str:
                            event = json.loads(data_str)
                            if event.get("type") == "token":
                                full_response_text += event.get("content", "")
                            elif event.get("type") == "citation":
                                citations_data = event.get("citations", [])
                    except Exception:
                        pass
            
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_response_text.strip(),
                correlation_id=correlation_id,
                citations=citations_data,
            )
            db.add(assistant_msg)
            await db.commit()

        return StreamingResponse(
            stream_and_save(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Correlation-ID": correlation_id,
            }
        )

    result = await invoke_agent(
        prompt=request.message,
        session_id=session.id,
        actor_id=current_user.username,
        correlation_id=correlation_id,
    )

    response_text = result["response"]
    citations_data = result.get("citations", [])

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        correlation_id=correlation_id,
        citations=citations_data,
    )
    db.add(assistant_msg)
    await db.commit()

    citations_models = [CitationItem(**c) for c in citations_data]

    return ChatResponse(
        session_id=session.id,
        response=response_text,
        citations=citations_models,
        correlation_id=correlation_id,
        agent_used="Supervisor (Strands SDK / AgentCore Runtime)",
        created_at=datetime.now(timezone.utc),
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_user_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.messages))
        .order_by(ChatSession.updated_at.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return sessions


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.messages))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return session
