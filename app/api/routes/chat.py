"""
Peanut 3.0 - Chat V2 Router (authenticated, session-aware, SSE streaming)
"""

import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies.auth import get_optional_user
from app.api.dependencies.database import get_db
from app.core.logging.logger import get_logger
from app.models.message import Message
from app.models.session import Session
from app.models.user import User
from app.llm.llm_service import llm_service
from app.rag.pipelines.rag_pipeline import RAGPipeline

logger = get_logger(__name__)
rag_pipeline = RAGPipeline()

router = APIRouter(prefix="/chat", tags=["Chat V2"])


# ── Schemas ──

class ChatV2Request(BaseModel):
    message: str
    session_id: Optional[uuid.UUID] = None


class FollowUpQuestion(BaseModel):
    text: str


class ChatV2Meta(BaseModel):
    session_id: uuid.UUID
    follow_up_questions: list[str] = []


# ── Helpers ──

def _generate_follow_ups(user_message: str) -> list[str]:
    """Generate contextual follow-up question suggestions based on the user's query."""
    base = user_message.lower().strip()
    suggestions: list[str] = []

    if any(kw in base for kw in ["project", "built", "develop", "create"]):
        suggestions = [
            "What technologies were used in this project?",
            "What challenges were faced during development?",
            "How long did this project take to complete?",
        ]
    elif any(kw in base for kw in ["experience", "work", "intern", "job"]):
        suggestions = [
            "What were the key responsibilities?",
            "What skills were developed during this role?",
            "How did this experience influence career goals?",
        ]
    elif any(kw in base for kw in ["skill", "tech", "language", "framework"]):
        suggestions = [
            "What projects showcase these skills?",
            "How proficient is Aquib with this technology?",
            "Are there any certifications related to this?",
        ]
    else:
        suggestions = [
            "Tell me more about Aquib's projects.",
            "What is Aquib's educational background?",
            "What are Aquib's key technical skills?",
        ]

    return suggestions


# ── Endpoints ──

@router.post("/stream")
async def chat_stream(
    req: ChatV2Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> EventSourceResponse:
    # Resolve or create session
    if req.session_id:
        query = select(Session).where(Session.id == req.session_id)
        if current_user:
            query = query.where(Session.user_id == current_user.id)
            
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    else:
        user_id = current_user.id if current_user else None
        session = Session(user_id=user_id, title=req.message[:50])
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # 2. Retrieve recent message history (last 10 messages) for context
    stmt = (
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    chat_history = list(result.scalars().all())
    chat_history.reverse()  # reverse to chronological order

    # 3. Save the new user message to the database
    user_msg = Message(session_id=session.id, role="user", content=req.message)
    db.add(user_msg)
    await db.commit()

    async def event_generator() -> AsyncGenerator[dict, None]:
        import json as _json

        # Session metadata event
        yield {
            "event": "metadata",
            "data": _json.dumps({"session_id": str(session.id)}),
        }

        # Retrieve context from premium RAG pipeline
        try:
            context = await rag_pipeline.retrieve(req.message, user_id="")
        except Exception:
            context = ""

        # Stream LLM response via Groq
        full_response: list[str] = []
        token_stream = llm_service.stream_chat_response(
            query=req.message,
            context=context,
            chat_history=chat_history,
            is_sse=False
        )
        async for chunk in token_stream:
            full_response.append(chunk)
            yield {"event": "token", "data": chunk}

        # Save assistant message (strip the follow-up XML block)
        raw_content = "".join(full_response)
        assistant_content = raw_content
        if "<follow_ups>" in raw_content:
            assistant_content = raw_content.split("<follow_ups>")[0].strip()

        assistant_msg = Message(session_id=session.id, role="assistant", content=assistant_content)
        db.add(assistant_msg)
        await db.commit()

        # Follow-up suggestions
        try:
            from app.services.followup_service import FollowupService
            followup_service = FollowupService()
            follow_ups = await followup_service.generate_followups(
                query=req.message,
                response=assistant_content,
                context=context
            )
        except Exception:
            follow_ups = _generate_follow_ups(req.message)
            
        yield {
            "event": "follow_ups",
            "data": _json.dumps({"questions": follow_ups}),
        }

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
