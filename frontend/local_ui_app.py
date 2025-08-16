import rootutils
import streamlit as st
from langchain_core.caches import InMemoryCache
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

rootutils.setup_root(__file__, indicator=".git", pythonpath=True)

from frontend.utils import (  # noqa: E402
    setup_logging,
    stream_graph_responses,
)
from src.agent.project_planning_genie import agent_builder  # noqa: E402

# from src.agent.clarification_agent_subgraph import clarify_builder

st.title("Project Planning Genie 🧞‍♀️")

# Create an empty list to store messages
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# loading the conversation history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# set_llm_cache(SQLiteCache(database_path=".langchain.db"))
setup_logging()

configurable = {"configurable": {"thread_id": "1"}}
graph = agent_builder.compile(
    name="Project Planning Genie Local",
    checkpointer=MemorySaver(),
    cache=InMemoryCache(),
)

if prompt := st.chat_input("Please Write Detail Project Description"):
    with st.chat_message("user"):
        st.markdown(prompt)

    # first add the message to message_history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # thread_state = graph.get_state(config=configurable)
    # print(thread_state)
    with st.chat_message("assistant", avatar="🧞‍♀️"):
        ai_message = st.write_stream(
            stream_graph_responses(
                user_input={"messages": [HumanMessage(content=prompt)]},
                graph=graph,
                config=configurable,
            ),
        )
    # the message to message_history
    st.session_state.messages.append({"role": "assistant", "content": ai_message})


# '{\n  "need_clarification": true,\n  "question": "- Could you elaborate on the specific features or functionalities of the note-taking app that are most important to showcase your skills in computer vision, multi-agent systems, and end-to-end AI engineering?\\n- What is your preferred programming language for this project? Are there any frameworks or libraries (like TensorFlow for image recognition) you would like to use or learn about?\\n- Do you have a particular frontend technology preference (React.js, Angular, Vue.js), or are you open to experimenting with something new for this project?",\n  "verification": ""\n}\n\n< TOOL CALL: ResearchQuestion >\n\n{"research_brief": "I need to develop an agent-powered AI note-taking app using LangGraph for personal productivity, showcasing my skills in computer vision, multi-agent systems, and end-to-end AI engineering. The app should capture handwritten notes, automatically format them (including equations and diagrams), classify content into the correct Notion section, and upload the processed notes with rich formatting. I aim to implement an MVP capable of image-to-text conversion and formatting within two weeks. What specific features of the note-taking app are most important to showcase my skills in computer vision, multi-agent systems, and end-to-end AI engineering? What is the best programming language for this project, and are there any frameworks or libraries (like TensorFlow for image recognition) I should use or learn about? What frontend technology should I use (React.js, Angular, Vue.js), or should I experiment with something new for this project?"}'
