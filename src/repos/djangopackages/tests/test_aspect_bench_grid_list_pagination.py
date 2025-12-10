"""
Benchmark test for: grid-list-pagination

Task: Switch grid list pagination from LimitOffset to PageNumber pagination.

Prompt:
The grid list endpoint currently uses LimitOffsetPagination (with limit/offset params).
Switch to PageNumberPagination with page/page_size parameters for better usability.
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestGridListBaseline:
    """Baseline tests that verify existing grid list functionality."""
    
    def test_grid_list_endpoint_exists(self, api_client):
        """BASELINE: Grid list endpoint should exist and return 200."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
    
    def test_grid_list_returns_json(self, api_client):
        """BASELINE: Grid list should return valid JSON."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
    
    def test_grid_list_has_count(self, api_client):
        """BASELINE: Paginated list has count field."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
    
    def test_grid_list_has_results(self, api_client):
        """BASELINE: Paginated list has results field."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# Switch from LimitOffsetPagination to PageNumberPagination
# =============================================================================

class TestPageNumberPaginationParams:
    """Tests for page/page_size parameters (PageNumberPagination)."""
    
    def test_page_size_in_url_params(self, api_client):
        """TASK: Response links should use page_size, not limit."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        
        data = response.json()
        # Check if next/previous URLs use page-style params
        next_url = data.get("next") or ""
        # LimitOffsetPagination uses 'limit=' and 'offset='
        # PageNumberPagination uses 'page=' and 'page_size='
        if next_url:
            assert "offset=" not in next_url, "next URL should not contain offset= (use page= instead)"
    
    def test_response_uses_page_not_offset(self, api_client):
        """TASK: Pagination links should use page parameter."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        
        data = response.json()
        next_url = data.get("next") or ""
        if next_url:
            assert "page=" in next_url, "next URL should contain page= (PageNumberPagination)"


class TestLimitOffsetParamsNotUsed:
    """Tests to verify LimitOffsetPagination is NOT used."""
    
    def test_limit_param_not_in_navigation(self, api_client):
        """TASK: Navigation links should NOT use 'limit' param."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        
        data = response.json()
        next_url = data.get("next") or ""
        prev_url = data.get("previous") or ""
        
        # With PageNumberPagination, neither limit nor offset should appear
        assert "limit=" not in next_url, "next URL should not contain limit="
        assert "limit=" not in prev_url, "previous URL should not contain limit="
    
    def test_offset_param_not_in_navigation(self, api_client):
        """TASK: Navigation links should NOT use 'offset' param."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        
        data = response.json()
        next_url = data.get("next") or ""
        prev_url = data.get("previous") or ""
        
        # With PageNumberPagination, offset should not appear
        assert "offset=" not in next_url, "next URL should not contain offset="
        assert "offset=" not in prev_url, "previous URL should not contain offset="
        
        # With PageNumberPagination, limit should be IGNORED
        # So results count should be the same
        assert len(data_limit.get("results", [])) == len(data_default.get("results", [])), \
            "'limit' param should be ignored with PageNumberPagination"
    
    def test_offset_param_not_recognized(self, api_client, grid):
        """TASK: 'offset' param should NOT affect results (PageNumberPagination doesn't use it)."""
        # With LimitOffsetPagination, 'offset=10' skips first 10 results
        # With PageNumberPagination, 'offset' is ignored
        response_with_offset = api_client.get("/api/v4/grids/?offset=10")
        response_default = api_client.get("/api/v4/grids/")
        
        data_offset = response_with_offset.json()
        data_default = response_default.json()
        
        # With PageNumberPagination, offset should be IGNORED
        assert len(data_offset.get("results", [])) == len(data_default.get("results", [])), \
            "'offset' param should be ignored with PageNumberPagination"
