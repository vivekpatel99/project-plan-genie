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

try:
    from .configuration import Configuration
    from .states import AgentInputState, AgentState, ClarifyWithUser, ResearchQuestion

except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.configuration import Configuration

    # from src.agent.prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS
    from src.agent.states import (
        AgentInputState,
        AgentState,
        ClarifyWithUser,
        ResearchQuestion,
    )


clarify_with_user_instructions = """
You are an expert AI Software Architect and with more than 10 years of SW development and design experience. Your primary role is to analyze user's project description and interact with the user to gather all necessary details for their project idea. You are the initial point of contact and must ensure that the project idea and description is fully understood before it moves to the research phase.
These are the messages that have been exchanged so far from the user asking for the report:
<Messages>
{messages}
</Messages>

Assess whether you need to ask a clarifying question, or if the user has already provided enough information for you to start research.
IMPORTANT: If you can see in the messages history that you have already asked a clarifying question, you almost always do not need to ask another one. Only ask another question if ABSOLUTELY NECESSARY.

If there are acronyms, abbreviations, or unknown terms, ask the user to clarify.
If you need to ask a question, follow these guidelines:
- Be concise while gathering all necessary information
- Make sure to gather all the information needed to carry out the research task in a concise, well-structured manner.
- Use bullet points or numbered lists if appropriate for clarity. Make sure that this uses markdown formatting and will be rendered correctly if the string output is passed to a markdown renderer.

Respond in valid JSON format with these exact keys:
"need_clarification": boolean,
"question": "<question to ask the user to clarify the report scope>",
"verification": "<verification message that we will start research>"

If you need to ask a clarifying question, return:
"need_clarification": true,
"question": "<your clarifying question>",
"verification": ""

If you do not need to ask a clarifying question, return:
"need_clarification": false,
"question": "",
"verification": "<acknowledgement message that you will now start research based on the provided information>"

For the verification message when no clarification is needed:
- Acknowledge that you have sufficient information to proceed
- Briefly summarize the key aspects of what you understand from their request
- Confirm that you will now begin the research process
- Keep the message concise and professional
"""
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
    """Clarify with user."""
    config = Configuration.from_runnable_config(config)
    if not config.allow_clarification:
        return Command(goto="write_research_brief")
    messages = state["messages"]
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
    response = await model.ainvoke(
        [
            HumanMessage(
                content=clarify_with_user_instructions.format(
                    messages=get_buffer_string(messages),
                ),
            ),
        ],
    )
    if response.need_clarification:
        return Command(
            goto=END,
            update={
                "messages": [*messages, AIMessage(content=response.question)],
            },
        )

    return Command(
        goto="write_research_brief",
        update={
            "messages": [*messages, AIMessage(content=response.verification)],
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
                    messages=get_buffer_string(state.get("messages", [])),
                ),
            ),
        ],
    )
    return Command(
        goto=END,
        update={
            "research_brief": response.research_brief,
        },
    )


clarify_graph = StateGraph(
    AgentState,
    input_schema=AgentInputState,
    config_schema=Configuration,
)

clarify_graph.add_node("clarify_with_user", clarify_with_user)
clarify_graph.add_node("write_research_brief", write_research_brief)

clarify_graph.add_edge(START, "clarify_with_user")
clarify_graph.add_edge("clarify_with_user", "write_research_brief")
clarify_graph.add_edge("write_research_brief", END)

graph = clarify_graph.compile(name="Clarify with User")
