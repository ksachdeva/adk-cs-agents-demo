import os

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

from backend._tools import faq_lookup_tool


def _instruction_provider(ctx: ReadonlyContext) -> str:
    return """
You are an FAQ agent. If you are speaking to a customer, you probably were transferred to from the triage agent.

Use the following routine to support the customer.
    1. Identify the last question asked by the customer.
    2. Use the faq lookup tool to get the answer. Do not rely on your own knowledge.
    3. Respond to the customer with the answer
"""


faq_agent = LlmAgent(
    name="faq_agent",
    model=LiteLlm(model=os.environ["FAQ_AGENT_MODEL"]),
    description="A helpful agent that can answer questions about the airline.",
    instruction=_instruction_provider,
    tools=[faq_lookup_tool],
)
