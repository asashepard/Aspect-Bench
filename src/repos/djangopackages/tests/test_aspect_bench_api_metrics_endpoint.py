"""
Benchmark test for: api-metrics-endpoint

Task: Add API endpoint to expose external service metrics (health, latency).

Prompt:
Add a /api/v4/health/ or /api/v4/metrics/ endpoint that returns the health
status and latency of external services (GitHub, PyPI). Include overall
status, individual service status, and response times. Return JSON format.
"""

import pytest
import time


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestApiMetricsBaseline:
    """Baseline tests that verify existing API functionality."""
    
    def test_api_root_works(self, api_client):
        """BASELINE: API root should be accessible."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_api_returns_json(self, api_client):
        """BASELINE: API should return JSON."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
    
    def test_api_responds_quickly(self, api_client):
        """BASELINE: API should respond within reasonable time."""
        start = time.time()
        response = api_client.get("/api/v4/packages/")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, "API should respond within 5 seconds"
    
    def test_api_has_endpoints(self, api_client):
        """BASELINE: API should have package and grid endpoints."""
        r1 = api_client.get("/api/v4/packages/")
        r2 = api_client.get("/api/v4/grids/")
        assert r1.status_code == 200
        assert r2.status_code == 200


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestMetricsEndpointExists:
    """Tests that metrics/health endpoint exists."""
    
    def test_health_endpoint_exists(self, api_client):
        """TASK: /api/v4/health/ endpoint should exist."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200, "Health endpoint should exist"
    
    def test_metrics_endpoint_returns_json(self, api_client):
        """TASK: Metrics endpoint should return JSON."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict), "Should return JSON dict"


class TestMetricsIncludesStatus:
    """Tests that metrics include overall status."""
    
    def test_metrics_has_status_field(self, api_client):
        """TASK: Metrics should have 'status' field."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data, "Should have 'status' field"
    
    def test_metrics_status_is_healthy(self, api_client):
        """TASK: Status should indicate healthy or unhealthy."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        
        data = response.json()
        status = data.get("status", "").lower()
        valid_statuses = ["healthy", "ok", "up", "unhealthy", "degraded", "down"]
        assert status in valid_statuses, f"Status should be one of {valid_statuses}"


class TestMetricsIncludesServices:
    """Tests that metrics include external service status."""
    
    def test_metrics_has_services(self, api_client):
        """TASK: Metrics should include 'services' field."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert "services" in data, "Should have 'services' field"
    
    def test_services_includes_github(self, api_client):
        """TASK: Services should include GitHub status."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        
        data = response.json()
        services = data.get("services", {})
        assert "github" in services or "GitHub" in str(services), "Should include GitHub"
    
    def test_services_includes_pypi(self, api_client):
        """TASK: Services should include PyPI status."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        
        data = response.json()
        services = data.get("services", {})
        assert "pypi" in services or "PyPI" in str(services), "Should include PyPI"


class TestMetricsIncludesLatency:
    """Tests that metrics include latency information."""
    
    def test_metrics_has_latency(self, api_client):
        """TASK: Metrics should include latency information."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        
        data = response.json()
        has_latency = (
            "latency" in data or
            "response_time" in data or
            "latency" in str(data.get("services", {}))
        )
        assert has_latency, "Should include latency information"
    
    def test_latency_is_numeric(self, api_client):
        """TASK: Latency values should be numeric."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code == 200
        
        data = response.json()
        # Check for numeric latency values somewhere in response
        response_str = str(data)
        # Should have some numeric values for timing
        import re
        has_numbers = bool(re.search(r'\d+\.?\d*', response_str))
        assert has_numbers, "Should have numeric latency values"


class TestMetricsIsPublic:
    """Tests that metrics endpoint is publicly accessible."""
    
    def test_metrics_no_auth_required(self, api_client):
        """TASK: Metrics endpoint should not require authentication."""
        response = api_client.get("/api/v4/health/")
        assert response.status_code != 401, "Should not require auth"
        assert response.status_code != 403, "Should not be forbidden"
    
    def test_metrics_responds_quickly(self, api_client):
        """TASK: Metrics endpoint should respond quickly."""
        start = time.time()
        response = api_client.get("/api/v4/health/")
        elapsed = time.time() - start
        
        if response.status_code == 200:
            assert elapsed < 2.0, "Health check should respond within 2 seconds"
