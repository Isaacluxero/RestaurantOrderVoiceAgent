"""Stage transition logic for conversation flow."""
import logging
from typing import Dict, Any
from app.services.agent.state import ConversationState
from app.services.agent.stages import ConversationStage
from app.services.agent.constants import (
    DONE_ORDERING_INDICATORS,
    REVISION_INDICATORS,
    CONFIRMATION_INDICATORS,
)

logger = logging.getLogger(__name__)


class StageTransitionHandler:
    """Handles stage transitions based on user input and intent."""

    @staticmethod
    def should_transition_to_review(
        state: ConversationState, user_input_lower: str, intent: str
    ) -> bool:
        """Check if should transition from ORDERING to REVIEW."""
        if state.stage != ConversationStage.ORDERING:
            return False
        
        is_done_ordering = any(
            indicator in user_input_lower for indicator in DONE_ORDERING_INDICATORS
        )
        return intent == "reviewing" or is_done_ordering

    @staticmethod
    def handle_stage_transitions(
        state: ConversationState,
        user_input_lower: str,
        intent: str,
        agent_response: Dict[str, Any],
    ) -> None:
        """
        Handle stage transitions based on current stage, user input, and intent.
        
        Modifies state.stage and agent_response in place.
        """
        old_stage = state.stage

        # Check for revision indicators (only in REVIEW stage)
        wants_revision = any(
            indicator in user_input_lower for indicator in REVISION_INDICATORS
        )

        # Check for confirmation indicators
        is_confirming = any(
            indicator in user_input_lower for indicator in CONFIRMATION_INDICATORS
        )

        if state.stage == ConversationStage.GREETING:
            state.stage = ConversationStage.ORDERING
            
        elif state.stage == ConversationStage.ORDERING:
            if StageTransitionHandler.should_transition_to_review(
                state, user_input_lower, intent
            ):
                # Validate that order is not empty before moving to REVIEW
                if not state.has_items():
                    logger.warning(
                        "[STAGE TRANSITION] Customer said 'that's all' but order is empty"
                    )
                    agent_response["response"] = (
                        "I don't see any items in your order yet. What would you like to order?"
                    )
                    agent_response["intent"] = "ordering"
                    # Stay in ORDERING stage
                else:
                    state.stage = ConversationStage.REVIEW
                    state.order_read_back = False  # Reset flag for new REVIEW entry
                    
        elif state.stage == ConversationStage.REVIEW:
            # Validate order is not empty before allowing conclusion
            if not state.has_items():
                logger.warning(
                    "[STAGE TRANSITION] Attempted to conclude review but order is empty"
                )
                agent_response["response"] = (
                    "I don't see any items in your order. What would you like to order?"
                )
                agent_response["intent"] = "ordering"
                state.stage = ConversationStage.ORDERING
            # Priority: Check for confirmation FIRST (go to CONCLUSION)
            elif intent == "concluding" or is_confirming:
                state.stage = ConversationStage.CONCLUSION
                agent_response["intent"] = "completing"
            # Then check for revision requests (go to REVISION)
            elif intent == "revising" or wants_revision:
                state.stage = ConversationStage.REVISION
                agent_response["intent"] = "revising"
                
        elif state.stage == ConversationStage.REVISION:
            is_done_revising = any(
                indicator in user_input_lower
                for indicator in ["that's all", "that's it", "done"]
            )
            if intent == "reviewing" or is_done_revising:
                state.stage = ConversationStage.REVIEW
                state.order_read_back = False  # Reset flag to read back updated order
                agent_response["response"] = "Got it! Let me read back your updated order."
                agent_response["intent"] = "reviewing"

        if old_stage != state.stage:
            logger.info(
                f"[STAGE TRANSITION] Stage changed: {old_stage.value} -> {state.stage.value}"
            )

