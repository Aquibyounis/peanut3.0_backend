import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.schemas.support import (
    SupportSessionCreate, 
    SupportSessionResponse,
    SupportSessionWithMessagesResponse,
    SupportMessageCreate, 
    SupportMessageResponse
)
from app.services.support import SupportService

router = APIRouter()

def get_support_service(db: AsyncSession = Depends(get_db)) -> SupportService:
    return SupportService(db)

@router.post("/session/create", response_model=SupportSessionResponse)
async def create_support_session(
    data: SupportSessionCreate, 
    service: SupportService = Depends(get_support_service)
):
    """Create a new live support session."""
    return await service.create_session(data)

@router.post("/session/{session_id}/message/send", response_model=SupportMessageResponse)
async def send_support_message(
    session_id: uuid.UUID,
    data: SupportMessageCreate,
    service: SupportService = Depends(get_support_service)
):
    """Send a message to an existing support session."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "open":
        raise HTTPException(status_code=400, detail="Session is closed")
        
    return await service.send_message(session_id, data)

@router.get("/session/{session_id}", response_model=SupportSessionResponse)
async def get_support_session(
    session_id: uuid.UUID,
    service: SupportService = Depends(get_support_service)
):
    """Get support session details."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/session/{session_id}/messages", response_model=SupportSessionWithMessagesResponse)
async def get_session_messages(
    session_id: uuid.UUID,
    service: SupportService = Depends(get_support_service)
):
    """Get all messages for a support session."""
    session = await service.get_session_with_messages(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/session/{session_id}/close", response_model=SupportSessionResponse)
async def close_support_session(
    session_id: uuid.UUID,
    service: SupportService = Depends(get_support_service)
):
    """Close a support session."""
    session = await service.close_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
