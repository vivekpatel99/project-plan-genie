"""you should find best and simple solution for those questions."""

import rootutils
import streamlit as st
from langchain_community.cache import SQLiteCache
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

from frontend.utils import (  # noqa: E402
    setup_logging,
    stream_graph_responses_test,
)
from src.agent.project_planning_genie import agent_builder  # noqa: E402

# from src.agent.clarification_agent_subgraph import clarify_builder

st.title("Project Planning Genie 🧞‍♀️")

# Create an empty list to store messages
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# check for is_interrupts
if "is_interrupt" not in st.session_state:
    st.session_state["is_interrupt"] = False

# loading the conversation history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

set_llm_cache(SQLiteCache(database_path=".langchain.db"))
setup_logging()

configurable = {"configurable": {"thread_id": "1"}}
graph = agent_builder.compile(
    name="Project Planning Genie Local",
    checkpointer=MemorySaver(),
    cache=InMemoryCache(),
)

if not st.session_state.is_interrupt and (prompt := st.chat_input("Please Write Detail Project Description")):
    with st.chat_message("user"):
        st.markdown(prompt)

    # first add the message to message_history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # thread_state = graph.get_state(config=configurable)
    # print(thread_state)
    with st.chat_message("assistant", avatar="🧞‍♀️"):
        ai_message = st.write_stream(
            stream_graph_responses_test(
                user_input={"messages": [HumanMessage(content=prompt)]},
                graph=graph,
                config=configurable,
            ),
        )
    # the message to message_history
    st.session_state.messages.append({"role": "assistant", "content": ai_message})

# After streaming completes
thread_state = graph.get_state(configurable)
print(thread_state)
if thread_state.next:
    st.session_state.is_interrupt = True
    # Show is_interrupt data to user
    for interrupt in thread_state.interrupts:
        interrupt_message = interrupt.value["message"]
        tool_calls = [f"Tool Name: {tc['name']} with Args: {tc['args']}" for tc in interrupt.value["tool_calls"]]
        st.session_state.messages.append({"role": "assistant", "content": ai_message})
        # Create Streamlit UI for user input
    with st.form("interrupt_form"):
        st.write("Form created")  # Debug
        st.write("Tool approval required")
        user_response = st.text_input("Action (accept/feedback): ", key="99999")
        submitted = st.form_submit_button("Submit")
        st.write(f"Form rendered, submitted: {submitted}")  # Debug
        if submitted:
            st.session_state.messages.append({"role": "user", "content": user_response})
            print("################################")
            # Resume with user input
            ai_message = st.write_stream(
                stream_graph_responses_test(
                    user_input=Command(resume=user_response),
                    graph=graph,
                    config=configurable,
                ),
            )
            # the message to message_history
            st.session_state.messages.append({"role": "assistant", "content": ai_message})
            st.session_state.is_interrupt = False  # Reset interrupt state
            st.rerun()
