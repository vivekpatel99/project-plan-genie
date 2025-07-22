"""Research Agent Subgraph."""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, filter_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .configuration import Configuration
    from .prompts import COMPRESS_RESEARCH_SIMPLE_HUMAN_MESSAGE, COMPRESS_RESEARCH_SYSTEM_PROMPT
    from .states import ResearcherOutputState, ResearchState, StatesKeys
    from .utils import (
        execute_tool_safely,
        get_all_tools,
        get_today_str,
        is_token_limit_exceeded,
        openai_websearch_called,
        remove_up_to_last_ai_message,
    )
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.prompts import COMPRESS_RESEARCH_SIMPLE_HUMAN_MESSAGE, COMPRESS_RESEARCH_SYSTEM_PROMPT
    from src.agent.states import ResearcherOutputState, ResearchState, StatesKeys
    from src.agent.utils import (
        execute_tool_safely,
        get_all_tools,
        get_today_str,
        is_token_limit_exceeded,
        openai_websearch_called,
        remove_up_to_last_ai_message,
    )

# Initialize a configurable model that we will use throughout the agent
researcher_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def research_agent(
    state: ResearchState,
    config: RunnableConfig,
) -> Command[Literal["research_tools"]]:
    """
    Research Agent.

    This agent is responsible for generating a research report given some messages
    about the topic.

    The agent will continue to call the research model until it has finished.

    The agent will continue to call the research model until one of the
    following conditions are met:

    1. The research model returns a ResearchComplete tool call.
    2. The number of research iterations exceeds the maximum number of
       iterations specified in the configuration.
    """
    config = Configuration.from_runnable_config(config)
    research_msgs = state.get(StatesKeys.RESEARCH_MSGS.value, [])
    tools = await get_all_tools(config)

    if len(tools) <= 1:  # ResearchComplete is default tool in the list
        msg = "No tools found to conduct research, please configure Search API"
        raise ValueError(msg)

    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
    }

    research_model = (
        researcher_model.bind_tools(
            tools,
        )
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(research_model_config)
    )

    response = await research_model.ainvoke(
        research_msgs,
    )

    return Command(
        goto="research_tools",
        update={
            StatesKeys.RESEARCH_MSGS.value: [response],
            StatesKeys.TOOL_CALL_ITERATIONS.value: state.get(StatesKeys.TOOL_CALL_ITERATIONS.value, 0) + 1,
        },
    )


async def research_tools(
    state: ResearchState,
    config: RunnableConfig,
) -> Command[Literal["compress_research", "research_agent"]]:
    """
    Execute tools and gather results.

    If no tool calls were made (or only native web search calls), then immediately go to compress_research.
    Otherwise, execute each tool call and gather the results.
    If we have exceeded our max guardrail tool call iterations or the most recent message contains ResearchComplete tool call, then go to compress_research.
    Otherwise, go back to research_agent.
    """
    config = Configuration.from_runnable_config(config)
    research_msgs = state.get(StatesKeys.RESEARCH_MSGS.value, [])
    most_recent_message = research_msgs[-1]

    # Early exit Criteria: No tools calls (or native web search calls) were made by the researcher
    if not most_recent_message.tool_calls and not openai_websearch_called(most_recent_message):
        return Command(goto="compress_research")

    # Otherwise, execute tools and gather results
    tools = await get_all_tools(config)

    tools_by_name = {tool.name if hasattr(tool, "name") else tool.get("name", "web_search"): tool for tool in tools}

    tool_calls = most_recent_message.tool_calls

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
    # Late Exit Criteria: We have exceeded our max guardrail tool call iterations or the most recent message contains ResearchComplete tool call
    # These are late exit criteria because we need to add ToolMessage
    update = {StatesKeys.RESEARCH_MSGS.value: tool_outputs}
    if state.get(StatesKeys.TOOL_CALL_ITERATIONS.value, 0) >= config.max_react_tool_calls or any(
        tool_call["name"] == "ResearchComplete" for tool_call in tool_calls
    ):
        return Command(
            goto="compress_research",
            update=update,
        )
    return Command(goto="research_agent", update=update)


async def compress_research(state: ResearchState, config: RunnableConfig) -> dict[str : str | list[str]]:
    """
    Compress research messages into a concise report.

    This function attempts to synthesize research messages into a compressed
    format using a configured compression model. It updates the system prompts
    for compression and retries the synthesis process until successful or the
    maximum number of attempts is reached. If successful, it returns a dictionary
    containing the compressed research and raw notes. If it fails due to token
    limits or other errors, it will prune messages and retry, or ultimately
    return an error message.

    Args:
        state (ResearchState): The current state of the research process,
            containing past messages and other relevant data.
        config (RunnableConfig): Configuration parameters for the compression
            model, including model type, max tokens, and the number of synthesis
            attempts.

    Returns:
        dict[str, str | list[str]]: A dictionary with keys for the compressed
        research content and raw notes, or an error message if synthesis fails.

    """
    config = Configuration.from_runnable_config(config)
    synthesize_attempts = 0
    compression_model = researcher_model.with_config(
        {
            "model": config.compression_model,
            "max_tokens": config.compression_model_max_tokens,
            # "api_key": config.compress_model_api_key,
        },
    )
    researcher_msgs = state.get(StatesKeys.RESEARCH_MSGS.value, [])

    # Update the system prompts to now focus on compression rather than research
    researcher_msgs[0] = SystemMessage(
        content=COMPRESS_RESEARCH_SYSTEM_PROMPT.format(date=get_today_str()),
    )
    researcher_msgs.append(HumanMessage(content=COMPRESS_RESEARCH_SIMPLE_HUMAN_MESSAGE))
    while synthesize_attempts < config.compression_attempts:
        try:
            response = await compression_model.ainvoke(
                researcher_msgs,
            )
            return {
                StatesKeys.COMPRESSED_RESEARCH.value: str(response.content),
                StatesKeys.RAW_NOTES.value: [
                    "\n".join(
                        [str(m.content) for m in filter_messages(researcher_msgs, include_types=["tool", "ai"])],
                    ),
                ],
            }
        except Exception as e:
            # import traceback

            # print(e, traceback.format_exc())
            synthesize_attempts += 1
            if is_token_limit_exceeded(e, config.research_model):
                researcher_msgs = remove_up_to_last_ai_message(researcher_msgs)
                print(f"Token limit exceeded while synthesizing: {e}. Pruning the messages to try again.")
                continue
            print(f"Error synthesizing research report: {e}")
    return {
        StatesKeys.COMPRESSED_RESEARCH.value: "Error synthesizing research report: Maximum retries exceeded",
        StatesKeys.RAW_NOTES.value: [
            "\n".join([str(m.content) for m in filter_messages(researcher_msgs, include_types=["tool", "ai"])]),
        ],
    }


research_builder = StateGraph(ResearchState, output_schema=ResearcherOutputState, config_schema=Configuration)
research_builder.add_node("research_agent", research_agent)
research_builder.add_node("research_tools", research_tools)
research_builder.add_node("compress_research", compress_research)

research_builder.add_edge(START, "research_agent")
research_builder.add_edge("compress_research", END)
researcher_subgraph = research_builder.compile(name="Research Agent")
