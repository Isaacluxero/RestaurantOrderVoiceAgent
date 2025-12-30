"""Call session manager."""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.call_session.models import CallSession
from app.services.agent.state import ConversationState
from app.services.agent.agent import AgentService
from app.services.speech.stt import SpeechToTextService
from app.services.speech.tts import TextToSpeechService
from app.services.menu.repository import MenuRepository
from app.services.ordering.parser import OrderParser
from app.services.ordering.validator import OrderValidator
from app.services.persistence.calls import CallPersistenceService
from app.services.persistence.orders import OrderPersistenceService
from app.services.agent.state import OrderItem as StateOrderItem


class CallSessionManager:
    """Manages call sessions and orchestrates the conversation flow."""

    def __init__(
        self,
        db: AsyncSession,
        agent_service: AgentService,
        menu_repository: MenuRepository,
    ):
        self.db = db
        self.agent_service = agent_service
        self.menu_repository = menu_repository
        self.stt_service = SpeechToTextService()
        self.tts_service = TextToSpeechService()
        self.order_parser = OrderParser(menu_repository)
        self.order_validator = OrderValidator(menu_repository)
        self.call_persistence = CallPersistenceService(db)
        self.order_persistence = OrderPersistenceService(db)

        # In-memory session storage (for MVP)
        # In production, use Redis or similar
        self.sessions: Dict[str, CallSession] = {}

    async def create_session(self, call_sid: str) -> CallSession:
        """Create a new call session."""
        # Create call record in database
        call_record = await self.call_persistence.create_call(call_sid)

        # Get menu text and requirements for context
        menu_text = await self.menu_repository.get_menu_text()
        item_requirements_text = await self.menu_repository.get_item_requirements_text()

        # Initialize conversation state
        state = await self.agent_service.initialize_state(call_sid, menu_text, item_requirements_text)

        # Create session
        session = CallSession(
            call_sid=call_sid,
            state=state,
            call_id=call_record.id,
        )

        # Store session
        self.sessions[call_sid] = session

        return session

    async def get_session(self, call_sid: str) -> Optional[CallSession]:
        """Get an existing call session."""
        return self.sessions.get(call_sid)

    async def get_greeting(self, call_sid: str) -> str:
        """Get greeting message for a call."""
        session = await self.get_session(call_sid)
        if not session:
            session = await self.create_session(call_sid)

        greeting = await self.agent_service.get_greeting(session.state)
        return greeting

    async def process_user_speech(
        self, call_sid: str, speech_result: Optional[str] = None
    ) -> str:
        """
        Process user speech and generate response.

        Args:
            call_sid: Twilio call SID
            speech_result: Transcribed speech from Twilio (if available)

        Returns:
            TwiML XML response
        """
        session = await self.get_session(call_sid)
        if not session:
            session = await self.create_session(call_sid)

        # If no speech result provided, we'll need to gather it
        if not speech_result:
            # This shouldn't happen in normal flow, but handle gracefully
            response_text = "I didn't catch that. Could you repeat?"
            return self.tts_service.generate_twiml_with_gather(
                response_text, f"/webhooks/voice/gather?CallSid={call_sid}"
            )

        # Process user input through agent
        agent_response = await self.agent_service.process_user_input(
            session.state, speech_result
        )

        response_text = agent_response.get("response", "")
        intent = agent_response.get("intent", "")
        action = agent_response.get("action", {})

        # Handle action
        if action.get("type") == "add_item":
            order_item = await self.order_parser.parse_agent_action(
                action, speech_result
            )
            if order_item:
                # Validate item
                is_valid, errors = await self.order_parser.validate_order_item(
                    order_item
                )
                if is_valid:
                    # Add to state
                    state_item = StateOrderItem(
                        item_name=order_item.item_name,
                        quantity=order_item.quantity,
                        modifiers=order_item.modifiers,
                    )
                    session.state.add_order_item(state_item)
                else:
                    # Item not valid, agent should have handled this, but add error context
                    if errors:
                        response_text += f" {errors[0]}"

        # Check if order is being confirmed
        if intent == "confirming_order" or intent == "completing":
            # Persist order
            await self._persist_order(session)

            if intent == "completing":
                # Read back order and end call
                order_summary = session.state.get_order_summary()
                from app.core.config import settings
                response_text = f"Perfect! Your order: {order_summary}. Thank you for calling {settings.restaurant_name}!"
                session.state.stage = "completed"

        # Generate TwiML response
        if session.state.stage == "completed":
            # End call
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{response_text}</Say>
    <Hangup/>
</Response>"""
        else:
            # Continue conversation
            return self.tts_service.generate_twiml_with_gather(
                response_text,
                f"/webhooks/voice/gather?CallSid={call_sid}",
            )

    async def _persist_order(self, session: CallSession) -> None:
        """Persist the current order to database."""
        if not session.state.current_order:
            return

        # Convert state items to dict format
        order_items = [
            {
                "item_name": item.item_name,
                "quantity": item.quantity,
                "modifiers": item.modifiers,
            }
            for item in session.state.current_order
        ]

        # Create order
        order = await self.order_persistence.create_order(
            call_id=session.call_id,
            raw_text=session.state.get_transcript_text(),
            structured_order={"items": order_items},
        )

        # Add order items
        await self.order_persistence.add_order_items(order.id, order_items)

        # Confirm order
        await self.order_persistence.confirm_order(order.id)

    async def end_session(self, call_sid: str, status: str = "completed") -> None:
        """End a call session and clean up.
        
        Args:
            call_sid: Twilio call SID
            status: Call status - "completed", "failed", "busy", or "no-answer"
        """
        from datetime import datetime
        from sqlalchemy import select, func
        from app.db.models import Order
        
        session = await self.get_session(call_sid)
        
        # Get the call record to check for orders
        call_record = await self.call_persistence.get_call_by_sid(call_sid)
        if not call_record:
            # Call doesn't exist, nothing to do
            return
        
        # Check if call has any orders in the database
        result = await self.db.execute(
            select(func.count(Order.id)).where(Order.call_id == call_record.id)
        )
        order_count = result.scalar() or 0
        
        # Also check session state for orders (in case they're in memory but not persisted)
        has_orders_in_session = False
        if session and session.state and session.state.current_order:
            has_orders_in_session = len(session.state.current_order) > 0
        
        # Determine final status
        # If no orders, always mark as failed
        if order_count == 0 and not has_orders_in_session:
            db_status = "failed"
        # If Twilio status indicates failure, mark as failed
        elif status in ["failed", "busy", "no-answer"]:
            db_status = "failed"
        # Otherwise mark as completed (has orders)
        else:
            db_status = "completed"
        
        # Always update status (never leave as in_progress)
        await self.call_persistence.update_call_status(
            call_sid, db_status, ended_at=datetime.utcnow()
        )

        # Update transcript if available
        if session and session.state:
            transcript = session.state.get_transcript_text()
            if transcript:
                await self.call_persistence.update_call_transcript(
                    call_sid, transcript
                )

        # Remove from memory
        if call_sid in self.sessions:
            del self.sessions[call_sid]

