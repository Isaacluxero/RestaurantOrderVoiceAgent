"""Call session models."""
from typing import Optional, Dict, Any
from app.services.agent.state import ConversationState


class CallSession:
    """Call session model."""

    def __init__(
        self,
        call_sid: str,
        state: ConversationState,
        call_id: Optional[int] = None,
    ):
        self.call_sid = call_sid
        self.state = state
        self.call_id = call_id  # Database ID

