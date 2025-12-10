"""
Benchmark test for: api-error-schema

Task: Standardize all API error responses with consistent schema.

Prompt:
All API errors should follow a consistent schema across all endpoints.
Create a custom exception handler for DRF that returns:
{"detail": "...", "code": "...", "field": "..." (optional)}
Apply to all apiv4 endpoints.
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestApiErrorsBaseline:
    """Baseline tests that verify existing API error behavior."""
    
    def test_404_returns_json_response(self, api_client):
        """BASELINE: 404 errors should return JSON, not HTML."""
        response = api_client.get("/api/v4/packages/nonexistent/")
        assert response.status_code == 404
        # Should be parseable as JSON
        data = response.json()
        assert isinstance(data, dict), "Error response should be a dict"
    
    def test_api_list_endpoint_works(self, api_client):
        """BASELINE: API list endpoint should work correctly."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_grid_api_list_endpoint_works(self, api_client):
        """BASELINE: Grid API list endpoint should work correctly."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
    
    def test_error_response_is_dict(self, api_client):
        """BASELINE: Error responses should be dictionaries, not strings."""
        response = api_client.get("/api/v4/packages/nonexistent/")
        if response.status_code >= 400:
            data = response.json()
            assert isinstance(data, dict), "Error should be a dict"
    
    def test_404_has_detail_field(self, api_client):
        """BASELINE: DRF 404 errors include 'detail' field by default."""
        response = api_client.get("/api/v4/packages/nonexistent/")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data, "DRF 404 has detail field"


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestErrorSchemaHasCodeField:
    """Tests for error responses including 'code' field."""
    
    def test_404_error_has_code_field(self, api_client):
        """TASK: 404 errors should have code field."""
        response = api_client.get("/api/v4/packages/nonexistent/")
        assert response.status_code == 404
        
        data = response.json()
        assert "code" in data, "404 error should have 'code' field"
    
    def test_404_code_is_not_found(self, api_client):
        """TASK: 404 errors should have code='not_found'."""
        response = api_client.get("/api/v4/packages/nonexistent/")
        assert response.status_code == 404
        
        data = response.json()
        assert data.get("code") == "not_found", "code should be 'not_found'"


class TestAuthErrorHasCode:
    """Tests for authentication errors having code field."""
    
    def test_auth_error_has_code_field(self, api_client):
        """TASK: 401 auth errors should include code field."""
        # Try to access protected endpoint without auth
        response = api_client.delete("/api/v4/packages/test/")
        if response.status_code in (401, 403):
            data = response.json()
            assert "code" in data, "Auth errors should have 'code' field"
    
    def test_auth_error_code_value(self, api_client):
        """TASK: Auth error code should be 'authentication_required' or 'permission_denied'."""
        response = api_client.delete("/api/v4/packages/test/")
        if response.status_code in (401, 403):
            data = response.json()
            valid_codes = ["authentication_required", "permission_denied", "not_authenticated"]
            assert data.get("code") in valid_codes, f"Auth code should be one of {valid_codes}"


class TestValidationErrorFormat:
    """Tests for validation error format with field names."""
    
    def test_validation_error_has_code(self, api_client):
        """TASK: Validation errors should have code field."""
        response = api_client.post("/api/v4/packages/", {})
        if response.status_code == 400:
            data = response.json()
            assert "code" in data, "Validation errors should have 'code' field"
    
    def test_validation_error_has_field_info(self, api_client):
        """TASK: Validation errors should include field information."""
        response = api_client.post("/api/v4/packages/", {})
        if response.status_code == 400:
            data = response.json()
            # Should have field-level errors or a fields list
            has_field_info = "field" in data or "fields" in data or any(
                k for k in data.keys() if k not in ("detail", "code")
            )
            assert has_field_info, "Validation errors should include field info"


class TestConsistentErrorFormat:
    """Tests for all errors having consistent format."""
    
    def test_all_errors_have_detail(self, api_client):
        """TASK: All error types should have 'detail' field."""
        # Test 404
        r1 = api_client.get("/api/v4/packages/nonexistent/")
        assert "detail" in r1.json(), "404 should have detail"
        
        # Test 401/403
        r2 = api_client.delete("/api/v4/packages/test/")
        if r2.status_code in (401, 403, 405):
            assert "detail" in r2.json(), "Auth error should have detail"
    
    def test_error_detail_is_string(self, api_client):
        """TASK: Error 'detail' should be a human-readable string."""
        response = api_client.get("/api/v4/packages/nonexistent/")
        assert response.status_code == 404
        
        data = response.json()
        assert isinstance(data.get("detail"), str), "detail should be a string"
        assert len(data.get("detail", "")) > 0, "detail should not be empty"
