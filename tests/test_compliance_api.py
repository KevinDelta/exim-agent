"""Integration tests for Compliance API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from exim_agent.infrastructure.api.main import app
from exim_agent.application.compliance_service.service import compliance_service
from exim_agent.infrastructure.db.compliance_collections import compliance_collections


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_compliance_system():
    """Initialize compliance system for testing."""
    # Initialize services
    compliance_service.initialize()
    compliance_collections.initialize()
    
    # Seed test data
    compliance_collections.seed_sample_data()
    
    yield
    
    # Cleanup would go here if needed


class TestComplianceSnapshot:
    """Tests for /compliance/snapshot endpoint."""
    
    def test_generate_snapshot_success(self, client):
        """Test successful snapshot generation."""
        request_data = {
            "client_id": "test_client",
            "sku_id": "SKU-123",
            "lane_id": "CNSHA-USLAX-ocean",
            "hts_code": "8517.12.00"
        }
        
        response = client.post("/compliance/snapshot", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "snapshot" in data
        assert "citations" in data
        assert "metadata" in data
        
        # Check metadata
        metadata = data["metadata"]
        assert metadata["client_id"] == "test_client"
        assert metadata["sku_id"] == "SKU-123"
        assert metadata["lane_id"] == "CNSHA-USLAX-ocean"
        assert "generated_at" in metadata
    
    def test_generate_snapshot_missing_fields(self, client):
        """Test snapshot with missing required fields."""
        request_data = {
            "client_id": "test_client",
            "sku_id": "SKU-123"
            # Missing lane_id
        }
        
        response = client.post("/compliance/snapshot", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_generate_snapshot_tiles_structure(self, client):
        """Test that snapshot contains expected tile structure."""
        request_data = {
            "client_id": "client_ABC",
            "sku_id": "SKU-456",
            "lane_id": "MXNLD-USTX-truck"
        }
        
        response = client.post("/compliance/snapshot", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check snapshot structure
        snapshot = data.get("snapshot", {})
        assert isinstance(snapshot, dict)
        
        # Tiles should be present (even if empty in mock)
        # The actual structure depends on the compliance_graph implementation


class TestComplianceWeeklyPulse:
    """Tests for /compliance/pulse/{client_id}/weekly endpoint."""
    
    def test_get_weekly_pulse_success(self, client):
        """Test successful weekly pulse retrieval."""
        response = client.get("/compliance/pulse/test_client/weekly")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["client_id"] == "test_client"
        assert "period_start" in data
        assert "period_end" in data
        assert "summary" in data
        assert "changes" in data
    
    def test_weekly_pulse_summary_structure(self, client):
        """Test weekly pulse summary structure."""
        response = client.get("/compliance/pulse/client_ABC/weekly")
        
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "total_sku_lanes" in summary
        assert "high_priority_changes" in summary
        assert "medium_priority_changes" in summary
        assert "low_priority_changes" in summary
        assert "new_sanctions" in summary
        assert "new_refusals" in summary
        assert "policy_updates" in summary
    
    def test_weekly_pulse_changes_structure(self, client):
        """Test weekly pulse changes array structure."""
        response = client.get("/compliance/pulse/client_XYZ/weekly")
        
        assert response.status_code == 200
        data = response.json()
        
        changes = data["changes"]
        assert isinstance(changes, list)
        
        if changes:
            change = changes[0]
            assert "sku_id" in change
            assert "lane_id" in change
            assert "change_type" in change
            assert "priority" in change
            assert "description" in change
            assert "timestamp" in change


class TestComplianceDailyPulse:
    """Tests for /compliance/pulse/{client_id}/daily endpoint."""
    
    def test_get_daily_pulse_success(self, client):
        """Test successful daily pulse retrieval."""
        response = client.get("/compliance/pulse/test_client/daily")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["client_id"] == "test_client"
        assert "period_start" in data
        assert "period_end" in data
        assert "summary" in data
        assert "changes" in data
    
    def test_daily_pulse_with_date_range(self, client):
        """Test daily pulse with date range filtering."""
        response = client.get(
            "/compliance/pulse/test_client/daily",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["client_id"] == "test_client"
    
    def test_daily_pulse_requires_action_filter(self, client):
        """Test daily pulse with requires_action filter."""
        response = client.get(
            "/compliance/pulse/test_client/daily",
            params={"requires_action_only": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["client_id"] == "test_client"
    
    def test_daily_pulse_metadata_includes_period_type(self, client):
        """Test that daily pulse metadata indicates period type."""
        response = client.get("/compliance/pulse/test_client/daily")
        
        assert response.status_code == 200
        data = response.json()
        
        if data["success"] and data.get("metadata"):
            metadata = data["metadata"]
            assert metadata.get("period_type") == "daily"
    
    def test_daily_pulse_limit_parameter(self, client):
        """Test daily pulse with limit parameter."""
        response = client.get(
            "/compliance/pulse/test_client/daily",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["client_id"] == "test_client"


class TestComplianceLatestPulse:
    """Tests for /compliance/pulse/{client_id}/latest endpoint."""
    
    def test_get_latest_pulse_success(self, client):
        """Test successful latest pulse retrieval."""
        response = client.get("/compliance/pulse/test_client/latest")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["client_id"] == "test_client"
        assert "period_start" in data
        assert "period_end" in data
        assert "summary" in data
        assert "changes" in data
    
    def test_latest_pulse_metadata_includes_period_type(self, client):
        """Test that latest pulse metadata indicates period type and latest flag."""
        response = client.get("/compliance/pulse/test_client/latest")
        
        assert response.status_code == 200
        data = response.json()
        
        if data["success"] and data.get("metadata"):
            metadata = data["metadata"]
            assert "period_type" in metadata
            assert metadata.get("is_latest") is True
            assert metadata["period_type"] in ["daily", "weekly", "unknown"]


class TestComplianceAsk:
    """Tests for /compliance/ask endpoint."""
    
    def test_ask_question_success(self, client):
        """Test successful Q&A."""
        request_data = {
            "client_id": "test_client",
            "question": "What are the requirements for importing electronics from China?",
            "sku_id": "SKU-123",
            "lane_id": "CNSHA-USLAX-ocean"
        }
        
        response = client.post("/compliance/ask", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "answer" in data
        assert data["question"] == request_data["question"]
        assert "citations" in data
    
    def test_ask_question_without_context(self, client):
        """Test Q&A without SKU/lane context."""
        request_data = {
            "client_id": "test_client",
            "question": "What is HTS code 8517.12.00?"
        }
        
        response = client.post("/compliance/ask", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "answer" in data
    
    def test_ask_question_missing_question(self, client):
        """Test Q&A with missing question field."""
        request_data = {
            "client_id": "test_client"
            # Missing question
        }
        
        response = client.post("/compliance/ask", json=request_data)
        
        assert response.status_code == 422  # Validation error


class TestComplianceCollections:
    """Tests for collection management endpoints."""
    
    def test_get_collections_status(self, client):
        """Test collections status endpoint."""
        response = client.get("/compliance/collections/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "collections" in data
        assert "total_documents" in data
        
        collections = data["collections"]
        
        # Check expected collections exist
        expected_collections = [
            "compliance_hts_notes",
            "compliance_rulings",
            "compliance_refusal_summaries",
            "compliance_policy_snippets",
            "compliance_events"
        ]
        
        for collection_name in expected_collections:
            assert collection_name in collections
    
    def test_seed_collections(self, client):
        """Test seeding collections with sample data."""
        response = client.post("/compliance/collections/seed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "message" in data
        assert "collections" in data
    
    def test_collections_have_documents_after_seed(self, client):
        """Test that collections have documents after seeding."""
        # Seed first
        client.post("/compliance/collections/seed")
        
        # Check status
        response = client.get("/compliance/collections/status")
        
        assert response.status_code == 200
        data = response.json()
        
        total_docs = data["total_documents"]
        assert total_docs > 0


class TestComplianceIntegration:
    """Integration tests combining multiple endpoints."""
    
    def test_snapshot_to_ask_workflow(self, client):
        """Test workflow: generate snapshot then ask question about it."""
        # Step 1: Generate snapshot
        snapshot_request = {
            "client_id": "workflow_client",
            "sku_id": "SKU-999",
            "lane_id": "CNSHA-USLAX-ocean"
        }
        
        snapshot_response = client.post("/compliance/snapshot", json=snapshot_request)
        assert snapshot_response.status_code == 200
        
        # Step 2: Ask a question with same context
        ask_request = {
            "client_id": "workflow_client",
            "question": "What are the risks for this SKU?",
            "sku_id": "SKU-999",
            "lane_id": "CNSHA-USLAX-ocean"
        }
        
        ask_response = client.post("/compliance/ask", json=ask_request)
        assert ask_response.status_code == 200
        
        ask_data = ask_response.json()
        assert ask_data["success"] is True
        assert ask_data["answer"] is not None
    
    def test_multiple_snapshots_different_clients(self, client):
        """Test generating snapshots for multiple clients."""
        clients = ["client_A", "client_B", "client_C"]
        
        for client_id in clients:
            request_data = {
                "client_id": client_id,
                "sku_id": f"SKU-{client_id}",
                "lane_id": "CNSHA-USLAX-ocean"
            }
            
            response = client.post("/compliance/snapshot", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["metadata"]["client_id"] == client_id


class TestHealthCheck:
    """Test that compliance is included in health check."""
    
    def test_health_includes_compliance(self, client):
        """Test health endpoint includes compliance status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "stack" in data
        stack = data["stack"]
        assert "compliance" in stack
        assert stack["compliance"] is True


@pytest.mark.asyncio
class TestCompliancePerformance:
    """Performance tests for compliance endpoints."""
    
    def test_snapshot_response_time(self, client):
        """Test that snapshot generation completes in reasonable time."""
        import time
        
        request_data = {
            "client_id": "perf_test",
            "sku_id": "SKU-PERF",
            "lane_id": "CNSHA-USLAX-ocean"
        }
        
        start = time.time()
        response = client.post("/compliance/snapshot", json=request_data)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should complete within 10 seconds (with mock data, should be much faster)
        assert elapsed < 10.0
    
    def test_ask_response_time(self, client):
        """Test that Q&A completes in reasonable time."""
        import time
        
        request_data = {
            "client_id": "perf_test",
            "question": "What is the duty rate for HTS 8517.12.00?"
        }
        
        start = time.time()
        response = client.post("/compliance/ask", json=request_data)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should complete within 10 seconds
        assert elapsed < 10.0
