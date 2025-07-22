"""Clarification Agent Subgraph."""

from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

try:
    from .configuration import Configuration
    from .prompts import CLARIFY_WITH_USER_INSTRUCTIONS, TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT
    from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys

    # from .supervisor_agent import supervisor_subgraph
    from .utils import get_today_str
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.prompts import CLARIFY_WITH_USER_INSTRUCTIONS, TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT
    from src.agent.states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys

    # from src.agent.supervisor_agent import supervisor_subgraph
    from src.agent.utils import get_today_str

# Initialize a configurable model that we will use throughout the agent
clarification_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def clarify_with_user(
    state: AgentState,
    config: RunnableConfig,
) -> Command[Literal["write_research_brief", "__end__"]]:
    """
    Clarify the user's project idea through interaction.

    This function engages with the user to clarify their project description,
    ensuring all necessary details are gathered before moving to the research phase.
    If clarification is not allowed by the configuration, it directly proceeds to
    writing the research brief.

    Args:
        state (AgentState): The current state containing messages exchanged with the user.
        config (RunnableConfig): Configuration parameters determining model and clarification settings.

    Returns:
        Command: An instruction indicating the next step, either updating the messages for further clarification
        or proceeding to write the research brief.

    """
    config = Configuration.from_runnable_config(config)

    if not config.allow_clarification:
        return Command(goto="write_research_brief")

    messages = state[StatesKeys.MSGS.value]
    model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
    }
    model = (
        clarification_model.with_structured_output(ClarifyWithUser)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(model_config)
    )
    response: ClarifyWithUser = await model.ainvoke(
        [
            HumanMessage(
                content=CLARIFY_WITH_USER_INSTRUCTIONS.format(
                    messages=get_buffer_string(messages),
                    date=get_today_str(),
                ),
            ),
        ],
    )
    if response.need_clarification:
        return Command(
            goto=END,
            update={
                StatesKeys.MSGS.value: [*messages, AIMessage(content=response.question)],
            },
        )

    return Command(
        goto="write_research_brief",
        update={
            StatesKeys.MSGS.value: [*messages, AIMessage(content=response.verification)],
        },
    )


async def write_research_brief(state: AgentState, config: RunnableConfig) -> Command[Literal["supervisor_subgraph"]]:
    """Create the research brief from previous conversations to prepare for research."""
    config = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
    }
    research_model = (
        clarification_model.with_structured_output(ResearchQuestion)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(research_model_config)
    )
    response: ResearchQuestion = await research_model.ainvoke(
        [
            HumanMessage(
                content=TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT.format(
                    messages=get_buffer_string(state.get(StatesKeys.MSGS.value, [])),
                    date=get_today_str(),
                ),
            ),
        ],
    )
    return Command(
        goto="supervisor_subgraph",
        update={
            StatesKeys.RESEARCH_BRIEF.value: response.research_brief,
        },
    )


# clarify_builder = StateGraph(
#     AgentState,
#     input_schema=AgentInputState,
#     config_schema=Configuration,
# )

# clarify_builder.add_node("clarify_with_user", clarify_with_user)
# clarify_builder.add_node("write_research_brief", write_research_brief)

# clarify_builder.add_edge(START, "clarify_with_user")
# # clarify_builder.add_edge("clarify_with_user", "write_research_brief")
# # clarify_builder.add_edge("write_research_brief", END)

# clarify_subgraph = clarify_builder.compile(name="Clarify with User")
