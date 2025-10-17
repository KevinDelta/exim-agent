# Multi-Provider Architecture Guide

## Overview

The application uses a **modular multi-provider architecture** where each LLM provider (OpenAI, Anthropic, Groq) is implemented in its own file with a consistent interface.

## Architecture

### File Structure

```bash
infrastructure/llm_providers/
├── __init__.py                    # Clean exports
├── base_provider.py               # Abstract base classes
├── langchain_provider.py          # Factory/Entry point
├── openai_provider.py             # OpenAI implementation
├── anthropic_provider.py          # Anthropic implementation
├── groq_provider.py               # Groq implementation
└── provider_utils.py              # Utility functions
```

### Design Benefits

✅ **Separation of Concerns**: Each provider in its own file  
✅ **Lazy Loading**: Only imports what's needed  
✅ **Easy to Extend**: Add new providers without touching existing code  
✅ **Testable**: Each provider can be tested independently  
✅ **Type Safe**: Consistent interface via abstract base classes  
✅ **No Bloat**: Dependencies only loaded when used  

## Usage

### Basic Usage

```python
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm, get_embeddings

# Get LLM (uses provider from config)
llm = get_llm()
response = llm.invoke("Hello!")

# Get embeddings
embeddings = get_embeddings()
vectors = embeddings.embed_query("test")
```

### Switching Providers

#### Via Environment Variables (Recommended)

```python
# .env file
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

#### Via Code (Runtime)

```python
from acc_llamaindex.config import config
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import reset_llm, get_llm

# Switch to Anthropic
config.llm_provider = "anthropic"
reset_llm()
llm = get_llm()  # Now using Claude

# Switch to Groq
config.llm_provider = "groq"
reset_llm()
llm = get_llm()  # Now using Llama via Groq
```

### Provider-Specific Usage

```python
# Direct provider usage (advanced)
from acc_llamaindex.infrastructure.llm_providers.anthropic_provider import AnthropicProvider
from acc_llamaindex.infrastructure.llm_providers.groq_provider import GroqProvider

# Use specific provider
anthropic = AnthropicProvider()
claude = anthropic.initialize_llm()
groq = GroqProvider()
llama = groq.initialize_llm()

# Get model info
models = AnthropicProvider.get_available_models()
info = AnthropicProvider.get_model_info("claude-3-5-sonnet-20241022")
print(f"Context: {info['context_window']} tokens")
```

### Utility Functions

```python
from acc_llamaindex.infrastructure.llm_providers.provider_utils import (
    get_provider_info,
    get_model_recommendations,
    validate_provider_config
)

# Get current configuration
info = get_provider_info()
print(f"Provider: {info['provider']}")
print(f"Model: {info['model']}")

# Get recommendations
rec = get_model_recommendations("fast")
print(f"For fast tasks: {rec['provider']} - {rec['model']}")
print(f"Reason: {rec['reason']}")

# Validate configuration
validate_provider_config("anthropic")  # Raises error if not configured
```

## Configuration

### Environment Variables

```bash
# Provider Selection
LLM_PROVIDER=openai              # openai, anthropic, or groq
EMBEDDING_PROVIDER=openai        # Currently only openai

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-nano-2025-08-07
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Common Settings
LLM_TEMPERATURE=0.7
MAX_TOKENS=4096
STREAMING=true
```

### Config File

All settings are defined in `config.py` with sensible defaults:

```python
class Settings(BaseSettings):
    # Provider Selection
    llm_provider: str = "openai"
    embedding_provider: str = "openai"
    
    # OpenAI
    openai_model: str = "gpt-5-nano-2025-08-07"
    
    # Anthropic
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    
    # Groq
    groq_model: str = "llama-3.3-70b-versatile"
    
    # Common settings
    llm_temperature: float = 0.7
    max_tokens: int | None = None
    streaming: bool = True
```

## Provider Comparison

### OpenAI

- **Models**: GPT-5 Nano, GPT-4o, etc.
- **Strengths**: Balanced performance, good ecosystem
- **Context**: Up to 128K tokens
- **Best for**: General purpose, production applications

### Anthropic (Claude)

- **Models**: Claude 3.5 Sonnet, Opus, Haiku
- **Strengths**: Excellent reasoning, long context, safety
- **Context**: Up to 200K tokens
- **Best for**: Complex analysis, long documents, careful reasoning

### Groq

- **Models**: Llama 3.3, Mixtral, Gemma
- **Strengths**: Extremely fast inference (800-2000 tokens/sec)
- **Context**: 128K tokens
- **Best for**: High-throughput, real-time applications

## Adding New Providers

### 1. Create Provider File

```python
# infrastructure/llm_providers/newprovider_provider.py

from langchain_newprovider import ChatNewProvider
from .base_provider import BaseLLMProvider

