"""you should find best and simple solution for those questions."""

import rootutils
import streamlit as st
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langgraph.cache.memory import InMemoryCache
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

from frontend.utils import (  # noqa: E402
    final_report_generation_input,
    setup_logging,
    stream_graph_responses_test,
)

# from src.agent.project_planning_genie import agent_builder
from src.agent.final_report_generation import builder  # noqa: E402
from src.agent.states import ReportGeneratorState  # noqa: E402

# from src.agent.clarification_agent_subgraph import clarify_builder


@st.cache_resource
def get_graph() -> CompiledStateGraph:
    """Load and compile the graph, caching it for reuse."""
    checkpointer = MemorySaver()
    graph = builder.compile(
        name="Test Final Report Generation",
        checkpointer=checkpointer,
        cache=InMemoryCache(),
    )
    return graph


# ──────────────────────────────────────────────────────────────
# 1.  Page & persistent state
# ──────────────────────────────────────────────────────────────
st.title("Project Planning Genie 🧞‍♀️")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = False  # flag: waiting for approval
    st.session_state.interrupt_snapshot = None  # stores ThreadState obj

# ──────────────────────────────────────────────────────────────
# 2.  Re-display chat history
# ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ──────────────────────────────────────────────────────────────
# 3.  Build / load graph
# ──────────────────────────────────────────────────────────────
set_llm_cache(SQLiteCache(database_path=".langchain.db"))
setup_logging()

configurable = {"configurable": {"thread_id": "1"}}

graph = get_graph()
test_input = ReportGeneratorState(
    research_brief=final_report_generation_input["research_brief"],
    raw_notes=final_report_generation_input["raw_notes"],
    notes=final_report_generation_input["notes"],
    # The final_report is an output field, so we initialize it as empty.
    final_report="",
    # The tool manager parts are also needed for the final_report_graph state.
    tool_manager_messages=[],
    mcp_tools=[],
    mcp_tools_by_name={},
    tool_call_tracker={},
)

# ──────────────────────────────────────────────────────────────
# 4.  Normal chat flow (only if no pending interrupt)
# ──────────────────────────────────────────────────────────────

if not st.session_state.pending_interrupt and (prompt := st.chat_input("Please write a detailed project description")):
    # save & echo user message
    st.session_state.messages.append({"role": "user", "content": test_input})
    with st.chat_message("user"):
        st.markdown(test_input)

    # run graph
    with st.chat_message("assistant", avatar="🧞‍♀️"):
        ai_msg = st.write_stream(
            stream_graph_responses_test(
                user_input=test_input,
                graph=graph,
                config=configurable,
            ),
        )
    st.session_state.messages.append({"role": "assistant", "content": ai_msg})

# ──────────────────────────────────────────────────────────────
# 5.  Detect new interrupt *once*
# ──────────────────────────────────────────────────────────────
if not st.session_state.pending_interrupt:  # only check when free
    ts = graph.get_state(configurable)
    if ts.next:  # graph is waiting
        st.session_state.pending_interrupt = True
        st.session_state.interrupt_snapshot = ts  # keep for display

# ──────────────────────────────────────────────────────────────
# 6.  Show interrupt approval UI (survives reruns)
# ──────────────────────────────────────────────────────────────
if st.session_state.pending_interrupt:
    ts = st.session_state.interrupt_snapshot

    # show context to the user
    with st.chat_message("assistant", avatar="🧞‍♀️"):
        for intr in ts.interrupts:
            st.markdown(f"**{intr.value['message']}**")
            for tc in intr.value["tool_calls"]:
                st.markdown(f"• Tool **{tc['name']}** with args `{tc['args']}`")

    # single, stable form
    with st.form("interrupt_form", clear_on_submit=True):
        reply = st.text_input("Action (accept/feedback):")
        sent = st.form_submit_button("Submit")

    # process once when the button is clicked
    if sent:
        st.session_state.messages.append({"role": "user", "content": reply})

        # Prepare the command for resuming the graph
        user_response = None
        reply_lower = reply.strip().lower()
        if reply_lower == "accept":
            user_response = Command(resume={"action": "accept", "feedback": None})
        else:
            # Assuming any other input is feedback.
            # The supervisor agent expects a dictionary for the `resume` argument.
            user_response = Command(resume={"action": "feedback", "feedback": reply})

        with st.chat_message("assistant", avatar="🧞‍♀️"):
            ai_msg = st.write_stream(
                stream_graph_responses_test(
                    user_input=user_response,
                    graph=graph,
                    config=configurable,
                ),
            )
        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

        # clear flag and rerun
        st.session_state.pending_interrupt = False
        st.session_state.interrupt_snapshot = None
        st.rerun()
