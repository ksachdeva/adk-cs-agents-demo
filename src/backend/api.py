import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import uuid4

from adk_dynamodb_session import DynamoDBSessionService
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from ._types import AgentEvent, AirlineAgentContext, ChatRequest, ChatResponse, GuardrailCheck, MessageResponse
from .agents import agents_info, root_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADK_APP_NAME = "cs-agents-demo"
ADK_USER_ID = "cs-agents-demo-user"

load_dotenv()

if os.getenv("USE_LOCAL_DYNAMO_DB", "false").lower() == "true":
    session_service = DynamoDBSessionService()  # type: ignore
    session_service.create_table_if_not_exists()
else:
    # Use in-memory session service for local development or testing
    # This is not suitable for production use as it does not persist data
    session_service = InMemorySessionService()  # type: ignore


runner_dict: dict[str, Runner] = {}  # type: ignore


async def _get_runner_async(app_name: str) -> Runner:
    """Returns the runner for the given app."""
    if app_name in runner_dict:
        return runner_dict[app_name]
    runner = Runner(
        app_name=app_name,
        agent=root_agent,
        session_service=session_service,
    )
    runner_dict[app_name] = runner
    return runner


async def _close_runners(runners: list[Runner]) -> None:
    cleanup_tasks = [asyncio.create_task(runner.close()) for runner in runners]  # type: ignore
    if cleanup_tasks:
        # Wait for all cleanup tasks with timeout
        done, pending = await asyncio.wait(
            cleanup_tasks,
            timeout=30.0,  # 30 second timeout for cleanup
            return_when=asyncio.ALL_COMPLETED,
        )

        # If any tasks are still pending, log it
        if pending:
            logger.warning("%s runner close tasks didn't complete in time", len(pending))
            for task in pending:
                task.cancel()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        # Create tasks for all runner closures to run concurrently
        await _close_runners(list(runner_dict.values()))


app = FastAPI(
    lifespan=lifespan,
)

# CORS configuration (adjust as needed for deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# There is only 1 endpoint that the frontend will call.
# Depending on the ChatRequest, we will construct an
# appropriate response and return it.
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    # if conversation_id is not provided or it does not
    # match an existing session, create a new session

    session = (
        None
        if not req.conversation_id
        else await session_service.get_session(
            app_name=ADK_APP_NAME,
            user_id=ADK_USER_ID,
            session_id=req.conversation_id,
        )
    )

    is_new = not req.conversation_id or session is None
    if is_new:
        ctx = AirlineAgentContext.create_initial_context()
        current_agent_name = "triage_agent"
        state: dict[str, Any] = {
            "context": ctx.model_dump(),
            "current_agent": current_agent_name,
        }
        session = await session_service.create_session(
            app_name=ADK_APP_NAME,
            user_id=ADK_USER_ID,
            state=state,
        )

        if req.message.strip() == "":
            return ChatResponse(
                conversation_id=session.id,
                current_agent=current_agent_name,
                messages=[],
                events=[],
                context=ctx.model_dump(),
                agents=agents_info(),
                guardrails=[],
            )
    else:
        assert req.conversation_id is not None, "Conversation ID should not be None if session exists"
        session = await session_service.get_session(
            app_name=ADK_APP_NAME,
            user_id=ADK_USER_ID,
            session_id=req.conversation_id,
        )

    assert session is not None, "Session should not be None if conversation_id is provided"

    new_message = req.message.strip()
    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=new_message)],
    )

    runner = await _get_runner_async(app_name=ADK_APP_NAME)

    messages: list[MessageResponse] = []
    events: list[AgentEvent] = []
    guardrails: list[GuardrailCheck] = []

    async for event in runner.run_async(
        user_id=ADK_USER_ID,
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts and event.content.parts[0].text:
            author = event.author
            text = event.content.parts[0].text
            messages.append(MessageResponse(content=text, agent=author))
            events.append(AgentEvent(id=uuid4().hex, type="message", agent=author, content=text))

            if event.custom_metadata and "guard_rail_triggered" in event.custom_metadata:
                guardrails.append(event.custom_metadata["guard_rail_triggered"])

        if fn_calls := event.get_function_calls():
            for fn_call in fn_calls:
                events.append(
                    AgentEvent(
                        id=uuid4().hex,
                        type="tool_call",
                        agent=event.author,
                        content=fn_call.name or "",
                        metadata={"tool_args": fn_call.args},
                    )
                )

                if fn_call.name == "display_seat_map":
                    messages.append(
                        MessageResponse(
                            content="DISPLAY_SEAT_MAP",
                            agent=event.author,
                        )
                    )

        if fn_responses := event.get_function_responses():
            for fn_response in fn_responses:
                events.append(
                    AgentEvent(
                        id=uuid4().hex,
                        type="tool_output",
                        agent=event.author,
                        content=str(fn_response.response),
                        metadata={"tool_result": fn_response.response},
                    )
                )

    # we need to refresh the session to get the latest state
    assert req.conversation_id is not None, "Conversation ID should not be None if session exists"
    session = await session_service.get_session(
        app_name=ADK_APP_NAME,
        user_id=ADK_USER_ID,
        session_id=req.conversation_id,
    )

    assert session is not None, "Session should not be None after running the agent"
    airline_context = session.state.get("context", AirlineAgentContext.create_initial_context().model_dump())
    current_agent_name = session.state.get("current_agent", "triage_agent")

    return ChatResponse(
        conversation_id=session.id,
        current_agent=current_agent_name,
        messages=messages,
        events=events,
        context=airline_context,
        agents=agents_info(),
        guardrails=guardrails,
    )