class NewProviderProvider(BaseLLMProvider):
    def validate_config(self) -> bool:
        if not config.newprovider_api_key:
            raise ValueError("API key not configured")
        return True
    
    def get_model_name(self) -> str:
        return config.newprovider_model
    
    def initialize_llm(self) -> ChatNewProvider:
        self.validate_config()
        return ChatNewProvider(
            model=config.newprovider_model,
            api_key=config.newprovider_api_key,
            temperature=config.llm_temperature,
        )
```

### 2. Add to Factory

```python
# In langchain_provider.py

elif provider == "newprovider":
    from .newprovider_provider import NewProviderProvider
    return NewProviderProvider().initialize_llm()
```

### 3. Add Configuration

```python
# In config.py

newprovider_api_key: str | None = None
newprovider_model: str = "default-model"
```

### 4. Install Package

```bash
uv add langchain-newprovider
```

## Testing

### Test Individual Providers

```python
# Test all providers
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm
from acc_llamaindex.config import config

for provider in ["openai", "anthropic", "groq"]:
    try:
        config.llm_provider = provider
        llm = get_llm()
        response = llm.invoke("Say hello!")
        print(f"✓ {provider}: {response.content}")
    except Exception as e:
        print(f"✗ {provider}: {e}")
```

### Test Provider Selection

```python
import pytest
from acc_llamaindex.infrastructure.llm_providers.provider_utils import (
    validate_provider_config,
    get_provider_info
)

def test_provider_validation():
    """Test provider validation."""
    # Should succeed if configured
    validate_provider_config("openai")
    
    # Should raise error for unconfigured provider
    with pytest.raises(ValueError):
        validate_provider_config("anthropic")

def test_provider_info():
    """Test getting provider info."""
    info = get_provider_info()
    assert info["provider"] in ["openai", "anthropic", "groq"]
    assert "model" in info
```

## Common Patterns

### Pattern 1: Dynamic Provider Selection

```python
def get_llm_for_task(task_complexity: str):
    """Get appropriate LLM based on task."""
    from acc_llamaindex.infrastructure.llm_providers.provider_utils import get_model_recommendations
    from acc_llamaindex.infrastructure.llm_providers.langchain_provider import reset_llm, get_llm
    from acc_llamaindex.config import config
    
    rec = get_model_recommendations(task_complexity)
    config.llm_provider = rec["provider"]
    reset_llm()
    return get_llm()

# Use fast model for simple tasks
llm = get_llm_for_task("fast")

# Use complex model for reasoning
llm = get_llm_for_task("complex")
```

### Pattern 2: Fallback Provider

```python
def get_llm_with_fallback():
    """Get LLM with automatic fallback."""
    from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_llm, reset_llm
    from acc_llamaindex.config import config
    
    providers = ["openai", "anthropic", "groq"]
    
    for provider in providers:
        try:
            config.llm_provider = provider
            reset_llm()
            return get_llm()
        except Exception as e:
            print(f"Failed to initialize {provider}: {e}")
            continue
    
    raise RuntimeError("All providers failed")
```

### Pattern 3: Multi-Provider Ensemble

```python
async def ensemble_response(query: str):
    """Get responses from multiple providers and combine."""
    from acc_llamaindex.infrastructure.llm_providers import (
        openai_provider,
        anthropic_provider,
        groq_provider
    )
    
    providers = [
        openai_provider.OpenAIProvider(),
        anthropic_provider.AnthropicProvider(),
        groq_provider.GroqProvider(),
    ]
    
    responses = []
    for provider in providers:
        try:
            llm = provider.initialize_llm()
            response = await llm.ainvoke(query)
            responses.append(response.content)
        except:
            continue
    
    # Combine or vote on responses
    return combine_responses(responses)
```

## Troubleshooting

### Provider Not Available

```bash
# Error: Provider 'anthropic' not available
# Solution: Install the package
uv add langchain-anthropic
```

### API Key Not Configured

```bash
# Error: Anthropic API key not configured
# Solution: Add to .env
ANTHROPIC_API_KEY=your-key-here
```

### Import Errors

```python
# If you see: ImportError: cannot import name 'ChatAnthropic'
# Make sure package is installed:
uv add langchain-anthropic
```

## Best Practices

1. **Use Environment Variables**: Configure providers via `.env`
2. **Lazy Loading**: Providers only loaded when used
3. **Validation**: Always validate configuration before use
4. **Error Handling**: Use try/except with provider initialization
5. **Reset Instances**: Call `reset_llm()` when switching providers
6. **Provider Info**: Use `get_provider_info()` for debugging
7. **Type Hints**: Use `BaseChatModel` for provider independence

## Summary

This architecture provides:

- ✅ Clean separation of provider implementations
- ✅ Easy to add new providers
- ✅ No cross-provider dependencies
- ✅ Consistent interface across all providers
- ✅ Better maintainability and testability
- ✅ Lazy loading of dependencies
- ✅ Production-ready error handling

The modular approach scales better than a single monolithic provider file and makes the codebase easier to maintain and extend.
