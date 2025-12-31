"""LLM agent service."""
import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.agent.state import ConversationState
from app.services.agent.prompt import get_system_prompt, get_user_prompt
from app.services.agent.stages import ConversationStage
from app.services.menu.repository import MenuRepository

logger = logging.getLogger(__name__)


class AgentService:
    """Service for LLM-powered conversation agent."""

    def __init__(self, menu_repository: MenuRepository):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.menu_repository = menu_repository

    async def initialize_state(
        self, call_sid: str, menu_text: str, item_requirements_text: str = ""
    ) -> ConversationState:
        """Initialize conversation state."""
        state = ConversationState(
            call_sid=call_sid,
            menu_context=menu_text,
            stage=ConversationStage.GREETING,
        )
        # Note: item_requirements_text is no longer stored in state.menu_context
        # It's handled by the flow manager via the menu repository
        return state

    async def process_user_input(
        self, state: ConversationState, user_input: str
    ) -> Dict[str, Any]:
        """
        Process user input and generate agent response.

        Returns:
            Dict with 'response' (text to speak) and 'action' (structured action)
        """
        # Add user input to transcript
        state.add_transcript_turn("Customer", user_input)

        # Get menu text if not already loaded
        if not state.menu_context:
            menu_text = await self.menu_repository.get_menu_text()
            state.menu_context = menu_text

        # Build conversation context
        context = state.get_transcript_text()
        order_summary = state.get_order_summary()
        menu_text = await self.menu_repository.get_menu_text()

        # ===== COMPREHENSIVE LOGGING: AGENT INPUTS =====
        logger.info("=" * 80)
        logger.info(f"[AGENT INPUT] CallSid: {state.call_sid}")
        logger.info(f"[AGENT INPUT] User Input: '{user_input}'")
        logger.info(f"[AGENT INPUT] Current Stage: {state.stage.value}")
        logger.info(f"[AGENT INPUT] Current Order Summary:\n{order_summary}")
        logger.info(f"[AGENT INPUT] State.current_item_being_discussed: {state.current_item_being_discussed or 'NONE'}")
        logger.info(f"[AGENT INPUT] Current Order Items: {[{'name': item.item_name, 'qty': item.quantity, 'mods': item.modifiers} for item in state.current_order]}")
        logger.info("=" * 80)
        
        # Get system and user prompts (simplified)
        system_prompt = get_system_prompt(menu_text)

        pending_notes_item_name = state.pending_notes_item_name
        pending_notes_examples = None
        if pending_notes_item_name:
            try:
                pending_notes_examples = await self.menu_repository.get_item_options(pending_notes_item_name)
            except Exception:
                pending_notes_examples = None

        user_prompt = get_user_prompt(
            context, 
            user_input,
            conversation_stage=state.stage,
            current_order_summary=order_summary,
            pending_notes_item_name=pending_notes_item_name,
            pending_notes_examples=pending_notes_examples,
        )
        
        # ===== LOGGING: PROMPTS SENT TO LLM =====
        logger.info("=" * 80)
        logger.info(f"[AGENT PROMPT] System Prompt Length: {len(system_prompt)} chars")
        logger.info(f"[AGENT PROMPT] User Prompt:\n{user_prompt}")
        logger.info("=" * 80)

        # Call LLM to extract item names and general intent
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            # Parse LLM response
            content = response.choices[0].message.content
            llm_response = json.loads(content)
            
            # ===== LOGGING: LLM OUTPUT =====
            logger.info("=" * 80)
            logger.info(f"[AGENT LLM OUTPUT] Raw Response: {content}")
            logger.info(f"[AGENT LLM OUTPUT] Parsed JSON: {json.dumps(llm_response, indent=2)}")
            logger.info("=" * 80)
            
            user_input_lower = user_input.lower().strip()

            # Use LLM response directly (no structured customization state machine)
            agent_response = llm_response

            # Check for done ordering indicators (server-side deterministic transition)
            done_ordering_indicators = [
                "that's all",
                "that's it",
                "nothing else",
                "i'm done",
                "i'm finished",
                "that's everything",
                "no that's all",
                "no thanks that's all",
            ]
            is_done_ordering = any(indicator in user_input_lower for indicator in done_ordering_indicators)

            if is_done_ordering and state.stage == ConversationStage.ORDERING:
                logger.info("[AGENT FLOW] Detected 'done ordering', moving to REVIEW stage")
                state.stage = ConversationStage.REVIEW
                agent_response["response"] = "Great! Let me read back your order to make sure I have everything correct."
                agent_response["intent"] = "reviewing"
                agent_response["action"] = {"type": "none"}
            
            # Add agent response to transcript
            state.add_transcript_turn("Agent", agent_response.get("response", ""))
            
            # Update stage based on intent
            old_stage = state.stage
            intent = agent_response.get("intent", "")
            
            # Check for revision indicators (only in REVIEW stage)
            revision_indicators = [
                "change", "remove", "delete", "don't want", "cancel", 
                "take out", "add", "actually", "wait", "hold on", "no wait"
            ]
            wants_revision = any(indicator in user_input_lower for indicator in revision_indicators)
            
            # Check for confirmation indicators
            confirmation_indicators = ["yes", "correct", "that's right", "sounds good", "perfect", "that works", "looks good"]
            is_confirming = any(indicator in user_input_lower for indicator in confirmation_indicators)
            
            if state.stage == ConversationStage.GREETING:
                state.stage = ConversationStage.ORDERING
            elif state.stage == ConversationStage.ORDERING:
                if intent == "reviewing" or "that's all" in user_input_lower or "that's it" in user_input_lower:
                    state.stage = ConversationStage.REVIEW
            elif state.stage == ConversationStage.REVIEW:
                # Priority: Check for confirmation FIRST (go to CONCLUSION)
                if intent == "concluding" or is_confirming:
                    state.stage = ConversationStage.CONCLUSION
                    agent_response["intent"] = "completing"
                # Then check for revision requests (go to REVISION)
                elif intent == "revising" or wants_revision:
                    state.stage = ConversationStage.REVISION
                    agent_response["intent"] = "revising"
            elif state.stage == ConversationStage.REVISION:
                if intent == "reviewing" or "that's all" in user_input_lower or "done" in user_input_lower or "that's it" in user_input_lower:
                    state.stage = ConversationStage.REVIEW
                    agent_response["response"] = "Got it! Let me read back your updated order."
                    agent_response["intent"] = "reviewing"
            
            if old_stage != state.stage:
                logger.info(f"[AGENT STAGE] Stage changed: {old_stage.value} -> {state.stage.value}")
            
            # ===== LOGGING: AGENT OUTPUT =====
            logger.info("=" * 80)
            logger.info(f"[AGENT OUTPUT] Final Response: '{agent_response.get('response', '')}'")
            logger.info(f"[AGENT OUTPUT] Intent: {agent_response.get('intent', '')}")
            logger.info(f"[AGENT OUTPUT] Action: {json.dumps(agent_response.get('action', {}), indent=2)}")
            logger.info(f"[AGENT OUTPUT] Final Stage: {state.stage.value}")
            logger.info(f"[AGENT OUTPUT] Final current_item_being_discussed: {state.current_item_being_discussed or 'NONE'}")
            logger.info(f"[AGENT OUTPUT] Final Order Items: {[{'name': item.item_name, 'qty': item.quantity, 'mods': item.modifiers} for item in state.current_order]}")
            logger.info("=" * 80)
            
            return agent_response

        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            return {
                "response": "I'm sorry, I didn't understand that. Could you repeat?",
                "intent": "asking_question",
                "action": {"type": "none"},
            }
        except Exception as e:
            return {
                "response": "I'm having trouble processing that. Could you try again?",
                "intent": "asking_question",
                "action": {"type": "none"},
            }
    
    async def get_greeting(self, state: ConversationState) -> str:
        """Get initial greeting message."""
        menu_text = await self.menu_repository.get_menu_text()
        
        if not state.menu_context:
            state.menu_context = menu_text

        system_prompt = get_system_prompt(menu_text)
        user_prompt = """The customer just called. Give them a warm, friendly, and enthusiastic greeting. 
Be personable and welcoming. Ask how you can help them today with a warm tone. 
Make them feel valued and welcomed to the restaurant. Keep it brief (1-2 sentences) but friendly."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            agent_response = json.loads(content)
            greeting = agent_response.get("response", f"Hello! Welcome to {settings.restaurant_name}. How can I help you today?")

            state.add_transcript_turn("Agent", greeting)
            # Stage will transition to ORDERING after first user input

            return greeting
        except Exception:
            return f"Hello! Welcome to {settings.restaurant_name}. How can I help you today?"

