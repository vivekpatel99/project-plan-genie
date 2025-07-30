"""State of conversation between Agent and User."""

import operator
from enum import Enum
from typing import Annotated, TypedDict

from langchain_core.messages import MessageLikeRepresentation
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class StatesKeys(str, Enum):
    """States keys. used to pass updated states to avoid types."""

    MSGS = "messages"
    SUPERVISOR_MSGS = "supervisor_messages"
    RESEARCH_BRIEF = "research_brief"
    RAW_NOTES = "raw_notes"
    NOTES = "notes"
    FINAL_REPORT = "final_report"
    RESEARCH_TOPIC = "research_topic"
    RESEARCH_ITERATIONS = "research_iterations"
    RESEARCH_MSGS = "research_messages"
    TOOL_CALL_ITERATIONS = "tool_call_iterations"
    COMPRESSED_RESEARCH = "compressed_research"


# --- Clarification Agent ------------------------------------------------------------------


class AgentInputState(MessagesState):
    """Input state is only messages."""


class AgentState(MessagesState):
    """Agents States."""

    supervisor_messages: Annotated[list[MessageLikeRepresentation], add_messages]
    research_brief: str | None
    raw_notes: Annotated[list[str] | None, operator.add] = None
    notes: Annotated[list[str] | None, operator.add] = None
    final_report: str


class Summary(BaseModel):
    """contain summary and key excerpts."""

    summary: str
    key_excerpts: str


class ClarifyWithUser(BaseModel):
    """Call this tool to ask a clarification questions/information to the user."""

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


# --- Supervisor Agent--------------------------------------------------------------


class ConductResearch(BaseModel):
    """Call this tool to conduct research on a specific topic."""

    research_topic: str = Field(
        description="Project idea with detailed description (as much as information possible) by User",
    )


class SupervisorState(TypedDict):
    """Supervisor State."""

    supervisor_messages: Annotated[list[MessageLikeRepresentation], add_messages]
    research_brief: str | None
    raw_notes: Annotated[list[str] | None, add_messages] = None
    notes: Annotated[list[str] | None, add_messages] = None
    research_iterations: int = 0


# --- Research Agent--------------------------------------------------------------


class ResearchComplete(BaseModel):
    """Call this tool to indicate that the research is complete."""


class ResearchState(TypedDict):
    """The state of the research agent."""

    research_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    tool_call_iterations: int = 0
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[list[str] | None, add_messages] = None


class ResearcherOutputState(BaseModel):
    compressed_research: str
    raw_notes: Annotated[list[str] | None, add_messages] = None
