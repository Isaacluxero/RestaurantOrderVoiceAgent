"""Twilio voice webhook endpoints."""
import logging
from fastapi import APIRouter, Request, Form, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_menu_repository
from app.core.config import settings
from app.services.menu.repository import MenuRepository
from app.services.agent.agent import AgentService
from app.services.call_session.manager import CallSessionManager

router = APIRouter()
logger = logging.getLogger(__name__)


def get_base_url(request: Request) -> str:
    """
    Get the base URL for constructing absolute URLs.
    
    Uses BASE_URL environment variable if set (e.g., for Railway),
    otherwise constructs from request.
    """
    if settings.base_url:
        # Use configured base URL (e.g., from Railway environment variable)
        return settings.base_url.rstrip('/')
    
    # Fall back to request.base_url (works on Railway)
    return str(request.base_url).rstrip('/')


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
    logger.info(
        f"[INCOMING CALL] Received incoming call webhook - CallSid: {CallSid}, "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    try:
        # Create session and get greeting
        logger.debug(f"[INCOMING CALL] Creating session for CallSid: {CallSid}")
        greeting = await session_manager.get_greeting(CallSid)
        logger.info(f"[INCOMING CALL] Session created, greeting generated (length: {len(greeting)}) - CallSid: {CallSid}")

        # Generate TwiML with Gather to collect user speech
        from app.services.speech.tts import TextToSpeechService

        tts_service = TextToSpeechService()
        # Construct absolute URL from request (handles proxy headers like ngrok)
        base_url = get_base_url(request)
        gather_url = f"{base_url}/webhooks/voice/gather?CallSid={CallSid}"
        logger.debug(f"[INCOMING CALL] Generating TwiML with gather URL: {gather_url} - CallSid: {CallSid}")
        twiml = tts_service.generate_twiml_with_gather(greeting, gather_url)
        
        logger.info(
            f"[INCOMING CALL] Successfully processed incoming call - CallSid: {CallSid}, "
            f"TwiML length: {len(twiml)} bytes"
        )
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(
            f"[INCOMING CALL] Error processing incoming call - CallSid: {CallSid}, "
            f"Error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Error processing incoming call: {str(e)}")


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
    logger.info(
        f"[GATHER] Received speech input - CallSid: {CallSid}, "
        f"SpeechResult length: {len(SpeechResult) if SpeechResult else 0}, "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    if SpeechResult:
        logger.debug(
            f"[GATHER] Speech text: '{SpeechResult[:200]}{'...' if len(SpeechResult) > 200 else ''}' - CallSid: {CallSid}"
        )
    else:
        logger.warning(f"[GATHER] No speech result provided (empty or None) - CallSid: {CallSid}")
    
    try:
        # Process the speech and generate response
        # Construct absolute URL from request (handles proxy headers like ngrok)
        base_url = get_base_url(request)
        logger.debug(f"[GATHER] Processing speech for CallSid: {CallSid}")
        twiml = await session_manager.process_user_speech(CallSid, SpeechResult, base_url=base_url)
        
        logger.info(
            f"[GATHER] Successfully processed speech input - CallSid: {CallSid}, "
            f"TwiML length: {len(twiml)} bytes"
        )
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(
            f"[GATHER] Error processing speech input - CallSid: {CallSid}, "
            f"SpeechResult: '{SpeechResult[:100] if SpeechResult else 'None'}', "
            f"Error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        # Return a graceful error response to Twilio
        error_message = "I'm sorry, I encountered an error. Please try again."
        from app.services.speech.tts import TextToSpeechService
        tts_service = TextToSpeechService()
        # Construct absolute URL from request (handles proxy headers like ngrok)
        base_url = get_base_url(request)
        error_twiml = tts_service.generate_twiml_with_gather(
            error_message, f"{base_url}/webhooks/voice/gather?CallSid={CallSid}"
        )
        return Response(content=error_twiml, media_type="application/xml")


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
    logger.info(
        f"[CALL STATUS] Received status update - CallSid: {CallSid}, "
        f"CallStatus: {CallStatus}, "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    try:
        if CallStatus in ["completed", "failed", "busy", "no-answer"]:
            logger.info(
                f"[CALL STATUS] Ending session for call - CallSid: {CallSid}, "
                f"Reason: {CallStatus}"
            )
            # End session with the actual status
            await session_manager.end_session(CallSid, status=CallStatus)
            logger.info(
                f"[CALL STATUS] Session ended successfully - CallSid: {CallSid}, "
                f"Final status: {CallStatus}"
            )
        else:
            logger.debug(
                f"[CALL STATUS] Status update received but no action needed - "
                f"CallSid: {CallSid}, CallStatus: {CallStatus}"
            )

        return Response(content="OK", media_type="text/plain")
    
    except Exception as e:
        logger.error(
            f"[CALL STATUS] Error handling call status update - CallSid: {CallSid}, "
            f"CallStatus: {CallStatus}, Error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        # Still return OK to Twilio to avoid retries
        return Response(content="OK", media_type="text/plain")

