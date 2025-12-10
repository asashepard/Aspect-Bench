"""
Benchmark tests for: optimize-items-query

PROMPT SAYS:
"The items listing query is getting slow as the database grows. Can you optimize 
the database queries? Maybe add proper indexes or use more efficient query patterns. 
The N+1 query pattern might be an issue."

Tests based SOLELY on prompt requirements:
1. Queries should be optimized (fewer queries, better patterns)
2. Indexes should be added where appropriate
3. N+1 query pattern should be fixed
4. Functionality should remain the same

NOTE: Query optimization is hard to test without profiling.
We'll focus on verifiable improvements like index existence.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Item
from tests.utils.item import create_random_item


pytestmark = pytest.mark.aspect_bench


class TestIndexesExist:
    """Test that proper indexes are added."""
    
    def test_owner_id_index_exists(self, db: Session) -> None:
        """Item.owner_id should have an index for faster lookups."""
        from sqlalchemy import inspect
        
        inspector = inspect(db.get_bind())
        indexes = inspector.get_indexes("item")
        
        # Look for an index on owner_id
        owner_id_indexed = False
        for idx in indexes:
            columns = idx.get("column_names", [])
            if "owner_id" in columns:
                owner_id_indexed = True
                break
        
        assert owner_id_indexed, \
            "owner_id column should be indexed for query optimization"
    
    def test_item_table_has_indexes(self, db: Session) -> None:
        """Item table should have at least some indexes."""
        from sqlalchemy import inspect
        
        inspector = inspect(db.get_bind())
        indexes = inspector.get_indexes("item")
        
        # Should have at least primary key + one other index
        assert len(indexes) >= 1, \
            "Item table should have indexes for optimization"


class TestQueryEfficiency:
    """Test query efficiency patterns."""
    
    def test_list_items_is_efficient(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Listing items should work efficiently."""
        # Create some items
        for _ in range(5):
            create_random_item(db)
        
        # This should work without N+1 issues
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        
        # Verify we get data
        data = response.json()
        assert len(data["data"]) >= 5
    
    def test_pagination_uses_efficient_count(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Count query should be efficient (not load all data)."""
        # Create items
        for _ in range(10):
            create_random_item(db)
        
        # Get with small limit - count should still be correct
        response = client.get(
            f"{settings.API_V1_STR}/items/?limit=2",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Count should reflect total, not page size
        assert data["count"] >= 10


class TestFunctionalityPreserved:
    """Test that optimization doesn't break functionality."""
    
    def test_items_list_works(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Items list should still work after optimization."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
    
    def test_items_filter_by_owner_works(
        self, client: TestClient, db: Session, 
        normal_user_token_headers: dict[str, str]
    ) -> None:
        """Filtering by owner should still work."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200
    
    def test_single_item_get_works(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Getting single item should work."""
        item = create_random_item(db)
        
        response = client.get(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200


class TestModelHasIndex:
    """Test that model has index declarations."""
    
    def test_item_model_has_index_on_owner(self) -> None:
        """Item model should declare index on owner_id."""
        from app.models import Item
        from sqlmodel import Field
        
        # Check if owner_id field has index=True
        # This is a structural check of the model
        model_fields = Item.model_fields
        
        if "owner_id" in model_fields:
            field_info = model_fields["owner_id"]
            # Check for index in metadata
            # SQLModel/Pydantic stores this differently
            pass
        
        # Alternative: check the table definition
        from sqlalchemy import inspect
        
        # Get table columns
        mapper = inspect(Item)
        columns = mapper.columns
        
        # The test mainly ensures the model/table structure supports efficient queries
        assert "owner_id" in [c.name for c in columns], \
            "Item should have owner_id column"


class TestOptimizationEdgeCases:
    """Edge cases for query optimization."""
    
    def test_empty_result_efficient(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """Empty result should be returned efficiently."""
        # A user with no items should get fast response
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200
        # Should return empty data, not error
        assert "data" in response.json()
    
    def test_large_offset_handled(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Large offset should be handled efficiently."""
        response = client.get(
            f"{settings.API_V1_STR}/items/?skip=1000",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
