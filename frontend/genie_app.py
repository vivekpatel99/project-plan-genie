import rootutils
import streamlit as st
from langgraph.checkpoint.memory import InMemorySaver

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
from src.agent.clarification_agent_subgraph import clarify_builder  # noqa: E402

CONFIG = {"configurable": {"thread_id": "1"}}

st.title("Project Planning Genie")

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []


# loading the conversation history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

clarify_subgraph = clarify_builder.compile(name="Clarify with User", checkpointer=InMemorySaver())
user_input = st.chat_input("Please Write Detail Project Description")


# async def chat_astream(user_input: dict[str, BaseMessage], config: dict):
#     async for message_chunk, metadata in clarify_subgraph.astream(
#         input=user_input,
#         config=config,
#         stream_mode="messages",
#     ):
#         clarification_object = ClarifyWithUser.model_validate(message_chunk.content)
#         yield clarification_object.question


# if user_input:
#     # first add the message to message_history
#     st.session_state["message_history"].append({"role": "user", "content": user_input})
#     with st.chat_message("user"):
#         st.text(user_input)
#     user_input_message = {"messages": [HumanMessage(content=user_input)]}
#     ai_message = st.write_stream(chat_astream(user_input_message, CONFIG))
#     thread_state = clarify_subgraph.get_state(config=CONFIG)

#     # # first add the message to message_history
#     st.session_state["message_history"].append({"role": "assistant", "content": ai_message})
#     with st.chat_message("assistant"):
#         st.text(ai_message)
