"""
Benchmark test for: api-package-404

Task: Return structured 404 errors for missing packages with detail, code, lookup fields.

Prompt:
The APIv4 package endpoint should return consistent error responses when packages 
are not found. Customize the PackageViewSet to return structured 404 errors.
Response format: {"detail": "Package not found", "code": "not_found", "lookup": "<slug_or_id>"}
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# These verify existing functionality that the LLM should NOT break
# =============================================================================

class TestPackageApiBaseline:
    """Baseline tests that verify existing package API functionality."""
    
    def test_package_list_endpoint_exists(self, api_client):
        """BASELINE: GET /api/v4/packages/ endpoint should exist and return 200."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200, "Package list endpoint should return 200"
    
    def test_package_list_returns_json(self, api_client):
        """BASELINE: Package list should return JSON response."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict)), "Response should be JSON"
    
    def test_nonexistent_package_returns_404_status(self, api_client):
        """BASELINE: Nonexistent package should return 404 status code."""
        response = api_client.get("/api/v4/packages/nonexistent-package-xyz/")
        assert response.status_code == 404, "Missing package should return 404"
    
    def test_nonexistent_package_returns_json(self, api_client):
        """BASELINE: 404 response should be JSON."""
        response = api_client.get("/api/v4/packages/nonexistent-package-xyz/")
        assert response.status_code == 404
        # Should be able to parse as JSON
        data = response.json()
        assert isinstance(data, dict), "404 response should be a JSON object"
    
    def test_404_response_has_detail_field(self, api_client):
        """BASELINE: DRF already includes 'detail' field in 404 responses."""
        response = api_client.get("/api/v4/packages/nonexistent-package-xyz/")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data, "DRF 404 responses include 'detail' field by default"


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# These verify the new functionality that needs to be implemented
# =============================================================================

class TestPackage404HasCodeField:
    """Tests for 404 responses including 'code' field."""
    
    def test_package_404_has_code_field(self, api_client):
        """TASK: 404 response should include 'code' field."""
        response = api_client.get("/api/v4/packages/nonexistent-package/")
        assert response.status_code == 404
        
        data = response.json()
        assert "code" in data, "404 response should include 'code' field"
    
    def test_package_404_code_is_not_found(self, api_client):
        """TASK: 404 response 'code' should be 'not_found'."""
        response = api_client.get("/api/v4/packages/nonexistent-package/")
        assert response.status_code == 404
        
        data = response.json()
        assert "code" in data, "404 response should include 'code' field"
        assert data["code"] == "not_found", "code should be 'not_found'"


class TestPackage404IncludesLookupValue:
    """Tests for 404 responses including the lookup value that failed."""
    
    def test_package_404_has_lookup_field(self, api_client):
        """TASK: 404 response should include 'lookup' field."""
        response = api_client.get("/api/v4/packages/my-missing-package/")
        assert response.status_code == 404
        
        data = response.json()
        assert "lookup" in data, "404 response should include 'lookup' field"
    
    def test_package_404_lookup_matches_request(self, api_client):
        """TASK: 404 'lookup' field should contain the requested identifier."""
        response = api_client.get("/api/v4/packages/my-missing-package/")
        assert response.status_code == 404
        
        data = response.json()
        assert "lookup" in data, "404 response should include 'lookup' field"
        assert data["lookup"] == "my-missing-package", "lookup should match requested slug"
