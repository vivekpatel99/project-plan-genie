"""
reference: https://github.com/kenneth-liao/crm-agent/blob/main/frontend/chat_local.py.

you should find best and simple solution for those questions
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import rootutils
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.cache.memory import InMemoryCache
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from loguru import logger

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

# from src.agent.project_planning_genie import agent_builder
from frontend.utils import final_report_generation_input, setup_logging  # noqa: E402
from src.agent.final_report_generation import builder  # noqa: E402
from src.agent.states import ClarifyWithUser, ReportGeneratorState  # noqa: E402

set_llm_cache(SQLiteCache(database_path=".langchain.db"))
THINK_REGEX = r"<think>(.*?)</think>"

#         graph_input = AgentState(
#             messages=[
#                 HumanMessage(
#                     content=""" Develop an agent-powered AI note-taking app using LangGraph, designed for personal productivity and as a demonstration of your skills in computer vision, multi-agent systems, and end-to-end AI engineering. The app will facilitate capturing handwritten notes, automatically formatting them (including complex content like equations and diagrams), classifying content into the correct Notion section, and uploading the processed notes with rich formatting. The goal is to implement a Minimum Viable Product (MVP) capable of image-to-text conversion and formatting within two weeks.

# **Core Features**
# **Image Capture:**
# Capture pictures of handwritten notes in English via a user interface (LangGraph's prebuilt UI, accessible from PC). It should capture image one by one.
# **English Handwriting Recognition:**
# Automatically extract typed text (including digits, equations, and diagrams) from handwritten pictures using cutting-edge OCR. you should search for best open source(free) ocr engine for python. Equation must be also in Latex format. You must find best open source OCR engine for this task
# **Formatting & Structuring:**
# Clean and format extracted notes (markdown, LaTeX for equations, code blocks, etc.).
# Detect and separate sections; classify content to either add as a new Notion sub-page/page or merge with an existing page.
# The diagram can be either a flowchart or a block diagram. it must supports tables. Diagram must be editable for user interaction/update.
# **Integration with Notion:**
# Upload formatted notes programmatically into Notion, preserving structure and style. it must use Notion integration API key (my personal API keys) for authentication and access to Notion's database. I will mcp server for communicating with Notion.

# **Agentic Orchestration:**
# Use a multi-agent system in LangGraph for more information -'https://docs.oap.langchain.com/quickstart':
# Agent 1: Image-to-text extraction (OCR, diagram/equation recognition)
# Agent 2: Text cleanup, markdown formatting, and Notion posting
# **PC Interaction:**
# Leverage LangGraph's prebuilt UI for smooth agent interaction from a PC browser, more information about open agent platform for ui 'https://docs.oap.langchain.com/quickstart'.
# **Python First:**
# Entire codebase written in Python, using established libraries for AI, vision, and web connectivity.

# - you must select clean architecture and SOLID principles and decide where to use which principles for this project
# - you must select best testing strategy for this project
# - you must decide better architecture style, such as a microservice-style modular backend, a monolith and so on
# - use model can be easily swappable to keep up with the latest developments in AI technology
# - it is personal project for personal portfolio development so good readme with proper diagram (visualization) is required. so anybody can easily understand your project idea and workflow.
#  """,
#                 ),
#             ],
#         )


@logger.catch
async def stream_graph_responses(
    *,
    user_input: dict[str, Any],
    graph: CompiledStateGraph,
    config: dict[str, Any],
) -> AsyncGenerator[tuple[str, str]]:
    async for stream_mode, message_chunk in graph.astream(
        input=user_input,
        config=config,
        stream_mode=["updates", "messages"],
    ):
        if stream_mode == "updates" and isinstance(message_chunk, dict):
            keys = list(message_chunk.keys())
            subgraph_name = keys[0]
            print(f"\n\n------------------{subgraph_name} subgraph------------------\n\n")
            yield "\n\n", subgraph_name
        if stream_mode == "messages":  # TODO: grab graph name here and use token streaming from messages
            message, metadata = message_chunk
            subgraph_name = metadata["langgraph_node"]
            if isinstance(message, AIMessageChunk):
                if message.response_metadata:
                    finish_reason = message.response_metadata.get("finish_reason", "")
                    if finish_reason == "tool_calls":
                        yield "\n\n", subgraph_name

                if message.tool_call_chunks:
                    tool_chunk = message.tool_call_chunks[0]

                    tool_name = tool_chunk.get("name", "")
                    args = tool_chunk.get("args", "")

                    if tool_name:
                        tool_call_str = f"\n\n< TOOL CALL: {tool_name} >\n\n"
                    if args:
                        tool_call_str = args

                    yield tool_call_str, subgraph_name
                else:
                    yield message.content, subgraph_name


async def handle_clarification(graph: CompiledStateGraph, config: dict, full_response: str) -> dict:  # noqa: ARG001
    """Handle user clarification workflow."""
    str_to_dict = json.loads(full_response)
    question: ClarifyWithUser = ClarifyWithUser.model_validate(str_to_dict)
    print(question.question, end="", flush=True)

    user_input = input("\n\nUser Clarification needed: ").strip()
    print(f"\n\n ----- 🥷 Human ----- \n\n{user_input}\n")

    return {"messages": [HumanMessage(content=user_input)]}


async def handle_interrupts(graph: CompiledStateGraph, config: dict) -> None:
    """Handle human-in-the-loop interrupts."""
    thread_state = graph.get_state(config=config)

    while thread_state.interrupts:
        print("\n\n -----  __interrupt__ ----- \n\n")

        for interrupt in thread_state.interrupts:
            print("\n ----- ✅ / ❌ Human Approval Required ----- \n")
            interrupt_message = interrupt.value["message"]
            tool_calls = [f"Tool Name: {tc['name']} with Args: {tc['args']}" for tc in interrupt.value["tool_calls"]]
            print(f"{interrupt_message} => **{chr(10).join(tool_calls)}**")

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
            print(" ---- 🧞‍♀️ Assistant ---- \n")
            async for message, _ in stream_graph_responses(
                user_input=user_response,
                graph=graph,
                config=config,
            ):
                print(message, end="", flush=True)

        thread_state = graph.get_state(config=config)


@logger.catch
async def main() -> None:
    setup_logging()
    graph_input: ReportGeneratorState = final_report_generation_input
    try:
        configurable = {"configurable": {"thread_id": "1"}}
        graph = builder.compile(
            name="Final Report Generation",
            checkpointer=MemorySaver(),
            cache=InMemoryCache(),
        )  # test_graph_builder()

        # Clarification with User Graph
        while True:
            print(" ---- 🧞‍♀️ Assistant ---- \n")
            full_response = ""
            async for message, subgraph_name in stream_graph_responses(
                user_input=graph_input,
                graph=graph,
                config=configurable,
            ):
                # can't stream, because we need to format the questions from LLM
                if subgraph_name == "clarify_with_user":
                    full_response += message
                else:
                    print(message, end="", flush=True)

            last_subgraph_name = subgraph_name

            # Handle clarification
            if last_subgraph_name == "clarify_with_user":
                graph_input = await handle_clarification(graph, configurable, full_response)
                continue

            # Handle interrupts
            await handle_interrupts(graph, configurable)

            # Check if we should continue or break
            thread_state = graph.get_state(config=configurable)
            if not thread_state.interrupts and thread_state.next == ():
                print("\n\n🎉 Process completed successfully!")
                break

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
    except Exception as e:
        logger.exception("Unexpected error in main execution")
        print(f"❌ Error: {e}")
        return


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
