"""State of conversation between Agent and User."""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import MessageLikeRepresentation
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# --- Clarification Agent ------------------------------------------------------------------


class AgentInputState(MessagesState):
    """Input state is only messages."""


class AgentState(MessagesState):
    """Agents States."""

    supervisor_message: Annotated[list[MessageLikeRepresentation], add_messages]
    research_brief: str | None
    raw_notes: Annotated[list[str], add_messages] = None
    notes: Annotated[list[str] | None, add_messages] = None
    final_report: str


class Summary(BaseModel):
    """contain summary and key excerpts."""

    Summary: str
    key_excerpts: str


class ClarifyWithUser(BaseModel):
    """Call this tool to ask a clarification questions/infomartion to the user."""

    need_clarification: bool = Field(
        description="Whether the user needs to be asked a clarification question.",
    )
    question: str = Field(
        description="The question to ask the user to clarify the report scope",
    )
    verification: str = Field(
        description="Verify message that we will start research after the user has provided the necessary information.",
    )


class ResearchQuestion(BaseModel):
    """Research questions to guide the research."""

    research_brief: str = Field(
        description="A research question that will be used to guide the research.",
    )


# --- Superviser Agent--------------------------------------------------------------


class ConductResearch(BaseModel):
    """Call this tool to conduct research on a specific topic."""

    research_topic: str = Field(
        description="Project idea with detailed description (as much as information possible) by User",
    )


class SuperviserState(TypedDict):
    """Superviser State."""

    superviser_messages: Annotated[list[MessageLikeRepresentation], add_messages]
    research_brief: str | None
    raw_notes: Annotated[list[str] | None, add_messages] = None
    notes: Annotated[list[str] | None, add_messages] = None
    research_iteration: int = 0


# --- Research Agent--------------------------------------------------------------


class ResearchComplete(BaseModel):
    """Call this tool to indicate that the research is complete."""


class ResearchState(BaseModel):
    """The state of the research agent."""

    research_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    tool_call_iterations: int = 0
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[list[str], add_messages] = []


class ResearcherOutputState(BaseModel):
    compressed_research: str
    raw_notes: Annotated[list[str], add_messages] = []
