"""Call session manager."""
import logging
from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.call_session.models import CallSession
from app.services.agent.state import ConversationState
from app.services.agent.stages import ConversationStage
from app.services.agent.agent import AgentService
from app.services.speech.stt import SpeechToTextService
from app.services.speech.tts import TextToSpeechService
from app.services.menu.repository import MenuRepository
from app.services.ordering.parser import OrderParser
from app.services.ordering.validator import OrderValidator
from app.services.persistence.calls import CallPersistenceService
from app.services.persistence.orders import OrderPersistenceService
from app.services.agent.state import OrderItem as StateOrderItem
from app.services.agent.constants import NO_RESPONSE_INDICATORS

logger = logging.getLogger(__name__)

# Module-level session storage (persists across requests)
# In production, use Redis or similar
_sessions: Dict[str, CallSession] = {}


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

    async def create_session(self, call_sid: str) -> CallSession:
        """Create a new call session."""
        # Create call record in database
        call_record = await self.call_persistence.create_call(call_sid)

        # Get menu text and requirements for context
        menu_text = await self.menu_repository.get_menu_text()

        # Initialize conversation state
        state = await self.agent_service.initialize_state(call_sid, menu_text, "")

        # Create session
        session = CallSession(
            call_sid=call_sid,
            state=state,
            call_id=call_record.id,
        )

        # Store session in module-level dict
        _sessions[call_sid] = session

        return session

    async def get_session(self, call_sid: str) -> Optional[CallSession]:
        """Get an existing call session."""
        return _sessions.get(call_sid)

    async def get_greeting(self, call_sid: str) -> str:
        """Get greeting message for a call."""
        session = await self.get_session(call_sid)
        if not session:
            session = await self.create_session(call_sid)

        greeting = await self.agent_service.get_greeting(session.state)
        return greeting

    async def process_user_speech(
        self, call_sid: str, speech_result: Optional[str] = None, base_url: str = ""
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

        # Validate speech result
        if not speech_result or not speech_result.strip():
            # Empty or whitespace-only speech
            logger.warning(
                f"[SESSION MANAGER] Empty speech result for call {call_sid}"
            )
            response_text = "I didn't catch that. Could you please repeat what you'd like?"
            gather_url = f"{base_url}/webhooks/voice/gather?CallSid={call_sid}" if base_url else f"/webhooks/voice/gather?CallSid={call_sid}"
            return self.tts_service.generate_twiml_with_gather(
                response_text, gather_url
            )

        # Check for very short speech (likely transcription error or noise)
        if len(speech_result.strip()) < 2:
            logger.warning(
                f"[SESSION MANAGER] Very short speech result for call {call_sid}: '{speech_result}'"
            )
            response_text = "I didn't quite get that. Could you please say that again?"
            gather_url = f"{base_url}/webhooks/voice/gather?CallSid={call_sid}" if base_url else f"/webhooks/voice/gather?CallSid={call_sid}"
            return self.tts_service.generate_twiml_with_gather(
                response_text, gather_url
            )

        # Increment turn count
        session.state.turn_count += 1
        logger.info(f"[SESSION MANAGER] Turn {session.state.turn_count} for call {call_sid}")

        # Check turn limit (20 turns max)
        MAX_TURNS = 20
        if session.state.turn_count >= MAX_TURNS:
            logger.warning(
                f"[SESSION MANAGER] Turn limit reached ({MAX_TURNS}) for call {call_sid}, "
                f"offering to transfer"
            )
            response_text = (
                "I apologize, but I'm having difficulty completing your order. "
                "Would you like me to transfer you to someone who can help?"
            )
            from app.services.agent.stages import ConversationStage
            session.state.stage = ConversationStage.CONCLUSION
            gather_url = f"{base_url}/webhooks/voice/gather?CallSid={call_sid}" if base_url else f"/webhooks/voice/gather?CallSid={call_sid}"
            return self.tts_service.generate_twiml_with_gather(
                response_text, gather_url
            )

        # Process user input through agent
        agent_response = await self.agent_service.process_user_input(
            session.state, speech_result
        )

        # Validate agent response has required fields
        if not agent_response or not isinstance(agent_response, dict):
            logger.error(
                f"[SESSION MANAGER] Invalid agent response (not a dict): {agent_response}"
            )
            response_text = "I'm having trouble processing that. Could you please say that again?"
            gather_url = f"{base_url}/webhooks/voice/gather?CallSid={call_sid}" if base_url else f"/webhooks/voice/gather?CallSid={call_sid}"
            return self.tts_service.generate_twiml_with_gather(
                response_text, gather_url
            )

        response_text = agent_response.get("response", "")
        intent = agent_response.get("intent", "")
        action = agent_response.get("action", {})
        has_error = agent_response.get("error", False)

        # Treat as error if response text is missing or empty
        if not response_text or not response_text.strip():
            logger.warning(
                "[SESSION MANAGER] Agent returned empty response text, treating as error"
            )
            has_error = True
            response_text = "I'm sorry, I didn't understand that. Could you please repeat?"

        # Track consecutive errors
        if has_error:
            session.state.consecutive_errors += 1
            logger.warning(
                f"[SESSION MANAGER] Consecutive errors: {session.state.consecutive_errors} "
                f"for call {call_sid}"
            )

            # If 3+ consecutive errors, offer to transfer
            if session.state.consecutive_errors >= 3:
                logger.error(
                    f"[SESSION MANAGER] Too many consecutive errors ({session.state.consecutive_errors}) "
                    f"for call {call_sid}, offering to transfer"
                )
                response_text = (
                    "I'm having trouble understanding you. "
                    "Would you like me to transfer you to someone who can help with your order?"
                )
                from app.services.agent.stages import ConversationStage
                session.state.stage = ConversationStage.CONCLUSION
                gather_url = f"{base_url}/webhooks/voice/gather?CallSid={call_sid}" if base_url else f"/webhooks/voice/gather?CallSid={call_sid}"
                return self.tts_service.generate_twiml_with_gather(
                    response_text, gather_url
                )
        else:
            # Reset error counter on successful response
            session.state.consecutive_errors = 0

        # Skip action processing if there was an error (agent didn't understand)
        if has_error:
            logger.warning(
                "[SESSION MANAGER] Skipping action processing due to agent error/fallback response"
            )
            # Keep current stage and just return the clarification response
            gather_url = f"{base_url}/webhooks/voice/gather?CallSid={call_sid}" if base_url else f"/webhooks/voice/gather?CallSid={call_sid}"
            return self.tts_service.generate_twiml_with_gather(
                response_text, gather_url
            )

        # Validate action structure
        if not isinstance(action, dict) or "type" not in action:
            logger.warning(
                f"[SESSION MANAGER] Invalid action structure: {action}, setting to none"
            )
            action = {"type": "none"}

        # Validate action type is allowed in current stage
        action_type = action.get("type", "none")
        if not self._is_action_allowed_in_stage(action_type, session.state.stage):
            logger.warning(
                f"[SESSION MANAGER] Action '{action_type}' not allowed in stage "
                f"{session.state.stage.value}"
            )
            # Reset action to none if invalid for current stage
            action = {"type": "none"}

        # Handle action
        if action.get("type") == "add_item":
            response_text = await self._handle_add_item(
                action, speech_result, session, response_text
            )
        elif action.get("type") == "add_modifiers":
            response_text = await self._handle_add_modifiers(
                action, speech_result, session, response_text
            )
        elif action.get("type") == "remove_item":
            response_text = await self._handle_remove_item(action, session, response_text)
        elif action.get("type") == "modify_item":
            response_text = await self._handle_modify_item(action, session, response_text)

        # Check if order is being confirmed
        if intent == "confirming_order" or intent == "completing":
            # Persist order
            persist_success = await self._persist_order(session)

            if intent == "completing":
                # End call - order was already read back in REVIEW stage
                from app.services.agent.stages import ConversationStage
                from app.core.config import settings

                if persist_success:
                    response_text = f"Perfect! Thank you for calling {settings.restaurant_name}! Your order will be ready in 30 minutes."
                    session.state.stage = ConversationStage.CONCLUSION
                else:
                    # Critical error - order failed to save
                    logger.error(
                        f"[SESSION MANAGER] Order persistence failed for call {call_sid}, "
                        f"not completing order"
                    )
                    response_text = (
                        "I'm sorry, we're having technical difficulties. "
                        "Please call us back in a few minutes to place your order."
                    )
                    session.state.stage = ConversationStage.CONCLUSION

        # Handle REVIEW stage: read back order on first entry (server-side)
        from app.services.agent.stages import ConversationStage

        # Check if customer is asking for order repeat in REVIEW stage
        repeat_keywords = ["repeat", "say that again", "what did", "can you repeat", "tell me again", "what was"]
        is_asking_repeat = False
        if session.state.stage == ConversationStage.REVIEW and speech_result:
            speech_lower = speech_result.lower()
            is_asking_repeat = any(keyword in speech_lower for keyword in repeat_keywords)

        # Read back order if: (1) first time in REVIEW, OR (2) customer asks for repeat
        if session.state.stage == ConversationStage.REVIEW and (not session.state.order_read_back or is_asking_repeat):
            # First time in REVIEW - read back the order
            # Format order summary for TTS (no newlines, natural speech)
            order_items = session.state.current_order
            if not order_items:
                order_summary_tts = "No items in order yet."
                response_text = f"Perfect! Here's your order: {order_summary_tts}. Does that look correct?"
            else:
                item_parts = []
                for item in order_items:
                    qty_str = f"{item.quantity} " if item.quantity > 1 else ""
                    mod_str = f" with {', '.join(item.modifiers)}" if item.modifiers else ""
                    item_parts.append(f"{qty_str}{item.item_name}{mod_str}")
                # Join with "and" for natural speech
                if len(item_parts) == 1:
                    order_summary_tts = item_parts[0]
                elif len(item_parts) == 2:
                    order_summary_tts = f"{item_parts[0]} and {item_parts[1]}"
                else:
                    order_summary_tts = ", ".join(item_parts[:-1]) + f", and {item_parts[-1]}"

                # Calculate order total
                subtotal = 0.0
                for item in order_items:
                    menu_item = await self.menu_repository.get_item_by_name(item.item_name)
                    if menu_item and menu_item.price:
                        subtotal += menu_item.price * item.quantity

                # Calculate tax and total
                from app.core.config import settings
                tax = subtotal * settings.tax_rate
                total = subtotal + tax

                # Format total for speech
                total_text = f" Your total is ${total:.2f}."
                response_text = f"Perfect! Here's your order: {order_summary_tts}.{total_text} Does that look correct?"

            session.state.order_read_back = True  # Mark as read back
            if is_asking_repeat:
                logger.info(f"[SESSION MANAGER] Customer requested order repeat in REVIEW stage")
            else:
                logger.info(f"[SESSION MANAGER] First entry into REVIEW stage - reading back order")
        
        # Generate TwiML response
        if session.state.stage == ConversationStage.CONCLUSION:
            # End call - escape XML and use consistent voice
            escaped_text = (
                response_text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna-Neural">{escaped_text}</Say>
    <Pause length="1"/>
    <Hangup/>
</Response>"""
        else:
            # Continue conversation
            gather_url = f"{base_url}/webhooks/voice/gather?CallSid={call_sid}" if base_url else f"/webhooks/voice/gather?CallSid={call_sid}"
            return self.tts_service.generate_twiml_with_gather(
                response_text,
                gather_url,
            )

    def _is_action_allowed_in_stage(
        self, action_type: str, stage: ConversationStage
    ) -> bool:
        """
        Validate that an action type is allowed in the current stage.
        
        Returns:
            True if action is allowed, False otherwise
        """
        from app.services.agent.stages import ConversationStage

        # Map of stages to allowed action types
        stage_allowed_actions = {
            ConversationStage.GREETING: ["none"],
            ConversationStage.ORDERING: ["add_item", "none"],
            ConversationStage.REVIEW: ["none"],  # Review only, no modifications
            ConversationStage.REVISION: [
                "add_item",
                "remove_item",
                "modify_item",
                "none",
            ],
            ConversationStage.CONCLUSION: ["none"],
        }

        allowed = stage_allowed_actions.get(stage, ["none"])
        return action_type in allowed

    async def _handle_add_item(
        self,
        action: Dict[str, Any],
        speech_result: Optional[str],
        session: CallSession,
        response_text: str,
    ) -> str:
        """Handle add_item action."""
        logger.info("=" * 80)
        logger.info(f"[SESSION MANAGER] add_item action received - Action: {action}")
        order_item = await self.order_parser.parse_agent_action(action, speech_result)
        logger.info(f"[SESSION MANAGER] Parsed order_item: {order_item}")
        
        if order_item:
            # Validate item
            is_valid, errors = await self.order_parser.validate_order_item(order_item)
            logger.info(
                f"[SESSION MANAGER] Item validation - Valid: {is_valid}, Errors: {errors}"
            )
            
            if is_valid:
                # Add to state
                state_item = StateOrderItem(
                    item_name=order_item.item_name,
                    quantity=order_item.quantity,
                    modifiers=order_item.modifiers,
                )
                logger.info(
                    f"[SESSION MANAGER] Adding item to state - Item: {state_item.item_name}, "
                    f"Qty: {state_item.quantity}, Mods: {state_item.modifiers}"
                )
                session.state.add_order_item(state_item)
                logger.info(
                    f"[SESSION MANAGER] Item added! Current order now has "
                    f"{len(session.state.current_order)} items"
                )
                order_items_repr = [
                    {"name": item.item_name, "qty": item.quantity, "mods": item.modifiers}
                    for item in session.state.current_order
                ]
                logger.info(f"[SESSION MANAGER] Current order items: {order_items_repr}")
                logger.info("=" * 80)

                # Simplified: Trust LLM to capture modifiers in the conversation naturally
                # No automatic follow-up questions - keeps flow conversational
            else:
                logger.warning(f"[SESSION MANAGER] Item validation failed: {errors}")
                if errors:
                    response_text += f" {errors[0]}"
                logger.info("=" * 80)
        else:
            logger.info("=" * 80)

        return response_text

    async def _handle_add_modifiers(
        self,
        action: Dict[str, Any],
        speech_result: Optional[str],
        session: CallSession,
        response_text: str,
    ) -> str:
        """
        Handle add_modifiers action (DEPRECATED - no longer used).

        Kept for backward compatibility but does nothing.
        Modifiers are now captured directly in add_item actions by the LLM.
        """
        logger.info(
            "[SESSION MANAGER] add_modifiers action received but is deprecated. "
            "Modifiers should be captured in add_item actions."
        )
        return response_text

    async def _handle_remove_item(
        self,
        action: Dict[str, Any],
        session: CallSession,
        response_text: str,
    ) -> str:
        """Handle remove_item action."""
        item_name = action.get("item_name", "").strip().lower()
        if item_name:
            # Find and remove the item from the order
            original_count = len(session.state.current_order)
            session.state.current_order = [
                item
                for item in session.state.current_order
                if item.item_name.lower() != item_name
            ]
            removed_count = original_count - len(session.state.current_order)
            
            if removed_count > 0:
                logger.info(f"[SESSION MANAGER] Removed item: {item_name}")
                return f"Removed {item_name} from your order. Anything else you'd like to change?"
            else:
                logger.warning(
                    f"[SESSION MANAGER] Tried to remove item '{item_name}' "
                    f"but it wasn't found in order"
                )
                return (
                    f"I don't see {item_name} in your order. "
                    f"What else would you like to change?"
                )
        return response_text

    async def _handle_modify_item(
        self,
        action: Dict[str, Any],
        session: CallSession,
        response_text: str,
    ) -> str:
        """Handle modify_item action."""
        item_name = action.get("item_name", "").strip().lower()
        modifiers_text = action.get("modifiers", "").strip()

        if item_name:
            # Find the item and update its modifiers
            found = False
            for item in session.state.current_order:
                if item.item_name.lower() == item_name:
                    if modifiers_text:
                        item.modifiers = [modifiers_text]
                    else:
                        item.modifiers = []
                    logger.info(
                        f"[SESSION MANAGER] Modified item: {item_name} with modifiers: {modifiers_text}"
                    )
                    found = True
                    return f"Updated {item_name}. Anything else you'd like to change?"

            if not found:
                logger.warning(
                    f"[SESSION MANAGER] Tried to modify item '{item_name}' "
                    f"but it wasn't found in order"
                )
                return (
                    f"I don't see {item_name} in your order. "
                    f"What else would you like to change?"
                )

        return response_text

    async def _persist_order(self, session: CallSession) -> bool:
        """
        Persist the current order to database.

        Returns:
            True if order was successfully persisted, False otherwise
        """
        if not session.state.current_order:
            logger.warning("[SESSION MANAGER] No items in order, skipping persistence")
            return True  # Empty order is not an error

        try:
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

            logger.info(
                f"[SESSION MANAGER] Successfully persisted order {order.id} "
                f"for call {session.call_sid} with {len(order_items)} items"
            )
            return True

        except Exception as e:
            logger.error(
                f"[SESSION MANAGER] CRITICAL: Failed to persist order for call {session.call_sid}: {e}",
                exc_info=True
            )
            return False

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
        if call_sid in _sessions:
            del _sessions[call_sid]

