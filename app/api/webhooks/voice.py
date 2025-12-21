"""Twilio voice webhook endpoints."""
from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_menu_repository
from app.services.menu.repository import MenuRepository
from app.services.agent.agent import AgentService
from app.services.call_session.manager import CallSessionManager

router = APIRouter()


def get_session_manager(
    db: AsyncSession = Depends(get_db),
    menu_repository: MenuRepository = Depends(get_menu_repository),
) -> CallSessionManager:
    """Get call session manager."""
    agent_service = AgentService(menu_repository)
    return CallSessionManager(db, agent_service, menu_repository)


@router.post("/voice/incoming")
async def handle_incoming_call(
    request: Request,
    CallSid: str = Form(...),
    session_manager: CallSessionManager = Depends(get_session_manager),
):
    """
    Handle incoming call from Twilio.

    This endpoint is called when a call comes in.
    """
    # Create session and get greeting
    greeting = await session_manager.get_greeting(CallSid)

    # Generate TwiML with Gather to collect user speech
    from app.services.speech.tts import TextToSpeechService

    tts_service = TextToSpeechService()
    twiml = tts_service.generate_twiml_with_gather(
        greeting, f"/webhooks/voice/gather?CallSid={CallSid}"
    )

    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/gather")
async def handle_gather(
    request: Request,
    CallSid: str = Query(...),
    SpeechResult: str = Form(None),
    session_manager: CallSessionManager = Depends(get_session_manager),
):
    """
    Handle gathered speech from Twilio.

    This endpoint is called after Twilio collects user speech.
    """
    # Process the speech and generate response
    twiml = await session_manager.process_user_speech(CallSid, SpeechResult)

    return Response(content=twiml, media_type="application/xml")


@router.post("/voice/status")
async def handle_call_status(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    session_manager: CallSessionManager = Depends(get_session_manager),
):
    """
    Handle call status updates from Twilio.

    This endpoint is called when call status changes (completed, failed, etc.).
    """
    if CallStatus in ["completed", "failed", "busy", "no-answer"]:
        # End session
        await session_manager.end_session(CallSid)

    return Response(content="OK", media_type="text/plain")

