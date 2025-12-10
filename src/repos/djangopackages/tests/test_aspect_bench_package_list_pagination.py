"""
Benchmark test for: package-list-pagination

Task: Switch package list endpoint from LimitOffsetPagination to PageNumberPagination.

Prompt:
The package list endpoint currently uses LimitOffsetPagination which exposes
implementation details. Change to PageNumberPagination for a cleaner API.
Response should use 'page' parameter instead of 'offset' for navigation.
The 'next' and 'previous' URLs should use page= not offset=.
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestPackageListBaseline:
    """Baseline tests that verify existing package list functionality."""
    
    def test_package_list_endpoint_exists(self, api_client):
        """BASELINE: Package list endpoint should exist and return 200."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_package_list_returns_json(self, api_client):
        """BASELINE: Package list should return valid JSON."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
    
    def test_package_appears_in_list(self, api_client, package):
        """BASELINE: Created package should appear in list."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        data = response.json()
        # Package should be somewhere in the response
        assert package.slug in str(data)
    
    def test_package_list_has_count_field(self, api_client, package):
        """BASELINE: Response should have count field (pagination exists)."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestPageNumberPaginationUsed:
    """Tests that PageNumberPagination is being used, not LimitOffset."""
    
    def test_page_parameter_works_not_ignored(self, api_client):
        """TASK: page= parameter should be recognized and not ignored."""
        # With LimitOffsetPagination, page= parameter is ignored
        # With PageNumberPagination, page= parameter controls paging
        response1 = api_client.get("/api/v4/packages/?page=1")
        response2 = api_client.get("/api/v4/packages/?page=99999")
        
        assert response1.status_code == 200
        # If PageNumber is used, page=99999 should either return 404 or empty results
        # If LimitOffset is used, page= is ignored and both return same thing
        if response2.status_code == 404:
            pass  # PageNumber with strict mode
        elif response2.status_code == 200:
            data2 = response2.json()
            # PageNumber with non-strict should show different/empty results for high page
            results = data2.get("results", [])
            # This should be empty or different from page 1
            assert len(results) == 0, "High page number should return empty results with PageNumberPagination"
    
    def test_invalid_page_returns_404_or_empty(self, api_client, package):
        """TASK: Invalid page number should return 404 or empty results."""
        response = api_client.get("/api/v4/packages/?page=99999")
        
        if response.status_code == 404:
            pass  # PageNumber strict mode returns 404
        elif response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            assert len(results) == 0, "Invalid page should return empty results"
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


class TestNoOffsetParameter:
    """Tests that offset= is not the primary navigation."""
    
    def test_offset_parameter_not_recognized_as_primary(self, api_client, package):
        """TASK: offset= should not be the primary pagination parameter."""
        # With LimitOffset: offset= is recognized and used
        # With PageNumber: offset= is ignored, only page= matters
        
        # Request with offset=10 - with LimitOffset this skips items
        # With PageNumber this should be ignored
        response = api_client.get("/api/v4/packages/?offset=10")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        # With LimitOffset, offset=10 would skip first 10 items
        # With PageNumber, offset is ignored and you get first page
        # If we have at least 1 package and it appears, PageNumber is working
        assert package.slug in str(results), "offset= should be ignored with PageNumberPagination"
    
    def test_page_size_not_limit(self, api_client, package):
        """TASK: page_size= should be used, not limit=."""
        # With LimitOffset: limit= controls page size
        # With PageNumber: page_size= controls page size
        
        # This test verifies page_size works
        response = api_client.get("/api/v4/packages/?page_size=1")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", [])
        
        # Should respect page_size
        assert len(results) <= 1, "page_size=1 should return at most 1 result"
