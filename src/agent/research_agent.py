"""Agent to understand conversation and user web tools or python to peform research."""

from langchain_community.document_loaders import WikipediaLoader
from langchain_core.messages import SystemMessage
from langchain_core.tools import Tool, tool
from langchain_experimental.utilities import PythonREPL
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

try:
    from prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS
    from providers.model_provider_factory import ModelProviderFactory
    from states import PlanningState, ResearchState, SearchQuery

except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.prompts import PROJECT_RESEARCH_AGENT_PROMPT, SEARCH_INSTRUCTIONS
    from src.agent.providers.model_provider_factory import ModelProviderFactory
    from src.agent.states import PlanningState, ResearchState, SearchQuery

thread = {"configurable": {"thread_id": "1"}}
memory = MemorySaver()
llm = ModelProviderFactory.get_model_provider("openai", {"model_name": "gpt-4o"})


def research_agent(state: PlanningState) -> PlanningState:
    """Understand conversation and user web tools or python to peform research."""
    print("[INFO] research_agent called")
    msg_history = state["messages"]
    system_msg = SystemMessage(PROJECT_RESEARCH_AGENT_PROMPT)

    result = llm_with_tools.invoke([system_msg] + msg_history + state["project_plan"])
    return {"result": [result]}


@tool
def search_web(state: PlanningState) -> PlanningState:
    """Retrieve docs from the web."""
    print("[INFO] search_web tool called")
    structured_llm = llm.with_structured_output(SearchQuery)
    search_query: SearchQuery = structured_llm.invoke(
        [SEARCH_INSTRUCTIONS] + state["messages"]
    )
    tavily_search = TavilySearch(max_results=3)
    search_docs = tavily_search.invoke(search_query.query)
    # format
    formatted_search_docs = [
        f"""<Document href='{doc["url"]}'messages/>\n{doc["content"]}\n<Document>"""
        for doc in search_docs
    ]

    return {"project_plan": [formatted_search_docs]}


@tool
def search_wikipedia(state: PlanningState) -> PlanningState:
    """Retrieve docs from Wikipedia."""
    print("[INFO] search_wikipedia tool called")
    structured_llm = llm.with_structured_output(SearchQuery)
    search_query: SearchQuery = structured_llm.invoke(
        [SystemMessage(SEARCH_INSTRUCTIONS)] + state["messages"]
    )
    search_docs = WikipediaLoader(
        query=search_query.search_query, load_max_docs=2
    ).load()
    # format
    formatted_search_docs = [
        f"""<Document href='{doc["url"]}'/>\n{doc["content"]}\n<Document>"""
        for doc in search_docs
    ]

    state.project_plan = [formatted_search_docs]
    return {"project_plan": [formatted_search_docs]}


python_repl = PythonREPL()
# You can create the tool to pass to an agent
repl_tool = Tool(
    name="python_repl",
    description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
    func=python_repl.run,
)
TOOLS = [search_wikipedia, search_wikipedia, repl_tool]

llm_with_tools = llm.bind_tools(TOOLS)

research_agent_graph = StateGraph(
    state_schema=PlanningState, output_schema=ResearchState
)

research_agent_graph.add_node("research_agent", research_agent)
research_agent_graph.add_node("tools", ToolNode(TOOLS))

research_agent_graph.add_edge(START, "research_agent")
research_agent_graph.add_conditional_edges("research_agent", tools_condition)
research_agent_graph.add_edge("tools", "research_agent")


graph = research_agent_graph.compile(
    # checkpointer=memory,
    name="Research Agent",
)
