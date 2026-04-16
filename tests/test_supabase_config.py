"""Tests for Supabase configuration and connection."""

import os
import pytest
from unittest.mock import patch, MagicMock

from exim_agent.config import Settings
from exim_agent.infrastructure.db.supabase_client import SupabaseClient


class TestSupabaseConfiguration:
    """Test Supabase configuration and client functionality."""
    
    def test_supabase_config_fields_exist(self):
        """Test that Supabase configuration fields are available."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config = Settings(_env_file=None)
            # Fields should exist and default to None
            assert hasattr(config, 'supabase_url')
            assert hasattr(config, 'supabase_anon_key')
            assert config.supabase_url is None
            assert config.supabase_anon_key is None
    
    def test_supabase_config_loads_from_env(self):
        """Test that Supabase configuration loads from environment variables."""
        env_vars = {
            "OPENAI_API_KEY": "test-openai-key",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key"
        }
        
        with patch.dict(os.environ, env_vars):
            config = Settings()
            assert config.supabase_url == "https://test.supabase.co"
            assert config.supabase_anon_key == "test-anon-key"
    
    def test_supabase_client_initialization_without_config(self):
        """Test that SupabaseClient handles missing configuration gracefully."""
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = None
            mock_config.supabase_anon_key = None
            
            client = SupabaseClient()
            assert client._client is None
    
    @patch('exim_agent.infrastructure.db.supabase_client.create_client')
    def test_supabase_client_initialization_with_config(self, mock_create_client):
        """Test that SupabaseClient initializes properly with configuration."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = "https://test.supabase.co"
            mock_config.supabase_anon_key = "test-key"
            
            client = SupabaseClient()
            assert client._client == mock_client
            mock_create_client.assert_called_once_with("https://test.supabase.co", "test-key")
    
    def test_store_compliance_data_without_client(self):
        """Test storing data when client is not available."""
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = None
            mock_config.supabase_anon_key = None
            
            client = SupabaseClient()
            result = client.store_compliance_data("hts", "8517.12.00", {"test": "data"})
            assert result is False
    
    @patch('exim_agent.infrastructure.db.supabase_client.create_client')
    def test_store_compliance_data_success(self, mock_create_client):
        """Test successful data storage."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_execute = MagicMock()
        
        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = {"data": [{"id": 1}]}
        mock_create_client.return_value = mock_client
        
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = "https://test.supabase.co"
            mock_config.supabase_anon_key = "test-key"
            
            client = SupabaseClient()
            result = client.store_compliance_data("hts", "8517.12.00", {"test": "data"})
            
            assert result is True
            mock_table.upsert.assert_called_once_with({
                'source_type': 'hts',
                'source_id': '8517.12.00',
                'data': {'test': 'data'}
            })
    
    def test_health_check_without_client(self):
        """Test health check when client is not available."""
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = None
            mock_config.supabase_anon_key = None
            
            client = SupabaseClient()
            result = client.health_check()
            assert result is False
