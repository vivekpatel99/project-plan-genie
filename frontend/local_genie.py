"""reference: https://github.com/kenneth-liao/crm-agent/blob/main/frontend/chat_local.py."""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import rootutils
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from loguru import logger

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
from utils import States, test_graph_builder  # noqa: E402

# from src.agent.clarification_agent_subgraph import clarify_builder


THINK_REGEX = r"<think>(.*?)</think>"


async def stream_graph_responses(
    *,
    user_input: dict[str, Any],
    graph: CompiledStateGraph,
    config: dict,
) -> AsyncGenerator[str]:
    async for stream_mode, message_chunk in graph.astream(
        input=user_input,
        config=config,
        stream_mode=["updates", "messages"],
    ):
        if stream_mode == "messages":  # TODO: grab graph name here and use token streaming from messages
            message, metadata = message_chunk
            # node: str | Any = metadata["langgraph_node"]
            if isinstance(message, AIMessageChunk):
                if message.response_metadata:
                    finish_reason = message.response_metadata.get("finish_reason", "")
                    if finish_reason == "tool_calls":
                        yield "\n\n"

                if message.tool_call_chunks:
                    tool_chunk = message.tool_call_chunks[0]

                    tool_name = tool_chunk.get("name", "")
                    args = tool_chunk.get("args", "")

                    if tool_name:
                        tool_call_str = f"\n\n< TOOL CALL: {tool_name} >\n\n"
                    if args:
                        tool_call_str = args

                    yield tool_call_str
                else:
                    yield message.content
                continue

        # if stream_mode == "updates" and isinstance(message_chunk, dict):
        #     keys = list(message_chunk.keys())
        #     graph_name = keys[0]
        #     chunk = message_chunk[graph_name]

        #     if isinstance(chunk, tuple) and isinstance(chunk[0], Interrupt):
        #         interrupt_message = chunk[0].value
        #         message = interrupt_message["message"]
        #         tools_calls = interrupt_message["tool_call"]["name"]
        #         yield f"\n\n {message} => **{tools_calls}**"
        #         # yield "\n\n"

        #     if isinstance(chunk, dict) and "messages" in chunk:  # messages
        #         last_message = chunk["messages"][-1]

        #         if isinstance(last_message, AIMessage) and last_message.tool_calls:
        #             tool_calls = [f"Tool Name: {tc['name']} with Args: {tc['args']}" for tc in last_message.tool_calls]
        #             yield "All Tool Calls: " + "\n\n".join(tool_calls)

        #         yield last_message.content


async def main() -> None:  # noqa: C901
    config = {
        "handlers": [
            {"sink": sys.stdout, "level": "ERROR", "colorize": True},
            {
                "sink": f"{Path.cwd().parent / f'{__name__}.log'}",
                "enqueue": True,
                "level": "DEBUG",
                "rotation": "10 MB",
                "compression": "zip",
            },
        ],
    }
    logger.configure(**config)
    configurable = {"configurable": {"thread_id": "1"}}

    try:
        graph = await test_graph_builder()
        graph_input = States(
            messages=[
                HumanMessage(
                    content="Generate a report on the project planning process. I don't know where to start, i want to create simple chatbot using langgraph. i am testing that you can use filesystem or not. simply generate a report without asking further question.",
                ),
            ],
        )
        while True:
            print(" ---- 🧞‍♀️ Assistant ---- \n")
            async for response in stream_graph_responses(
                user_input=graph_input,
                graph=graph,
                config=configurable,
            ):
                print(response, end="", flush=True)
            thread_state = graph.get_state(config=configurable)

            while thread_state.interrupts:  # handle interrupts
                user_action = None
                feedback = None
                for interrupt in thread_state.interrupts:
                    print("\n ----- ✅ / ❌ Human Approval Required ----- \n")
                    interrupt_message = interrupt.value["message"]
                    tools_calls = interrupt.value["tool_call"]["name"]
                    print(f"{interrupt_message} => **{tools_calls}**")

                    user_input = input("Action: Accept or Feedback: ").strip().lower()
                    while user_input not in ["accept", "feedback"]:
                        user_input = input("Action: Accept or Feedback: ").strip().lower()

                    # user can either accept or provide feedback
                    if user_input == "accept":
                        user_action = user_input
                    elif user_input == "feedback":
                        feedback = user_input
                    print(" ---- 🧞‍♀️ Assistant ---- \n")
                    user_response = {"action": user_action, "feedback": feedback}
                    async for response in stream_graph_responses(
                        user_input=Command(resume=user_response),
                        graph=graph,
                        config=configurable,
                    ):
                        print(response, end="", flush=True)
                    thread_state = graph.get_state(config=configurable)

            user_input = input("\n\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                print("\n\nExit command received. Exiting...\n\n")
                break

            graph_input = {
                "messages": [
                    HumanMessage(content=user_input),
                ],
            }

            print(f"\n\n ----- 🥷 Human ----- \n\n{user_input}\n")

    except Exception as e:
        print(e)
        return


if __name__ == "__main__":
    import asyncio

    # `nest_asyncio.apply()` is a workaround for Jupyter notebooks.
    #
    # By default, Jupyter notebooks use the "asyncio" event loop policy,
    # which doesn't allow nested event loops. However, some libraries
    # (like `streamlit`) create their own event loops internally.
    #
    # `nest_asyncio.apply()` changes the event loop policy to allow
    # nested event loops, which fixes the issue.
    #
    # However, this is only needed for Jupyter notebooks, not for
    # standalone Python scripts. So, we only apply the workaround
    # if we're running inside a Jupyter notebook.
    #
    # See: https://github.com/nteract/hydrogen/issues/1337
    if "ipykernel" in sys.modules:
        import nest_asyncio

        nest_asyncio.apply()
    asyncio.run(main())
