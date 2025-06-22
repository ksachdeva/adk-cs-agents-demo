import os
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

from backend._types import AirlineAgentContext

from .cancel_flight import cancel_flight_agent
from .faq import faq_agent
from .flight_status import flight_status_agent
from .seat_booking import seat_booking_agent


def _instruction_provider(ctx: ReadonlyContext) -> str:
    return """
You are a helpful triaging agent. You can use your tools to delegate questions to other appropriate agents.
"""


def _ensure_context(callback_context: CallbackContext) -> None:
    airline_context: AirlineAgentContext | None = callback_context.state.get("context", None)
    if not airline_context:
        airline_context = AirlineAgentContext.create_initial_context()
        callback_context.state["context"] = airline_context
        callback_context.state["current_agent"] = "triage_agent"


triage_agent = LlmAgent(
    name="triage_agent",
    model=LiteLlm(model=os.environ["TRIAGE_AGENT_MODEL"]),
    description="A triage agent that can delegate a customer's request to the appropriate agent.",
    instruction=_instruction_provider,
    sub_agents=[
        flight_status_agent,
        cancel_flight_agent,
        seat_booking_agent,
        faq_agent,
    ],
    before_agent_callback=_ensure_context,
)


def agents_info() -> list[dict[str, Any]]:
    def make_agent_dict(agent: LlmAgent) -> dict[str, Any]:
        return {
            "name": agent.name,
            "description": getattr(agent, "description", ""),
            "handoffs": [getattr(h, "agent_name", getattr(h, "name", "")) for h in getattr(agent, "sub_agents", [])],
            "tools": [getattr(t, "name", getattr(t, "__name__", "")) for t in getattr(agent, "tools", [])],
            "input_guardrails": [],
        }

    return [
        make_agent_dict(triage_agent),
        make_agent_dict(faq_agent),
        make_agent_dict(seat_booking_agent),
        make_agent_dict(flight_status_agent),
        make_agent_dict(cancel_flight_agent),
    ]
