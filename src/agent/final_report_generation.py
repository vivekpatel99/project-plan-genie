import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.func import END, Any, CachePolicy
from langgraph.graph import START, StateGraph
from langgraph.types import Command, interrupt
from loguru import logger

try:
    from .configuration import Configuration
    from .mcp_tool_service import MCPToolService
    from .prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE, TOOL_MANAGER_PROMPT
    from .states import ReportGeneratorState, StatesKeys
    from .utils import execute_tool_safely, get_today_str
except ImportError:
    # rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.mcp_tool_service import MCPToolService
    from src.agent.prompts import SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE, TOOL_MANAGER_PROMPT
    from src.agent.states import ReportGeneratorState, StatesKeys
    from src.agent.utils import execute_tool_safely, get_today_str

protected_tools: tuple[str] = (
    "create_directory",
    "edit_file",
    "move_file",
    "write_file",
)
# https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
mcp_tool_service = MCPToolService()


@logger.catch
async def final_report_generation(
    state: ReportGeneratorState,
    config: RunnableConfig,
) -> Command[Literal["tool_manager"]]:
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

    # Initialize a configurable model that we will use throughout the agent
    model_shell = init_chat_model(
        configurable_fields=("model", "max_tokens"),
    )

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
                goto="tool_manager",
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


# @logger.catch
# async def get_mcp_tools_node(
#     state: ReportGeneratorState,
#     config: RunnableConfig,  #
# ) -> Command[Literal["tool_manager"]]:
#     """
#     Get all the available tools on the MCP servers.

#     Args:
#         state (Report generation state): Unused
#         config (Runnable configuration): Unused

#     Returns:
#         list[ToolMessage]: List of all available tools

#     Note: The parameters 'state' and 'config' are not used in this implementation but kept to satisfy langgraph requirements

#     """
#     logger.info("Getting MCP tools...")
#     client = MultiServerMCPClient(connections=mcp_config["mcpServers"])
#     tools = await client.get_tools()
#     tools_by_name = {tool.name: tool for tool in tools if hasattr(tool, "name")}

#     return Command(goto="tool_manager", update={"mcp_tools": tools, "mcp_tools_by_name": tools_by_name})


@logger.catch
async def tool_manager(state: ReportGeneratorState, config: RunnableConfig) -> dict[str, Any]:  # | Command[str]:
    """Tool manager to handle the execution of tools. It has single responsibility to save the markdown report into .md file with given format."""
    logger.info("Tool manager invoked.")

    final_report = state.get(StatesKeys.FINAL_REPORT.value)
    tool_manager_messages = state.get(StatesKeys.TOOL_MANAGER_MESSAGES.value, [])

    config = Configuration.from_runnable_config(config)

    # Initialize a configurable model that we will use throughout the agent
    model_shell = init_chat_model(
        configurable_fields=("model", "max_tokens"),
    )

    mcp_tool_manager_config = {
        "model": config.mcp_tool_manager_model,
        "max_tokens": config.mcp_tool_manager_max_tokens,
    }
    logger.info("Configuration for tool manager: {}", config)

    max_retries: int = 3
    current_retry: int = 0

    # Get actual tools from the service
    tools, _ = await mcp_tool_service.get_tools()
    tool_manager_model = (
        model_shell.bind_tools(tools)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(mcp_tool_manager_config)
    )
    prompt = f"""Conversation history:
    <messages>
    {get_buffer_string(tool_manager_messages)}
    </messages>
    here is the final report \n{final_report}"""
    while current_retry <= max_retries:
        try:
            response = await tool_manager_model.ainvoke([HumanMessage(content=prompt)])

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
    _, tools_by_name = await mcp_tool_service.get_tools()

    last_message = messages[-1]
    tool_calls = last_message.tool_calls

    # Execute tools step by step, because directory must be created first and the file creation
    tool_results = [
        await execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config.model_dump())
        for tool_call in tool_calls
    ]

    tool_outputs: list[ToolMessage] = [
        ToolMessage(
            content=f"Successfully executed {tool_call['name']}: {result}",
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        for result, tool_call in zip(tool_results, tool_calls, strict=True)
    ]
    # Go back to tool manager with tool results
    return Command(
        goto="tool_manager",
        update={
            StatesKeys.TOOL_MANAGER_MESSAGES.value: tool_outputs,
        },
    )


async def should_continue(state: ReportGeneratorState) -> Literal["human_tool_review_node", "mcp_tool_call", "__end__"]:
    logger.info("[INFO] Checking if we should continue...")
    messages = state.get(StatesKeys.TOOL_MANAGER_MESSAGES.value, [])

    last_message = messages[-1]
    # Check if it's an AI message with tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        if any(tool_call["name"] in protected_tools for tool_call in last_message.tool_calls):
            logger.info("Going to human_tool_review_node: last_message.tool_calls: ")
            return "human_tool_review_node"

        logger.info("Directly going to mcp_tool_call because tool calls are not protected")
        return "mcp_tool_call"

    print("[INFO] No tool calls found, going to __end__")
    return "__end__"


async def human_tool_review_node(
    state: ReportGeneratorState,
) -> Command[Literal["mcp_tool_call", "tool_manager"]]:
    """Node is a placeholder for the human to review the final report generation process to verify proper tool call checks before tools are called by the agent."""
    print("[INFO] human_tool_review_node called")
    last_message = state[StatesKeys.TOOL_MANAGER_MESSAGES.value][-1]

    # Ensure we have a valid AI message with tool calls
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        msg = "human_tool_review_node called without valid tool calls"
        logger.error(msg)
        raise ValueError(msg)

    tool_calls = list(last_message.tool_calls)
    # Stop graph execution and wait for human input
    human_review: dict = interrupt(
        {
            "message": r"Your input is required for the following tool and your response must be in json format such as {'action': 'accept'} or {'feedback':'wrong toll call'}",
            "tool_calls": tool_calls,
        },
    )
    review_action = human_review.get("action")

    if review_action == "accept":
        return Command(
            goto="mcp_tool_call",
        )

    human_feedback = human_review.get("feedback")

    tagged_feedback = f"""HUMAN INTERVENTION: The user has rejected this tool call and provided new instructions.
    User feedback: {human_feedback}
    **IMPORTANT**: You must follow the user's instructions exactly. Do not repeat the rejected tool calls. Adapt your approach based on the feedback provided."""

    # Create the ToolMessage with the tagged content.
    tool_messages: list[ToolMessage] = [
        ToolMessage(
            tagged_feedback,
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        for tool_call in tool_calls
    ]
    return Command(
        goto="tool_manager",
        update={
            StatesKeys.TOOL_MANAGER_MESSAGES.value: tool_messages,
        },
    )


builder = StateGraph(ReportGeneratorState, config_schema=Configuration)
builder.add_node("final_report_generation", final_report_generation, cache_policy=CachePolicy())
builder.add_node("human_tool_review_node", human_tool_review_node)
builder.add_node("tool_manager", tool_manager)  # , cache_policy=CachePolicy())
builder.add_node("mcp_tool_call", mcp_tool_call)

builder.add_edge(START, "final_report_generation")
builder.add_conditional_edges(
    "tool_manager",
    should_continue,
    {
        "human_tool_review_node": "human_tool_review_node",
        "mcp_tool_call": "mcp_tool_call",
        "__end__": END,
    },
)


final_report_graph = builder.compile(name="Final Report Generation")
# {"action": "", "feedback": "No need to create directory, just save the file in root directory"}
