import re
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import rootutils
import streamlit as st
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Interrupt
from loguru import logger

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
from utils import test_graph  # noqa: E402

# from src.agent.clarification_agent_subgraph import clarify_builder
config = {
    "handlers": [
        {"sink": sys.stdout, "level": "ERROR", "colorize": True},
        {
            "sink": f"{Path.cwd().parent.parent / f'{__name__}.log'}",
            "enqueue": True,
            "level": "DEBUG",
            "rotation": "10 MB",
            "compression": "zip",
        },
    ],
}


logger.configure(**config)

CONFIG = {"configurable": {"thread_id": "1"}}
THINK_REGEX = r"<think>(.*?)</think>"

st.title("Project Planning Genie 🧞‍♀️")

# Create an empty list to store messages
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# loading the conversation history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


async def stream_graph_responses(
    *,
    user_input: dict[str, BaseMessage],
    graph: CompiledStateGraph,
    config: dict,
) -> AsyncGenerator[str]:
    async for message_chunk in graph.astream(
        input=user_input,
        config=config,
        stream_mode="updates",  # ["updates", "messages"],
    ):
        # if stream_mode == "messages": # TODO: grab graph name here and use token streaming from messages
        #     ...
        # if stream_mode == "updates" and isinstance(message_chunk, dict):
        with st.status(label="Thinking...", expanded=True) as status:
            keys = list(message_chunk.keys())
            graph_name = keys[0]
            status.write(f"📍 Current Stage: **{graph_name}**")
            chunk = message_chunk[graph_name]

            print(chunk)
            if isinstance(chunk, tuple) and isinstance(chunk[0], Interrupt):
                interrupt_message = chunk[0].value
                message = interrupt_message["message"]
                tools_calls = interrupt_message["tool_call"]["name"]
                yield f"\n\n{message} => **{tools_calls}**"

            if isinstance(chunk, dict) and "messages" in chunk:  # messages
                last_message = chunk["messages"][-1]

                if isinstance(last_message, AIMessage) and last_message.tool_calls:
                    tool_call = last_message.tool_calls[-1]
                    yield f"Tool call: **{tool_call['name']}**"
                    # continue

                parts = re.split(THINK_REGEX, last_message.content, flags=re.DOTALL)

                # The parts will alternate between reply text and thought text.
                # Reply parts are at even indices, thoughts at odd indices.
                reply = "".join(parts[::2]).strip()
                thoughts = parts[1::2]
                if thoughts:
                    status.markdown(f"🤔 {thoughts[0]}")
                    status.update(label="Complete!", state="complete", expanded=False)

                yield reply


if prompt := st.chat_input("Please Write Detail Project Description"):
    # first add the message to message_history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    user_input_message = {"messages": [HumanMessage(content=prompt)]}

    # thread_state = clarify_subgraph.get_state(config=CONFIG)
    with st.chat_message("assistant", avatar="🧞‍♀️"):
        ai_message = st.write_stream(
            stream_graph_responses(
                user_input=user_input_message,
                graph=test_graph,
                config=CONFIG,
                # status=None,
            ),
        )
        # Update status display

        print("#############")
    print("ai_message", ai_message)
    # the message to message_history
    st.session_state.messages.append({"role": "assistant", "content": ai_message})
