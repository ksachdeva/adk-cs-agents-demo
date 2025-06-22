import os

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

from backend._tools import flight_status_tool
from backend._types import AirlineAgentContext

from .guard_rails import run_jailbreak_guardrail_agent, run_relevance_guardrail_agent


def _instruction_provider(ctx: ReadonlyContext) -> str:
    airline_context: AirlineAgentContext = ctx.state["context"]
    confirmation = airline_context.confirmation_number or "not available"
    flight = airline_context.flight_number or "not available"
    return f"""
You are a Flight Status Agent. Use the following routine to support the customer:
    1. The customer's confirmation number is {confirmation} and flight number is {flight}
       - If either is not available, ask the customer for the missing information.
       - If you have both, confirm with the customer that these are correct.
    2. Use the flight_status_tool to report the status of the flight.

    If the customer asks a question that is not related to flight status, transfer back to the triage agent.
"""


def _ensure_context(callback_context: CallbackContext) -> None:
    callback_context.state["current_agent"] = "flight_status_agent"


flight_status_agent = LlmAgent(
    name="flight_status_agent",
    model=LiteLlm(model=os.environ["FLIGHT_STATUS_AGENT_MODEL"]),
    description="An agent to provide flight status information.",
    instruction=_instruction_provider,
    tools=[flight_status_tool],
    before_agent_callback=_ensure_context,
    before_model_callback=[run_relevance_guardrail_agent, run_jailbreak_guardrail_agent],
)
