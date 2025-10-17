"""
LangChain provider module - Factory for different LLM providers.
This is the main entry point for getting LLM and embedding instances.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from loguru import logger

from acc_llamaindex.config import config


# Global instances (singleton pattern)
_llm = None
_embeddings = None


def get_llm() -> BaseChatModel:
    """
    Get or create the global LLM instance based on configured provider.
    
    Returns:
        BaseChatModel: The initialized LLM instance
    """
    global _llm
    if _llm is None:
        _llm = _initialize_llm()
    return _llm


def get_embeddings() -> Embeddings:
    """
    Get or create the global embeddings instance based on configured provider.
    
    Returns:
        Embeddings: The initialized embeddings instance
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = _initialize_embeddings()
    return _embeddings


def reset_llm():
    """Reset LLM instance (useful for switching providers at runtime)."""
    global _llm
    _llm = None
    logger.info("LLM instance reset")


def reset_embeddings():
    """Reset embeddings instance."""
    global _embeddings
    _embeddings = None
    logger.info("Embeddings instance reset")


def _initialize_llm() -> BaseChatModel:
    """Initialize LLM based on configured provider."""
    provider = config.llm_provider.lower()
    logger.info(f"Initializing LLM with provider: {provider}")
    
    try:
        if provider == "openai":
            from .openai_provider import OpenAIProvider
            return OpenAIProvider().initialize_llm()
        elif provider == "anthropic":
            from .anthropic_provider import AnthropicProvider
            return AnthropicProvider().initialize_llm()
        elif provider == "groq":
            from .groq_provider import GroqProvider
            return GroqProvider().initialize_llm()
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: openai, anthropic, groq"
            )
    except ImportError as e:
        logger.error(f"Failed to import provider {provider}: {e}")
        raise RuntimeError(
            f"Provider '{provider}' not available. "
            f"Install with: uv add langchain-{provider}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLM provider {provider}: {e}")
        raise


def _initialize_embeddings() -> Embeddings:
    """Initialize embeddings based on configured provider."""
    provider = config.embedding_provider.lower() if hasattr(config, 'embedding_provider') else 'openai'
    logger.info(f"Initializing embeddings with provider: {provider}")
    
    try:
        if provider == "openai":
            from .openai_provider import OpenAIProvider
            return OpenAIProvider().initialize_embeddings()
        else:
            raise ValueError(
                f"Unsupported embedding provider: {provider}. "
                f"Currently only 'openai' embeddings are supported."
            )
    except ImportError as e:
        logger.error(f"Failed to import embedding provider {provider}: {e}")
        raise RuntimeError(
            f"Embedding provider '{provider}' not available. "
            f"Install with: uv add langchain-{provider}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize embedding provider {provider}: {e}")
        raise
