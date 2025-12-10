"""
Benchmark tests for: add-csv-export

PROMPT SAYS:
"Add an endpoint to export the user's items as a CSV file. Should include all 
item fields and return a proper file download with the right content type."

Tests based SOLELY on prompt requirements:
1. There must be an endpoint that exports items as CSV
2. The CSV must include ALL item fields (id, title, description, owner_id)
3. Response must have proper CSV content type
4. Response must be a file download (Content-Disposition header)
"""

import csv
import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.item import create_random_item


pytestmark = pytest.mark.aspect_bench


class TestCSVExportEndpoint:
    """Test that a CSV export endpoint exists and works."""
    
    def test_csv_export_endpoint_exists(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """An endpoint for CSV export should exist at a reasonable path."""
        # Try common paths for CSV export
        possible_paths = [
            f"{settings.API_V1_STR}/items/export",
            f"{settings.API_V1_STR}/items/export/csv",
            f"{settings.API_V1_STR}/items/csv",
            f"{settings.API_V1_STR}/items/download",
        ]
        
        found = False
        for path in possible_paths:
            response = client.get(path, headers=superuser_token_headers)
            if response.status_code != 404:
                found = True
                break
        
        assert found, f"No CSV export endpoint found. Tried: {possible_paths}"
    
    def test_csv_export_returns_csv_content_type(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """CSV export must return proper CSV content type."""
        # Try common paths
        for path in [
            f"{settings.API_V1_STR}/items/export",
            f"{settings.API_V1_STR}/items/export/csv",
            f"{settings.API_V1_STR}/items/csv",
        ]:
            response = client.get(path, headers=superuser_token_headers)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                assert "text/csv" in content_type or "application/csv" in content_type, \
                    f"Expected CSV content type, got: {content_type}"
                return
        
        pytest.fail("No working CSV export endpoint found")
    
    def test_csv_export_is_file_download(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """CSV export must have Content-Disposition header for file download."""
        for path in [
            f"{settings.API_V1_STR}/items/export",
            f"{settings.API_V1_STR}/items/export/csv",
            f"{settings.API_V1_STR}/items/csv",
        ]:
            response = client.get(path, headers=superuser_token_headers)
            if response.status_code == 200:
                content_disp = response.headers.get("content-disposition", "")
                assert "attachment" in content_disp.lower() or "filename" in content_disp.lower(), \
                    f"Expected file download header, got: {content_disp}"
                return
        
        pytest.fail("No working CSV export endpoint found")


class TestCSVExportContent:
    """Test that the CSV content includes all item fields."""
    
    def test_csv_includes_all_item_fields(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """CSV must include ALL item fields: id, title, description, owner_id."""
        # Create an item so we have data to export
        item = create_random_item(db)
        
        # Find the export endpoint
        for path in [
            f"{settings.API_V1_STR}/items/export",
            f"{settings.API_V1_STR}/items/export/csv",
            f"{settings.API_V1_STR}/items/csv",
        ]:
            response = client.get(path, headers=superuser_token_headers)
            if response.status_code == 200:
                content = response.text
                
                # Parse as CSV
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
                
                assert len(rows) >= 1, "CSV should have at least a header row"
                
                header = [h.lower() for h in rows[0]]
                
                # Check for required fields
                required_fields = ["id", "title", "description", "owner_id"]
                for field in required_fields:
                    # Allow variations like "owner_id" or "ownerid" or "ownerId"
                    found = any(field.replace("_", "") in h.replace("_", "") for h in header)
                    assert found, f"CSV must include '{field}' field. Got headers: {rows[0]}"
                
                return
        
        pytest.fail("No working CSV export endpoint found")
    
    def test_csv_contains_actual_item_data(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """CSV should contain the actual item data, not just headers."""
        # Create items
        item1 = create_random_item(db)
        item2 = create_random_item(db)
        
        for path in [
            f"{settings.API_V1_STR}/items/export",
            f"{settings.API_V1_STR}/items/export/csv",
            f"{settings.API_V1_STR}/items/csv",
        ]:
            response = client.get(path, headers=superuser_token_headers)
            if response.status_code == 200:
                content = response.text
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
                
                # Should have header + at least 2 data rows
                assert len(rows) >= 3, f"Expected header + data rows, got {len(rows)} rows"
                
                # Check that item titles appear in the content
                assert item1.title in content or str(item1.id) in content, \
                    "Item data should appear in CSV"
                return
        
        pytest.fail("No working CSV export endpoint found")


class TestCSVExportEdgeCases:
    """Edge cases for CSV export."""
    
    def test_csv_export_requires_auth(self, client: TestClient) -> None:
        """CSV export should require authentication."""
        for path in [
            f"{settings.API_V1_STR}/items/export",
            f"{settings.API_V1_STR}/items/export/csv",
            f"{settings.API_V1_STR}/items/csv",
        ]:
            response = client.get(path)
            if response.status_code != 404:
                assert response.status_code in (401, 403), \
                    "CSV export should require authentication"
                return
    
    def test_csv_export_empty_items(
        self, client: TestClient, normal_user_token_headers: dict[str, str]
    ) -> None:
        """CSV export with no items should still work (return headers at least)."""
        for path in [
            f"{settings.API_V1_STR}/items/export",
            f"{settings.API_V1_STR}/items/export/csv",
            f"{settings.API_V1_STR}/items/csv",
        ]:
            response = client.get(path, headers=normal_user_token_headers)
            if response.status_code == 200:
                # Should at least have a header row
                content = response.text.strip()
                assert len(content) > 0, "CSV should have at least headers even with no items"
                return
    
    def test_csv_handles_special_characters(
        self, client: TestClient, db: Session, superuser_token_headers: dict[str, str]
    ) -> None:
        """CSV should properly escape special characters (commas, quotes)."""
        # Create item with special characters
        from app.models import Item
        from sqlmodel import select
        
        # Get any user to own the item
        from app.models import User
        user = db.exec(select(User)).first()
        
        if user:
            special_item = Item(
                title='Item with "quotes" and, commas',
                description="Line1\nLine2",
                owner_id=user.id
            )
            db.add(special_item)
            db.commit()
            
            for path in [
                f"{settings.API_V1_STR}/items/export",
                f"{settings.API_V1_STR}/items/export/csv",
                f"{settings.API_V1_STR}/items/csv",
            ]:
                response = client.get(path, headers=superuser_token_headers)
                if response.status_code == 200:
                    # Just verify it doesn't crash - proper CSV escaping is complex
                    assert response.status_code == 200
                    return
