import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.func import END
from langgraph.graph import START, StateGraph
from langgraph.types import Command
from loguru import logger
from pydantic import BaseModel

try:
    from .configuration import Configuration
    from .my_mcps import mcp_config
    from .prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE
    from .states import AgentState, StatesKeys
    from .utils import execute_tool_safely, get_today_str
except ImportError:
    # rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.my_mcps import mcp_config
    from src.agent.prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE
    from src.agent.states import AgentState, StatesKeys
    from src.agent.utils import execute_tool_safely, get_today_str

protected_tools: list[str] = ["create_directory", "write_file"]

# https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem


client = MultiServerMCPClient(connections=mcp_config["mcpServers"])


@tool
class ReportGenerated(BaseModel):
    """Call this tool to indicate that the Report generation is successfully completed."""


# Initialize a configurable model that we will use throughout the agent
model_shell = init_chat_model(
    configurable_fields=("model", "max_tokens"),
)


@logger.catch
async def final_report_generation(
    state: AgentState,
    config: RunnableConfig,
):
    """
    Generate final report from the  research notes and findings.

    Takes in a state and config and generates a final report by calling
    the report generator model. If the model fails to generate a report, it retries
    up to `max_retries` times before giving up and returning an error message.
    """
    notes = state.get(StatesKeys.NOTES.value, [])
    messages = state.get(StatesKeys.MSGS.value, [])
    # last_message = messages[-1] if messages else []
    research_brief = state[StatesKeys.RESEARCH_BRIEF.value]

    config = Configuration.from_runnable_config(config)
    report_generator_config = {
        "model": config.final_report_generation_model,
        "max_tokens": config.final_report_generation_model_max_tokens,
    }

    findings = "\n".join(note.content if hasattr(note, "content") else str(note) for note in notes)

    max_retries: int = 3
    current_retry: int = 0
    tools = await client.get_tools()
    final_report_prompt = SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE.format(
        research_brief=research_brief,
        findings=findings,
        date=get_today_str(),
        messages=get_buffer_string(messages),
    )
    report_generator_model = (
        model_shell.bind_tools([*tools, ReportGenerated])
        .with_retry(
            stop_after_attempt=config.max_structured_output_retries,
        )
        .with_config(report_generator_config)
    )

    while current_retry <= max_retries:
        try:
            response = await report_generator_model.ainvoke([HumanMessage(content=final_report_prompt)])

            logger.info("Final report generated: {}", response)
            return {  # noqa: TRY300
                StatesKeys.FINAL_REPORT.value: response.content,
                StatesKeys.MSGS.value: [response],
            }
        except Exception as e:
            last_exception = e
            current_retry += 1
            logger.warning(f"Attempt {current_retry} to generate report failed: {e}")
            if current_retry <= max_retries:
                await asyncio.sleep(2)  # Small delay before retrying

    final_report_content = f"Error generating final report: Maximum retries exceeded, Last error: {last_exception}"
    return {
        StatesKeys.FINAL_REPORT.value: final_report_content,
        StatesKeys.MSGS.value: [AIMessage(content=final_report_content)],
    }


@logger.catch
async def mcp_tool_call(state: AgentState, config: RunnableConfig) -> Command[Literal["final_report_generation"]]:
    """Call this tool to indicate that the Report generation is successfully completed."""
    # Initialize a configurable model that we will use throughout the agent
    messages = state.get(StatesKeys.MSGS.value, [])
    last_message = messages[-1]

    config = Configuration.from_runnable_config(config)

    tools = await client.get_tools()
    tools_by_name = {tool.name: tool for tool in tools if hasattr(tool, "name")}
    tool_calls = last_message.tool_calls

    # Check for ReportGenerated BEFORE executing other tools
    if any(tool_call["name"] == "ReportGenerated" for tool_call in last_message.tool_calls):
        return Command(goto="end")

    # Execute tools step by step, because directory must be created first and the file creation
    observations = [
        await execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config.model_dump())
        for tool_call in tool_calls
    ]
    # observations = await asyncio.gather(*async_responses)
    tool_outputs: list[ToolMessage] = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        for observation, tool_call in zip(observations, tool_calls, strict=False)
    ]

    return {
        StatesKeys.MSGS.value: tool_outputs,
        StatesKeys.NOTES.value: state.get(StatesKeys.NOTES.value, []),  # keep track of notes
    }


# Ensure your state uses "messages" key if using prebuilt tools_condition
async def should_continue(state: AgentState) -> str:
    messages = state.get(StatesKeys.MSGS.value, [])
    if not messages:
        return "end"
    last_message = messages[-1]
    # Check if it's an AI message with tool calls
    if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
        # Check for ReportGenerated tool call
        if any(tool_call["name"] == "ReportGenerated" for tool_call in last_message.tool_calls):
            return "end"
        return "mcp_tool_call"
    return "end"


builder = StateGraph(AgentState, config_schema=Configuration)
# builder = StateGraph(state, config_schema=config)
builder.add_node("final_report_generation", final_report_generation)

builder.add_node("mcp_tool_call", mcp_tool_call)

builder.add_edge(START, "final_report_generation")
builder.add_conditional_edges(
    "final_report_generation",
    should_continue,
    {
        "mcp_tool_call": "mcp_tool_call",
        "end": END,  # Explicit end path
    },
)
# builder.add_edge("mcp_tool_call", "final_report_generation")

final_report_graph = builder.compile(name="Final Report Generation")
