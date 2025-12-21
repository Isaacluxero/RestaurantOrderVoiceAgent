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
        self, call_sid: str, menu_text: str
    ) -> ConversationState:
        """Initialize conversation state."""
        state = ConversationState(
            call_sid=call_sid,
            menu_context=menu_text,
            stage="greeting",
        )
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
            state.menu_context = await self.menu_repository.get_menu_text()

        # Build conversation context
        context = state.get_transcript_text()
        if state.current_order:
            context += f"\n\nCurrent order:\n{state.get_order_summary()}"

        # Get system and user prompts
        system_prompt = get_system_prompt(state.menu_context)
        user_prompt = get_user_prompt(context, user_input)

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

            # Add agent response to transcript
            state.add_transcript_turn("Agent", agent_response.get("response", ""))

            # Update state based on intent
            intent = agent_response.get("intent", "")
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
        if not state.menu_context:
            state.menu_context = await self.menu_repository.get_menu_text()

        system_prompt = get_system_prompt(state.menu_context)
        user_prompt = "The customer just called. Give them a warm greeting and ask how you can help."

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

