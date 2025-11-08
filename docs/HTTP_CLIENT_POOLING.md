# HTTP Client Connection Pooling

## Overview

The Compliance Intelligence Platform uses shared HTTP client connection pooling to optimize performance when making external API calls through compliance tools (HTS, Sanctions, Refusals, Rulings).

## Architecture

### Shared Client Manager

The `HTTPClientManager` class (located in `src/exim_agent/infrastructure/http_client.py`) provides singleton instances of both synchronous and asynchronous HTTP clients with optimized connection pooling.

### Configuration

Both sync and async clients are configured with:

- **Connection Limits**:
  - Max 100 total connections
  - Max 20 keepalive connections
  - 30s keepalive expiry

- **Timeouts**:
  - 30s connect timeout
  - 60s read timeout
  - 30s write timeout
  - 5s pool timeout

- **Features**:
  - HTTP/2 enabled for better performance
  - Automatic redirect following
  - Custom User-Agent header

## Usage

### In Compliance Tools

All compliance tools (`ComplianceTool` subclasses) automatically use the shared HTTP clients through properties:

```python
from exim_agent.domain.tools.base_tool import ComplianceTool

class MyTool(ComplianceTool):
    def _run_impl(self, **kwargs):
        # Sync client (automatically uses shared pool)
        response = self.client.get("https://api.example.com/data")
        return response.json()
    
    async def _run_impl_async(self, **kwargs):
        # Async client (automatically uses shared pool)
        response = await self.async_client.get("https://api.example.com/data")
        return response.json()
```

### Direct Access

You can also access the shared clients directly:

```python
from exim_agent.infrastructure.http_client import get_sync_client, get_async_client

# Synchronous
client = get_sync_client()
response = client.get("https://api.example.com/data")

# Asynchronous
async_client = get_async_client()
response = await async_client.get("https://api.example.com/data")
```

## Lifecycle Management

### Application Startup

HTTP clients are lazily initialized on first use. No explicit startup is required.

### Application Shutdown

The FastAPI application automatically closes all HTTP clients during shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    
    # Shutdown - closes all HTTP clients
    await shutdown_http_clients()
```

### Manual Cleanup

If needed, you can manually close clients:

```python
from exim_agent.infrastructure.http_client import shutdown_http_clients

# Close all clients
await shutdown_http_clients()
```

## Benefits

1. **Performance**: Connection reuse reduces latency and overhead
2. **Resource Efficiency**: Limits total connections to prevent resource exhaustion
3. **Scalability**: Supports concurrent requests across multiple tools
4. **Reliability**: Proper timeout handling prevents hanging requests

## Monitoring

Get client statistics:

```python
from exim_agent.infrastructure.http_client import HTTPClientManager

stats = HTTPClientManager.get_client_stats()
# Returns:
# {
#     "sync_client_initialized": bool,
#     "async_client_initialized": bool,
#     "sync_client_closed": bool,
#     "async_client_closed": bool
# }
```

## Testing

Tests are located in `tests/test_http_client_pooling.py` and verify:

- Singleton behavior (same instance returned)
- Configuration correctness (timeouts, limits)
- Shared usage across multiple tools
- Proper shutdown behavior

Run tests:

```bash
uv run pytest tests/test_http_client_pooling.py -v
```

## Migration Notes

### Before (Per-Tool Clients)

Each tool instance created its own HTTP client:

```python
class ComplianceTool:
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)  # New client per tool
```

### After (Shared Pool)

All tools share the same HTTP client pool:

```python
class ComplianceTool:
    @property
    def client(self):
        return get_sync_client()  # Shared client
```

This change is transparent to tool implementations - no code changes required in individual tools.

## Troubleshooting

### Connection Pool Exhausted

If you see errors about connection limits, check:

1. Are you making too many concurrent requests?
2. Are connections being properly released?
3. Consider increasing `max_connections` if needed

### Timeout Issues

If requests are timing out:

1. Check if the timeout values are appropriate for your APIs
2. Verify network connectivity
3. Check if circuit breakers are triggering

### Memory Leaks

The shared client pattern prevents memory leaks from creating too many client instances. If you still see issues:

1. Verify `shutdown_http_clients()` is called on application shutdown
2. Check for long-running processes that don't clean up properly
