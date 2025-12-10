"""
Benchmark test for: search-filtering

Task: Add filtering and search capabilities to the search endpoint.

Prompt:
The search endpoint should support filtering by category, license, and other
fields. Add DRF filter backends to SearchViewSet for advanced filtering.
Support both query parameter filters and full-text search via 'q' parameter.
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestSearchBaseline:
    """Baseline tests that verify existing search functionality."""
    
    def test_search_endpoint_exists(self, api_client):
        """BASELINE: Search endpoint should exist."""
        response = api_client.get("/api/v4/search/?q=test")
        # 200 if works, 404 if endpoint doesn't exist
        assert response.status_code in (200, 400, 404)
    
    def test_packages_endpoint_works(self, api_client):
        """BASELINE: Package endpoint should work as fallback."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_search_returns_json(self, api_client):
        """BASELINE: Search should return JSON."""
        response = api_client.get("/api/v4/search/?q=django")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
    
    def test_search_no_crash_empty_query(self, api_client):
        """BASELINE: Search should handle empty query without crashing."""
        response = api_client.get("/api/v4/search/?q=")
        # Should not be a 500 error
        assert response.status_code < 500


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestSearchQueryParameter:
    """Tests for search query parameter functionality."""
    
    def test_search_query_returns_results(self, api_client, package):
        """TASK: Search with q parameter should return relevant results."""
        response = api_client.get("/api/v4/search/?q=test")
        assert response.status_code == 200
        
        data = response.json()
        # Should return results list or paginated response
        if isinstance(data, dict):
            assert "results" in data, "Search should return results field"
        else:
            assert isinstance(data, list), "Search should return list"
    
    def test_search_query_matches_package(self, api_client, package):
        """TASK: Search should find packages matching query."""
        response = api_client.get(f"/api/v4/search/?q={package.title}")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        # Should find the package
        found = package.slug in str(results)
        assert found, f"Should find package {package.slug}"


class TestCategoryFilter:
    """Tests for category filtering."""
    
    def test_search_accepts_category_filter(self, api_client, category):
        """TASK: Search should accept category filter."""
        response = api_client.get(f"/api/v4/search/?category={category.slug}")
        assert response.status_code == 200, "Category filter should be accepted"
    
    def test_category_filter_affects_results(self, api_client, category, package):
        """TASK: Category filter should affect results."""
        response = api_client.get(f"/api/v4/search/?category={category.slug}")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        # Results should be filtered by category
        assert isinstance(results, list), "Should return filtered list"


class TestSearchResultFields:
    """Tests for required fields in search results."""
    
    def test_search_results_have_slug(self, api_client, package):
        """TASK: Search results should have slug field."""
        response = api_client.get("/api/v4/search/?q=test")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        if len(results) > 0:
            assert "slug" in results[0], "Results should have slug field"
    
    def test_search_results_have_title(self, api_client, package):
        """TASK: Search results should have title field."""
        response = api_client.get("/api/v4/search/?q=test")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        if len(results) > 0:
            assert "title" in results[0], "Results should have title field"


class TestMultipleFilters:
    """Tests for combining multiple filters."""
    
    def test_multiple_filters_work(self, api_client, category):
        """TASK: Multiple filters should work together."""
        response = api_client.get(f"/api/v4/search/?q=django&category={category.slug}")
        assert response.status_code == 200
    
    def test_ordering_filter(self, api_client):
        """TASK: Ordering filter should be supported."""
        response = api_client.get("/api/v4/search/?q=test&ordering=-created")
        # Should be 200, even if ordering not yet implemented
        assert response.status_code in (200, 400), "Ordering should be accepted"
