from google.adk.tools import ToolContext

from ._types import AirlineAgentContext


def faq_lookup_tool(question: str) -> str:
    """Lookup answers to frequently asked questions.

    Args:
        question (str): The question to look up.
    Returns:
        str: The answer to the question.
    """
    q = question.lower()
    if "bag" in q or "baggage" in q:
        return (
            "You are allowed to bring one bag on the plane. "
            "It must be under 50 pounds and 22 inches x 14 inches x 9 inches."
        )
    elif "seats" in q or "plane" in q:
        return (
            "There are 120 seats on the plane. "
            "There are 22 business class seats and 98 economy seats. "
            "Exit rows are rows 4 and 16. "
            "Rows 5-8 are Economy Plus, with extra legroom."
        )
    elif "wifi" in q:
        return "We have free wifi on the plane, join Airline-Wifi"

    return "I'm sorry, I don't know the answer to that question."


def update_seat(confirmation_number: str, new_seat: str, tool_context: ToolContext) -> str:
    """Update the seat for a given confirmation number.

    Args:
        confirmation_number (str): The confirmation number for the flight.
        new_seat (str): The new seat to assign.
    Returns:
        str: Confirmation message with updated seat information.
    """

    # TODO: Flight number is checked in the original implementation
    # but not used in the logic.

    airline_context: AirlineAgentContext = tool_context.state["context"]
    airline_context.confirmation_number = confirmation_number
    airline_context.seat_number = new_seat

    tool_context.state["context"] = airline_context

    return f"Updated seat to {new_seat} for confirmation number {confirmation_number}"


def flight_status_tool(flight_number: str) -> str:
    """Lookup the status for a flight.

    Args:
        flight_number (str): The flight number to check.
    Returns:
        str: The status of the flight.
    """
    return f"Flight {flight_number} is on time and scheduled to depart at gate A10."


def baggage_tool(query: str) -> str:
    """Lookup baggage allowance and fees.

    Args:
        query (str): The baggage-related question to answer.
    Returns:
        str: The answer to the baggage question.
    """
    q = query.lower()
    if "fee" in q:
        return "Overweight bag fee is $75."
    if "allowance" in q:
        return "One carry-on and one checked bag (up to 50 lbs) are included."
    return "Please provide details about your baggage inquiry."


def display_seat_map() -> str:
    """Display an interactive seat map to the customer so they can choose a new seat.

    Returns:
        str: A command to display the seat map.
    """
    # The returned string will be interpreted by the UI to open the seat selector.
    return "DISPLAY_SEAT_MAP"


def cancel_flight(tool_context: ToolContext) -> str:
    """Cancel the flight in the context.

    Returns:
        str: Confirmation message for flight cancellation.
    """
    context: AirlineAgentContext = tool_context.state["context"]
    fn = context.flight_number
    assert fn is not None, "Flight number is required"
    return f"Flight {fn} successfully cancelled"
