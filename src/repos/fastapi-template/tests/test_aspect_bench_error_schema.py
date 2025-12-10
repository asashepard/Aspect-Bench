"""
Benchmark tests for: missing-item-404 AND consistent-error-schema

PROMPT FOR missing-item-404 SAYS:
"When a user tries to access an item that doesn't exist (or one they don't own), 
the API just returns a generic error. Can you make it return a proper 404 Not Found 
with a clear message when the item doesn't exist?"

PROMPT FOR consistent-error-schema SAYS:
"Our API error responses are inconsistent - sometimes we return {"detail": "..."} 
and sometimes different formats. I need all error responses to follow the same 
schema so the frontend can handle them predictably."

KEY INSIGHT: The prompt for missing-item-404 asks for:
- 404 status code when item doesn't exist
- Clear message in the response

The template ALREADY does this! The tests should verify this existing behavior.

The prompt for consistent-error-schema asks for:
- Consistent schema (all errors have "detail" field at minimum)
- Predictable format for frontend

Tests based SOLELY on prompt requirements:
1. missing-item-404: 404 status code + clear message for missing items
2. consistent-error-schema: All errors have consistent "detail" field
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.item import create_random_item


pytestmark = pytest.mark.aspect_bench


class TestMissingItemReturns404:
    """Test that missing items return 404 with clear message."""
    
    def test_get_missing_item_returns_404(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """GET /items/{id} for missing item should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"{settings.API_V1_STR}/items/{fake_id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 404, \
            f"Missing item should return 404, got {response.status_code}"
    
    def test_put_missing_item_returns_404(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """PUT /items/{id} for missing item should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"{settings.API_V1_STR}/items/{fake_id}",
            headers=superuser_token_headers,
            json={"title": "Test", "description": "Test"},
        )
        assert response.status_code == 404
    
    def test_delete_missing_item_returns_404(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """DELETE /items/{id} for missing item should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"{settings.API_V1_STR}/items/{fake_id}",
            headers=superuser_token_headers,
        )
        assert response.status_code == 404


