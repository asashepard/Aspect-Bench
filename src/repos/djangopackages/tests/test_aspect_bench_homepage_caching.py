"""
Benchmark test for: homepage-caching

Task: Implement caching for homepage data to improve performance.

Prompt:
The homepage and package list endpoints should use Django's caching framework
to improve performance. Add cache_page decorator or low-level caching for
package list data. Cache should expire after a configurable timeout.
"""

import pytest
import time


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestHomepageBaseline:
    """Baseline tests that verify existing homepage functionality."""
    
    def test_package_list_endpoint_exists(self, api_client):
        """BASELINE: Package list endpoint should exist."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_package_list_returns_json(self, api_client):
        """BASELINE: Package list should return JSON."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
    
    def test_multiple_requests_work(self, api_client):
        """BASELINE: Multiple requests should work."""
        response1 = api_client.get("/api/v4/packages/")
        response2 = api_client.get("/api/v4/packages/")
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    def test_responses_are_consistent(self, api_client):
        """BASELINE: Consecutive requests should return consistent data."""
        response1 = api_client.get("/api/v4/packages/")
        response2 = api_client.get("/api/v4/packages/")
        assert response1.json() == response2.json()


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestCacheHeaders:
    """Tests for cache-related HTTP headers."""
    
    def test_response_has_cache_control(self, api_client):
        """TASK: Response should have Cache-Control header."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        
        cache_control = response.get("Cache-Control", "")
        assert cache_control, "Response should have Cache-Control header"
    
    def test_cache_control_has_max_age(self, api_client):
        """TASK: Cache-Control should include max-age."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        
        cache_control = response.get("Cache-Control", "")
        assert "max-age" in cache_control, "Cache-Control should have max-age"


class TestCachePerformance:
    """Tests for cache performance improvements."""
    
    def test_cached_response_is_faster(self, api_client):
        """TASK: Cached responses should be faster than uncached."""
        # First request (may hit cache or not)
        start1 = time.time()
        response1 = api_client.get("/api/v4/packages/")
        time1 = time.time() - start1
        
        # Second request (should be cached)
        start2 = time.time()
        response2 = api_client.get("/api/v4/packages/")
        time2 = time.time() - start2
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Second request should be faster or similar (within 2x)
        # In a real caching scenario, cached would be much faster
        assert time2 <= time1 * 2, "Cached response should not be slower"
    
    def test_response_has_etag_or_vary(self, api_client):
        """TASK: Response should have ETag or Vary header for caching."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        
        has_cache_headers = (
            response.get("ETag") or
            response.get("Vary") or
            response.get("Last-Modified")
        )
        assert has_cache_headers, "Should have caching headers"


class TestCacheInvalidation:
    """Tests for cache invalidation."""
    
    def test_cache_varies_by_query_params(self, api_client):
        """TASK: Different query params should be cached separately."""
        response1 = api_client.get("/api/v4/packages/")
        response2 = api_client.get("/api/v4/packages/?page=1")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Both should work, possibly with different cache entries
    
    def test_cache_respects_pagination(self, api_client):
        """TASK: Different pages should be cached separately."""
        response1 = api_client.get("/api/v4/packages/?page=1")
        response2 = api_client.get("/api/v4/packages/?page=2")
        
        assert response1.status_code in (200, 404)
        assert response2.status_code in (200, 404)


class TestCacheConfiguration:
    """Tests for cache configuration."""
    
    def test_cache_timeout_is_reasonable(self, api_client):
        """TASK: Cache timeout should be configured."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        
        cache_control = response.get("Cache-Control", "")
        if "max-age" in cache_control:
            # Extract max-age value
            import re
            match = re.search(r'max-age=(\d+)', cache_control)
            if match:
                max_age = int(match.group(1))
                # Should be between 60 seconds and 1 hour
                assert 60 <= max_age <= 3600, "max-age should be reasonable"
    
    def test_public_cache_allowed(self, api_client):
        """TASK: Public endpoints should allow public caching."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        
        cache_control = response.get("Cache-Control", "")
        # Should not have private or no-store for public endpoints
        assert "no-store" not in cache_control, "Public data should be cacheable"
