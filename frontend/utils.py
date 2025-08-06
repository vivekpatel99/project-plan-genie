from typing import Literal

import rootutils
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt
from loguru import logger

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
from src.agent.my_mcps import mcp_config  # noqa: E402


class States(MessagesState):
    """State of conversation between Agent and User."""

    # messages: Annotated[list[BaseMessage], add_messages] = []


protected_tools: list[str] = ["create_directory", "edit_file", "write_file"]
# async def display_with_subgraph_status_TODO(user_input: dict[str, BaseMessage], config: dict):
#     with st.status(label="Thinking...", expanded=True) as status:
#         async for stream_mode, chunk in test_graph.astream(
#             input=user_input,
#             config=config,
#             stream_mode=["updates", "messages"],
#         ):
#             # get info from update mode
#             if stream_mode == "updates" and isinstance(chunk, dict):
#                 # chunk is dict of graph name and update
#                 keys = list(chunk.keys())
#                 graph_name = keys[0]
#                 status.write(f"📍 Current Stage: **{graph_name}**")

#             # get info from message mode
#             if stream_mode == "messages":
#                 # chunk is tuple of (message, metadata)
#                 message, metadata = chunk

#                 message = message.content

#                 # parts = re.split(THINK_REGEX, message, flags=re.DOTALL)

#                 # # The parts will alternate between reply text and thought text.
#                 # # Reply parts are at even indices, thoughts at odd indices.
#                 # reply = "".join(parts[::2]).strip()
#                 # thoughts = parts[1::2]

#                 if message == "<think>":
#                     is_thinking = True
#                     continue
#                 if message == "</think>":
#                     is_thinking = False
#                 if not is_thinking:
#                     status.write_stream(f"🤔 {message}")
#                 else:
#                     status.update(label="Done!", state="complete", expanded=False)
#                     yield message

#                 # Update status displays


async def test_graph_builder() -> StateGraph:
    client = MultiServerMCPClient(connections=mcp_config["mcpServers"])

    tools = await client.get_tools()

    llm = ChatOllama(name="qwen", model="qwen3:14b", temperature=0).bind_tools(tools)

    def human_tool_review_node(
        state: States,
    ) -> Command[Literal["tools", "assistant_node"]]:
        """Node is a placeholder for the human to review the final report generation process to verify proper tool call checks before tools are called by the agent."""
        print("[INFO] human_tool_review_node called")
        last_message = state["messages"][-1]

        # Ensure we have a valid AI message with tool calls
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            msg = "human_tool_review_node called without valid tool calls"
            logger.error(msg)
            raise ValueError(msg)

        tool_call = last_message.tool_calls[-1]

        # Stop graph execution and wait for human input
        human_review: dict = interrupt(
            {"message": "Your input is required for the following tool:", "tool_call": tool_call},
        )
        review_action = human_review.get("action")
        review_data = human_review.get("data")

        if review_action == "accept":
            return Command(
                goto="tools",
            )
        return Command(
            goto="assistant_node",
            update={
                "messages": [
                    HumanMessage(content=review_data),
                ],
            },
        )

    def assistant_node(state: States) -> States:
        print("[INFO] assistant_node called")
        response = llm.invoke(
            [
                SystemMessage(
                    content="You are a helpful assistant. You have access to the local filesystem but only within an approved directory. The approved directory is /projects/workspace and all paths must begin with /projects/workspace/. You must use /project/workspace/generated_example directory. if directory does not exists then create it and then give a good name of the <file_name>.md file (for example sw_design.md) and save the generated report in /project/workspace/generated_example directory.",
                ),
                *state["messages"],
            ],
        )
        state["messages"] = [*state["messages"], response]
        return state

    def router(state: States) -> str:
        print("[INFO] router called")
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            if any(tool_call["name"] in protected_tools for tool_call in last_message.tool_calls):
                return "human_tool_review_node"
            return "tools"
        return END

    builder = StateGraph(States)

    builder.add_node("assistant_node", assistant_node)
    builder.add_node("human_tool_review_node", human_tool_review_node)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant_node")
    builder.add_conditional_edges("assistant_node", router, ["tools", "human_tool_review_node", END])
    builder.add_edge("tools", "assistant_node")

    return builder.compile(checkpointer=MemorySaver())


# test_graph = asyncio.run(test_graph_builder())
