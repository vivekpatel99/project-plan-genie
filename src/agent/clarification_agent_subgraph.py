"""Clarification Agent Subgraph."""

from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, get_buffer_string
from langchain_core.runnables import RunnableConfig
from langgraph.func import START
from langgraph.graph import END, StateGraph
from langgraph.types import Command
from loguru import logger

try:
    from .configuration import Configuration
    from .prompts import (
        CLARIFY_WITH_USER_INSTRUCTIONS,
        LEAD_RESEARCHER_PROMPT,
        TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT,
    )
    from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
    from .utils import get_today_str
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.prompts import (
        CLARIFY_WITH_USER_INSTRUCTIONS,
        LEAD_RESEARCHER_PROMPT,
        TRANSFORM_MESSAGES_INTO_RESEARCH_TOPIC_PROMPT,
    )
    from src.agent.states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys
    from src.agent.utils import get_today_str

# Initialize a configurable model that we will use throughout the agent
clarification_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "model_provider"),
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
    logger.info("Clarifying with user...")
    config = Configuration.from_runnable_config(config)
    logger.debug("Configuration for clarification: {}", config)
    if not config.allow_clarification:
        return Command(goto="write_research_brief")

    messages = state[StatesKeys.MSGS.value]
    model_config = {
        "model": config.clarification_model,
        "max_tokens": config.clarification_model_max_tokens,
        "name": "Genie",
        # "api_key": config.clarification_model_api_key,
    }
    logger.debug("Model configuration for clarification: {}", model_config)
    model = (
        clarification_model.with_structured_output(ClarifyWithUser)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(model_config)
    )
    synthesize_attempts = 0
    while synthesize_attempts < config.clarification_attempts:
        try:
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
                logger.info("User needs clarification.")
                return Command(
                    goto=END,
                    update={
                        StatesKeys.MSGS.value: [*messages, AIMessage(content=response.question)],
                    },
                )
            logger.info("User does not need clarification.")
            break
        except Exception as e:
            logger.error(e)
            synthesize_attempts += 1
            logger.warning("Attempts: " + str(synthesize_attempts) + ". Retrying...")
            print("Attempts: " + str(synthesize_attempts) + ". Retrying...")
            if synthesize_attempts == config.clarification_attempts:
                logger.error("Failed to synthesize response after " + str(synthesize_attempts) + " attempts.")
                raise
    logger.info("Clarification complete, proceeding to write research brief.")
    return Command(
        goto="write_research_brief",
        update={
            StatesKeys.MSGS.value: [*messages, AIMessage(content=response.verification)],
        },
    )


async def write_research_brief(state: AgentState, config: RunnableConfig) -> Command[Literal["supervisor_subgraph"]]:
    """Create the research brief from previous conversations to prepare for research."""
    logger.info("Writing research brief...")
    config = Configuration.from_runnable_config(config)
    logger.debug("Configuration for writing research brief: {}", config)
    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
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
    logger.debug("Research brief created: {}", response.research_brief)
    logger.info("Proceeding to supervisor subgraph for further processing.")
    return Command(
        goto="supervisor_subgraph",
        update={
            StatesKeys.RESEARCH_BRIEF.value: response.research_brief,
            StatesKeys.SUPERVISOR_MSGS.value: [
                SystemMessage(
                    content=LEAD_RESEARCHER_PROMPT.format(
                        date=get_today_str(),
                        max_concurrent_research_units=config.max_concurrent_research_units,
                    ),
                ),
                HumanMessage(content=response.research_brief),
            ],
        },
    )


clarify_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
    context_schema=Configuration,
)

clarify_builder.add_node("clarify_with_user", clarify_with_user)
clarify_builder.add_node("write_research_brief", write_research_brief)

clarify_builder.add_edge(START, "clarify_with_user")
clarify_builder.add_edge("clarify_with_user", "write_research_brief")
clarify_builder.add_edge("write_research_brief", END)

# clarify_subgraph = clarify_builder.compile(name="Clarify with User")
