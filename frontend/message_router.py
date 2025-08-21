"""
Router Pattern for handling messages from LangGraph agent.

1. NodHandler class  - Protocol ensures all handlers follow the same contract, making the code more maintainable and preventing runtime errors.
2. StreamManager class - Manages the stream modes (`updates` and `messages`) and routes messages to their respective handlers.
3. StreamRouter class - contain the handlers for each stream mode.
4. *Handler classes - each handler is responsible for handling messages from a specific node.

"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import get_buffer_string
from loguru import logger

from src.agent.states import StatesKeys


class NodeHandler(ABC):
    """
    An abstract base class for node handlers.

    This ABC ensures all handlers follow the same contract, making the code
    more maintainable and preventing runtime errors.
    """

    @abstractmethod
    async def handle(self, chunk: dict[str, Any], node_name: str) -> AsyncIterator[str]:
        """Handles a chunk of data for a specific node."""
        if False:
            yield


class BaseFormattingHandler(NodeHandler):
    """Base handler for nodes that require simple message formatting."""

    async def handle(self, chunk: dict[str, Any], node_name: str) -> AsyncIterator[str]:
        msg = self.extract_message(chunk, node_name)
        if msg is not None:
            yield f"\n\n **{node_name}**: \n{msg}"

    @abstractmethod
    def extract_message(self, chunk: dict[str, Any], node_name: str) -> str | None:
        """Extracts the relevant message from the chunk."""
        ...


class StreamRouter:
    def __init__(self) -> None:
        self.handlers: dict[str, NodeHandler] = {
            "__interrupt__": InterruptHandler(),
            "clarify_with_user": ClarifyWithUserHandler(),
            "write_research_brief": WriteResearchBriefHandler(),
            "supervisor_subgraph": SupervisorSubgraphHandler(StatesKeys),
            "final_report_generation": FinalReportGenerationHandler(StatesKeys),
            "final_report_graph": FinalReportGenerationHandler(StatesKeys),
            "tool_manager": ToolManagerHandler(StatesKeys),
            "mcp_tool_call": McpToolCallHandler(StatesKeys),
        }
        self.default_handler = self.DefaultHandler()

    async def route(self, chunk: dict[str, Any], node_name: str) -> AsyncIterator[str]:
        handler = self.handlers.get(node_name, self.default_handler)
        async for result in handler.handle(chunk, node_name):
            yield result

    class DefaultHandler(NodeHandler):
        """Default handler for unhandled nodes."""

        async def handle(self, chunk: dict[str, Any], node_name: str) -> AsyncIterator[str]:
            logger.warning(f"No specific handler for node '{node_name}'. Using default handler.")
            yield f"\n\n**FROM DEFAULT HANDLER ({node_name})** \n\n" + str(chunk)


class StreamManager:
    """Manages the stream of messages and updates from the agent."""

    def __init__(self) -> None:
        self.update_router = StreamRouter()
        # self.message_router = MessageRouter()  # Future implementation

    def get_router(self, stream_mode: str) -> StreamRouter:
        if stream_mode == "updates":
            return self.update_router
        # if stream_mode == "messages":
        #     return self.message_router
        msg = f"Unsupported stream mode: {stream_mode}"
        raise ValueError(msg)


class InterruptHandler(NodeHandler):
    def _format_tool_call(self, msg: str, tool_call: dict) -> str:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        formatted_string = "\n".join(f"{key.capitalize()}: {value}" for key, value in tool_args.items())
        return f"\n{msg}\n\n< TOOL CALL: tool_name: {tool_name} >\ntool_arg: {formatted_string}"

    async def handle(self, chunk: dict[str, Any], node_name: str) -> AsyncIterator[str]:
        total_interrupts = []
        for _interrupt in chunk.get(node_name, []):
            msg = _interrupt.value.get("message")
            interrupt_data = _interrupt.value

            tool_calls = interrupt_data.get("tool_calls", [])
            if "tool_calls" in interrupt_data:
                print("Found 'tool_calls' key.")
            elif "tool_call" in interrupt_data:
                # Handle cases where there's a single tool_call not in a list
                tool_calls.append(interrupt_data["tool_call"])

            for tool_call in tool_calls:
                if tool_call:
                    total_interrupts.append(self._format_tool_call(msg, tool_call))

        if total_interrupts:
            yield "\n\n".join(total_interrupts)


class ClarifyWithUserHandler(BaseFormattingHandler):
    def extract_message(self, chunk: dict[str, Any], node_name: str) -> str | None:
        msg = chunk.get(node_name)
        if msg and "messages" in msg and msg["messages"]:
            return msg["messages"][-1].content
        return None


class WriteResearchBriefHandler(BaseFormattingHandler):
    def extract_message(self, chunk: dict[str, Any], node_name: str) -> str | None:
        msg = chunk.get(node_name)
        return msg.get("research_brief") if msg else None


class SupervisorSubgraphHandler(NodeHandler):
    def __init__(self, states_keys: type[StatesKeys]):
        self.states_keys = states_keys

    async def handle(self, chunk: dict[str, Any], node_name: str) -> AsyncIterator[str]:
        msg = chunk.get(node_name)
        if not msg:
            return
        last_msg = msg.get(self.states_keys.SUPERVISOR_MSGS.value, [])[-1]
        supervisor_msgs = get_buffer_string(msg[self.states_keys.SUPERVISOR_MSGS.value][1:])  # removing system message
        additional_kwargs = getattr(last_msg, "additional_kwargs", {})
        function_call = additional_kwargs.get("function_call")
        formatted_string = ""
        if function_call:
            formatted_string = "\n".join(f"{key.capitalize()}: {value}" for key, value in function_call.items())
            yield f"\n\n **{node_name}**: \n{formatted_string}"

        if not formatted_string:  # If no function call, use the last message
            yield f"\n\n **{node_name}**: \n{supervisor_msgs}"


class FinalReportGenerationHandler(BaseFormattingHandler):
    def __init__(self, states_keys: type[StatesKeys]):
        self.states_keys = states_keys

    def extract_message(self, chunk: dict[str, Any], node_name: str) -> str | None:
        msg = chunk.get(node_name)
        return msg.get(self.states_keys.FINAL_REPORT.value) if msg else None


class ToolManagerHandler(BaseFormattingHandler):
    def __init__(self, states_keys: type[StatesKeys]):
        self.states_keys = states_keys

    def extract_message(self, chunk: dict[str, Any], node_name: str) -> str | None:
        msg = chunk.get(node_name)
        if (
            msg
            and self.states_keys.TOOL_MANAGER_MESSAGES.value in msg
            and msg[self.states_keys.TOOL_MANAGER_MESSAGES.value]
        ):
            return msg[self.states_keys.TOOL_MANAGER_MESSAGES.value][-1].content
        return None


class McpToolCallHandler(BaseFormattingHandler):
    def __init__(self, states_keys: type[StatesKeys]):
        self.states_keys = states_keys

    def extract_message(self, chunk: dict[str, Any], node_name: str) -> str | None:
        msg = chunk.get(node_name)
        return str(msg.get(self.states_keys.TOOL_MANAGER_MESSAGES.value)) if msg else None
