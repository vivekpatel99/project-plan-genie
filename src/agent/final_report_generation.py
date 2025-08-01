import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.func import END
from langgraph.graph import START, StateGraph
from langgraph.types import Command
from loguru import logger

try:
    from .configuration import Configuration
    from .my_mcps import mcp_config
    from .prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE, TOOL_MANAGER_PROMPT
    from .states import ReportGeneratorState, StatesKeys
    from .utils import execute_tool_safely, get_today_str
except ImportError:
    # rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.my_mcps import mcp_config
    from src.agent.prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE, TOOL_MANAGER_PROMPT
    from src.agent.states import ReportGeneratorState, StatesKeys
    from src.agent.utils import execute_tool_safely, get_today_str

protected_tools: list[str] = ["create_directory", "write_file"]

# https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem


# Initialize a configurable model that we will use throughout the agent
model_shell = init_chat_model(
    configurable_fields=("model", "max_tokens"),
)


@logger.catch
async def final_report_generation(
    state: ReportGeneratorState,
    config: RunnableConfig,
) -> Command[Literal["get_mcp_tools_node"]]:
    """
    Generate final report from the  research notes and findings.

    Takes in a state and config and generates a final report by calling
    the report generator model. If the model fails to generate a report, it retries
    up to `max_retries` times before giving up and returning an error message.
    """
    logger.info("Generating final report...")
    notes = state.get(StatesKeys.NOTES.value, [])
    messages = state.get(StatesKeys.MSGS.value, [])

    research_brief = state[StatesKeys.RESEARCH_BRIEF.value]

    config = Configuration.from_runnable_config(config)
    report_generator_config = {
        "model": config.final_report_generation_model,
        "max_tokens": config.final_report_generation_model_max_tokens,
    }

    findings = "\n".join(note.content if hasattr(note, "content") else str(note) for note in notes)

    max_retries: int = 3
    current_retry: int = 0

    final_report_prompt = SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE.format(
        research_brief=research_brief,
        findings=findings,
        date=get_today_str(),
        messages=get_buffer_string(messages),
    )
    report_generator_model = model_shell.with_retry(
        stop_after_attempt=config.max_structured_output_retries,
    ).with_config(report_generator_config)

    last_exception = None
    while current_retry <= max_retries:
        try:
            response = await report_generator_model.ainvoke([HumanMessage(content=final_report_prompt)])

            logger.info("Final report generated: {}", response)
            return Command(
                goto="get_mcp_tools_node",
                update={
                    StatesKeys.TOOL_MANAGER_MESSAGES.value: [
                        SystemMessage(content=TOOL_MANAGER_PROMPT),
                    ],
                    StatesKeys.FINAL_REPORT.value: response.content,
                },
            )
        except Exception as e:
            last_exception = e
            current_retry += 1
            logger.warning(f"Attempt {current_retry} to generate report failed: {e}")
            if current_retry <= max_retries:
                await asyncio.sleep(2)  # Small delay before retrying

    error = f"Error generating final report: Maximum retries exceeded, Last error: {last_exception}"
    return Command(
        goto=END,
        update={
            StatesKeys.FINAL_REPORT.value: error,
        },
    )


async def get_mcp_tools_node(
    state: ReportGeneratorState,  # noqa: ARG001
    config: RunnableConfig,  # # noqa: ARG001
) -> Command[Literal["tool_manager"]]:
    """
    Get all the available tools on the MCP servers.

    Args:
        state (Report generation state): Unused
        config (Runnable configuration): Unused

    Returns:
        list[ToolMessage]: List of all available tools

    Note: The parameters 'state' and 'config' are not used in this implementation but kept to satisfy langgraph requirements

    """
    logger.info("Getting MCP tools...")
    client = MultiServerMCPClient(connections=mcp_config["mcpServers"])
    tools = await client.get_tools()
    tools_by_name = {tool.name: tool for tool in tools if hasattr(tool, "name")}

    return Command(goto="tool_manager", update={"mcp_tools": tools, "mcp_tools_by_name": tools_by_name})


