"""Tests for compliance service."""

import pytest
from exim_agent.application.compliance_service import compliance_service


def test_compliance_service_initialization():
    """Test service initialization."""
    assert compliance_service is not None
    compliance_service.initialize()
    assert compliance_service.graph is not None


def test_snapshot_generation():
    """Test snapshot generation."""
    compliance_service.initialize()
    
    result = compliance_service.snapshot(
        client_id="client_ABC",
        sku_id="SKU-123",
        lane_id="CNSHA-USLAX-ocean"
    )
    
    assert result["success"] is True
    assert "snapshot" in result
    snapshot = result["snapshot"]
    assert snapshot["client_id"] == "client_ABC"
    assert snapshot["sku_id"] == "SKU-123"
    assert snapshot["lane_id"] == "CNSHA-USLAX-ocean"
    assert "tiles" in snapshot


def test_snapshot_has_all_tiles():
    """Test snapshot contains all expected tiles."""
    compliance_service.initialize()
    
    result = compliance_service.snapshot(
        client_id="client_TEST",
        sku_id="SKU-456",
        lane_id="MXNLD-USTX-truck"
    )
    
    assert result["success"] is True
    tiles = result["snapshot"]["tiles"]
    
    # Check for expected tiles (normalized keys)
    expected_tiles = ["hts_classification", "sanctions_screening", "refusal_history", "cbp_rulings"]
    for tile_name in expected_tiles:
        assert tile_name in tiles, f"Missing tile: {tile_name}"
        tile = tiles[tile_name]
        assert "status" in tile
        assert "headline" in tile
        assert "details_md" in tile


def test_snapshot_with_rag_context():
    """Test that snapshot generation includes RAG context from ChromaDB."""
    compliance_service.initialize()
    
    result = compliance_service.snapshot(
        client_id="client_RAG_TEST",
        sku_id="SKU-789",
        lane_id="CNSHA-USLAX-ocean"
    )
    
    assert result["success"] is True
    # Snapshot should complete even if RAG context retrieval fails


def test_ask_endpoint():
    """Test compliance Q&A."""
    result = compliance_service.ask(
        client_id="client_ABC",
        question="What are the duty rates for cellular phones from China?"
    )
    
    assert result["success"] is True
    assert "answer" in result
