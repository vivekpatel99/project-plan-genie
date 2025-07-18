"""OpenAI Provider definition."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .base_class import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    Concrete LLM provider for OpenAI models.

    more details: https://python.langchain.com/docs/integrations/providers/openai/
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        **kwargs,
    ) -> ChatOpenAI:
        """Initialize the OpenAIProvider."""
        self.model_name = model_name
        self.temperature = temperature
        self.kwargs = kwargs
        self.llm = self._create_llm_instance()

    def _create_llm_instance(self) -> BaseChatModel:
        """Concrete LLM provider for OpenAI models."""
        try:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                **self.kwargs,
            )
        except RuntimeError as e:
            msg = f"Failed to create ChatOpenAI instance: {e}"
            raise RuntimeError(msg)
