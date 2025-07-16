"""Model Provider factory pattern to select the right model provider."""

try:
    from .base_class import LLMProvider
    from .open_ai_provider import OpenAIProvider
    from .perplexity_provider import PerplexityProvider
except ImportError:
    import rootutils

    rootutils.setup_root(__file__, indicator=".git", pythonpath=True)
    from src.agent.providers.base_class import LLMProvider
    from src.agent.providers.open_ai_provider import OpenAIProvider
    from src.agent.providers.perplexity_provider import PerplexityProvider


class ModelProviderFactory:
    """Factory pattern to select the right model provider."""

    @staticmethod
    def get_model_provider(provider_type: str, config: dict) -> LLMProvider:
        """Select the right model provider."""
        providers = {"openai": OpenAIProvider, "perplexity": PerplexityProvider}
        if provider_type not in providers:
            raise ValueError(f"Unknown provider type: {provider_type}")
        return providers[provider_type](**config)


if __name__ == "__main__":
    model = ModelProviderFactory.get_model_provider("openai", {"model_name": "gpt-4o"})
    print(model)
