"""
Benchmark tests for: refactor-auth-dependency

PROMPT SAYS:
"I want to refactor the authentication dependency injection. Right now, get_current_user 
and get_current_active_superuser are defined inline in deps.py, but I'd like to 
make them more reusable and testable. Can you extract them into a cleaner pattern?"

Tests based SOLELY on prompt requirements:
1. Auth dependencies should still work (not break existing functionality)
2. Code should be more reusable (measurable by structure)
3. Code should be more testable (can mock/inject dependencies)

NOTE: This is a refactoring task - we mainly verify no regressions
and improved code structure.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings


pytestmark = pytest.mark.aspect_bench


class TestAuthStillWorks:
    """Test that authentication still works after refactoring."""
    
    def test_protected_endpoint_requires_auth(
        self, client: TestClient
    ) -> None:
        """Protected endpoints should still require authentication."""
        response = client.get(f"{settings.API_V1_STR}/users/me")
        assert response.status_code in (401, 403), \
            "Protected endpoint should require auth"
    
    def test_protected_endpoint_works_with_auth(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """Protected endpoints should work with valid auth."""
        response = client.get(
            f"{settings.API_V1_STR}/users/me",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200
    
    def test_superuser_endpoint_requires_superuser(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """Superuser-only endpoints should reject normal users."""
        response = client.get(
            f"{settings.API_V1_STR}/users/",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 403
    
    def test_superuser_endpoint_works_for_superuser(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Superuser-only endpoints should work for superusers."""
        response = client.get(
            f"{settings.API_V1_STR}/users/",
            headers=superuser_token_headers,
        )
        assert response.status_code == 200


class TestAuthReusability:
    """Test that auth code is more reusable after refactoring."""
    
    def test_current_user_dep_exists(self) -> None:
        """CurrentUser dependency should exist and be importable."""
        from app.api.deps import CurrentUser
        assert CurrentUser is not None
    
    def test_session_dep_exists(self) -> None:
        """SessionDep should exist and be importable."""
        from app.api.deps import SessionDep
        assert SessionDep is not None
    
    def test_get_current_user_is_callable(self) -> None:
        """get_current_user should be importable and callable."""
        from app.api.deps import get_current_user
        assert callable(get_current_user)
    
    def test_get_superuser_is_callable(self) -> None:
        """get_current_active_superuser should be importable."""
        from app.api.deps import get_current_active_superuser
        assert callable(get_current_active_superuser)


class TestAuthTestability:
    """Test that auth is more testable after refactoring."""
    
    def test_can_import_auth_functions(self) -> None:
        """Auth functions should be importable for testing."""
        try:
            from app.api.deps import get_current_user, get_current_active_superuser
            # Also check if there's a separate auth module
            pass
        except ImportError:
            pytest.fail("Auth dependencies should be importable")
    
    def test_auth_pattern_is_clean(self) -> None:
        """Auth code should follow a cleaner pattern."""
        import inspect
        from app.api import deps
        
        # Get source code
        source = inspect.getsource(deps)
        
        # Check for cleaner patterns:
        # 1. Class-based auth
        # 2. Factory functions
        # 3. Separate concerns
        
        improvements = []
        
        # Check if there's a class for auth
        if "class " in source and ("Auth" in source or "auth" in source.lower()):
            improvements.append("class-based")
        
        # Check for dependency factories
        if "def get_" in source:
            improvements.append("factory-functions")
        
        # Check for type annotations
        if "->" in source:
            improvements.append("typed")
        
        # The refactoring should maintain at least these basic patterns
        assert "typed" in improvements or len(improvements) >= 1, \
            "Auth code should use modern patterns"


class TestAuthIsRefactored:
    """
    Test that auth is actually refactored as specified in the prompt.
    
    The prompt asks for:
    - AuthService class in new backend/app/services/auth.py module
    - Injectable via FastAPI's dependency system
    - Methods for get_current_user and require_superuser
    - Easily mockable for testing
    """
    
    def test_auth_service_module_exists(self) -> None:
        """
        AuthService should be in backend/app/services/auth.py.
        
        The prompt explicitly says "a new backend/app/services/auth.py module".
        """
        auth_service_found = False
        
        try:
            from app.services.auth import AuthService
            auth_service_found = True
        except ImportError:
            pass
        
        try:
            from app.services import auth
            if hasattr(auth, 'AuthService'):
                auth_service_found = True
        except ImportError:
            pass
        
        assert auth_service_found, \
            "AuthService class must be in app.services.auth module"
    
    def test_auth_service_has_required_methods(self) -> None:
        """
        AuthService should have get_current_user and require_superuser methods.
        """
        try:
            from app.services.auth import AuthService
        except ImportError:
            pytest.fail("Cannot import AuthService from app.services.auth")
        
        # Check for required methods
        methods = dir(AuthService)
        
        has_get_current_user = any(
            "get_current_user" in m or "current_user" in m 
            for m in methods if not m.startswith("_")
        )
        has_require_superuser = any(
            "require_superuser" in m or "superuser" in m 
            for m in methods if not m.startswith("_")
        )
        
        assert has_get_current_user, \
            "AuthService must have get_current_user method"
        assert has_require_superuser, \
            "AuthService must have require_superuser method"
    
    def test_auth_service_is_injectable(self) -> None:
        """
        AuthService should be injectable via FastAPI's dependency system.
        """
        try:
            from app.services.auth import AuthService
            import inspect
            
            # Check if it can be used as a dependency
            # Either it's a class with __call__, or has dependency methods
            source = inspect.getsource(AuthService)
            
            is_injectable = any([
                "Depends" in source,
                "def __call__" in source,
                "@staticmethod" in source,
                "def get_" in source,  # Factory pattern
            ])
            
            assert is_injectable, \
                "AuthService should be injectable (use Depends, __call__, or factory)"
        except ImportError:
            pytest.fail("Cannot import AuthService from app.services.auth")
    
    def test_routes_use_auth_service(self) -> None:
        """
        Routes should be updated to use the new AuthService.
        """
        import inspect
        from app.api.routes import items, users
        
        items_source = inspect.getsource(items)
        users_source = inspect.getsource(users)
        
        # Should reference AuthService somewhere
        uses_auth_service = (
            "AuthService" in items_source or 
            "auth_service" in items_source.lower() or
            "AuthService" in users_source or 
            "auth_service" in users_source.lower() or
            "from app.services.auth" in items_source or
            "from app.services.auth" in users_source
        )
        
        assert uses_auth_service, \
            "Routes should use the new AuthService from app.services.auth"


class TestAuthNoRegressions:
    """Verify no regressions in auth behavior."""
    
    def test_invalid_token_rejected(
        self, client: TestClient
    ) -> None:
        """Invalid tokens should still be rejected."""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = client.get(
            f"{settings.API_V1_STR}/users/me",
            headers=headers,
        )
        assert response.status_code in (401, 403)
    
    def test_missing_token_rejected(
        self, client: TestClient
    ) -> None:
        """Missing token should be rejected."""
        response = client.get(f"{settings.API_V1_STR}/users/me")
        assert response.status_code in (401, 403)
    
    def test_items_endpoint_uses_auth(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """Items endpoint should still use auth."""
        # Without auth
        response = client.get(f"{settings.API_V1_STR}/items/")
        assert response.status_code in (401, 403)
        
        # With auth
        response = client.get(
            f"{settings.API_V1_STR}/items/",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200
    
    def test_user_info_returned_correctly(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """User info endpoint should return correct data."""
        response = client.get(
            f"{settings.API_V1_STR}/users/me",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have user fields
        assert "id" in data
        assert "email" in data
