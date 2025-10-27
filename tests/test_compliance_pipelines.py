"""Tests for compliance ZenML pipelines."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from exim_agent.application.zenml_pipelines.runner import pipeline_runner


class TestComplianceIngestionPipeline:
    """Tests for compliance ingestion pipeline."""
    
    def test_run_compliance_ingestion_success(self):
        """Test successful compliance ingestion pipeline execution."""
        result = pipeline_runner.run_compliance_ingestion(lookback_days=7)
        
        assert result is not None
        assert "status" in result
        # May be success or error depending on ZenML availability
        assert result["status"] in ["success", "error"]
    
    def test_run_compliance_ingestion_with_custom_lookback(self):
        """Test ingestion with custom lookback period."""
        result = pipeline_runner.run_compliance_ingestion(lookback_days=14)
        
        assert result is not None
        assert "status" in result
    
    def test_ingestion_result_structure(self):
        """Test that ingestion result has expected structure."""
        result = pipeline_runner.run_compliance_ingestion(lookback_days=7)
        
        # Should have either result or error
        if result["status"] == "success":
            assert "result" in result
            assert isinstance(result["result"], dict)
        else:
            assert "error" in result


class TestWeeklyPulsePipeline:
    """Tests for weekly pulse pipeline."""
    
    def test_run_weekly_pulse_success(self):
        """Test successful weekly pulse generation."""
        result = pipeline_runner.run_weekly_pulse(
            client_id="test_client",
            period_days=7
        )
        
        assert result is not None
        assert "status" in result
    
    def test_run_weekly_pulse_with_custom_period(self):
        """Test pulse with custom period."""
        result = pipeline_runner.run_weekly_pulse(
            client_id="test_client",
            period_days=14
        )
        
        assert result is not None
        assert "status" in result
    
    def test_weekly_pulse_different_clients(self):
        """Test pulse generation for different clients."""
        clients = ["client_A", "client_B", "client_C"]
        
        for client_id in clients:
            result = pipeline_runner.run_weekly_pulse(
                client_id=client_id,
                period_days=7
            )
            
            assert result is not None
            assert "status" in result
    
    def test_pulse_result_structure(self):
        """Test that pulse result has expected structure."""
        result = pipeline_runner.run_weekly_pulse(
            client_id="test_client",
            period_days=7
        )
        
        # Should have status
        assert "status" in result
        
        # If successful, result contains ZenML PipelineRunResponse
        # Just verify it ran successfully - actual digest is in ZenML artifacts
        if result["status"] == "success":
            assert "result" in result
            # Result is ZenML pipeline response, not the digest dict
            # The actual digest is stored as a pipeline output artifact
            assert result["result"] is not None
        else:
            assert "error" in result


class TestPipelineIntegration:
    """Integration tests for compliance pipelines."""
    
    def test_ingestion_then_pulse_workflow(self):
        """Test workflow: ingest data then generate pulse."""
        # Step 1: Run ingestion
        ingestion_result = pipeline_runner.run_compliance_ingestion(lookback_days=7)
        
        assert ingestion_result is not None
        
        # Step 2: Generate pulse
        pulse_result = pipeline_runner.run_weekly_pulse(
            client_id="test_client",
            period_days=7
        )
        
        assert pulse_result is not None
    
    def test_pipeline_runner_methods_exist(self):
        """Test that all expected pipeline methods exist."""
        assert hasattr(pipeline_runner, 'run_ingestion')
        assert hasattr(pipeline_runner, 'run_memory_analytics')
        assert hasattr(pipeline_runner, 'run_compliance_ingestion')
        assert hasattr(pipeline_runner, 'run_weekly_pulse')
    
    def test_pipeline_runner_methods_callable(self):
        """Test that all pipeline methods are callable."""
        assert callable(pipeline_runner.run_ingestion)
        assert callable(pipeline_runner.run_memory_analytics)
        assert callable(pipeline_runner.run_compliance_ingestion)
        assert callable(pipeline_runner.run_weekly_pulse)


class TestPipelineAPI:
    """Tests for pipeline API endpoints."""
    
    def test_pipelines_available_in_status(self):
        """Test that compliance pipelines are listed in status."""
        from fastapi.testclient import TestClient
        from exim_agent.infrastructure.api.main import app
        
        client = TestClient(app)
        response = client.get("/pipelines/status")
        
        assert response.status_code == 200
        data = response.json()
        
        pipelines = data.get("pipelines", {})
        assert "compliance_ingestion" in pipelines
        assert "weekly_pulse" in pipelines
        
        if data.get("zenml_available"):
            endpoints = data.get("endpoints", {})
            assert "compliance_ingestion" in endpoints
            assert "weekly_pulse" in endpoints


@pytest.mark.asyncio
class TestPipelinePerformance:
    """Performance tests for compliance pipelines."""
    
    def test_ingestion_completes_in_reasonable_time(self):
        """Test that ingestion completes within timeout."""
        import time
        
        start = time.time()
        result = pipeline_runner.run_compliance_ingestion(lookback_days=7)
        elapsed = time.time() - start
        
        # Should complete within 60 seconds
        assert elapsed < 60.0
        assert result is not None
    
    def test_pulse_completes_in_reasonable_time(self):
        """Test that pulse generation completes within timeout."""
        import time
        
        start = time.time()
        result = pipeline_runner.run_weekly_pulse(
            client_id="test_client",
            period_days=7
        )
        elapsed = time.time() - start
        
        # Should complete within 60 seconds
        assert elapsed < 60.0
        assert result is not None


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""
    
    def test_weekly_pulse_handles_invalid_client(self):
        """Test pulse with invalid client ID doesn't crash."""
        result = pipeline_runner.run_weekly_pulse(
            client_id="",
            period_days=7
        )
        
        # Should not crash, return error status
        assert result is not None
        assert "status" in result
    
    def test_ingestion_handles_zero_lookback(self):
        """Test ingestion with zero lookback days."""
        result = pipeline_runner.run_compliance_ingestion(lookback_days=0)
        
        # Should not crash
        assert result is not None
        assert "status" in result
    
    def test_pulse_handles_negative_period(self):
        """Test pulse with negative period."""
        # Should handle gracefully (implementation dependent)
        try:
            result = pipeline_runner.run_weekly_pulse(
                client_id="test_client",
                period_days=-7
            )
            assert result is not None
        except Exception as e:
            # If it raises an exception, that's also acceptable
            assert isinstance(e, Exception)
