"""Configuration for the Agent/App."""

import os
from enum import Enum
from typing import Any

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field


class SearchAPI(Enum):
    """Search APIs."""

    OPENAI = "openai"
    TAVILY = "tavily"
    DUCKDUCKGO = "duckduckgo"  # TODO(@viv): #123 Add duckduckgo
    NONE = "none"


class Defaults(Enum):
    """all Defaults settings."""

    CLARIFICATION_MODEL: str = "openai:gpt-4.1"
    RESEARCH_MODEL: str = "openai:gpt-4o"
    COMPRESSION_MODEL: str = "openai:gpt-4o-mini"
    SUMMARIZATION_MODEL: str = "openai:gpt-4o-mini"
    FINAL_REPORT_GENERATION_MODEL: str = "openai:gpt-4.1"
    SEARCH_API: SearchAPI = SearchAPI.TAVILY


class Configuration(BaseModel):
    """Configuration for the Agent/App."""

    # --- Clarification Model ---------------------------------------------------------------------
    clarification_model: str = Field(
        default=Defaults.CLARIFICATION_MODEL.value,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": Defaults.CLARIFICATION_MODEL.value,
                "description": "Model for conducting research. NOTE: Make sure your Researcher Model supports the selected search API.",
            },
        },
    )
    clarification_model_max_tokens: int = Field(
        default=10_000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 10_000,
                "description": "Maximum output tokens for research model",
            },
        },
    )
    # --- Research Model --------------------------------------------------------------------------
    research_model: str = Field(
        default=Defaults.RESEARCH_MODEL.value,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": "openai:gpt-4.1",
                "description": "Model for conducting research. NOTE: Make sure your Researcher Model supports the selected search API.",
            },
        },
    )
    research_model_max_tokens: int = Field(
        default=10_000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 10_000,
                "description": "Maximum output tokens for research model",
            },
        },
    )
    search_api: SearchAPI = Field(
        default=Defaults.SEARCH_API.value,
        metadata={
            "x_oap_ui_config": {
                "type": "select",
                "default": "tavily",
                "options": [
                    {"label": "Tavily", "value": SearchAPI.TAVILY.value},
                    {
                        "label": "OpenAI Native Web Search",
                        "value": SearchAPI.OPENAI.value,
                    },
                    {"value": "none", "label": "None"},
                ],
                "description": "Search API to use for research. NOTE: Make sure your Researcher Model supports the selected search API.",
            },
        },
    )
    max_concurrent_research_units: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 3,
                "min": 1,
                "max": 20,
                "description": "Maximum number of research units to run concurrently. This will allow the researcher to use multiple sub-agents to conduct research. Note: with more concurrency, you may run into rate limits.",
            },
        },
    )
    max_research_iterations: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 3,
                "min": 1,
                "max": 10,
                "step": 1,
                "description": "Maximum number of research iterations for the Research Supervisor. This is the number of times the Research Supervisor will reflect on the research and ask follow-up questions.",
            },
        },
    )
    max_react_tool_calls: int = Field(
        default=5,
        metadata={
            "x_oap_ui_config": {
                "type": "slider",
                "default": 5,
                "min": 1,
                "max": 30,
                "step": 1,
                "description": "Maximum number of tool calling iterations to make in a single researcher step.",
            },
        },
    )
    # --- Compression Model --------------------------------------------------------------------------
    compression_model: str = Field(
        default=Defaults.COMPRESSION_MODEL.value,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": Defaults.COMPRESSION_MODEL.value,
                "description": "Model for compressing research findings from sub-agents. NOTE: Make sure your Compression Model supports the selected search API.",
            },
        },
    )
    compression_model_max_tokens: int = Field(
        default=10_000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 10_000,
                "description": "Maximum output tokens for compression model",
            },
        },
    )
    compression_attempts: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 3,
                "description": "How many times to attempt compression by the compression model before giving up",
            },
        },
    )
    # --- Summarization Model --------------------------------------------------------------------------
    summarization_model: str = Field(
        default=Defaults.SUMMARIZATION_MODEL.value,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": Defaults.SUMMARIZATION_MODEL.value,
                "description": "Model for summarizing research results from Tavily search results",
            },
        },
    )
    summarization_model_max_tokens: int = Field(
        default=8192,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 8192,
                "description": "Maximum output tokens for summarization model",
            },
        },
    )
    max_structured_output_retries: int = Field(
        default=3,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 3,
                "min": 1,
                "max": 10,
                "description": "Maximum number of retries for structured output calls from models",
            },
        },
    )
    allow_clarification: bool = Field(
        default=True,
        metadata={
            "x_oap_ui_config": {
                "type": "boolean",
                "default": True,
                "description": "Whether to allow the researcher to ask the user clarifying questions before starting research",
            },
        },
    )
    # --- Final Report Model --------------------------------------------------------------------------
    final_report_generation_model: str = Field(
        default=Defaults.FINAL_REPORT_GENERATION_MODEL.value,
        metadata={
            "x_oap_ui_config": {
                "type": "text",
                "default": Defaults.FINAL_REPORT_GENERATION_MODEL.value,
                "description": "Model for writing the final report from all research findings",
            },
        },
    )
    final_report_generation_model_max_tokens: int = Field(
        default=10_000,
        metadata={
            "x_oap_ui_config": {
                "type": "number",
                "default": 10_000,
                "description": "Maximum output tokens for final report model",
            },
        },
    )

    @classmethod
    def from_runnable_config(
        cls,
        config: RunnableConfig | None = None,
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config.get("configurable", {}) if config else {}
        field_names = list(cls.model_fields.keys())
        values: dict[str, Any] = {
            field_name: os.environ.get(field_name.upper(), configurable.get(field_name)) for field_name in field_names
        }
        return cls(**{k: v for k, v in values.items() if v is not None})
