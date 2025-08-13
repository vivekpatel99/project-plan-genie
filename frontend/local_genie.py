"""
reference: https://github.com/kenneth-liao/crm-agent/blob/main/frontend/chat_local.py.

you should find best and simple solution for those questions
"""

import json
import re
from collections.abc import AsyncGenerator
from typing import Any

import rootutils
from langchain_core.caches import InMemoryCache
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolCallChunk
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from loguru import logger

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
from frontend.utils import setup_logging  # noqa: E402
from src.agent.project_planning_genie import agent_builder  # noqa: E402
from src.agent.states import AgentState, ClarifyWithUser  # noqa: E402

# set_llm_cache(SQLiteCache(database_path=".langchain.db"))
THINK_REGEX = r"<think>(.*?)</think>"


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
    async for message_chunk in graph.astream(input=user_input, config=config, stream_mode="messages"):
        message, metadata = message_chunk
        subgraph_name = metadata["langgraph_node"]
        if isinstance(message, AIMessageChunk):
            if message.tool_call_chunks:
                tool_chunk = message.tool_call_chunks[0]
                tool_call_str = await process_tool_call_chunk(tool_chunk)
                yield tool_call_str, subgraph_name
            else:
                yield message.content, subgraph_name


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


@logger.catch
async def main() -> None:
    setup_logging()
    graph_input = AgentState(
        messages=[
            HumanMessage(
                content=""" Develop an agent-powered AI note-taking app using LangGraph, designed for personal productivity and as a demonstration of your skills in computer vision, multi-agent systems, and end-to-end AI engineering. The app will facilitate capturing handwritten notes, automatically formatting them (including complex content like equations and diagrams), classifying content into the correct Notion section, and uploading the processed notes with rich formatting. The goal is to implement a Minimum Viable Product (MVP) capable of image-to-text conversion and formatting within two weeks.

**Core Features**
**Image Capture:**
Capture pictures of handwritten notes in English via a user interface (LangGraph's prebuilt UI, accessible from PC). It should capture image one by one.
**English Handwriting Recognition:**
Automatically extract typed text (including digits, equations, and diagrams) from handwritten pictures using cutting-edge OCR. you should search for best open source(free) ocr engine for python. Equation must be also in Latex format. You must find best open source OCR engine for this task
**Formatting & Structuring:**
Clean and format extracted notes (markdown, LaTeX for equations, code blocks, etc.).
Detect and separate sections; classify content to either add as a new Notion sub-page/page or merge with an existing page.
The diagram can be either a flowchart or a block diagram. it must supports tables. Diagram must be editable for user interaction/update.
**Integration with Notion:**
Upload formatted notes programmatically into Notion, preserving structure and style. it must use Notion integration API key (my personal API keys) for authentication and access to Notion's database. I will mcp server for communicating with Notion.

**Agentic Orchestration:**
Use a multi-agent system in LangGraph for more information -'https://docs.oap.langchain.com/quickstart':
Agent 1: Image-to-text extraction (OCR, diagram/equation recognition)
Agent 2: Text cleanup, markdown formatting, and Notion posting
**PC Interaction:**
Leverage LangGraph's prebuilt UI for smooth agent interaction from a PC browser, more information about open agent platform for ui 'https://docs.oap.langchain.com/quickstart'.
**Python First:**
Entire codebase written in Python, using established libraries for AI, vision, and web connectivity.

- you must select clean architecture and SOLID principles and decide where to use which principles for this project
- you must select best testing strategy for this project
- you must decide better architecture style, such as a microservice-style modular backend, a monolith and so on
- use model can be easily swappable to keep up with the latest developments in AI technology
- it is personal project for personal portfolio development so good readme with proper diagram (visualization) is required. so anybody can easily understand your project idea and workflow.
 """,
            ),
        ],
    )

    try:
        configurable = {"configurable": {"thread_id": "1"}}
        graph = agent_builder.compile(
            name="Project Planning Genie Local",
            checkpointer=MemorySaver(),
            cache=InMemoryCache(),
        )  # test_graph_builder()
        # Clarification with User Graph
        while True:
            full_response = ""
            print(" ---- 🧞‍♀️ Assistant ---- \n")
            async for message, subgraph_name in stream_graph_responses(
                user_input=graph_input,
                graph=graph,
                config=configurable,
            ):
                # can't stream, because we need to format the questions from LLM
                if subgraph_name == "clarify_with_user":
                    full_response += message
                    continue

                print(full_response, end="", flush=True)

            # Handle clarification
            if subgraph_name == "clarify_with_user":
                graph_input = await handle_clarification(full_response)
                continue

            # Handle interrupts
            await handle_interrupts(graph, configurable)

            # Check if we should continue or break
            thread_state = graph.get_state(config=configurable)
            if not thread_state.interrupts and thread_state.next == ():
                logger.info("\n\n🎉 Process completed successfully!")
                break

    except KeyboardInterrupt:
        logger.error("\n\n⚠️ Process interrupted by user")
    except Exception as e:
        logger.exception("Unexpected error in main execution")
        logger.error(f"❌ Error: {e}")
        return


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
