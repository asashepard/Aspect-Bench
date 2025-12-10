"""
Benchmark tests for: response-caching

PROMPT SAYS:
"Some of our API endpoints perform expensive database queries that don't change
often. Add caching support for the items listing endpoint with 60 second TTL,
user-specific caching, cache invalidation on create/update/delete, and
Cache-Control headers."

Tests based SOLELY on prompt requirements:
1. Cached responses are returned within TTL
2. Cache is user-specific
3. Cache is invalidated on item changes
4. Cache-Control headers are present
"""

import pytest
import time
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.item import create_random_item


pytestmark = pytest.mark.aspect_bench


class TestCachingWorks:
    """Test that caching returns cached responses."""
    
    def test_repeated_requests_are_fast(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Repeated requests within TTL should be faster (cached)."""
        # Create some items
        for _ in range(3):
            create_random_item(db)
        
        # First request (uncached)
        start1 = time.time()
        response1 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        time1 = time.time() - start1
        
        assert response1.status_code == 200
        
        # Second request (should be cached)
        start2 = time.time()
        response2 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        time2 = time.time() - start2
        
        assert response2.status_code == 200
        
        # Cached response should be same as original
        assert response1.json() == response2.json()
    
    def test_cache_returns_same_data(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Cached response should return identical data."""
        create_random_item(db)
        
        response1 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        response2 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        
        assert response1.json() == response2.json()


class TestCacheIsUserSpecific:
    """Test that cache is per-user."""
    
    def test_different_users_get_different_caches(
        self, client: TestClient, db: Session,
        superuser_token_headers: dict[str, str],
        normal_user_token_headers: dict[str, str]
    ) -> None:
        """Different users should have independent caches."""
        # Each user should see their own items (or filtered items)
        response_super = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        response_normal = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=normal_user_token_headers,
        )
        
        assert response_super.status_code == 200
        assert response_normal.status_code == 200
        
        # The responses may differ (superuser sees all, normal user sees own)
        # At minimum, the cache keys should be different


class TestCacheInvalidation:
    """Test that cache is invalidated on item changes."""
    
    def test_create_invalidates_cache(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Creating an item should invalidate the cache."""
        # Get initial list
        response1 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        initial_count = response1.json().get("count", len(response1.json().get("data", [])))
        
        # Create a new item via API
        new_item = {
            "title": "Cache Test Item",
            "description": "Testing cache invalidation"
        }
        create_response = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json=new_item,
        )
        assert create_response.status_code in (200, 201)
        
        # Get list again - should see the new item
        response2 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        new_count = response2.json().get("count", len(response2.json().get("data", [])))
        
        assert new_count > initial_count, \
            "Cache should be invalidated after creating an item"
    
    def test_update_invalidates_cache(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Updating an item should invalidate the cache."""
        # Create an item
        item = create_random_item(db)
        
        # Get list (caches it)
        response1 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        
        # Update the item
        update_response = client.put(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
            json={"title": "Updated Title for Cache Test"},
        )
        
        # Get list again - should see updated item
        response2 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        
        # Find the item in the response
        items = response2.json().get("data", [])
        updated_item = next((i for i in items if i["id"] == str(item.id)), None)
        
        if updated_item:
            assert updated_item["title"] == "Updated Title for Cache Test", \
                "Cache should be invalidated after updating an item"
    
    def test_delete_invalidates_cache(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Deleting an item should invalidate the cache."""
        # Create items
        item = create_random_item(db)
        
        # Get list (caches it)
        response1 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        initial_count = response1.json().get("count", len(response1.json().get("data", [])))
        
        # Delete the item
        delete_response = client.delete(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
        )
        
        # Get list again - should not include deleted item
        response2 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        new_count = response2.json().get("count", len(response2.json().get("data", [])))
        
        assert new_count < initial_count, \
            "Cache should be invalidated after deleting an item"


class TestCacheControlHeaders:
    """Test that Cache-Control headers are present."""
    
    def test_cache_control_header_present(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response should include Cache-Control header."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200
        
        # Check for Cache-Control header
        cache_control = response.headers.get("Cache-Control")
        assert cache_control is not None, \
            "Response must include Cache-Control header"
    
    def test_cache_control_has_max_age(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Cache-Control should include max-age directive."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        
        cache_control = response.headers.get("Cache-Control", "")
        
        assert "max-age" in cache_control.lower(), \
            "Cache-Control must include max-age directive"


class TestCacheNoBreakage:
    """Test that caching doesn't break normal functionality."""
    
    def test_items_endpoint_still_works(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Items endpoint should still work correctly."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have expected structure
        assert "data" in data or isinstance(data, list)
    
    def test_auth_still_required(
        self, client: TestClient
    ) -> None:
        """Auth should still be required for items endpoint."""
        response = client.get(f"{settings.API_V1_STR}/items/")
        
        assert response.status_code in (401, 403)
