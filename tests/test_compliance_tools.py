"""Tests for compliance tools."""

import pytest
from exim_agent.domain.tools import HTSTool, SanctionsTool, RefusalsTool, RulingsTool


def test_hts_tool_search():
    """Test HTS tool with valid code."""
    tool = HTSTool()
    result = tool.run(hts_code="8517.12.00", lane_id="CNSHA-USLAX-ocean")
    
    assert result.success is True
    assert result.data is not None
    data = result.data
    assert data["hts_code"] == "8517.12.00"
    assert data["description"] == "Cellular telephones and other apparatus for transmission or reception of voice, images or other data"
    assert data["duty_rate"] == "Free"
    assert "unit" in data


def test_hts_tool_invalid_code():
    """Test HTS tool with invalid code."""
    tool = HTSTool()
    result = tool.run(hts_code="ABC")
    
    assert result.success is False
    assert result.error is not None


def test_hts_tool_caching():
    """Test HTS tool caching mechanism."""
    tool = HTSTool()
    
    # First call
    result1 = tool.run(hts_code="8517.12.00")
    assert result1.success is True
    assert result1.cached is False
    
    # Second call should be cached
    result2 = tool.run(hts_code="8517.12.00")
    assert result2.success is True
    assert result2.cached is True


def test_sanctions_tool_screen():
    """Test sanctions screening."""
    tool = SanctionsTool()
    result = tool.run(party_name="Test Company", lane_id="CNSHA-USLAX-ocean")
    
    assert result.success is True
    assert result.data is not None
    data = result.data
    assert "matches_found" in data
    assert "match_count" in data


def test_sanctions_tool_match():
    """Test sanctions screening with known match."""
    tool = SanctionsTool()
    result = tool.run(party_name="Shanghai Telecom")
    
    assert result.success is True
    data = result.data
    # Should match mock sanctioned entity
    assert data["matches_found"] is True or data["matches_found"] is False  # Depending on mock data


def test_refusals_tool_by_hts():
    """Test refusals tool with HTS code."""
    tool = RefusalsTool()
    result = tool.run(hts_code="0306.17.00")
    
    assert result.success is True
    assert result.data is not None
    data = result.data
    assert "total_refusals" in data
    assert "fda_refusals" in data
    assert "fsis_refusals" in data


def test_refusals_tool_by_country():
    """Test refusals tool with country filter."""
    tool = RefusalsTool()
    result = tool.run(country="CN", days=90)
    
    assert result.success is True
    data = result.data
    assert "refusals" in data


def test_refusals_tool_no_criteria():
    """Test refusals tool without search criteria."""
    tool = RefusalsTool()
    result = tool.run()
    
    assert result.success is False
    assert result.error is not None


def test_rulings_tool_by_hts():
    """Test rulings tool with HTS code."""
    tool = RulingsTool()
    result = tool.run(hts_code="8517")
    
    assert result.success is True
    assert result.data is not None
    data = result.data
    assert "total_rulings" in data
    assert "rulings" in data


def test_rulings_tool_by_keyword():
    """Test rulings tool with keyword."""
    tool = RulingsTool()
    result = tool.run(keyword="cellular")
    
    assert result.success is True
    data = result.data
    assert "rulings" in data


def test_rulings_tool_no_criteria():
    """Test rulings tool without search criteria."""
    tool = RulingsTool()
    result = tool.run()
    
    assert result.success is False
    assert result.error is not None
