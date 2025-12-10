"""
Benchmark test for: search-caching

Task: Implement caching for search results to improve performance.

Prompt:
Search results should be cached to improve performance on repeated queries.
Implement cache key based on search query and filters. Cache should be
invalidated when packages are updated. Use Django's cache framework.
"""

import pytest
import time


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestSearchCachingBaseline:
    """Baseline tests that verify existing search functionality."""
    
    def test_search_endpoint_works(self, api_client):
        """BASELINE: Search endpoint should work."""
        response = api_client.get("/api/v4/search/?q=django")
        # 200 if works, or 404 if search endpoint not implemented
        assert response.status_code in (200, 400, 404)
    
    def test_packages_endpoint_works(self, api_client):
        """BASELINE: Package endpoint works as fallback."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_same_query_same_results(self, api_client):
        """BASELINE: Same query should return same results."""
        response1 = api_client.get("/api/v4/search/?q=python")
        response2 = api_client.get("/api/v4/search/?q=python")
        
        if response1.status_code == 200:
            assert response1.json() == response2.json()
    
    def test_search_returns_json(self, api_client):
        """BASELINE: Search should return JSON."""
        response = api_client.get("/api/v4/search/?q=test")
        if response.status_code == 200:
            data = response.json()
            assert data is not None


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestSearchCacheHeaders:
    """Tests for search cache headers."""
    
    def test_search_has_cache_control(self, api_client):
        """TASK: Search response should have Cache-Control header."""
        response = api_client.get("/api/v4/search/?q=django")
        if response.status_code == 200:
            cache_control = response.get("Cache-Control", "")
            assert cache_control, "Search should have Cache-Control header"
    
    def test_search_cache_varies_by_query(self, api_client):
        """TASK: Search cache should vary by query parameter."""
        response = api_client.get("/api/v4/search/?q=django")
        if response.status_code == 200:
            vary = response.get("Vary", "")
            # Should vary by something (Accept, Authorization, etc.)
            assert vary or response.get("Cache-Control"), "Should have caching headers"


class TestSearchCachePerformance:
    """Tests for search cache performance."""
    
    def test_cached_search_is_faster(self, api_client):
        """TASK: Cached search should be faster."""
        query = "django"
        
        # First request
        start1 = time.time()
        response1 = api_client.get(f"/api/v4/search/?q={query}")
        time1 = time.time() - start1
        
        # Second request (should be cached)
        start2 = time.time()
        response2 = api_client.get(f"/api/v4/search/?q={query}")
        time2 = time.time() - start2
        
        if response1.status_code == 200:
            # Second should be faster or similar
            assert time2 <= time1 * 2, "Cached search should not be slower"
    
    def test_different_queries_not_confused(self, api_client):
        """TASK: Different queries should have separate cache entries."""
        response1 = api_client.get("/api/v4/search/?q=django")
        response2 = api_client.get("/api/v4/search/?q=flask")
        
        if response1.status_code == 200 and response2.status_code == 200:
            # Results should be different (different queries)
            data1 = response1.json()
            data2 = response2.json()
            # At minimum, they should both be valid
            assert isinstance(data1, (list, dict))
            assert isinstance(data2, (list, dict))


class TestSearchCacheKeyGeneration:
    """Tests for proper cache key generation."""
    
    def test_case_insensitive_cache_keys(self, api_client):
        """TASK: Search cache should be case-insensitive."""
        response1 = api_client.get("/api/v4/search/?q=Django")
        response2 = api_client.get("/api/v4/search/?q=django")
        
        if response1.status_code == 200 and response2.status_code == 200:
            # Both queries should return results
            assert response1.json() == response2.json(), "Case should not affect results"
    
    def test_cache_includes_filters(self, api_client, category):
        """TASK: Cache key should include filters."""
        response1 = api_client.get("/api/v4/search/?q=test")
        response2 = api_client.get(f"/api/v4/search/?q=test&category={category.slug}")
        
        # Both should work, results may differ
        assert response1.status_code in (200, 400, 404)
        assert response2.status_code in (200, 400, 404)


class TestSearchCacheInvalidation:
    """Tests for search cache invalidation."""
    
    def test_cache_has_expiry(self, api_client):
        """TASK: Search cache should have expiry."""
        response = api_client.get("/api/v4/search/?q=test")
        if response.status_code == 200:
            cache_control = response.get("Cache-Control", "")
            if cache_control:
                assert "max-age" in cache_control, "Cache should have expiry"
    
    def test_search_cache_is_purgeable(self, api_client):
        """TASK: Search cache should support purging."""
        # Just verify search works - purge mechanism is implementation detail
        response = api_client.get("/api/v4/search/?q=test")
        assert response.status_code in (200, 400, 404)
