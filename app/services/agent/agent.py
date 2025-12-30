"""LLM agent service."""
import json
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.agent.state import ConversationState
from app.services.agent.prompt import get_system_prompt, get_user_prompt
from app.services.menu.repository import MenuRepository


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
            stage="greeting",
        )
        # Store item requirements in state for later use
        if item_requirements_text:
            state.menu_context += f"\n\n{item_requirements_text}"
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

        # Get menu text and requirements if not already loaded
        if not state.menu_context:
            menu_text = await self.menu_repository.get_menu_text()
            requirements_text = await self.menu_repository.get_item_requirements_text()
            state.menu_context = menu_text
            if requirements_text:
                state.menu_context += f"\n\n{requirements_text}"

        # Build conversation context
        context = state.get_transcript_text()
        order_summary = state.get_order_summary()

        # Get item requirements text for system prompt
        requirements_text = await self.menu_repository.get_item_requirements_text()
        menu_text = await self.menu_repository.get_menu_text()
        
        # Get system and user prompts
        system_prompt = get_system_prompt(menu_text, requirements_text)
        user_prompt = get_user_prompt(
            context, 
            user_input, 
            current_item=state.current_item_being_discussed,
            item_needs_size=state.current_item_needs_size,
            current_order_summary=order_summary,
            current_item_modifiers=state.current_item_modifiers,
            current_item_quantity=state.current_item_quantity
        )

        # Call LLM
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using mini for cost efficiency
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            # Parse response
            content = response.choices[0].message.content
            agent_response = json.loads(content)

            # Check for completion indicators before processing response
            user_input_lower = user_input.lower().strip()
            completion_indicators = ["none", "no", "no modifiers", "no thanks", "that's it", "that's all", 
                                   "nothing", "no changes", "that's fine", "sounds good", "yes", "correct"]
            
            # Update state based on intent and action
            intent = agent_response.get("intent", "")
            action = agent_response.get("action", {})
            
            # If we have a current item and user says completion indicators, force add_item action
            if state.current_item_being_discussed:
                # Check if user response indicates completion (saying none/no/confirmation)
                is_completion_response = any(indicator in user_input_lower for indicator in completion_indicators)
                
                # Also check if action already says to add item or complete
                action_type = action.get("type", "")
                should_add_item = action_type == "add_item" or action_type == "complete_item" or is_completion_response
                
                if should_add_item and action_type != "add_item":
                    # Force add_item action - user is completing the current item
                    action = {
                        "type": "add_item",
                        "item_name": state.current_item_being_discussed,
                        "quantity": state.current_item_quantity,
                        "modifiers": state.current_item_modifiers.copy(),
                    }
                    intent = "adding_item"
                    agent_response["intent"] = intent
                    agent_response["action"] = action
                    # Update response text if needed
                    if not agent_response.get("response") or "anything else" not in agent_response.get("response", "").lower():
                        agent_response["response"] = "Got it! Would you like anything else?"
            
            # Track current item being discussed
            current_item_tracking = action.get("current_item_tracking")
            if current_item_tracking:
                state.set_current_item(current_item_tracking, action.get("quantity", 1))
                # Check if this item needs size
                item_req = await self.menu_repository.get_item_requirements(current_item_tracking)
                if item_req and item_req.get("size_required"):
                    state.current_item_needs_size = True
                else:
                    state.current_item_needs_size = False
            elif action.get("type") == "start_item_discussion" and action.get("item_name"):
                state.set_current_item(action.get("item_name"), action.get("quantity", 1))
                # Check if this item needs size
                item_req = await self.menu_repository.get_item_requirements(action.get("item_name"))
                if item_req and item_req.get("size_required"):
                    state.current_item_needs_size = True
                else:
                    state.current_item_needs_size = False
            elif action.get("type") == "complete_item":
                state.current_item_is_complete = True
                state.current_item_needs_size = False
            elif action.get("type") == "add_item":
                # Item added to order, clear current item tracking
                state.clear_current_item_discussion()
            else:
                # Update modifiers if they're being discussed
                if state.current_item_being_discussed and action.get("modifiers"):
                    modifiers = action.get("modifiers", [])
                    if isinstance(modifiers, list):
                        for mod in modifiers:
                            state.add_modifier_to_current_item(mod)
                    elif isinstance(modifiers, str):
                        state.add_modifier_to_current_item(modifiers)
            
            # Add agent response to transcript
            state.add_transcript_turn("Agent", agent_response.get("response", ""))
            
            # Update stage
            if intent == "confirming_order":
                state.stage = "confirming"
            elif intent == "completing":
                state.stage = "completed"
            
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
        requirements_text = await self.menu_repository.get_item_requirements_text()
        
        if not state.menu_context:
            state.menu_context = menu_text
            if requirements_text:
                state.menu_context += f"\n\n{requirements_text}"

        system_prompt = get_system_prompt(menu_text, requirements_text)
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
            state.stage = "taking_order"

            return greeting
        except Exception:
            return f"Hello! Welcome to {settings.restaurant_name}. How can I help you today?"

