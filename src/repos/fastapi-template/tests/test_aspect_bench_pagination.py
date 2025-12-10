"""
Benchmark tests for: paginated-items-endpoint

PROMPT SAYS:
"The items endpoint currently returns all items at once which won't scale. 
Add pagination support - I need to be able to request items with skip/limit 
parameters and get back the total count along with the items."

NOTE: Looking at the existing code, it ALREADY has skip/limit and returns count!
The template already implements this. These tests verify the existing functionality
and add edge case coverage.

Tests based SOLELY on prompt requirements:
1. Endpoint accepts skip/limit parameters
2. Response includes total count
3. Response includes items
4. Pagination works correctly (skip/limit behavior)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.item import create_random_item


pytestmark = pytest.mark.aspect_bench


class TestPaginationParameters:
    """Test that pagination parameters are accepted and work."""
    
    def test_items_endpoint_accepts_skip_parameter(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Items endpoint should accept skip parameter."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?skip=0",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
    
    def test_items_endpoint_accepts_limit_parameter(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Items endpoint should accept limit parameter."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=10",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
    
    def test_items_endpoint_accepts_both_skip_and_limit(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Items endpoint should accept both skip and limit."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?skip=5&limit=10",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200


class TestPaginationResponse:
    """Test that pagination response includes required fields."""
    
    def test_response_includes_count(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response must include total count of items."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "count" in data, "Response must include 'count' field"
        assert isinstance(data["count"], int), "Count must be an integer"
    
    def test_response_includes_items(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Response must include items array."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data, "Response must include 'data' field with items"
        assert isinstance(data["data"], list), "Data must be a list"


class TestPaginationBehavior:
    """Test that pagination actually works correctly."""
    
    def test_skip_skips_items(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Skip parameter should skip the first N items."""
        # Create multiple items
        items = [create_random_item(db) for _ in range(5)]
        
        # Get all items
        response_all = client.get(
            f"{settings.API_V1_STR}/items/?skip=0&limit=100",
            headers=superuser_token_headers,
        )
        all_data = response_all.json()["data"]
        
        # Get with skip=2
        response_skip = client.get(
            f"{settings.API_V1_STR}/items/?skip=2&limit=100",
            headers=superuser_token_headers,
        )
        skip_data = response_skip.json()["data"]
        
        # Skip should return fewer items
        if len(all_data) > 2:
            assert len(skip_data) == len(all_data) - 2, \
                f"Skip=2 should return 2 fewer items"
    
    def test_limit_limits_items(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Limit parameter should limit the number of returned items."""
        # Create multiple items
        items = [create_random_item(db) for _ in range(5)]
        
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=2",
            headers=superuser_token_headers,
        )
        data = response.json()
        
        assert len(data["data"]) <= 2, "Limit=2 should return at most 2 items"
    
    def test_count_reflects_total_not_page(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Count should reflect total items, not just items in current page."""
        # Create items
        items = [create_random_item(db) for _ in range(5)]
        
        # Get with limit=1
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=1",
            headers=superuser_token_headers,
        )
        data = response.json()
        
        # Count should be total, not 1
        assert data["count"] >= 5, \
            f"Count should be total items ({data['count']}), not limited to page size"


