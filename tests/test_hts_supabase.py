"""Tests for HTS tool with Supabase integration."""

import pytest
from unittest.mock import patch, MagicMock
from src.exim_agent.domain.tools.hts_tool import HTSTool


class TestHTSToolSupabase:
    """Test HTS tool with Supabase storage functionality."""
    
    def test_hts_tool_initialization(self):
        """Test that HTS tool initializes correctly."""
        tool = HTSTool()
        assert tool.name == "search_hts"
        assert "HTS codes" in tool.description
    
    @patch('src.exim_agent.domain.tools.hts_tool.supabase_client')
    def test_store_hts_data(self, mock_supabase):
        """Test storing HTS data in Supabase."""
        mock_supabase.store_compliance_data.return_value = True
        
        tool = HTSTool()
        test_data = {"hts_code": "8517.12.00", "description": "Test data"}
        
        result = tool._store_hts_data("8517.12.00", test_data)
        
        assert result is True
        mock_supabase.store_compliance_data.assert_called_once_with("hts", "8517.12.00", test_data)
    
    def test_validate_hts_code_valid(self):
        """Test HTS code validation with valid codes."""
        tool = HTSTool()
        
        # Test valid HTS codes
        assert tool._validate_hts_code("8517.12.00") is True
        assert tool._validate_hts_code("8517") is True
        assert tool._validate_hts_code("851712") is True
        assert tool._validate_hts_code("8517120000") is True
    
    def test_validate_hts_code_invalid(self):
        """Test HTS code validation with invalid codes."""
        tool = HTSTool()
        
        # Test invalid HTS codes
        assert tool._validate_hts_code("") is False
        assert tool._validate_hts_code("abc") is False
        assert tool._validate_hts_code("123") is False  # Too short
        assert tool._validate_hts_code("12345") is False  # Invalid length
        assert tool._validate_hts_code("8517.12.ab") is False  # Non-numeric
    
    @patch('src.exim_agent.domain.tools.hts_tool.supabase_client')
    @patch('httpx.Client.get')
    def test_run_impl_success(self, mock_get, mock_supabase):
        """Test successful HTS data fetching and storage."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Sample HTS data</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock Supabase storage
        mock_supabase.store_compliance_data.return_value = True
        
        tool = HTSTool()
        result = tool._run_impl("8517.12.00")
        
        # Verify result structure
        assert "hts_code" in result
        assert result["hts_code"] == "8517.12.00"
        assert "description" in result
        assert "source_url" in result
        assert "last_updated" in result
        
        # Verify Supabase storage was called
        mock_supabase.store_compliance_data.assert_called_once()
    
    def test_get_fallback_data(self):
        """Test fallback data generation."""
        tool = HTSTool()
        
        # Test with known HTS code
        result = tool._get_fallback_data("8517.12.00", "Test error")
        
        assert result["hts_code"] == "8517.12.00"
        assert result["status"] == "fallback"
        assert result["error"] == "Test error"
        assert "description" in result
        assert "duty_rate" in result
        
        # Test with unknown HTS code
        result = tool._get_fallback_data("9999.99.99", "Test error")
        
        assert result["hts_code"] == "9999.99.99"
        assert result["status"] == "fallback"
        assert result["error"] == "Test error"
    
    @patch('src.exim_agent.domain.tools.hts_tool.supabase_client')
    @patch('httpx.Client.get')
    def test_run_impl_with_retry(self, mock_get, mock_supabase):
        """Test retry logic on API failures."""
        # Mock first two calls to fail, third to succeed
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = Exception("Connection error")
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.text = "<html>Success</html>"
        mock_response_success.raise_for_status.return_value = None
        
        mock_get.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        mock_supabase.store_compliance_data.return_value = True
        
        tool = HTSTool()
        
        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            result = tool._run_impl("8517.12.00")
        
        # Should succeed on third attempt
        assert result["hts_code"] == "8517.12.00"
        assert mock_get.call_count == 3
    
    @patch('src.exim_agent.domain.tools.hts_tool.supabase_client')
    @patch('httpx.Client.get')
    def test_run_impl_all_retries_fail(self, mock_get, mock_supabase):
        """Test behavior when all retry attempts fail."""
        # Mock all calls to fail
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("Persistent error")
        mock_get.return_value = mock_response
        
        tool = HTSTool()
        
        # Mock time.sleep to speed up test
        with patch('time.sleep'):
            result = tool._run_impl("8517.12.00")
        
        # Should return fallback data
        assert result["status"] == "fallback"
        assert "Unexpected error" in result["error"]
        assert mock_get.call_count == 3  # Should try 3 times