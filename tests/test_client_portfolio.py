"""Tests for client portfolio database integration."""

import pytest
from unittest.mock import patch, MagicMock

from exim_agent.infrastructure.db.supabase_client import SupabaseClient


class TestClientPortfolio:
    """Test client portfolio retrieval functionality."""
    
    def test_get_client_portfolio_without_client(self):
        """Test portfolio retrieval when Supabase client is not available."""
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = None
            mock_config.supabase_anon_key = None
            
            client = SupabaseClient()
            result = client.get_client_portfolio("test-client-001")
            assert result == []
    
    @patch('exim_agent.infrastructure.db.supabase_client.create_client')
    def test_get_client_portfolio_success(self, mock_create_client):
        """Test successful portfolio retrieval."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_eq2 = MagicMock()
        mock_order = MagicMock()
        mock_execute = MagicMock()
        
        # Mock the chain of method calls
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.order.return_value = mock_order
        mock_order.execute.return_value = MagicMock(data=[
            {"sku_id": "SKU-001", "lane_id": "CNSHA-USLAX-ocean", "hts_code": "8517.12.00"},
            {"sku_id": "SKU-002", "lane_id": "CNSHA-USLAX-ocean", "hts_code": "6203.42.40"}
        ])
        mock_create_client.return_value = mock_client
        
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = "https://test.supabase.co"
            mock_config.supabase_anon_key = "test-key"
            
            client = SupabaseClient()
            result = client.get_client_portfolio("test-client-001")
            
            assert len(result) == 2
            assert result[0]["sku_id"] == "SKU-001"
            assert result[0]["lane_id"] == "CNSHA-USLAX-ocean"
            assert result[0]["hts_code"] == "8517.12.00"
            
            # Verify the correct table and filters were used
            mock_client.table.assert_called_once_with("client_portfolios")
            mock_table.select.assert_called_once_with("sku_id, lane_id, hts_code")
    
    @patch('exim_agent.infrastructure.db.supabase_client.create_client')
    def test_get_client_portfolio_empty(self, mock_create_client):
        """Test portfolio retrieval when no data exists."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_eq2 = MagicMock()
        mock_order = MagicMock()
        mock_execute = MagicMock()
        
        # Mock empty result
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.order.return_value = mock_order
        mock_order.execute.return_value = MagicMock(data=[])
        mock_create_client.return_value = mock_client
        
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = "https://test.supabase.co"
            mock_config.supabase_anon_key = "test-key"
            
            client = SupabaseClient()
            result = client.get_client_portfolio("nonexistent-client")
            
            assert result == []
    
    @patch('exim_agent.infrastructure.db.supabase_client.create_client')
    def test_get_client_portfolio_error_handling(self, mock_create_client):
        """Test portfolio retrieval error handling."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        
        # Mock an exception during query
        mock_client.table.return_value = mock_table
        mock_table.select.side_effect = Exception("Database connection error")
        mock_create_client.return_value = mock_client
        
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = "https://test.supabase.co"
            mock_config.supabase_anon_key = "test-key"
            
            client = SupabaseClient()
            result = client.get_client_portfolio("test-client-001")
            
            # Should return empty list on error
            assert result == []
    
    @patch('exim_agent.infrastructure.db.supabase_client.create_client')
    def test_get_client_portfolio_active_only_false(self, mock_create_client):
        """Test portfolio retrieval including inactive SKU+Lanes."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_execute = MagicMock()
        
        # Mock the chain without the active filter
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.execute.return_value = MagicMock(data=[
            {"sku_id": "SKU-001", "lane_id": "CNSHA-USLAX-ocean", "hts_code": "8517.12.00"},
            {"sku_id": "SKU-999", "lane_id": "INACTIVE-LANE", "hts_code": "0000.00.00"}
        ])
        mock_create_client.return_value = mock_client
        
        with patch('exim_agent.infrastructure.db.supabase_client.config') as mock_config:
            mock_config.supabase_url = "https://test.supabase.co"
            mock_config.supabase_anon_key = "test-key"
            
            client = SupabaseClient()
            result = client.get_client_portfolio("test-client-001", active_only=False)
            
            assert len(result) == 2