@logger.catch
async def tool_manager(state: ReportGeneratorState, config: RunnableConfig):
    """Tool manager to handle the execution of tools. It has single responsibility to save the markdown report into .md file with given format."""
    logger.info("Tool manager invoked.")

    final_report = state.get(StatesKeys.FINAL_REPORT.value)
    tool_manager_messages = state.get(StatesKeys.TOOL_MANAGER_MESSAGES.value, [])

    config = Configuration.from_runnable_config(config)

    report_generator_config = {
        "model": config.final_report_generation_model,
        "max_tokens": config.final_report_generation_model_max_tokens,
    }
    logger.debug("Configuration for tool manager: {}", config)

    max_retries: int = 3
    current_retry: int = 0

    tools = state["mcp_tools"]
    _model = model_shell.bind_tools(tools)
    _model = _model.with_retry(stop_after_attempt=config.max_structured_output_retries)
    tool_manager_model = _model.with_config(report_generator_config)

    while current_retry <= max_retries:
        try:
            response = await tool_manager_model.ainvoke(
                [*tool_manager_messages, HumanMessage(content=f"here is the final report {final_report}")],
            )

            logger.debug("Tool Manager response:", response)
            return {  # noqa: TRY300
                StatesKeys.TOOL_MANAGER_MESSAGES.value: [response],
                StatesKeys.FINAL_REPORT.value: final_report,
            }

        except Exception as e:
            last_exception = e
            current_retry += 1
            logger.warning(f"Attempt {current_retry} to tool called failed: {e}")
            if current_retry <= max_retries:
                await asyncio.sleep(2)  # Small delay before retrying

    error = f"Error generating tool call: Maximum retries exceeded, Last error: {last_exception}"
    return Command(
        goto=END,
        update={
            StatesKeys.TOOL_MANAGER_MESSAGES.value: [AIMessage(content=error)],
        },
    )


@logger.catch
async def mcp_tool_call(state: ReportGeneratorState, config: RunnableConfig) -> Command[Literal["tool_manager"]]:
    """Call this tool to indicate that the Report generation is successfully completed."""
    logger.info("Running mcp_tool_call")
    # Get all tools
    # Initialize a configurable model that we will use throughout the agent
    messages = state.get(StatesKeys.TOOL_MANAGER_MESSAGES.value, [])
    config = Configuration.from_runnable_config(config)

    # tools = state["mcp_tools"]
    tools_by_name = state["mcp_tools_by_name"]

    last_message = messages[-1]
    tool_calls = last_message.tool_calls

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
    # Go back to tool manager with tool results
    return {
        StatesKeys.TOOL_MANAGER_MESSAGES.value: tool_outputs,
    }


async def should_continue(state: ReportGeneratorState) -> str:
    logger.info("Checking if we should continue...")
    messages = state.get(StatesKeys.TOOL_MANAGER_MESSAGES.value, [])
    if not messages:
        return "end"
    last_message = messages[-1]
    # Check if it's an AI message with tool calls
    if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
        logger.info("Going to mcp_tool_call: last_message.tool_calls: ")
        return "mcp_tool_call"
    return "end"


builder = StateGraph(ReportGeneratorState, config_schema=Configuration)
builder.add_node("final_report_generation", final_report_generation)
builder.add_node("get_mcp_tools_node", get_mcp_tools_node)
builder.add_node("tool_manager", tool_manager)
builder.add_node("mcp_tool_call", mcp_tool_call)

builder.add_edge(START, "final_report_generation")
builder.add_conditional_edges(
    "tool_manager",
    should_continue,
    {
        "mcp_tool_call": "mcp_tool_call",
        "end": END,
    },
)


final_report_graph = builder.compile(name="Final Report Generation")
