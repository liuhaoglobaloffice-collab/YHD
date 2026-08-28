"""
Weekly Meeting Chat API Routes.

Provides CRUD for meetings and messages, plus AI-powered summary generation.
"""

import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db
from src.api.dependencies import get_current_user
from src.identity.models import User
from src.database.models import MeetingModel, MessageModel
from src.knowledge.rag_pipeline import RAGPipeline
from src.knowledge.vector_store import SQLiteVectorStore

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/meetings", tags=["meetings"])


# ==================== Schemas ====================


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, pattern=r"^(active|completed)$")


class MeetingOut(BaseModel):
    id: str
    title: str
    date: str
    status: str
    created_at: str
    updated_at: str


class MessageSend(BaseModel):
    sender: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="member", pattern=r"^(admin|member)$")
    content: str = Field(..., min_length=1)


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class MessageOut(BaseModel):
    id: str
    meeting_id: str
    sender: str
    role: str
    content: str
    time: str


class MeetingListOut(BaseModel):
    meetings: List[MeetingOut]
    total: int


class MessageListOut(BaseModel):
    messages: List[MessageOut]
    total: int


class SummaryOut(BaseModel):
    summary: str


# ==================== Helpers ====================


def _to_meeting_out(m: MeetingModel) -> MeetingOut:
    return MeetingOut(
        id=m.id,
        title=m.title,
        date=m.date,
        status=m.status,
        created_at=m.created_at.isoformat() if m.created_at else "",
        updated_at=m.updated_at.isoformat() if m.updated_at else "",
    )


def _to_message_out(msg: MessageModel) -> MessageOut:
    return MessageOut(
        id=msg.id,
        meeting_id=msg.meeting_id,
        sender=msg.sender,
        role=msg.role,
        content=msg.content,
        time=msg.time,
    )


# ==================== Endpoints ====================


@router.get("", response_model=MeetingListOut)
async def list_meetings(
    status: Optional[str] = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all meetings, optionally filtered by status."""
    stmt = select(MeetingModel).order_by(MeetingModel.date.desc())
    if status:
        stmt = stmt.where(MeetingModel.status == status)
    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    meetings = result.scalars().all()

    return MeetingListOut(
        meetings=[_to_meeting_out(m) for m in meetings],
        total=len(meetings),
    )


@router.post("", response_model=MeetingOut, status_code=201)
async def create_meeting(
    request: MeetingCreate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Create a new weekly meeting."""
    meeting = MeetingModel(
        id=str(uuid.uuid4()),
        title=request.title,
        date=request.date,
        status="active",
    )
    session.add(meeting)
    await session.flush()
    await session.commit()

    logger.info("meeting_created", meeting_id=meeting.id, title=meeting.title)
    return _to_meeting_out(meeting)


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a single meeting by ID."""
    result = await session.execute(select(MeetingModel).where(MeetingModel.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return _to_meeting_out(meeting)


@router.get("/{meeting_id}/messages", response_model=MessageListOut)
async def list_messages(
    meeting_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all messages for a meeting."""
    # Verify meeting exists
    result = await session.execute(select(MeetingModel).where(MeetingModel.id == meeting_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Meeting not found")

    stmt = (
        select(MessageModel)
        .where(MessageModel.meeting_id == meeting_id)
        .order_by(MessageModel.id.asc())
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()

    return MessageListOut(
        messages=[_to_message_out(m) for m in messages],
        total=len(messages),
    )


@router.post("/{meeting_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    meeting_id: str,
    request: MessageSend,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Send a message in a meeting."""
    # Verify meeting exists
    result = await session.execute(select(MeetingModel).where(MeetingModel.id == meeting_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Meeting not found")

    now = datetime.now()
    time_str = now.strftime("%H:%M")

    msg = MessageModel(
        id=str(uuid.uuid4()),
        meeting_id=meeting_id,
        sender=request.sender,
        role=request.role,
        content=request.content,
        time=time_str,
    )
    session.add(msg)
    await session.flush()
    await session.commit()

    logger.info("message_sent", meeting_id=meeting_id, sender=request.sender)
    return _to_message_out(msg)


@router.post("/{meeting_id}/summary", response_model=SummaryOut)
async def generate_summary(
    meeting_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Generate an AI summary of the meeting using the RAG pipeline."""
    # Verify meeting exists
    result = await session.execute(select(MeetingModel).where(MeetingModel.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Fetch all messages
    stmt = (
        select(MessageModel)
        .where(MessageModel.meeting_id == meeting_id)
        .order_by(MessageModel.id.asc())
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()

    if not messages:
        raise HTTPException(status_code=400, detail="No messages to summarize")

    # Build context from messages
    context = "\n".join(
        f"[{m.sender} ({m.role})] {m.content}" for m in messages
    )

    # Use RAG pipeline to generate summary
    store = SQLiteVectorStore()
    pipeline = RAGPipeline(vector_store=store, provider_name="mock")
    result = await pipeline.query(
        f"Please summarize the following meeting '{meeting.title}' in bullet points:\n\n{context}",
        limit=1,
    )

    summary = result.get("answer", "Summary generation failed.")

    logger.info("summary_generated", meeting_id=meeting_id, meeting_title=meeting.title)
    return SummaryOut(summary=summary)


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(
    meeting_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a meeting and all its messages."""
    result = await session.execute(select(MeetingModel).where(MeetingModel.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Delete messages first
    await session.execute(delete(MessageModel).where(MessageModel.meeting_id == meeting_id))
    await session.delete(meeting)
    await session.flush()
    await session.commit()

    logger.info("meeting_deleted", meeting_id=meeting_id)


@router.patch("/{meeting_id}", response_model=MeetingOut)
async def update_meeting(
    meeting_id: str,
    request: MeetingUpdate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Update a meeting (title and/or status)."""
    result = await session.execute(select(MeetingModel).where(MeetingModel.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if request.title is not None:
        meeting.title = request.title
    if request.status is not None:
        meeting.status = request.status

    await session.flush()
    await session.commit()
    await session.refresh(meeting)

    logger.info("meeting_updated", meeting_id=meeting_id, status=meeting.status)
    return _to_meeting_out(meeting)


@router.put("/{meeting_id}/messages/{message_id}", response_model=MessageOut)
async def update_message(
    meeting_id: str,
    message_id: str,
    request: MessageUpdate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Edit a message's content."""
    result = await session.execute(
        select(MessageModel).where(
            MessageModel.id == message_id,
            MessageModel.meeting_id == meeting_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.content = request.content
    await session.flush()
    await session.commit()
    await session.refresh(msg)

    logger.info("message_updated", message_id=message_id, meeting_id=meeting_id)
    return _to_message_out(msg)


@router.delete("/{meeting_id}/messages/{message_id}", status_code=204)
async def delete_message(
    meeting_id: str,
    message_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Delete a message."""
    result = await session.execute(
        select(MessageModel).where(
            MessageModel.id == message_id,
            MessageModel.meeting_id == meeting_id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    await session.delete(msg)
    await session.flush()
    await session.commit()

    logger.info("message_deleted", message_id=message_id, meeting_id=meeting_id)