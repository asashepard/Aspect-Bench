"""
Regression tests for the benchmark.

These tests verify that the existing functionality is not broken
by any changes made for the benchmark tasks.

Run with: pytest tests/test_aspect_bench_regression.py -m regression
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.item import create_random_item
from tests.utils.utils import random_email


pytestmark = [pytest.mark.regression, pytest.mark.aspect_bench]


class TestAuthRegression:
    """Verify authentication still works."""
    
    def test_login_works(self, client: TestClient) -> None:
        """Login should work with correct credentials."""
        # Create a user first
        email = random_email()
        password = "TestPass123!"
        
        # Try to signup (if available)
        signup_response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={"email": email, "password": password},
        )
        
        if signup_response.status_code == 200:
            # Now try to login
            login_response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={"username": email, "password": password},
            )
            assert login_response.status_code == 200
            assert "access_token" in login_response.json()
    
    def test_protected_route_requires_auth(self, client: TestClient) -> None:
        """Protected routes should require authentication."""
        response = client.get(f"{settings.API_V1_STR}/users/me")
        assert response.status_code in (401, 403)


class TestItemsRegression:
    """Verify items CRUD still works."""
    
    def test_create_item(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should be able to create an item."""
        response = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json={"title": "Test Item", "description": "A test item"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Item"
    
    def test_get_item(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should be able to get an item by ID."""
        item = create_random_item(db)
        
        response = client.get(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(item.id)
    
    def test_update_item(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should be able to update an item."""
        item = create_random_item(db)
        
        response = client.put(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
            json={"title": "Updated Title", "description": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
    
    def test_delete_item(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should be able to delete an item."""
        item = create_random_item(db)
        
        response = client.delete(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
    
    def test_list_items(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should be able to list items."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        assert "data" in response.json()
        assert "count" in response.json()


class TestUsersRegression:
    """Verify user management still works."""
    
    def test_get_current_user(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should be able to get current user info."""
        response = client.get(
            f"{settings.API_V1_STR}/users/me",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        assert "email" in response.json()
    
    def test_user_signup(self, client: TestClient) -> None:
        """User signup should work."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "TestPass123!",
            },
        )
        # Either succeeds or already has password validation
        assert response.status_code in (200, 422)


class TestValidationRegression:
    """Verify input validation still works."""
    
    def test_empty_title_rejected(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Items with empty title should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json={"title": "", "description": "Test"},
        )
        assert response.status_code == 422
    
    def test_invalid_email_rejected(self, client: TestClient) -> None:
        """Invalid email should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": "not-an-email",
                "password": "TestPass123!!",
            },
        )
        assert response.status_code == 422


class TestCascadeDeleteRaceCondition:
    """
    Test for the cascade delete race condition fix.
    
    The prompt says:
    "Fix a critical bug: when a user is deleted, their items should be cascade-deleted 
    but the current implementation has a race condition. If items are created between 
    the delete query and user deletion, orphaned items remain."
    
    "Implement proper transactional cascade deletion using database-level cascades,
    add a test that creates items in a concurrent thread during deletion"
    """
    
    def test_user_deletion_cascades_items(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        When a user is deleted, their items should be deleted too.
        """
        from app.models import User, Item
        from sqlmodel import select
        
        # Create a test user
        email = random_email()
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={"email": email, "password": "StrongPass123!!"},
        )
        if response.status_code != 200:
            pytest.skip("Could not create test user")
        
        user_id = response.json()["id"]
        
        # Login as this user
        login_response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": email, "password": "StrongPass123!!"},
        )
        token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}
        
        # Create items for this user
        item_ids = []
        for i in range(3):
            r = client.post(
                f"{settings.API_V1_STR}/items/",
                headers=user_headers,
                json={"title": f"Test Item {i}", "description": "Will be deleted"},
            )
            if r.status_code == 200:
                item_ids.append(r.json()["id"])
        
        # Delete the user (as superuser)
        delete_response = client.delete(
            f"{settings.API_V1_STR}/users/{user_id}",
            headers=superuser_token_headers,
        )
        assert delete_response.status_code == 200
        
        # Verify items are gone (no orphans)
        db.expire_all()
        for item_id in item_ids:
            stmt = select(Item).where(Item.id == item_id)
            item = db.exec(stmt).first()
            assert item is None, \
                f"Item {item_id} should be cascade-deleted with user"
    
    def test_concurrent_item_creation_during_delete(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Test for race condition: items created during deletion should not become orphans.
        
        This tests the fix for the race condition mentioned in the prompt.
        """
        import threading
        import time
        from app.models import User, Item
        from sqlmodel import select
        
        # Create a test user
        email = random_email()
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={"email": email, "password": "StrongPass123!!"},
        )
        if response.status_code != 200:
            pytest.skip("Could not create test user")
        
        user_id = response.json()["id"]
        
        # Login as this user
        login_response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": email, "password": "StrongPass123!!"},
        )
        token = login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}
        
        # Create initial items
        for i in range(2):
            client.post(
                f"{settings.API_V1_STR}/items/",
                headers=user_headers,
                json={"title": f"Initial Item {i}", "description": "Test"},
            )
        
        # Track items created during deletion
        concurrent_item_ids = []
        deletion_started = threading.Event()
        deletion_done = threading.Event()
        
        def create_items_concurrently():
            """Try to create items while deletion is happening."""
            deletion_started.wait(timeout=5)  # Wait for deletion to start
            
            for i in range(5):
                if deletion_done.is_set():
                    break
                try:
                    r = client.post(
                        f"{settings.API_V1_STR}/items/",
                        headers=user_headers,
                        json={"title": f"Concurrent Item {i}", "description": "During delete"},
                    )
                    if r.status_code == 200:
                        concurrent_item_ids.append(r.json()["id"])
                except:
                    pass
                time.sleep(0.01)
        
        # Start concurrent item creation thread
        creator_thread = threading.Thread(target=create_items_concurrently)
        creator_thread.start()
        
        # Delete the user
        deletion_started.set()
        delete_response = client.delete(
            f"{settings.API_V1_STR}/users/{user_id}",
            headers=superuser_token_headers,
        )
        deletion_done.set()
        
        creator_thread.join(timeout=5)
        
        # The deletion should succeed
        assert delete_response.status_code == 200
        
        # Verify NO orphan items exist for this user
        db.expire_all()
        stmt = select(Item).where(Item.owner_id == user_id)
        orphan_items = db.exec(stmt).all()
        
        assert len(orphan_items) == 0, \
            f"Found {len(orphan_items)} orphan items - race condition not fixed!"
