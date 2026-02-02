"""LLM agent service."""
import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.agent.state import ConversationState
from app.services.agent.prompt import get_system_prompt, get_user_prompt
from app.services.agent.stages import ConversationStage
from app.services.agent.stage_transitions import StageTransitionHandler
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
        logger.info(f"[AGENT INPUT] Pending Modifiers Item: {state.pending_modifiers_item_name or 'NONE'}")
        logger.info(f"[AGENT INPUT] Current Order Items: {[{'name': item.item_name, 'qty': item.quantity, 'mods': item.modifiers} for item in state.current_order]}")
        logger.info("=" * 80)
        
        # Get system and user prompts (simplified)
        system_prompt = get_system_prompt(menu_text)

        pending_modifiers_item_name = state.pending_modifiers_item_name
        pending_modifiers_examples = None
        if pending_modifiers_item_name:
            try:
                pending_modifiers_examples = await self.menu_repository.get_item_options(pending_modifiers_item_name)
            except Exception:
                pending_modifiers_examples = None

        user_prompt = get_user_prompt(
            context,
            user_input,
            conversation_stage=state.stage,
            current_order_summary=order_summary,
            pending_modifiers_item_name=pending_modifiers_item_name,
            pending_modifiers_examples=pending_modifiers_examples,
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

        user_input_lower = user_input.lower().strip()

        # Use LLM response directly (simple approach)
        # Note: ConversationFlowManager/ItemCustomizationState exist but are intentionally unused
        # Current design: LLM extracts modifiers directly, then pending_modifiers system asks once if needed
        agent_response = llm_response

        # Add agent response to transcript (before stage transitions modify it)
        state.add_transcript_turn("Agent", agent_response.get("response", ""))

        # Handle stage transitions using centralized handler
        intent = agent_response.get("intent", "")
        StageTransitionHandler.handle_stage_transitions(
            state, user_input_lower, intent, agent_response
        )
        
        # ===== LOGGING: AGENT OUTPUT =====
        logger.info("=" * 80)
        logger.info(f"[AGENT OUTPUT] Final Response: '{agent_response.get('response', '')}'")
        logger.info(f"[AGENT OUTPUT] Intent: {agent_response.get('intent', '')}")
        logger.info(f"[AGENT OUTPUT] Action: {json.dumps(agent_response.get('action', {}), indent=2)}")
        logger.info(f"[AGENT OUTPUT] Final Stage: {state.stage.value}")
        logger.info(f"[AGENT OUTPUT] Final Pending Modifiers Item: {state.pending_modifiers_item_name or 'NONE'}")
        logger.info(f"[AGENT OUTPUT] Final Order Items: {[{'name': item.item_name, 'qty': item.quantity, 'mods': item.modifiers} for item in state.current_order]}")
        logger.info("=" * 80)
        
        return agent_response
    
    async def get_greeting(self, state: ConversationState) -> str:
        """Get initial greeting message."""
        menu_text = await self.menu_repository.get_menu_text()
        
        if not state.menu_context:
            state.menu_context = menu_text

        greeting = f"Hi! Thanks for calling {settings.restaurant_name}. What can I get for you today?"

        state.add_transcript_turn("Agent", greeting)
        # Stage will transition to ORDERING after first user input

        return greeting

