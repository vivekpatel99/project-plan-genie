"""Tests for the Configuration class."""

import pytest
from langchain_core.runnables import RunnableConfig

from src.agent.configuration import Configuration, Defaults, SearchAPI


def test_configuration_defaults() -> None:
    """Test that the Configuration class initializes with default values."""
    config = Configuration()
    assert config.research_model == Defaults.RESEARCH_MODEL.value
    assert config.compression_model == Defaults.COMPRESSION_MODEL.value
    assert config.summarization_model == Defaults.SUMMARIZATION_MODEL.value
    assert config.final_report_generation_model == Defaults.FINAL_REPORT_GENERATION_MODEL.value
    assert config.search_api == Defaults.SEARCH_API.value
    assert config.max_concurrent_research_units == 3  # noqa: PLR2004
    assert config.max_research_iterations == 3  # noqa: PLR2004
    assert config.max_react_tool_calls == 5  # noqa: PLR2004
    assert config.compression_model_max_tokens == 8192  # noqa: PLR2004
    assert config.compression_attempts == 3  # noqa: PLR2004
    assert config.summarization_model_max_tokens == 8192  # noqa: PLR2004
    assert config.max_structured_output_retries == 3  # noqa: PLR2004
    assert config.allow_clarification is True
    assert config.final_report_generation_model_max_tokens == 10000  # noqa: PLR2004


def test_configuration_initialization() -> None:
    """Test that the Configuration class can be initialized with custom values."""
    custom_values = {
        "research_model": "test_model",
        "search_api": SearchAPI.OPENAI,
        "max_research_iterations": 5,
        "allow_clarification": False,
    }
    config = Configuration(**custom_values)
    assert config.research_model == "test_model"
    assert config.search_api == SearchAPI.OPENAI
    assert config.max_research_iterations == 5  # noqa: PLR2004
    assert config.allow_clarification is False
    # Check a default value is still there
    assert config.compression_model == Defaults.COMPRESSION_MODEL.value


def test_from_runnable_config_empty() -> None:
    """Test creating a Configuration from an empty RunnableConfig."""
    runnable_config = RunnableConfig(configurable={})
    config = Configuration.from_runnable_config(runnable_config)
    # Should be all defaults
    assert config.research_model == Defaults.RESEARCH_MODEL.value
    assert config.search_api == Defaults.SEARCH_API.value


def test_from_runnable_config_with_configurable() -> None:
    """Test creating a Configuration from a RunnableConfig with values."""
    runnable_config = RunnableConfig(
        configurable={
            "research_model": "configurable_model",
            "max_research_iterations": 7,
            "search_api": SearchAPI.OPENAI.value,
        },
    )
    config = Configuration.from_runnable_config(runnable_config)
    assert config.research_model == "configurable_model"
    assert config.max_research_iterations == 7  # noqa: PLR2004
    assert config.search_api == SearchAPI.OPENAI


def test_from_runnable_config_with_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test creating a Configuration from environment variables."""
    monkeypatch.setenv("RESEARCH_MODEL", "env_model")
    monkeypatch.setenv("MAX_RESEARCH_ITERATIONS", "8")
    config = Configuration.from_runnable_config(RunnableConfig(configurable={}))
    assert config.research_model == "env_model"
    # Note: Pydantic will cast the string "8" to an int
    assert config.max_research_iterations == 8  # noqa: PLR2004


def test_from_runnable_config_env_overrides_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that environment variables override values in RunnableConfig."""
    monkeypatch.setenv("RESEARCH_MODEL", "env_model_override")
    runnable_config = RunnableConfig(
        configurable={
            "research_model": "configurable_model",
        },
    )
    config = Configuration.from_runnable_config(runnable_config)
    assert config.research_model == "env_model_override"


def test_from_runnable_config_with_none() -> None:
    """Test creating a Configuration from a None config."""
    config = Configuration.from_runnable_config(None)
    # Should be all defaults
    assert config.research_model == Defaults.RESEARCH_MODEL.value
    assert config.search_api == Defaults.SEARCH_API.value
