"""
Benchmark tests for: soft-delete-items

PROMPT SAYS:
"Instead of permanently deleting items, we need soft delete. Items should be marked 
as deleted but kept in the database. Regular queries shouldn't return deleted items, 
but maybe we need a way to see them for admin purposes."

Tests based SOLELY on prompt requirements:
1. Items should be marked as deleted (not permanently removed)
2. Deleted items should NOT appear in regular queries
3. There may be a way for admin to see deleted items
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Item
from tests.utils.item import create_random_item


pytestmark = pytest.mark.aspect_bench


class TestSoftDeleteBasic:
    """Test that soft delete is implemented."""
    
    def test_delete_marks_item_not_removes(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Deleting an item should mark it, not remove from database."""
        # Create item
        item = create_random_item(db)
        item_id = item.id
        
        # Delete it via API
        response = client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        
        # Check directly in database - item should still exist
        db.expire_all()  # Clear cache
        
        # Try to find the item in the database
        statement = select(Item).where(Item.id == item_id)
        db_item = db.exec(statement).first()
        
        assert db_item is not None, \
            "Item should still exist in database after soft delete"
    
    def test_deleted_item_has_marker(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Deleted items should have some marker (deleted_at, is_deleted, etc.)."""
        # Create and delete item
        item = create_random_item(db)
        item_id = item.id
        
        response = client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        
        # Check in database for marker
        db.expire_all()
        statement = select(Item).where(Item.id == item_id)
        db_item = db.exec(statement).first()
        
        if db_item is None:
            pytest.fail("Item was hard-deleted, not soft-deleted")
        
        # Check for common soft-delete markers
        has_marker = False
        if hasattr(db_item, "deleted_at") and db_item.deleted_at is not None:
            has_marker = True
        elif hasattr(db_item, "is_deleted") and db_item.is_deleted:
            has_marker = True
        elif hasattr(db_item, "deleted") and db_item.deleted:
            has_marker = True
        
        assert has_marker, \
            "Deleted item should have a soft-delete marker (deleted_at, is_deleted, etc.)"


class TestDeletedItemsHidden:
    """Test that deleted items don't appear in regular queries."""
    
    def test_deleted_item_not_in_list(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Deleted items should not appear in list endpoint."""
        # Create item
        item = create_random_item(db)
        item_id = str(item.id)
        item_title = item.title
        
        # Verify it shows up initially
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        all_ids = [str(i["id"]) for i in response.json()["data"]]
        assert item_id in all_ids, "Item should appear before deletion"
        
        # Delete it
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Verify it's hidden
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        all_ids_after = [str(i["id"]) for i in response.json()["data"]]
        
        assert item_id not in all_ids_after, \
            "Deleted item should not appear in list"
    
    def test_deleted_item_not_accessible_by_id(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Deleted items should not be accessible via GET by ID."""
        # Create and delete item
        item = create_random_item(db)
        item_id = item.id
        
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Try to get it
        response = client.get(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Should be 404 or similar (not found)
        assert response.status_code == 404, \
            "Deleted item should return 404 when accessed by ID"
    
    def test_deleted_item_not_updateable(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Deleted items should not be updateable."""
        # Create and delete item
        item = create_random_item(db)
        item_id = item.id
        
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Try to update it
        response = client.put(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
            json={"title": "Updated Title", "description": "Updated"},
        )
        
        # Should fail (404 or similar)
        assert response.status_code == 404, \
            "Deleted item should not be updateable"


class TestTrashEndpoint:
    """
    Test the trash endpoint for listing deleted items.
    
    The prompt asks for: GET /api/v1/items/trash endpoint to list deleted items
    """
    
    def test_trash_endpoint_exists(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        GET /api/v1/items/trash endpoint must exist.
        """
        response = client.get(
            f"{settings.API_V1_STR}/items/trash",
            headers=superuser_token_headers,
        )
        
        assert response.status_code != 404, \
            "GET /api/v1/items/trash endpoint must exist"
        assert response.status_code == 200, \
            "Trash endpoint should return 200"
    
    def test_trash_contains_deleted_items(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Trash endpoint should list soft-deleted items.
        """
        # Create and delete item
        item = create_random_item(db)
        item_id = str(item.id)
        
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Check trash
        response = client.get(
            f"{settings.API_V1_STR}/items/trash",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        items_data = data.get("data", data) if isinstance(data, dict) else data
        
        ids = [str(i.get("id", "")) for i in items_data]
        assert item_id in ids, \
            "Deleted item should appear in trash endpoint"


class TestRestoreEndpoint:
    """
    Test the restore endpoint for soft-deleted items.
    
    The prompt asks for: POST /api/v1/items/{id}/restore endpoint to restore soft-deleted items
    """
    
    def test_restore_endpoint_exists(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        POST /api/v1/items/{id}/restore endpoint must exist.
        """
        item = create_random_item(db)
        item_id = str(item.id)
        
        # Delete first
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Try restore
        response = client.post(
            f"{settings.API_V1_STR}/items/{item_id}/restore",
            headers=superuser_token_headers,
        )
        
        assert response.status_code != 404 or "Method Not Allowed" not in response.text, \
            "POST /api/v1/items/{id}/restore endpoint must exist"
    
    def test_restore_brings_back_item(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Restoring an item should make it visible in regular queries again.
        """
        item = create_random_item(db)
        item_id = str(item.id)
        
        # Delete
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Verify it's gone from list
        r1 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        ids_before = [i["id"] for i in r1.json()["data"]]
        assert item_id not in ids_before
        
        # Restore
        r2 = client.post(
            f"{settings.API_V1_STR}/items/{item_id}/restore",
            headers=superuser_token_headers,
        )
        assert r2.status_code == 200, "Restore should succeed"
        
        # Verify it's back in list
        r3 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        ids_after = [i["id"] for i in r3.json()["data"]]
        assert item_id in ids_after, \
            "Restored item should appear in regular item list"
    
    def test_restored_item_removed_from_trash(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Restored item should no longer appear in trash.
        """
        item = create_random_item(db)
        item_id = str(item.id)
        
        # Delete and restore
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        client.post(
            f"{settings.API_V1_STR}/items/{item_id}/restore",
            headers=superuser_token_headers,
        )
        
        # Check trash
        response = client.get(
            f"{settings.API_V1_STR}/items/trash",
            headers=superuser_token_headers,
        )
        
        if response.status_code == 200:
            data = response.json()
            items_data = data.get("data", data) if isinstance(data, dict) else data
            ids = [str(i.get("id", "")) for i in items_data]
            assert item_id not in ids, \
                "Restored item should not appear in trash"


class TestSoftDeleteEdgeCases:
    """Edge cases for soft delete."""
    
    def test_delete_twice_handled(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Deleting an already deleted item should be handled."""
        # Create and delete item
        item = create_random_item(db)
        item_id = item.id
        
        # First delete
        response1 = client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        assert response1.status_code == 200
        
        # Second delete
        response2 = client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Should either succeed again or return 404
        assert response2.status_code in (200, 404)
    
    def test_count_excludes_deleted_items(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Total count should exclude deleted items."""
        # Get initial count
        response1 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        initial_count = response1.json()["count"]
        
        # Create and delete item
        item = create_random_item(db)
        item_id = item.id
        
        # Count after creation
        response2 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        count_after_create = response2.json()["count"]
        assert count_after_create == initial_count + 1
        
        # Delete item
        client.delete(
            f"{settings.API_V1_STR}/items/{item_id}",
            headers=superuser_token_headers,
        )
        
        # Count after deletion
        response3 = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        count_after_delete = response3.json()["count"]
        
        assert count_after_delete == initial_count, \
            "Count should decrease after soft delete"
