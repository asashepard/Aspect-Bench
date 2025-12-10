"""
Benchmark test for: api-grid-404

Task: Return structured 404 errors for missing grids with detail, code, lookup fields.

Prompt:
The APIv4 grid endpoint should return consistent error responses when grids 
are not found. Customize the GridViewSet to return structured 404 errors.
Response format: {"detail": "Grid not found", "code": "not_found", "lookup": "<slug_or_id>"}
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestGridApiBaseline:
    """Baseline tests that verify existing grid API functionality."""
    
    def test_grid_list_endpoint_exists(self, api_client):
        """BASELINE: GET /api/v4/grids/ endpoint should exist and return 200."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200, "Grid list endpoint should return 200"
    
    def test_grid_list_returns_json(self, api_client):
        """BASELINE: Grid list should return JSON response."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict)), "Response should be JSON"
    
    def test_existing_grid_returns_200(self, api_client, grid):
        """BASELINE: Existing grid should return 200."""
        url = f"/api/v4/grids/{grid.slug}/"
        response = api_client.get(url)
        assert response.status_code == 200, f"Existing grid {grid.slug} should return 200"
    
    def test_nonexistent_grid_returns_404_status(self, api_client):
        """BASELINE: Nonexistent grid should return 404 status code."""
        response = api_client.get("/api/v4/grids/nonexistent-grid-xyz/")
        assert response.status_code == 404, "Missing grid should return 404"


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestGrid404HasDetailField:
    """Tests for 404 responses including 'detail' field."""
    
    def test_grid_404_by_slug_has_detail_field(self, api_client):
        """TASK: 404 response should include 'detail' field with clear message."""
        response = api_client.get("/api/v4/grids/nonexistent-grid/")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data, "404 response must include 'detail' field"
        assert isinstance(data["detail"], str), "detail should be a string"
    
    def test_grid_404_by_id_has_detail_field(self, api_client):
        """TASK: 404 response by ID should include 'detail' field."""
        response = api_client.get("/api/v4/grids/99999/")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data, "404 response must include 'detail' field"


class TestGrid404HasCodeField:
    """Tests for 404 responses including 'code' field."""
    
    def test_grid_404_has_code_field(self, api_client):
        """TASK: 404 response should include 'code' field."""
        response = api_client.get("/api/v4/grids/nonexistent-grid/")
        assert response.status_code == 404
        
        data = response.json()
        assert "code" in data, "404 response should include 'code' field"
    
    def test_grid_404_code_is_not_found(self, api_client):
        """TASK: 404 response 'code' should be 'not_found'."""
        response = api_client.get("/api/v4/grids/nonexistent-grid/")
        assert response.status_code == 404
        
        data = response.json()
        assert data.get("code") == "not_found", "code should be 'not_found'"


class TestGrid404IncludesLookupValue:
    """Tests for 404 responses including the lookup value that failed."""
    
    def test_grid_404_has_lookup_field(self, api_client):
        """TASK: 404 response should include 'lookup' field."""
        response = api_client.get("/api/v4/grids/my-missing-grid/")
        assert response.status_code == 404
        
        data = response.json()
        assert "lookup" in data, "404 response should include 'lookup' field"
    
    def test_grid_404_lookup_matches_request(self, api_client):
        """TASK: 404 'lookup' field should contain the requested identifier."""
        response = api_client.get("/api/v4/grids/my-missing-grid/")
        assert response.status_code == 404
        
        data = response.json()
        assert data.get("lookup") == "my-missing-grid", "lookup should match requested slug"
