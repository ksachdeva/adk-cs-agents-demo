import os
import random
import string

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

from backend._tools import cancel_flight
from backend._types import AirlineAgentContext


def _instruction_provider(ctx: ReadonlyContext) -> str:
    airline_context: AirlineAgentContext = ctx.state["context"]
    confirmation = airline_context.confirmation_number or "not available"
    flight = airline_context.flight_number or "not available"
    return f"""
You are a Cancellation Agent. Use the following routine to support the customer:
    1. The customer's confirmation number is {confirmation} and flight number is {flight}.
        - If either is not available, ask the customer for the missing information.
        - If you have both, confirm with the customer that these are correct.
    2. If the customer confirms, use the cancel_flight tool to cancel their flight.

    If the customer asks anything else, transfer back to the triage agent.
"""


async def _ensure_context(callback_context: CallbackContext) -> None:
    # Equivalent to on_cancellation_handoff
    airline_context: AirlineAgentContext = callback_context.state["context"]

    if airline_context.confirmation_number is None:
        airline_context.confirmation_number = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    if airline_context.flight_number is None:
        airline_context.flight_number = f"FLT-{random.randint(100, 999)}"

    callback_context.state["context"] = airline_context


cancel_flight_agent = LlmAgent(
    name="cancellation_agent",
    model=LiteLlm(model=os.environ["CANCEL_FLIGHT_AGENT_MODEL"]),
    description="An agent to cancel flights.",
    instruction=_instruction_provider,
    tools=[cancel_flight],
    before_agent_callback=_ensure_context,
)
