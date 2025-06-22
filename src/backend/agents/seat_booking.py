import os

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

from backend._tools import display_seat_map, update_seat
from backend._types import AirlineAgentContext


def _instruction_provider(ctx: ReadonlyContext) -> str:
    airline_context: AirlineAgentContext = ctx.state["context"]
    confirmation = airline_context.confirmation_number or "not available"
    return f"""
You are a seat booking agent. If you are speaking to a customer, you probably were transferred to from the triage agent.

Use the following routine to support the customer.
        1. The customer's confirmation number is {confirmation}
            - If this is not available, ask the customer for their confirmation number.
            - If you have it, confirm that is the confirmation number they are referencing.
        2. Ask the customer what their desired seat number is. You can also use the display_seat_map tool to show them an interactive seat map where they can click to select their preferred seat.
        3. Use the update seat tool to update the seat on the flight.
        If the customer asks a question that is not related to the routine, transfer back to the triage agent.
"""


seat_booking_agent = LlmAgent(
    name="seat_booking_agent",
    model=LiteLlm(model=os.environ["SEAT_BOOKING_AGENT_MODEL"]),
    description="A helpful agent that can update a seat on a flight.",
    instruction=_instruction_provider,
    tools=[
        update_seat,
        display_seat_map,
    ],
)
