"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

try:
    from model_provider_factory import ModelProviderFactory
    from prompts import ENDING_KEYWORD, PROJECT_CLARIFICATION_PROMPT
    from states import PlanningState

except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.prompts import ENDING_KEYWORD, PROJECT_CLARIFICATION_PROMPT
    from src.agent.providers.model_provider_factory import ModelProviderFactory
    from src.agent.states import PlanningState

thread = {"configurable": {"thread_id": "1"}}
memory = MemorySaver()
llm = ModelProviderFactory.get_model_provider("openai", {"model_name": "gpt-4o"})


def ask_question_by_agent(state: PlanningState) -> PlanningState:
    """Call the info gathering agent to gather information about the project. who will ask question to user."""
    print("[INFO] calling info gathering agent...")
    messages_history = state["messages"]
    project_desc = state["project_description"]

    prompt = PROJECT_CLARIFICATION_PROMPT.format(
        project_description=project_desc, ending_keyword=ENDING_KEYWORD
    )

    response = llm.invoke([SystemMessage(content=prompt)] + messages_history)

    return {"messages": response}


def answer_question_by_user(state: PlanningState) -> PlanningState:
    """User will answer/reply the questions asked by the info gathering agent."""
    print("[INFO] waiting for user reply...")
    user_reply = interrupt({"messages": state["messages"][-1].content})
    print("user reply has been received!")
    return {"messages": state["messages"] + [user_reply]}


def route_messages_btn_user_end(state: PlanningState) -> PlanningState:
    """Run after each question - answer pair."""
    # Get messages
    messages = state["messages"]

    # Get the last question asked to check if it signals the end of discussion
    last_question = messages[-1].content
    if ENDING_KEYWORD.lower() in last_question.lower():
        print("[INFO] end of discussion reached!")
        return "end"
    return "to_user"


builder = StateGraph(PlanningState)  # , config_schema=Configuration)

# Nodes
builder.add_node("ask_question_by_agent", ask_question_by_agent)
builder.add_node("answer_question_by_user", answer_question_by_user)

# Edges
builder.add_edge(START, "ask_question_by_agent")
builder.add_conditional_edges(
    "ask_question_by_agent",
    route_messages_btn_user_end,
    {
        "end": END,
        "to_user": "answer_question_by_user",
    },
)
builder.add_edge("answer_question_by_user", "ask_question_by_agent")


graph = builder.compile(
    # interrupt_before=["ask_user"],
    # checkpointer=memory,
    name="Information Gathering Agent",
)
