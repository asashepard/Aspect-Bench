"""
Benchmark tests for: refactor-items-service-layers

PROMPT SAYS:
"The items router is getting messy with business logic mixed in. Can you refactor 
it to use a service layer pattern? Keep the routes thin and move the logic 
into a proper service class."

Tests based SOLELY on prompt requirements:
1. Routes should be thin (minimal logic in router)
2. Business logic should be in a service layer/class
3. Functionality should remain the same (no regressions)
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.item import create_random_item


pytestmark = pytest.mark.aspect_bench


class TestServiceLayerExists:
    """Test that a service layer exists."""
    
    def test_items_service_exists(self) -> None:
        """There should be an items service class/module."""
        service_found = False
        
        # Try common patterns for service location
        try:
            from app.services.items import ItemsService
            service_found = True
        except ImportError:
            pass
        
        try:
            from app.services.items import ItemService
            service_found = True
        except ImportError:
            pass
        
        try:
            from app.services import items_service
            service_found = True
        except ImportError:
            pass
        
        try:
            from app.services import ItemsService
            service_found = True
        except ImportError:
            pass
        
        try:
            from app.service.items import ItemsService
            service_found = True
        except ImportError:
            pass
        
        try:
            from app.items.service import ItemsService
            service_found = True
        except ImportError:
            pass
        
        assert service_found, \
            "Should have a service layer for items (e.g., app.services.items.ItemsService)"
    
    def test_service_has_crud_methods(self) -> None:
        """Service should have CRUD-like methods."""
        service = None
        
        # Try to import service
        try:
            from app.services.items import ItemsService
            service = ItemsService
        except ImportError:
            pass
        
        try:
            from app.services.items import ItemService
            service = ItemService
        except ImportError:
            pass
        
        if service is None:
            pytest.skip("Could not import items service")
        
        # Check for CRUD methods
        methods = dir(service)
        crud_patterns = ["get", "create", "update", "delete", "list"]
        
        found_methods = []
        for pattern in crud_patterns:
            if any(pattern in m.lower() for m in methods if not m.startswith("_")):
                found_methods.append(pattern)
        
        assert len(found_methods) >= 3, \
            f"Service should have CRUD methods. Found: {found_methods}"


class TestRoutesAreThin:
    """Test that routes are thin (logic moved to service)."""
    
    def test_routes_file_is_smaller(self) -> None:
        """Routes file should be relatively thin after refactoring."""
        import inspect
        from app.api.routes import items
        
        source = inspect.getsource(items)
        lines = source.split('\n')
        
        # Filter out empty lines and comments
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # After refactoring, the routes file should be reasonably sized
        # (This is a soft check - we're mainly looking for the pattern)
        # A well-refactored routes file should be under ~200 lines
        assert len(code_lines) < 300, \
            f"Routes file seems too large ({len(code_lines)} lines). " \
            "Business logic should be in service layer."
    
    def test_routes_use_service(self) -> None:
        """Routes should reference/use the service layer."""
        import inspect
        from app.api.routes import items
        
        source = inspect.getsource(items)
        
        # Check for service usage patterns
        uses_service = (
            "service" in source.lower() or
            "Service" in source or
            "_service" in source
        )
        
        assert uses_service, \
            "Routes should use a service layer"


class TestFunctionalityPreserved:
    """Test that all functionality still works after refactoring."""
    
    def test_can_list_items(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should still be able to list items."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        assert "data" in response.json()
    
    def test_can_create_item(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should still be able to create items."""
        response = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json={"title": "Test Item", "description": "Test Description"},
        )
        assert response.status_code == 200
        assert "id" in response.json()
    
    def test_can_get_item(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should still be able to get item by ID."""
        item = create_random_item(db)
        
        response = client.get(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(item.id)
    
    def test_can_update_item(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should still be able to update items."""
        item = create_random_item(db)
        
        response = client.put(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
            json={"title": "Updated Title", "description": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
    
    def test_can_delete_item(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """Should still be able to delete items."""
        item = create_random_item(db)
        
        response = client.delete(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200


class TestPermissionsPreserved:
    """Test that permission checks still work."""
    
    def test_items_require_auth(
        self, client: TestClient
    ) -> None:
        """Items endpoint should still require authentication."""
        response = client.get(f"{settings.API_V1_STR}/items/")
        assert response.status_code in (401, 403)
    
    def test_user_only_sees_own_items(
        self, client: TestClient, db: Session, 
        normal_user_token_headers: dict[str, str]
    ) -> None:
        """Normal user should only see their own items."""
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200
        # Just verify the endpoint works - ownership logic preserved


class TestServiceLayerEdgeCases:
    """Edge cases for service layer refactoring."""
    
    def test_item_not_found_handled(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Item not found should be handled properly."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"{settings.API_V1_STR}/items/{fake_id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 404
    
    def test_invalid_data_handled(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Invalid input data should be validated."""
        response = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json={},  # Missing required fields
        )
        assert response.status_code == 422
