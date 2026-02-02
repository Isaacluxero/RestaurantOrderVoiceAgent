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

        # Check for revision indicators
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
                    agent_response["action"] = {"type": "none"}
                    # Stay in ORDERING stage
                else:
                    logger.info("[STAGE TRANSITION] Transitioning from ORDERING to REVIEW")
                    state.stage = ConversationStage.REVIEW
                    state.order_read_back = False  # Reset flag for new REVIEW entry
                    # Clear response - manager will read back the order
                    agent_response["response"] = ""
                    agent_response["intent"] = "reviewing"
                    agent_response["action"] = {"type": "none"}

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
            # FIXED: Check for revision FIRST (before confirmation)
            # This prevents "yes, but actually add X" from being treated as pure confirmation
            elif wants_revision and (intent == "revising" or not is_confirming):
                logger.info("[STAGE TRANSITION] Revision requested in REVIEW stage")
                state.stage = ConversationStage.REVISION
                agent_response["intent"] = "revising"
            # Then check for confirmation (go to CONCLUSION)
            elif intent == "concluding" or is_confirming:
                logger.info("[STAGE TRANSITION] Order confirmed in REVIEW stage")
                state.stage = ConversationStage.CONCLUSION
                agent_response["intent"] = "completing"
                # Clear response - manager will set the conclusion message
                agent_response["response"] = ""

        elif state.stage == ConversationStage.REVISION:
            is_done_revising = any(
                indicator in user_input_lower
                for indicator in DONE_ORDERING_INDICATORS
            )
            if intent == "reviewing" or is_done_revising:
                logger.info("[STAGE TRANSITION] Done with revisions, back to REVIEW")
                state.stage = ConversationStage.REVIEW
                state.order_read_back = False  # Reset flag to read back updated order
                # Clear response - manager will read back the order
                agent_response["response"] = ""
                agent_response["intent"] = "reviewing"

        if old_stage != state.stage:
            logger.info(
                f"[STAGE TRANSITION] Stage changed: {old_stage.value} -> {state.stage.value}"
            )

