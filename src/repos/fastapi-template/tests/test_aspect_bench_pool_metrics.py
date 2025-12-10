"""
Benchmark tests for: connection-pool-metrics

PROMPT SAYS:
"Add a metrics endpoint for database connection pool status. 
GET /api/v1/utils/db-pool-status returning pool_size, checked_out, checked_in,
overflow, invalid. Require superuser auth. Include 'healthy' boolean."

Tests based SOLELY on prompt requirements:
1. Endpoint exists at correct path
2. Returns pool metrics
3. Requires superuser auth
4. Includes health indicator
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings


pytestmark = pytest.mark.aspect_bench


class TestPoolMetricsEndpointExists:
    """Test that pool metrics endpoint exists."""
    
    def test_endpoint_exists(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Pool metrics endpoint should exist."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        # Should not be 404
        assert response.status_code != 404, \
            "GET /api/v1/utils/db-pool-status endpoint must exist"
    
    def test_endpoint_returns_json(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Endpoint should return JSON response."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")


class TestPoolMetricsAuth:
    """Test authentication requirements."""
    
    def test_requires_authentication(
        self, client: TestClient
    ) -> None:
        """Endpoint should require authentication."""
        response = client.get(f"{settings.API_V1_STR}/utils/db-pool-status")
        
        assert response.status_code in (401, 403), \
            "Pool metrics endpoint must require authentication"
    
    def test_requires_superuser(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """Endpoint should require superuser privileges."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=normal_user_token_headers,
        )
        
        assert response.status_code == 403, \
            "Pool metrics endpoint must require superuser"
    
    def test_superuser_can_access(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Superuser should be able to access endpoint."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200


class TestPoolMetricsContent:
    """Test that response contains required metrics."""
    
    def test_has_pool_size(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response should include pool_size."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        assert "pool_size" in data, "Response must include pool_size"
        assert isinstance(data["pool_size"], int)
    
    def test_has_checked_out(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response should include checked_out (connections in use)."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        assert "checked_out" in data or "in_use" in data or "active" in data, \
            "Response must include checked_out/in_use/active connections"
    
    def test_has_checked_in(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response should include checked_in (idle connections)."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        assert "checked_in" in data or "idle" in data or "available" in data, \
            "Response must include checked_in/idle/available connections"
    
    def test_has_overflow(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response should include overflow count."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        assert "overflow" in data or "max_overflow" in data, \
            "Response must include overflow info"
    
    def test_has_healthy_indicator(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response should include healthy boolean."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        assert "healthy" in data or "status" in data, \
            "Response must include healthy/status indicator"
        
        if "healthy" in data:
            assert isinstance(data["healthy"], bool)


class TestPoolMetricsAccuracy:
    """Test that metrics are accurate."""
    
    def test_metrics_are_non_negative(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """All numeric metrics should be non-negative."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        
        for key, value in data.items():
            if isinstance(value, (int, float)) and key != "overflow":
                assert value >= 0, f"{key} must be non-negative"
    
    def test_healthy_true_when_pool_ok(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Healthy should be true when pool is functioning normally."""
        response = client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        
        # If we can make the request, pool should be healthy
        if "healthy" in data:
            assert data["healthy"] is True


class TestNoPerformanceImpact:
    """Test that metrics don't impact normal operations."""
    
    def test_items_endpoint_still_works(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Regular endpoints should still work normally."""
        # Get metrics
        client.get(
            f"{settings.API_V1_STR}/utils/db-pool-status",
            headers=superuser_token_headers,
        )
        
        # Normal operations should still work
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200
    
    def test_multiple_metrics_calls_work(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Multiple calls to metrics should work."""
        for _ in range(5):
            response = client.get(
                f"{settings.API_V1_STR}/utils/db-pool-status",
                headers=superuser_token_headers,
            )
            assert response.status_code == 200
