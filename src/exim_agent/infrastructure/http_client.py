"""Shared HTTP client with connection pooling for compliance tools."""

import httpx
from typing import Optional
from loguru import logger


class HTTPClientManager:
    """
    Singleton manager for shared HTTP clients with connection pooling.
    
    Provides both sync and async HTTP clients with optimized connection pooling
    for compliance tool API calls.
    """
    
    _instance: Optional['HTTPClientManager'] = None
    _sync_client: Optional[httpx.Client] = None
    _async_client: Optional[httpx.AsyncClient] = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_sync_client(cls) -> httpx.Client:
        """
        Get or create shared synchronous HTTP client.
        
        Returns:
            Configured httpx.Client with connection pooling
        """
        if cls._sync_client is None:
            logger.info("Initializing shared sync HTTP client with connection pooling")
            cls._sync_client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=30.0,  # 30s connect timeout
                    read=60.0,     # 60s read timeout
                    write=30.0,    # 30s write timeout
                    pool=5.0       # 5s pool timeout
                ),
                limits=httpx.Limits(
                    max_connections=100,        # Max 100 total connections
                    max_keepalive_connections=20,  # Keep 20 connections alive
                    keepalive_expiry=30.0      # Keep connections alive for 30s
                ),
                headers={
                    "User-Agent": "ComplianceIntelligencePlatform/1.0"
                },
                follow_redirects=True,
                http2=True  # Enable HTTP/2 for better performance
            )
            logger.info("Sync HTTP client initialized successfully")
        return cls._sync_client
    
    @classmethod
    def get_async_client(cls) -> httpx.AsyncClient:
        """
        Get or create shared asynchronous HTTP client.
        
        Returns:
            Configured httpx.AsyncClient with connection pooling
        """
        if cls._async_client is None:
            logger.info("Initializing shared async HTTP client with connection pooling")
            cls._async_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=30.0,  # 30s connect timeout
                    read=60.0,     # 60s read timeout
                    write=30.0,    # 30s write timeout
                    pool=5.0       # 5s pool timeout
                ),
                limits=httpx.Limits(
                    max_connections=100,        # Max 100 total connections
                    max_keepalive_connections=20,  # Keep 20 connections alive
                    keepalive_expiry=30.0      # Keep connections alive for 30s
                ),
                headers={
                    "User-Agent": "ComplianceIntelligencePlatform/1.0"
                },
                follow_redirects=True,
                http2=True  # Enable HTTP/2 for better performance
            )
            logger.info("Async HTTP client initialized successfully")
        return cls._async_client
    
    @classmethod
    def close_sync_client(cls):
        """Close the shared synchronous HTTP client."""
        if cls._sync_client is not None:
            logger.info("Closing shared sync HTTP client")
            try:
                cls._sync_client.close()
                cls._sync_client = None
                logger.info("Sync HTTP client closed successfully")
            except Exception as e:
                logger.error(f"Error closing sync HTTP client: {e}")
    
    @classmethod
    async def close_async_client(cls):
        """Close the shared asynchronous HTTP client."""
        if cls._async_client is not None:
            logger.info("Closing shared async HTTP client")
            try:
                await cls._async_client.aclose()
                cls._async_client = None
                logger.info("Async HTTP client closed successfully")
            except Exception as e:
                logger.error(f"Error closing async HTTP client: {e}")
    
    @classmethod
    def close_all(cls):
        """Close all HTTP clients (sync only, async must be awaited separately)."""
        cls.close_sync_client()
    
    @classmethod
    async def close_all_async(cls):
        """Close all HTTP clients asynchronously."""
        cls.close_sync_client()
        await cls.close_async_client()
    
    @classmethod
    def get_client_stats(cls) -> dict:
        """
        Get statistics about the HTTP clients.
        
        Returns:
            Dictionary with client status information
        """
        return {
            "sync_client_initialized": cls._sync_client is not None,
            "async_client_initialized": cls._async_client is not None,
            "sync_client_closed": cls._sync_client is None or cls._sync_client.is_closed if cls._sync_client else True,
            "async_client_closed": cls._async_client is None or cls._async_client.is_closed if cls._async_client else True
        }


# Convenience functions for direct access
def get_sync_client() -> httpx.Client:
    """Get shared synchronous HTTP client."""
    return HTTPClientManager.get_sync_client()


def get_async_client() -> httpx.AsyncClient:
    """Get shared asynchronous HTTP client."""
    return HTTPClientManager.get_async_client()


async def shutdown_http_clients():
    """Shutdown all HTTP clients. Call this on application shutdown."""
    logger.info("Shutting down HTTP clients")
    await HTTPClientManager.close_all_async()
    logger.info("HTTP clients shutdown complete")