class TestMissingItemHasClearMessage:
    """Test that missing item errors have clear messages."""
    
    def test_missing_item_has_detail_message(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Missing item response should have a detail message."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"{settings.API_V1_STR}/items/{fake_id}",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data, "Error should have 'detail' field"
        assert len(data["detail"]) > 0, "Detail message should not be empty"
    
    def test_missing_item_message_is_clear(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Missing item message should be understandable."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"{settings.API_V1_STR}/items/{fake_id}",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        detail = data.get("detail", "").lower()
        
        # Message should indicate item not found
        clear_indicators = ["not found", "not exist", "does not exist", "missing"]
        is_clear = any(ind in detail for ind in clear_indicators)
        
        assert is_clear, \
            f"Message should clearly indicate item not found. Got: {data.get('detail')}"


class TestConsistentErrorSchema:
    """Test that all error responses have consistent schema."""
    
    def test_404_has_detail_field(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """404 errors should have 'detail' field."""
        response = client.get(
            f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 404
        assert "detail" in response.json()
    
    def test_401_has_detail_field(
        self, client: TestClient
    ) -> None:
        """401/403 errors should have 'detail' field."""
        response = client.get(f"{settings.API_V1_STR}/items/")
        
        assert response.status_code in (401, 403)
        assert "detail" in response.json()
    
    def test_422_has_detail_field(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """422 validation errors should have 'detail' field."""
        response = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json={},  # Missing required fields
        )
        
        assert response.status_code == 422
        assert "detail" in response.json()
    
    def test_400_has_detail_field(
        self, client: TestClient
    ) -> None:
        """400 errors should have 'detail' field."""
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 400
        assert "detail" in response.json()


class TestAllErrorsHaveConsistentFormat:
    """Test that different error types have the same basic format."""
    
    def test_all_4xx_errors_are_json(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """All 4xx errors should return JSON."""
        # 401/403
        r1 = client.get(f"{settings.API_V1_STR}/items/")
        assert r1.headers.get("content-type", "").startswith("application/json")
        
        # 404
        r2 = client.get(
            f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
            headers=superuser_token_headers,
        )
        assert r2.headers.get("content-type", "").startswith("application/json")
        
        # 422
        r3 = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json={},
        )
        assert r3.headers.get("content-type", "").startswith("application/json")
    
    def test_error_detail_is_string_or_list(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Error detail should be a string or list (consistent types)."""
        # 404 - typically string
        r1 = client.get(
            f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
            headers=superuser_token_headers,
        )
        detail1 = r1.json().get("detail")
        assert isinstance(detail1, (str, list)), "Detail should be string or list"
        
        # 422 - typically list
        r2 = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=superuser_token_headers,
            json={},
        )
        detail2 = r2.json().get("detail")
        assert isinstance(detail2, (str, list)), "Detail should be string or list"


class TestPermissionErrors:
    """Test permission-related errors."""
    
    def test_no_permission_returns_appropriate_error(
        self, client: TestClient, db: Session, 
        normal_user_token_headers: dict[str, str]
    ) -> None:
        """Accessing item without permission should return appropriate error."""
        # Create item owned by someone else (superuser)
        item = create_random_item(db)
        
        response = client.get(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=normal_user_token_headers,
        )
        
        # Should return error (400 or 403 depending on implementation)
        assert response.status_code in (400, 403, 404)
        assert "detail" in response.json()


class TestErrorSchemaEdgeCases:
    """Edge cases for error schema."""
    
    def test_invalid_uuid_format(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Invalid UUID format should return 422 with detail."""
        response = client.get(
            f"{settings.API_V1_STR}/items/not-a-uuid",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 422
        assert "detail" in response.json()
    
    def test_missing_item_not_found(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Missing item should return 404 with detail."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"{settings.API_V1_STR}/items/{fake_id}",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 404
        assert "detail" in response.json()


class TestConsistentSchemaImplemented:
    """
    Test that a CONSISTENT error schema is actually implemented.
    
    The prompt asks for:
    - AppError exception class with error_code, message, details
    - Global exception handler
    - JSON response with {"error_code": "...", "message": "...", "details": {...}, "timestamp": "ISO8601"}
    """
    
    def test_app_error_exception_exists(self) -> None:
        """
        AppError exception class should be defined.
        
        The prompt explicitly asks for an AppError class with error_code,
        message, and optional details dict.
        """
        app_error_found = False
        
        # Check common locations for AppError
        try:
            from app.core.exceptions import AppError
            app_error_found = True
        except ImportError:
            pass
        
        try:
            from app.exceptions import AppError
            app_error_found = True
        except ImportError:
            pass
        
        try:
            from app.api.exceptions import AppError
            app_error_found = True
        except ImportError:
            pass
        
        assert app_error_found, \
            "AppError exception class should be defined (e.g., in app.core.exceptions)"
    
    def test_error_response_has_error_code(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Error responses must have error_code field.
        
        The prompt specifies: {"error_code": "ITEM_NOT_FOUND", ...}
        """
        response = client.get(
            f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
            headers=superuser_token_headers,
        )
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error_code" in data, \
            "Error response must have 'error_code' field (e.g., 'ITEM_NOT_FOUND')"
        assert isinstance(data["error_code"], str), \
            "error_code must be a string"
    
    def test_error_response_has_message(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Error responses must have message field.
        """
        response = client.get(
            f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        
        assert "message" in data, \
            "Error response must have 'message' field"
    
    def test_error_response_has_timestamp(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Error responses must have ISO8601 timestamp.
        
        The prompt specifies: {"timestamp": "ISO8601"}
        """
        import re
        
        response = client.get(
            f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
            headers=superuser_token_headers,
        )
        
        data = response.json()
        
        assert "timestamp" in data, \
            "Error response must have 'timestamp' field"
        
        # Check ISO8601 format (basic check)
        timestamp = data["timestamp"]
        iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        assert re.match(iso8601_pattern, timestamp), \
            f"Timestamp must be ISO8601 format, got: {timestamp}"
    
    def test_routes_use_app_error(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """
        Routes should use AppError instead of raw HTTPException.
        
        The prompt says to "migrate the items and users routes to use
        this new error pattern instead of raw HTTPException".
        """
        import inspect
        from app.api.routes import items
        
        source = inspect.getsource(items)
        
        # Should reference AppError, not just HTTPException
        uses_app_error = "AppError" in source or "app_error" in source.lower()
        
        assert uses_app_error, \
            "Items routes should use AppError instead of raw HTTPException"
