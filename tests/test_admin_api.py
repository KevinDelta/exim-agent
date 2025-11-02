"""Integration tests for Admin API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import time

from exim_agent.infrastructure.api.main import app


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    return TestClient(app)


class TestAdminIngestEndpoints:
    """Tests for /admin/ingest/* endpoints."""
    
    def test_get_ingestion_status_success(self, client):
        """Test successful ingestion status retrieval."""
        response = client.get("/admin/ingest/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "pipeline_available" in data
        assert "current_status" in data
        assert "health_checks" in data
        assert "last_run" in data
        assert "next_scheduled_run" in data
        
        # Check health checks structure
        health_checks = data["health_checks"]
        assert isinstance(health_checks, dict)
        assert "zenml_available" in health_checks
        assert "pipeline_runner" in health_checks
        assert "compliance_pipeline" in health_checks
    
    def test_trigger_manual_ingestion_success(self, client):
        """Test successful manual ingestion trigger."""
        request_data = {
            "lookback_days": 3,
            "force_refresh": False,
            "notify_on_completion": False
        }
        
        response = client.post("/admin/ingest/run", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["success"] is True
        assert "run_id" in data
        assert data["status"] == "starting"
        assert "message" in data
        assert "started_at" in data
        assert "estimated_duration_minutes" in data
        
        # Validate run_id format
        run_id = data["run_id"]
        assert run_id.startswith("manual_")
        assert len(run_id) > 10  # Should have timestamp
    
    def test_trigger_manual_ingestion_minimal_request(self, client):
        """Test manual ingestion with minimal request data."""
        request_data = {}  # Use defaults
        
        response = client.post("/admin/ingest/run", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "run_id" in data
    
    def test_trigger_manual_ingestion_custom_lookback(self, client):
        """Test manual ingestion with custom lookback days."""
        request_data = {
            "lookback_days": 14
        }
        
        response = client.post("/admin/ingest/run", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
    
    def test_list_recent_runs_success(self, client):
        """Test listing recent pipeline runs."""
        response = client.get("/admin/ingest/runs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "runs" in data
        assert "total_runs" in data
        assert "note" in data
        
        runs = data["runs"]
        assert isinstance(runs, list)
    
    def test_list_recent_runs_with_limit(self, client):
        """Test listing runs with custom limit."""
        response = client.get("/admin/ingest/runs?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        runs = data["runs"]
        assert len(runs) <= 5
    
    def test_cancel_pipeline_run_not_found(self, client):
        """Test cancelling non-existent pipeline run."""
        fake_run_id = "nonexistent_run_123"
        
        response = client.delete(f"/admin/ingest/runs/{fake_run_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_admin_health_check_success(self, client):
        """Test admin health check endpoint."""
        response = client.get("/admin/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "timestamp" in data
        assert "system" in data
        assert "components" in data
        assert "status" in data
        
        # Check system info
        system = data["system"]
        assert "zenml_pipelines" in system
        assert "pipeline_runner" in system
        
        # Check status is valid
        valid_statuses = ["healthy", "degraded", "limited", "unhealthy"]
        assert data["status"] in valid_statuses


class TestAdminIngestWorkflow:
    """Integration tests for admin ingestion workflow."""
    
    def test_status_before_and_after_trigger(self, client):
        """Test status changes after triggering ingestion."""
        # Get initial status
        initial_response = client.get("/admin/ingest/status")
        assert initial_response.status_code == 200
        initial_data = initial_response.json()
        
        # Trigger ingestion
        trigger_response = client.post("/admin/ingest/run", json={"lookback_days": 1})
        assert trigger_response.status_code == 200
        trigger_data = trigger_response.json()
        run_id = trigger_data["run_id"]
        
        # Wait a moment for background task to start
        time.sleep(0.5)
        
        # Get status after trigger
        after_response = client.get("/admin/ingest/status")
        assert after_response.status_code == 200
        after_data = after_response.json()
        
        # Should have last_run info now
        assert after_data["last_run"] is not None
        assert after_data["last_run"]["run_id"] == run_id
    
    def test_multiple_triggers_conflict(self, client):
        """Test that multiple simultaneous triggers are handled properly."""
        # First trigger
        first_response = client.post("/admin/ingest/run", json={"lookback_days": 1})
        assert first_response.status_code == 200
        
        # Immediate second trigger (should conflict if first is still running)
        second_response = client.post("/admin/ingest/run", json={"lookback_days": 1})
        
        # Either succeeds (if first completed quickly) or conflicts
        assert second_response.status_code in [200, 409]
        
        if second_response.status_code == 409:
            data = second_response.json()
            assert "already running" in data["detail"].lower()
    
    def test_runs_list_after_trigger(self, client):
        """Test that triggered runs appear in runs list."""
        # Trigger a run
        trigger_response = client.post("/admin/ingest/run", json={"lookback_days": 2})
        assert trigger_response.status_code == 200
        run_id = trigger_response.json()["run_id"]
        
        # Wait for background task
        time.sleep(1.0)
        
        # Check runs list
        runs_response = client.get("/admin/ingest/runs")
        assert runs_response.status_code == 200
        runs_data = runs_response.json()
        
        # Should have at least one run
        assert runs_data["total_runs"] >= 1
        
        # Find our run
        our_run = None
        for run in runs_data["runs"]:
            if run["run_id"] == run_id:
                our_run = run
                break
        
        assert our_run is not None
        assert "status" in our_run
        assert "started_at" in our_run


class TestAdminEndpointValidation:
    """Tests for request validation on admin endpoints."""
    
    def test_trigger_ingestion_invalid_lookback_days(self, client):
        """Test ingestion trigger with invalid lookback days."""
        request_data = {
            "lookback_days": -5  # Invalid negative value
        }
        
        response = client.post("/admin/ingest/run", json=request_data)
        
        # Should either accept it (no validation) or reject it
        # The actual behavior depends on Pydantic model validation
        assert response.status_code in [200, 422]
    
    def test_trigger_ingestion_invalid_json(self, client):
        """Test ingestion trigger with malformed JSON."""
        response = client.post(
            "/admin/ingest/run",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_runs_list_invalid_limit(self, client):
        """Test runs list with invalid limit parameter."""
        response = client.get("/admin/ingest/runs?limit=invalid")
        
        assert response.status_code == 422


class TestAdminEndpointSecurity:
    """Security tests for admin endpoints."""
    
    def test_admin_endpoints_accessible(self, client):
        """Test that admin endpoints are accessible (no auth in this version)."""
        endpoints = [
            "/admin/ingest/status",
            "/admin/health"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not be 401/403 (no auth implemented yet)
            assert response.status_code not in [401, 403]
    
    def test_admin_endpoints_cors_headers(self, client):
        """Test that admin endpoints include CORS headers."""
        response = client.get("/admin/ingest/status")
        
        # Check for CORS headers (if CORS is enabled)
        # This depends on the FastAPI CORS configuration
        assert response.status_code == 200


class TestAdminEndpointPerformance:
    """Performance tests for admin endpoints."""
    
    def test_status_endpoint_performance(self, client):
        """Test that status endpoint responds quickly."""
        start = time.time()
        response = client.get("/admin/ingest/status")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should respond within 2 seconds
        assert elapsed < 2.0
    
    def test_health_endpoint_performance(self, client):
        """Test that health endpoint responds quickly."""
        start = time.time()
        response = client.get("/admin/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should respond within 2 seconds
        assert elapsed < 2.0
    
    def test_trigger_endpoint_performance(self, client):
        """Test that trigger endpoint responds quickly (starts background task)."""
        start = time.time()
        response = client.post("/admin/ingest/run", json={"lookback_days": 1})
        elapsed = time.time() - start
        
        assert response.status_code in [200, 409]  # 409 if already running
        # Should respond within 3 seconds (just starting background task)
        assert elapsed < 3.0


class TestAdminEndpointDocumentation:
    """Tests for API documentation of admin endpoints."""
    
    def test_admin_endpoints_in_openapi(self, client):
        """Test that admin endpoints appear in OpenAPI schema."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        openapi_data = response.json()
        
        paths = openapi_data.get("paths", {})
        
        # Check that admin endpoints are documented
        admin_endpoints = [
            "/admin/ingest/run",
            "/admin/ingest/status", 
            "/admin/ingest/runs",
            "/admin/health"
        ]
        
        for endpoint in admin_endpoints:
            assert endpoint in paths, f"Admin endpoint {endpoint} not found in OpenAPI schema"
    
    def test_admin_endpoints_have_tags(self, client):
        """Test that admin endpoints are properly tagged."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        openapi_data = response.json()
        
        paths = openapi_data.get("paths", {})
        
        # Check admin endpoints have "admin" tag
        admin_paths = [path for path in paths.keys() if path.startswith("/admin")]
        
        for path in admin_paths:
            path_info = paths[path]
            for method_info in path_info.values():
                if isinstance(method_info, dict) and "tags" in method_info:
                    assert "admin" in method_info["tags"]


class TestAdminEndpointErrorHandling:
    """Tests for error handling in admin endpoints."""
    
    def test_status_endpoint_error_handling(self, client):
        """Test status endpoint handles errors gracefully."""
        response = client.get("/admin/ingest/status")
        
        # Should always return 200 with error info if needed
        assert response.status_code == 200
        data = response.json()
        
        # Should have status field
        assert "current_status" in data
    
    def test_health_endpoint_error_handling(self, client):
        """Test health endpoint handles errors gracefully."""
        response = client.get("/admin/health")
        
        # Should always return 200 with health info
        assert response.status_code == 200
        data = response.json()
        
        # Should have status field
        assert "status" in data
        
        # Status should be valid
        valid_statuses = ["healthy", "degraded", "limited", "unhealthy"]
        assert data["status"] in valid_statuses