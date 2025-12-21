"""Call persistence service."""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Call


class CallPersistenceService:
    """Service for persisting call data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_call(self, call_sid: str) -> Call:
        """Create a new call record or return existing one."""
        # Check if call already exists
        existing_call = await self.get_call_by_sid(call_sid)
        if existing_call:
            return existing_call
        
        # Create new call
        call = Call(call_sid=call_sid, status="in_progress")
        self.db.add(call)
        await self.db.commit()
        await self.db.refresh(call)
        return call

    async def get_call_by_sid(self, call_sid: str) -> Optional[Call]:
        """Get call by Twilio call SID."""
        result = await self.db.execute(
            select(Call).where(Call.call_sid == call_sid)
        )
        return result.scalar_one_or_none()

    async def update_call_status(
        self, call_sid: str, status: str, ended_at: Optional[datetime] = None
    ) -> Optional[Call]:
        """Update call status."""
        call = await self.get_call_by_sid(call_sid)
        if call:
            call.status = status
            if ended_at:
                call.ended_at = ended_at
            await self.db.commit()
            await self.db.refresh(call)
        return call

    async def update_call_transcript(self, call_sid: str, transcript: str) -> Optional[Call]:
        """Update call transcript."""
        call = await self.get_call_by_sid(call_sid)
        if call:
            call.transcript = transcript
            await self.db.commit()
            await self.db.refresh(call)
        return call

