from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessageChunk, ToolCallChunk
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command


async def process_tool_call_chunk(chunk: ToolCallChunk):
    tool_call_str = ""
    tool_name = chunk.tool_name
    args = chunk.get("args", "")

    if tool_name:
        tool_call_str += f"Tool name: {tool_name}\n"
    if args:
        tool_call_str += f"Args: {args}\n"

    return tool_call_str


async def stream_graph_responses(
    user_input: dict[str, Any] | Command,
    graph: CompiledStateGraph,
    **kwargs,
) -> AsyncGenerator[str]:
    async for msg_chunk, _ in graph.astream(input=user_input, stream_mode="messages", **kwargs):
        if isinstance(msg_chunk, AIMessageChunk):
            finish_reason = msg_chunk.response_metadata.get("finish_reason", "")
            if finish_reason == "tool_call":
                yield "\n\n"
        if msg_chunk.tool_call_chunks:
            tool_chunk = msg_chunk.tool_call_chunks[0]
            tool_call_str = await process_tool_call_chunk(tool_chunk)
            yield tool_call_str

        else:
            content = msg_chunk.content
            if isinstance(content, str):
                yield content
            elif isinstance(content, list):
                yield "\n".join(content)
            else:
                yield str(content)


# async def main():
#     try:
#         final_report_graph = await  builder.compile(name="Project Planning Genie")

#         # Checkpointing and a thread_id are required for human-in-the-loop in Langgraph
#         config = RunnableConfig(
#             recursion_limit=25,
#             configurable = {
#                 "thread_id": "1"
#             }
#         )
#         # Initial input
#         graph_input = {
#             "messages": [
#                 HumanMessage(content="Briefly introduce yourself and offer to help me.")
#             ],

#         }
