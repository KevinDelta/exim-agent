"""Base provider interface for LLM implementations."""

from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def initialize_llm(self) -> BaseChatModel:
        """Initialize and return the LLM instance."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration."""
        pass


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def initialize_embeddings(self) -> Embeddings:
        """Initialize and return the embeddings instance."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the embedding model name."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate embedding configuration."""
        pass
