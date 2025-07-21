"""Clarification Agent Subgraph."""

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from agent.states import StatesKeys

try:
    from .configuration import Configuration
    from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys

except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration
    from src.agent.prompts import CLARIFY_WITH_USER_INSTRUCTIONS
    from src.agent.states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion, StatesKeys


transform_messages_into_research_topic_prompt = """You will be given a set of messages that have been exchanged so far between yourself and the user.
Your job is to translate these messages into a more detailed and concrete research question that will be used to guide the research.
The messages that have been exchanged so far between yourself and the user are:
<Messages>
{messages}
</Messages>
You will return a single research question that will be used to guide the research.
Guidelines:
1. Maximize Specificity and Detail
- Include all known user preferences and explicitly list key attributes or dimensions to consider.
- It is important that all details from the user are included in the instructions.

2. Fill in Unstated But Necessary Dimensions as Open-Ended
- If certain attributes are essential for a meaningful output but the user has not provided them, explicitly state that they are open-ended or default to no specific constraint.

3. Avoid Unwarranted Assumptions
- If the user has not provided a particular detail, do not invent one.
- Instead, state the lack of specification and guide the researcher to treat it as flexible or accept all possible options.

4. Use the First Person
- Phrase the request from the perspective of the user.

5. Sources
- If specific sources should be prioritized, specify them in the research question.
- For academic or scientific queries, prefer linking directly to the original paper or official journal publication rather than survey papers or secondary summaries.
"""
# Initialize a configurable model that we will use throughout the agent
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def clarify_with_user(state: AgentState, config: RunnableConfig):
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
        configurable_model.with_structured_output(ClarifyWithUser)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(model_config)
    )
    response: ClarifyWithUser = await model.ainvoke(
        [
            HumanMessage(
                content=CLARIFY_WITH_USER_INSTRUCTIONS.format(
                    messages=get_buffer_string(messages),
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


async def write_research_brief(state: AgentState, config: RunnableConfig):
    """Create the research brief from previous conversations to prepare for research."""
    config = Configuration.from_runnable_config(config)
    research_model_config = {
        "model": config.research_model,
        "max_tokens": config.research_model_max_tokens,
        # "api_key": config.research_model_api_key,
    }
    research_model = (
        configurable_model.with_structured_output(ResearchQuestion)
        .with_retry(stop_after_attempt=config.max_structured_output_retries)
        .with_config(research_model_config)
    )
    response: ResearchQuestion = await research_model.ainvoke(
        [
            HumanMessage(
                content=transform_messages_into_research_topic_prompt.format(
                    messages=get_buffer_string(state.get(StatesKeys.MSGS.value, [])),
                ),
            ),
        ],
    )
    return Command(
        goto=END,
        update={
            StatesKeys.RESEARCH_BRIEF.value: response.research_brief,
        },
    )


clarify_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
    config_schema=Configuration,
)

clarify_builder.add_node("clarify_with_user", clarify_with_user)
clarify_builder.add_node("write_research_brief", write_research_brief)

clarify_builder.add_edge(START, "clarify_with_user")
clarify_builder.add_edge("clarify_with_user", "write_research_brief")
clarify_builder.add_edge("write_research_brief", END)

clarify_subgraph = clarify_builder.compile(name="Clarify with User")
