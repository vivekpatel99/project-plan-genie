import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.func import END
from langgraph.graph import START, StateGraph
from langgraph.types import Command
from loguru import logger

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
# loop = asyncio.new_event_loop()  # 1️⃣ make a loop for this thread
# tools = loop.run_until_complete(client.get_tools())  # 2️⃣ run the async call
# loop.close()


class ReportGenerated:
    """Call this tool to indicate that the Report generation is successfully completed."""


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
    # Initialize a configurable model that we will use throughout the agent
    model_shell = init_chat_model(
        configurable_fields=("model", "max_tokens"),
    )

    notes = state.get(StatesKeys.NOTES.value, [])
    config = Configuration.from_runnable_config(config)
    report_generator_config = {
        "model": config.final_report_generation_model,
        "max_tokens": config.final_report_generation_model_max_tokens,
    }
    print("################### notes", notes)
    findings = "\n".join(notes)

    max_retries: int = 3
    current_retry: int = 0
    tools = await client.get_tools()
    research_brief = state[StatesKeys.RESEARCH_BRIEF.value]
    while current_retry <= max_retries:
        final_report_prompt = SYSTEM_PROMPT_PROJECT_PLAN_STRUCTURE.format(
            research_brief=research_brief,
            findings=findings,
            date=get_today_str(),
            messages=get_buffer_string(state.get(StatesKeys.MSGS.value, [])),
        )
        try:
            report_generator_model = model_shell.bind_tools(tools)

            report_generator_model = report_generator_model.with_retry(
                stop_after_attempt=config.max_structured_output_retries,
            )

            report_generator_model = report_generator_model.with_config(report_generator_config)

            response = await report_generator_model.ainvoke(
                [
                    HumanMessage(content=final_report_prompt),
                ],
            )

            # msgs.append(response)
            print("################### report_generator_model", response)
            logger.info("Final report generated: {}", response)
            return {  # noqa: TRY300
                StatesKeys.FINAL_REPORT.value: response.content,
                StatesKeys.MSGS.value: response,
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
    print("######## Tool Calls: {}", tool_calls)
    print("######## Tools: {}", tools_by_name)
    async_responses = [
        execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config.model_dump())
        for tool_call in tool_calls
    ]
    observations = await asyncio.gather(*async_responses)
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        for observation, tool_call in zip(observations, tool_calls, strict=False)
    ]
    print("######## tool_outputs: {}", tool_outputs)
    print(f"tools messages {[tools_msg.content for tools_msg in tool_outputs]}")
    return Command(
        goto="final_report_generation",
        update={
            StatesKeys.MSGS.value: tool_outputs,
            # StatesKeys.NOTES.value: state.get(StatesKeys.NOTES.value, [])
            # + [tools_msg.content for tools_msg in tool_outputs],
        },
    )


# Ensure your state uses "messages" key if using prebuilt tools_condition
async def should_continue(state: AgentState) -> str:
    messages = state.get(StatesKeys.MSGS.value, [])
    if messages and hasattr(messages[-1], "tool_calls"):
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

final_report_graph = builder.compile(name="Final Report Generation")
