import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.models.message import Message
from app.models.session import Session
from app.llm.llm_service import llm_service
from app.rag.pipelines.rag_pipeline import RAGPipeline

router = APIRouter()
rag_pipeline = RAGPipeline()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@router.post("/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. Resolve or create session
    session = None
    if req.session_id:
        try:
            session_uuid = uuid.UUID(str(req.session_id))
            query = select(Session).where(Session.id == session_uuid)
            result = await db.execute(query)
            session = result.scalar_one_or_none()
            if session is None:
                # Create a new session with this specific ID
                session = Session(id=session_uuid, title=req.message[:50])
                db.add(session)
                await db.commit()
                await db.refresh(session)
        except ValueError:
            pass

    if session is None:
        session = Session(title=req.message[:50])
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

    # 4. Stream response and save assistant reply upon completion
    async def response_generator():
        # Retrieve hybrid RAG context asynchronously
        try:
            context = await rag_pipeline.retrieve(req.message, user_id="")
        except Exception:
            context = ""
            
        full_response = []
        token_stream = llm_service.stream_chat_response(
            query=req.message,
            context=context,
            chat_history=chat_history,
            is_sse=False
        )
        
        async for chunk in token_stream:
            full_response.append(chunk)
            yield chunk

        # Save assistant message to database (strip the follow-up XML block)
        raw_content = "".join(full_response)
        assistant_content = raw_content
        if "<follow_ups>" in raw_content:
            assistant_content = raw_content.split("<follow_ups>")[0].strip()
            
        assistant_msg = Message(
            session_id=session.id,
            role="assistant",
            content=assistant_content
        )
        db.add(assistant_msg)
        await db.commit()

    return StreamingResponse(
        response_generator(),
        media_type="text/plain"
    )