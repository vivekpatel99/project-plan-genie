import json
import re
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import rootutils
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolCallChunk
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from loguru import logger

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
from frontend.message_router import StreamManager  # noqa: E402
from src.agent.states import ClarifyWithUser  # noqa: E402


def setup_logging() -> None:
    """Configure logging for the application."""
    logging_config = {
        "handlers": [
            {"sink": sys.stdout, "level": "DEBUG", "colorize": True},
            {
                "sink": f"{Path.cwd().parent / f'{__name__}.log'}",
                "enqueue": True,
                "level": "DEBUG",
                "rotation": "1 MB",
            },
        ],
    }
    logger.configure(**logging_config)


async def process_tool_call_chunk(chunk: ToolCallChunk):
    """Process a tool call chunk and return a formatted string."""
    tool_call_str = ""

    tool_name = chunk.get("name", "")
    args = chunk.get("args", "")

    if tool_name:
        tool_call_str += f"\n\n< TOOL CALL: {tool_name} >\n\n"
    if args:
        tool_call_str += args

    return tool_call_str


@logger.catch
async def stream_graph_responses(
    *,
    user_input: dict[str, Any],
    graph: CompiledStateGraph,
    config: dict[str, Any],
) -> AsyncGenerator[tuple[str, str]]:
    """
    Stream messages from a LangGraph agent, separating updates and messages.

    When the agent makes a tool call, yields a message like "< TOOL CALL: tool_name >".
    Otherwise, yields the message content.

    Args:
        user_input: The input to the agent.
        graph: The agent to stream messages from.
        config: The configuration to use when streaming messages.

    Yields:
        A tuple of (message, subgraph_name), where message is the message to display and
        subgraph_name is the name of the subgraph that the message belongs to.

    """
    async for mode, message_chunk in graph.astream(
        input=user_input,
        config=config,
        stream_mode=["updates", "messages"],
    ):
        if mode == "updates":
            graph_name = next(iter(message_chunk.keys()))
            if graph_name == "clarify_with_user":
                last_message = message_chunk[graph_name]["messages"][-1].content
                yield last_message
        if mode == "messages":
            message, metadata = message_chunk
            subgraph_name = metadata["langgraph_node"]
            if isinstance(message, AIMessageChunk):
                if message.tool_call_chunks:
                    tool_chunk = message.tool_call_chunks[0]
                    tool_call_str = await process_tool_call_chunk(tool_chunk)
                    yield tool_call_str, subgraph_name
                elif subgraph_name == "clarify_with_user":
                    pass  # grab the question, so we can't stream the token
            else:
                yield message.content, subgraph_name


@logger.catch
async def stream_graph_responses_test(
    *,
    user_input: Any,
    graph: CompiledStateGraph,
    config: dict[str, Any],
    stream_mode: str = "updates",
) -> AsyncGenerator[tuple[str, str]]:
    """
    Stream messages from a LangGraph agent, separating updates and messages.

    When the agent makes a tool call, yields a message like "< TOOL CALL: tool_name >".
    Otherwise, yields the message content.

    Args:
        user_input: The input to the agent.
        graph: The agent to stream messages from.
        config: The configuration to use when streaming messages.
        stream_mode: The stream mode to use when streaming messages either `updates` or `messages`.

    Yields:
        A tuple of (message, subgraph_name), where message is the message to display and
        subgraph_name is the name of the subgraph that the message belongs to.

    """
    stream_manager = StreamManager()
    async for chunk in graph.astream(
        input=user_input,
        config=config,
        stream_mode=stream_mode,
    ):
        node_name = next(iter(chunk.keys()))
        if node_name == "final_report_graph":
            print()
        print(node_name)
        router = stream_manager.get_router(stream_mode)
        async for output in router.route(chunk, node_name):
            yield output


async def handle_clarification(full_response: str) -> dict:
    """Handle user clarification workflow."""
    pattern = r"\{.*\}"
    match_str = re.search(pattern, full_response, re.DOTALL)
    json_str = match_str.group()
    str_to_dict = json.loads(json_str)
    question: ClarifyWithUser = ClarifyWithUser.model_validate(str_to_dict)
    print(question.question, end="", flush=True)

    user_input = input("\n\nUser Clarification needed: ").strip()
    print(f"\n\n ----- 🥷 Human ----- \n\n{user_input}\n")

    return {"messages": [HumanMessage(content=user_input)]}


async def handle_interrupts(graph: CompiledStateGraph, config: dict) -> None:
    """Handle human-in-the-loop interrupts."""
    thread_state = graph.get_state(config=config)

    while thread_state.interrupts:
        for interrupt in thread_state.interrupts:
            logger.debug("\n ----- ✅ / ❌ Human Approval Required ----- \n")
            interrupt_message = interrupt.value["message"]
            tool_calls = [f"Tool Name: {tc['name']} with Args: {tc['args']}" for tc in interrupt.value["tool_calls"]]
            logger.debug(f"{interrupt_message} => **{chr(10).join(tool_calls)}**")

            # Get user action
            while True:
                user_input = input("Action (accept/feedback): ").strip().lower()
                if user_input in ["accept", "feedback"]:
                    break
                print("Please enter 'accept' or 'feedback'")

            # Handle user response
            if user_input == "accept":
                user_response = Command(resume={"action": "accept", "feedback": None})
            else:
                feedback = input("Please provide your feedback: ").strip()
                user_response = Command(resume={"action": "feedback", "feedback": feedback})

            # Continue execution
            logger.debug(" ---- 🧞‍♀️ Assistant ---- \n")
            async for message, _ in stream_graph_responses(
                user_input=user_response,
                graph=graph,
                config=config,
            ):
                logger.debug(message, end="", flush=True)

        thread_state = graph.get_state(config=config)
