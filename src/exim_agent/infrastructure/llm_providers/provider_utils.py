"""Utility functions for working with LLM providers."""

from typing import Dict, List
from loguru import logger

from exim_agent.config import config


def list_available_providers() -> List[str]:
    """List all available LLM providers."""
    return ["openai", "anthropic", "groq"]


def get_current_provider() -> str:
    """Get the currently configured provider."""
    return config.llm_provider


def get_provider_info() -> Dict[str, any]:
    """Get information about the current provider configuration."""
    provider = config.llm_provider.lower()
    
    info = {
        "provider": provider,
        "embedding_provider": config.embedding_provider,
        "available_providers": list_available_providers(),
    }
    
    if provider == "openai":
        info["model"] = config.openai_model
        info["embedding_model"] = config.openai_embedding_model
        info["api_key_configured"] = bool(config.openai_api_key)
    elif provider == "anthropic":
        info["model"] = config.anthropic_model
        info["api_key_configured"] = bool(config.anthropic_api_key)
    elif provider == "groq":
        info["model"] = config.groq_model
        info["api_key_configured"] = bool(config.groq_api_key)
    
    info["temperature"] = config.llm_temperature
    info["max_tokens"] = config.max_tokens
    info["streaming"] = config.streaming
    
    return info


def validate_provider_config(provider: str) -> bool:
    """
    Validate that a provider is properly configured.
    
    Args:
        provider: The provider name to validate
        
    Returns:
        bool: True if configured, raises ValueError otherwise
    """
    provider = provider.lower()
    
    if provider not in list_available_providers():
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Available: {', '.join(list_available_providers())}"
        )
    
    if provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
    elif provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
    elif provider == "groq":
        if not config.groq_api_key:
            raise ValueError("Groq API key not configured")
    
    return True


def get_model_recommendations(task_type: str) -> Dict[str, str]:
    """
    Get model recommendations for different task types.
    
    Args:
        task_type: Type of task (e.g., 'fast', 'complex', 'long_context')
        
    Returns:
        Dict with provider and model recommendations
    """
    recommendations = {
        "fast": {
            "provider": "groq",
            "model": "llama-3.1-8b-instant",
            "reason": "Fastest inference, 2000+ tokens/sec"
        },
        "complex": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "reason": "Best reasoning and instruction following"
        },
        "long_context": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5-20250929",
            "reason": "200K context window"
        },
        "cost_effective": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "reason": "High performance, lower cost"
        },
        "balanced": {
            "provider": "openai",
            "model": "gpt-5-nano-2025-08-07",
            "reason": "Good balance of speed, quality, and cost"
        }
    }
    
    return recommendations.get(task_type, recommendations["balanced"])


def log_provider_status():
    """Log the current provider configuration status."""
    info = get_provider_info()
    logger.info(f"Current LLM Provider: {info['provider']}")
    logger.info(f"Model: {info.get('model', 'N/A')}")
    logger.info(f"API Key Configured: {info.get('api_key_configured', False)}")
    logger.info(f"Temperature: {info['temperature']}")
    logger.info(f"Streaming: {info['streaming']}")
