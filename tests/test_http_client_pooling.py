"""Tests for HTTP client connection pooling."""

import pytest
import asyncio
import httpx
from exim_agent.infrastructure.http_client import (
    HTTPClientManager,
    get_sync_client,
    get_async_client,
    shutdown_http_clients
)

# Mark all async tests
pytestmark = pytest.mark.anyio


def test_sync_client_singleton():
    """Test that sync client returns the same instance."""
    client1 = get_sync_client()
    client2 = get_sync_client()
    
    assert client1 is client2, "Sync client should be a singleton"


def test_sync_client_configuration():
    """Test that sync client has correct configuration."""
    client = get_sync_client()
    
    # Check timeout configuration
    assert client.timeout.connect == 30.0, "Connect timeout should be 30s"
    assert client.timeout.read == 60.0, "Read timeout should be 60s"
    
    # Check that client is properly configured (limits are internal)
    assert isinstance(client, httpx.Client), "Should be an httpx.Client instance"
    
    # Check headers
    assert "User-Agent" in client.headers
    assert client.headers["User-Agent"] == "ComplianceIntelligencePlatform/1.0"


async def test_async_client_singleton():
    """Test that async client returns the same instance."""
    client1 = get_async_client()
    client2 = get_async_client()
    
    assert client1 is client2, "Async client should be a singleton"
    
    # Cleanup
    await shutdown_http_clients()


async def test_async_client_configuration():
    """Test that async client has correct configuration."""
    client = get_async_client()
    
    # Check timeout configuration
    assert client.timeout.connect == 30.0, "Connect timeout should be 30s"
    assert client.timeout.read == 60.0, "Read timeout should be 60s"
    
    # Check that client is properly configured (limits are internal)
    assert isinstance(client, httpx.AsyncClient), "Should be an httpx.AsyncClient instance"
    
    # Check headers
    assert "User-Agent" in client.headers
    assert client.headers["User-Agent"] == "ComplianceIntelligencePlatform/1.0"
    
    # Cleanup
    await shutdown_http_clients()


def test_client_stats():
    """Test that client stats are reported correctly."""
    # Get clients to initialize them
    sync_client = get_sync_client()
    
    stats = HTTPClientManager.get_client_stats()
    
    assert stats["sync_client_initialized"] is True
    assert stats["sync_client_closed"] is False
    
    # Cleanup
    HTTPClientManager.close_sync_client()
    
    stats_after = HTTPClientManager.get_client_stats()
    assert stats_after["sync_client_initialized"] is False


async def test_shutdown_http_clients():
    """Test that shutdown closes all clients."""
    # Initialize both clients
    sync_client = get_sync_client()
    async_client = get_async_client()
    
    # Verify they're initialized
    stats_before = HTTPClientManager.get_client_stats()
    assert stats_before["sync_client_initialized"] is True
    assert stats_before["async_client_initialized"] is True
    
    # Shutdown
    await shutdown_http_clients()
    
    # Verify they're closed
    stats_after = HTTPClientManager.get_client_stats()
    assert stats_after["sync_client_initialized"] is False
    assert stats_after["async_client_initialized"] is False


async def test_multiple_tools_share_client():
    """Test that multiple tool instances share the same HTTP client."""
    from exim_agent.domain.tools.hts_tool import HTSTool
    from exim_agent.domain.tools.sanctions_tool import SanctionsTool
    
    tool1 = HTSTool()
    tool2 = SanctionsTool()
    
    # Both tools should use the same shared client
    assert tool1.client is tool2.client, "Tools should share the same sync client"
    assert tool1.async_client is tool2.async_client, "Tools should share the same async client"
    
    # Cleanup
    await shutdown_http_clients()