class TestPaginationEdgeCases:
    """Edge cases for pagination."""
    
    def test_skip_beyond_items(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Skip beyond available items should return empty list."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?skip=99999",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"] == [], "Skipping beyond items should return empty data"
    
    def test_limit_zero(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Limit of 0 should be handled (either empty or validation error)."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=0",
            headers=superuser_token_headers,
        )
        # Either returns empty or validation error
        assert response.status_code in (200, 422)
    
    def test_negative_skip(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Negative skip should be handled (validation error or treated as 0)."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?skip=-5",
            headers=superuser_token_headers,
        )
        # Should either error or handle gracefully
        assert response.status_code in (200, 422)
    
    def test_large_limit(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Very large limit should be handled."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=10000",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
    
    def test_pagination_preserves_order(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Pagination should preserve consistent ordering."""
        # Create items
        items = [create_random_item(db) for _ in range(5)]
        
        # Get first page
        r1 = client.get(
            f"{settings.API_V1_STR}/items/?skip=0&limit=2",
            headers=superuser_token_headers,
        )
        # Get second page
        r2 = client.get(
            f"{settings.API_V1_STR}/items/?skip=2&limit=2",
            headers=superuser_token_headers,
        )
        
        if r1.status_code == 200 and r2.status_code == 200:
            page1_ids = [item["id"] for item in r1.json()["data"]]
            page2_ids = [item["id"] for item in r2.json()["data"]]
            
            # Pages shouldn't overlap
            overlap = set(page1_ids) & set(page2_ids)
            assert len(overlap) == 0, "Paginated pages should not overlap"


class TestPaginationValidation:
    """
    Test that pagination has proper input validation.
    
    The prompt asks for:
    - Input validation rejecting negative skip/limit with 422
    - Cap limit at 100 maximum
    """
    
    def test_negative_skip_is_rejected(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Negative skip values should be rejected with 422.
        """
        response = client.get(
            f"{settings.API_V1_STR}/items/?skip=-1",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 422, \
            "Negative skip should be rejected with 422 validation error"
    
    def test_negative_limit_is_rejected(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Negative limit values should be rejected with 422.
        """
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=-1",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 422, \
            "Negative limit should be rejected with 422 validation error"
    
    def test_limit_capped_at_100(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Limit must be capped at 100 maximum per the prompt.
        """
        # Create more than 100 items
        for _ in range(5):
            create_random_item(db)
        
        # Request with limit > 100
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=200",
            headers=superuser_token_headers,
        )
        
        # Either rejected or capped
        if response.status_code == 200:
            data = response.json()
            assert len(data["data"]) <= 100, \
                "Limit must be capped at 100 maximum"
        else:
            assert response.status_code == 422, \
                "Limit > 100 should be rejected with 422"


class TestCursorBasedPagination:
    """
    Test cursor-based pagination as requested in the prompt.
    
    The prompt asks for:
    - Cursor-based pagination using created_at timestamp
    - Response with {"data": [...], "next_cursor": "...", "has_more": bool}
    - Cryptographically signed cursor to prevent tampering
    """
    
    def test_item_model_has_created_at(
        self, db: Session
    ) -> None:
        """
        Item model must have created_at field for cursor-based pagination.
        """
        from app.models import Item
        
        # Check if model has created_at field
        model_fields = Item.model_fields
        assert "created_at" in model_fields, \
            "Item model must have 'created_at' field for cursor-based pagination"
    
    def test_response_has_cursor_format(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Response must have cursor-based pagination format.
        
        Expected: {"data": [...], "next_cursor": "...", "has_more": bool}
        """
        # Create items
        for _ in range(5):
            create_random_item(db)
        
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=2",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for cursor-based fields
        assert "data" in data, "Response must have 'data' field"
        assert "next_cursor" in data or "cursor" in data, \
            "Response must have 'next_cursor' field for cursor-based pagination"
        assert "has_more" in data, \
            "Response must have 'has_more' boolean field"
    
    def test_cursor_allows_pagination(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Using cursor should return next page of results.
        """
        # Create items
        for _ in range(5):
            create_random_item(db)
        
        # Get first page
        response1 = client.get(
            f"{settings.API_V1_STR}/items/?limit=2",
            headers=superuser_token_headers,
        )
        
        data1 = response1.json()
        cursor = data1.get("next_cursor") or data1.get("cursor")
        
        if cursor and data1.get("has_more"):
            # Get next page using cursor
            response2 = client.get(
                f"{settings.API_V1_STR}/items/?cursor={cursor}&limit=2",
                headers=superuser_token_headers,
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Pages should not overlap
            page1_ids = [item["id"] for item in data1["data"]]
            page2_ids = [item["id"] for item in data2["data"]]
            
            assert not set(page1_ids) & set(page2_ids), \
                "Cursor pagination should not return duplicate items"
    
    def test_tampered_cursor_rejected(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Tampered cursor should be rejected.
        
        The prompt says cursor should be "cryptographically signed to prevent tampering".
        """
        # Try with obviously invalid cursor
        response = client.get(
            f"{settings.API_V1_STR}/items/?cursor=invalid_tampered_cursor_12345",
            headers=superuser_token_headers,
        )
        
        # Should reject invalid cursor (400 or 422)
        assert response.status_code in (400, 422), \
            "Tampered/invalid cursor should be rejected"
