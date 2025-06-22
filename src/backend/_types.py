from __future__ import annotations

import random
import string
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str


class MessageResponse(BaseModel):
    content: str
    agent: str


class AgentEvent(BaseModel):
    id: str
    type: str
    agent: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None


class GuardrailCheck(BaseModel):
    id: str
    name: str
    input: str
    reasoning: str
    passed: bool
    timestamp: float


class ChatResponse(BaseModel):
    conversation_id: str
    current_agent: str
    messages: List[MessageResponse]
    events: List[AgentEvent]
    context: Dict[str, Any]
    agents: List[Dict[str, Any]]
    guardrails: List[GuardrailCheck] = []


class AirlineAgentContext(BaseModel):
    """Context for airline customer service agents."""

    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None
    account_number: str | None = None  # Account number associated with the customer

    @staticmethod
    def create_initial_context() -> AirlineAgentContext:
        """
        Factory for a new AirlineAgentContext.
        For demo: generates a fake account number.
        In production, this should be set from real user data.
        """
        ctx = AirlineAgentContext()
        ctx.account_number = str(random.randint(10000000, 99999999))
        ctx.confirmation_number = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        ctx.passenger_name = "John Doe"
        ctx.flight_number = "FL123"
        ctx.seat_number = "12A"
        return ctx
