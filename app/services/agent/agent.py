"""LLM agent service."""
import json
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.agent.state import ConversationState
from app.services.agent.prompt import get_system_prompt, get_user_prompt
from app.services.agent.stages import ConversationStage
from app.services.agent.flow_manager import ConversationFlowManager
from app.services.menu.repository import MenuRepository


class AgentService:
    """Service for LLM-powered conversation agent."""

    def __init__(self, menu_repository: MenuRepository):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.menu_repository = menu_repository
        # Flow manager is created per-call via get_flow_manager() method

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
        
        # Get system and user prompts (simplified)
        system_prompt = get_system_prompt(menu_text)
        user_prompt = get_user_prompt(
            context, 
            user_input,
            conversation_stage=state.stage,
            current_order_summary=order_summary
        )

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
            
            user_input_lower = user_input.lower().strip()
            
            # Get or create flow manager for this call session (stored in state)
            # Flow manager state is stored per-call to avoid conflicts
            flow_manager = self._get_flow_manager_for_state(state)
            
            # Check if we're currently customizing an item
            current_item_name = flow_manager.get_current_item_name()
            
            if current_item_name:
                # We're in the middle of customizing an item - process modifier response
                flow_response = await flow_manager.process_modifier_response(user_input)
                agent_response = flow_response
                # Update state
                state.current_item_being_discussed = flow_manager.get_current_item_name()
            else:
                # Check if LLM extracted an item name
                extracted_item_name = llm_response.get("action", {}).get("item_name")
                
                if extracted_item_name:
                    # Customer mentioned an item - start customizing it
                    flow_response = await flow_manager.process_item_mention(extracted_item_name)
                    agent_response = flow_response
                    # Update state
                    state.current_item_being_discussed = flow_manager.get_current_item_name()
                else:
                    # No item mentioned, use LLM response as-is
                    agent_response = llm_response
                    # Check for done ordering indicators
                    done_ordering_indicators = ["that's all", "that's it", "nothing else", "i'm done", "i'm finished", 
                                              "that's everything", "no that's all", "no thanks that's all"]
                    is_done_ordering = any(indicator in user_input_lower for indicator in done_ordering_indicators)
                    
                    if is_done_ordering and state.stage == ConversationStage.ORDERING:
                        # Move to review
                        state.stage = ConversationStage.REVIEW
                        agent_response["response"] = "Great! Let me read back your order to make sure I have everything correct."
                        agent_response["intent"] = "reviewing"
            
            # Handle add_item action from flow manager
            if agent_response.get("action", {}).get("type") == "add_item":
                # Flow manager handled the item customization, item is ready to add
                state.current_item_being_discussed = None
                flow_manager.clear_current_item()
            
            # Add agent response to transcript
            state.add_transcript_turn("Agent", agent_response.get("response", ""))
            
            # Update stage based on intent
            intent = agent_response.get("intent", "")
            if state.stage == ConversationStage.GREETING:
                state.stage = ConversationStage.ORDERING
            elif state.stage == ConversationStage.ORDERING:
                if intent == "reviewing" or "that's all" in user_input_lower or "that's it" in user_input_lower:
                    state.stage = ConversationStage.REVIEW
            elif state.stage == ConversationStage.REVIEW:
                if intent == "concluding" or "yes" in user_input_lower or "correct" in user_input_lower:
                    state.stage = ConversationStage.CONCLUSION
            
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
    
    def _get_flow_manager_for_state(self, state: ConversationState) -> ConversationFlowManager:
        """Get or create a flow manager for this conversation state.
        
        Uses state.call_sid as key to store flow managers per-call.
        This ensures each call has its own flow manager state.
        """
        # Store flow managers in a dict keyed by call_sid
        # This is thread-safe for our use case (each call gets its own state object)
        if not hasattr(self, '_flow_managers'):
            self._flow_managers = {}
        
        if state.call_sid not in self._flow_managers:
            self._flow_managers[state.call_sid] = ConversationFlowManager(self.menu_repository)
        
        return self._flow_managers[state.call_sid]

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

