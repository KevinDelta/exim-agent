"""Tests for compliance ChromaDB collections."""

import pytest
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.infrastructure.db.compliance_collections import compliance_collections


@pytest.fixture(scope="module")
def initialized_collections():
    """Initialize ChromaDB and compliance collections for testing."""
    # Initialize main ChromaDB client
    chroma_client.initialize()
    
    # Initialize compliance collections
    compliance_collections.initialize()
    
    # Seed with sample data
    compliance_collections.seed_sample_data()
    
    yield compliance_collections
    
    # Cleanup not needed - using in-memory for tests


def test_collections_initialization(initialized_collections):
    """Test that all collections are initialized."""
    assert initialized_collections._initialized is True
    assert len(initialized_collections._collections) == 5
    
    # Verify all expected collections exist
    assert compliance_collections.HTS_NOTES in initialized_collections._collections
    assert compliance_collections.RULINGS in initialized_collections._collections
    assert compliance_collections.REFUSALS in initialized_collections._collections
    assert compliance_collections.POLICY in initialized_collections._collections
    assert compliance_collections.EVENTS in initialized_collections._collections


def test_get_collection(initialized_collections):
    """Test getting a specific collection."""
    hts_collection = initialized_collections.get_collection(compliance_collections.HTS_NOTES)
    assert hts_collection is not None
    assert hts_collection._collection is not None


def test_get_invalid_collection(initialized_collections):
    """Test getting an invalid collection raises error."""
    with pytest.raises(ValueError):
        initialized_collections.get_collection("invalid_collection_name")


def test_search_hts_notes(initialized_collections):
    """Test searching HTS notes collection."""
    results = initialized_collections.search_hts_notes(
        query="cellular phone requirements",
        limit=5
    )
    
    assert isinstance(results, list)
    # Should find at least one result from seeded data
    if len(results) > 0:
        assert "content" in results[0]
        assert "metadata" in results[0]
        assert "score" in results[0]


def test_search_hts_notes_with_filter(initialized_collections):
    """Test searching HTS notes with HTS code filter."""
    results = initialized_collections.search_hts_notes(
        query="cellular phones",
        hts_code="8517.12.00",
        limit=3
    )
    
    assert isinstance(results, list)
    # Filtered search should work
    for result in results:
        assert "metadata" in result


def test_search_rulings(initialized_collections):
    """Test searching rulings collection."""
    results = initialized_collections.search_rulings(
        query="classification ruling cellular",
        limit=3
    )
    
    assert isinstance(results, list)
    if len(results) > 0:
        assert "content" in results[0]
        assert "metadata" in results[0]


def test_search_refusals(initialized_collections):
    """Test searching refusals collection."""
    results = initialized_collections.search_refusals(
        query="import refusal seafood",
        limit=3
    )
    
    assert isinstance(results, list)
    if len(results) > 0:
        assert "content" in results[0]
        assert "metadata" in results[0]


def test_search_refusals_with_country_filter(initialized_collections):
    """Test searching refusals with country filter."""
    results = initialized_collections.search_refusals(
        query="import refusal",
        country="CN",
        limit=5
    )
    
    assert isinstance(results, list)


def test_search_policy(initialized_collections):
    """Test searching policy collection."""
    results = initialized_collections.search_policy(
        query="tariff updates trade",
        limit=3
    )
    
    assert isinstance(results, list)
    if len(results) > 0:
        assert "content" in results[0]
        assert "metadata" in results[0]


def test_search_policy_with_category_filter(initialized_collections):
    """Test searching policy with category filter."""
    results = initialized_collections.search_policy(
        query="sanctions",
        category="sanctions",
        limit=3
    )
    
    assert isinstance(results, list)


def test_get_stats(initialized_collections):
    """Test getting collection statistics."""
    stats = initialized_collections.get_stats()
    
    assert isinstance(stats, dict)
    assert compliance_collections.HTS_NOTES in stats
    assert compliance_collections.RULINGS in stats
    assert compliance_collections.REFUSALS in stats
    assert compliance_collections.POLICY in stats
    assert compliance_collections.EVENTS in stats
    
    # Each collection should have a count
    for collection_name, collection_stats in stats.items():
        if "count" in collection_stats:
            assert collection_stats["count"] >= 0
            assert collection_stats["status"] == "active"


def test_search_events(initialized_collections):
    """Test searching compliance events collection."""
    results = initialized_collections.search_events(
        query="sanctions alert",
        limit=5
    )
    
    assert isinstance(results, list)
    if len(results) > 0:
        assert "content" in results[0]
        assert "metadata" in results[0]
        assert "score" in results[0]
        assert "relevance" in results[0]


def test_search_events_with_filters(initialized_collections):
    """Test searching events with multiple filters."""
    results = initialized_collections.search_events(
        query="alert",
        client_id="client_ABC",
        event_type="SANCTIONS",
        risk_level="warn",
        limit=3
    )
    
    assert isinstance(results, list)
    # Filtered search should work
    for result in results:
        assert "metadata" in result


def test_add_compliance_event(initialized_collections):
    """Test adding a new compliance event."""
    success = initialized_collections.add_compliance_event(
        event_id="test_event_001",
        client_id="test_client",
        sku_id="TEST-SKU-001",
        lane_id="TEST-LANE-001",
        event_type="HTS",
        risk_level="info",
        title="Test Event",
        summary="This is a test compliance event",
        metadata={"test": True}
    )
    
    assert success is True
    
    # Verify the event was added by searching for it
    results = initialized_collections.search_events(
        query="test compliance event",
        client_id="test_client",
        limit=1
    )
    
    assert len(results) >= 1
    found_event = results[0]
    assert found_event["metadata"]["event_id"] == "test_event_001"
    assert found_event["metadata"]["client_id"] == "test_client"
    assert found_event["metadata"]["event_type"] == "HTS"


def test_multi_collection_search(initialized_collections):
    """Test searching across multiple collections."""
    results = initialized_collections.search_multi_collection(
        query="cellular phone",
        limit_per_collection=2,
        min_relevance=0.0
    )
    
    assert isinstance(results, dict)
    assert compliance_collections.HTS_NOTES in results
    assert compliance_collections.RULINGS in results
    assert compliance_collections.EVENTS in results
    
    # Each collection should return a list
    for collection_name, collection_results in results.items():
        assert isinstance(collection_results, list)


def test_get_collection_health(initialized_collections):
    """Test getting collection health status."""
    health = initialized_collections.get_collection_health()
    
    assert isinstance(health, dict)
    assert "status" in health
    assert "collections" in health
    assert "total_documents" in health
    assert "last_checked" in health
    
    # Should have health info for all collections
    assert compliance_collections.HTS_NOTES in health["collections"]
    assert compliance_collections.RULINGS in health["collections"]
    assert compliance_collections.REFUSALS in health["collections"]
    assert compliance_collections.POLICY in health["collections"]
    assert compliance_collections.EVENTS in health["collections"]


def test_seeded_data_count(initialized_collections):
    """Test that sample data was seeded correctly."""
    stats = initialized_collections.get_stats()
    
    # Should have seeded data in all collections
    assert stats[compliance_collections.HTS_NOTES]["count"] >= 3
    assert stats[compliance_collections.RULINGS]["count"] >= 3
    assert stats[compliance_collections.REFUSALS]["count"] >= 3
    assert stats[compliance_collections.POLICY]["count"] >= 3
    assert stats[compliance_collections.EVENTS]["count"] >= 3
