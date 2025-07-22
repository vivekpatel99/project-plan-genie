"""Supervisor Agent Subgraph."""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .configuration import Configuration
    from .prompts import RESEARCH_SYSTEM_PROMPT
    from .researcher_agent import researcher_subgraph
    from .states import ConductResearch, ResearchComplete, StatesKeys, SupervisorState
    from .utils import get_notes_from_tool_calls, is_token_limit_exceeded
except ImportError:
    import rootutils

    rootutils.setup_root(search_from=__file__, indicator=[".git", "pyproject.toml"], pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.prompts import RESEARCH_SYSTEM_PROMPT
    from src.agent.researcher_agent import researcher_subgraph
    from src.agent.states import ConductResearch, ResearchComplete, StatesKeys, SupervisorState
    from src.agent.utils import get_notes_from_tool_calls, is_token_limit_exceeded

# Initialize a configurable model that we will use throughout the agent
supervisor_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def supervisor(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor_tool"]]:
    """
    Supervisor agent.

    This agent is responsible for controlling the flow of research. It will
    repeatedly call the research model until it has finished.

    The agent will continue to call the research model until one of the
    following conditions are met:

    1. The research model returns a ResearchComplete tool call.
    2. The number of research iterations exceeds the maximum number of
       iterations specified in the configuration.
    """
    config = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
        # "tags": ["langsmith:nostream"],
    }

    lead_research_tool = [ConductResearch, ResearchComplete]
    research_model = (
        supervisor_model.bind_tools(lead_research_tool)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(
            research_model_config,
        )
    )
    supervisor_message = state.get(StatesKeys.SUPERVISOR_MSGS.value, [])
    response = await research_model.ainvoke(supervisor_message)
    return Command(
        goto="supervisor_tool",
        update={
            StatesKeys.SUPERVISOR_MSGS.value: [response],
            StatesKeys.RESEARCH_ITERATIONS.value: state.get(StatesKeys.RESEARCH_ITERATIONS.value, 0) + 1,
        },
    )


async def supervisor_tool(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor", "__end__"]]:
    """
    Supervisor tool.

    This function is called after supervisor has finished.
    1. If we have exceeded our max guardrail research  iteration, or
    2. No tool call were made by supervisor, or
    3. The most recent message contain a ResearchComplete tool call and there is only one tool call in the message.
    We go to __end__.

    Otherwise, we continue with research.
    We take all ConductResearch tool calls and:
    1. Limit total concurrent research units/calls to max_concurrent_research_units.
    2. Execute each tool call and gather the results.
    3. Handle any tool calls made > max_concurrent_research_units.
    4. Return to supervisor with the tool results.

    If there is an error in the reflection phase, then we go to __end__.
    """
    configurable = Configuration.from_runnable_config(config)
    supervisor_messages = state.get(StatesKeys.SUPERVISOR_MSGS.value, [])
    research_iterations = state.get(StatesKeys.RESEARCH_ITERATIONS.value, 0)
    most_recent_message = supervisor_messages[-1]

    # Exit Criteria
    # 1. we have exceeded our max guardrail research  iteration
    # 2. No tool call were made by supervisor
    # 3. The most recent message contain a ResearchComplete tool call and there is only one tool call in the message
    exceeded_allowed_iterations = research_iterations >= configurable.max_research_iterations
    no_tool_calls = not most_recent_message.tool_calls
    research_complete_tool_call = any(
        tool_call["name"] == "ResearchComplete" for tool_call in most_recent_message.tool_calls
    )
    if exceeded_allowed_iterations or no_tool_calls or research_complete_tool_call:
        return Command(
            goto=END,
            update={
                StatesKeys.NOTES.value: get_notes_from_tool_calls(supervisor_messages),
                StatesKeys.RESEARCH_BRIEF.value: state.get(StatesKeys.RESEARCH_BRIEF.value, ""),
            },
        )
    # otherwise, continue with research
    try:
        all_conduct_research = [
            tool_call for tool_call in most_recent_message.tool_calls if tool_call["name"] == "ConductResearch"
        ]
        # Limit total concurrent research units/calls
        conduct_research_calls = all_conduct_research[: configurable.max_concurrent_research_units]
        overflow_conduct_research_calls = all_conduct_research[configurable.max_concurrent_research_units :]

        coros = [
            researcher_subgraph.ainvoke(
                {
                    StatesKeys.RESEARCH_MSGS.value: [
                        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
                        HumanMessage(content=tool_call["args"][StatesKeys.RESEARCH_TOPIC.value]),
                    ],
                    StatesKeys.RESEARCH_TOPIC.value: tool_call["args"][StatesKeys.RESEARCH_TOPIC.value],
                },
                config,
            )
            for tool_call in conduct_research_calls
        ]
        tool_results = await asyncio.gather(*coros)
        tool_messages = [
            ToolMessage(
                content=observation.get(
                    StatesKeys.COMPRESSED_RESEARCH.value,
                    "Error synthesizing research report: Maximum retries exceeded",
                ),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
            for observation, tool_call in zip(tool_results, conduct_research_calls, strict=False)
        ]
        # Handle any tool calls made > max_concurrent_research_units
        for overflow_conduct_research_call in overflow_conduct_research_calls:
            tool_messages.append(
                ToolMessage(
                    content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units. Please try again with {configurable.max_concurrent_research_units} or fewer research units.",
                    name="ConductResearch",
                    tool_call_id=overflow_conduct_research_call["id"],
                ),
            )
        raw_notes_concat = "\n".join(
            ["\n".join(observation.get(StatesKeys.RAW_NOTES.value, [])) for observation in tool_results],
        )
        return Command(
            goto="supervisor",
            update={
                StatesKeys.SUPERVISOR_MSGS.value: tool_messages,
                StatesKeys.RAW_NOTES.value: [raw_notes_concat],
            },
        )
    except Exception as e:
        # import traceback

        # print(traceback.format_exc())
        if is_token_limit_exceeded(e, configurable.research_model):
            print(f"Token limit exceeded while reflecting: {e}")
        else:
            print(f"Other error in reflection phase: {e}")
        return Command(
            goto=END,
            update={
                StatesKeys.NOTES.value: get_notes_from_tool_calls(supervisor_messages),
                StatesKeys.RESEARCH_BRIEF.value: state.get(StatesKeys.RESEARCH_BRIEF.value, ""),
            },
        )


if __name__ == "__main__":
    supervisor_builder = StateGraph(SupervisorState, config_schema=Configuration)
    supervisor_builder.add_node("supervisor", supervisor)
    supervisor_builder.add_node("supervisor_tool", supervisor_tool)
    supervisor_builder.add_edge(START, "supervisor")
    # supervisor_builder.add_edge("supervisor_tool", END)
    supervisor_subgraph = supervisor_builder.compile(name="Supervisor")
