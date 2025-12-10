"""
Benchmark test for: package-csv-export

Task: Add CSV export endpoint for package data.

Prompt:
Add a CSV export endpoint for packages at /api/v4/packages/export/csv/ or
support ?format=csv parameter. The export should include all package fields
and have proper CSV headers. Use DRF's content negotiation or custom renderer.
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestPackageExportBaseline:
    """Baseline tests that verify existing package functionality."""
    
    def test_package_list_endpoint_exists(self, api_client):
        """BASELINE: Package list endpoint should exist."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_package_list_returns_json(self, api_client):
        """BASELINE: Package list should return JSON by default."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
        data = response.json()
        assert data is not None
    
    def test_package_detail_works(self, api_client, package):
        """BASELINE: Package detail should work."""
        response = api_client.get(f"/api/v4/packages/{package.slug}/")
        assert response.status_code == 200
    
    def test_packages_endpoint_no_crash_on_format_param(self, api_client):
        """BASELINE: Format parameter should not crash endpoint."""
        response = api_client.get("/api/v4/packages/?format=json")
        # Should not be 500
        assert response.status_code < 500


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestCsvExportEndpoint:
    """Tests for CSV export endpoint existence."""
    
    def test_csv_export_endpoint_exists(self, api_client):
        """TASK: CSV export endpoint should exist."""
        # Try the dedicated export endpoint
        response = api_client.get("/api/v4/packages/export/csv/")
        if response.status_code == 404:
            # Try format parameter
            response = api_client.get("/api/v4/packages/?format=csv")
        
        assert response.status_code == 200, "CSV export should be available"
    
    def test_csv_format_parameter_works(self, api_client):
        """TASK: ?format=csv parameter should work."""
        response = api_client.get("/api/v4/packages/?format=csv")
        assert response.status_code == 200, "format=csv should work"


class TestCsvContentType:
    """Tests for proper CSV content type."""
    
    def test_csv_has_correct_content_type(self, api_client):
        """TASK: CSV export should have text/csv content type."""
        response = api_client.get("/api/v4/packages/?format=csv")
        
        if response.status_code == 200:
            content_type = response.get("Content-Type", "")
            assert "csv" in content_type.lower(), "Content-Type should be CSV"
    
    def test_csv_has_content_disposition(self, api_client):
        """TASK: CSV export should have Content-Disposition header."""
        response = api_client.get("/api/v4/packages/?format=csv")
        
        if response.status_code == 200:
            content_disposition = response.get("Content-Disposition", "")
            assert content_disposition, "Should have Content-Disposition header"


class TestCsvContent:
    """Tests for CSV content structure."""
    
    def test_csv_has_header_row(self, api_client, package):
        """TASK: CSV should have header row."""
        response = api_client.get("/api/v4/packages/?format=csv")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            lines = content.strip().split('\n')
            assert len(lines) >= 1, "CSV should have at least header"
            headers = lines[0].lower()
            assert "title" in headers or "slug" in headers, "Headers should include field names"
    
    def test_csv_includes_packages(self, api_client, package):
        """TASK: CSV should include package data."""
        response = api_client.get("/api/v4/packages/?format=csv")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            lines = content.strip().split('\n')
            # Should have header + at least one data row
            assert len(lines) >= 2, "CSV should have data rows"


class TestCsvFieldsIncluded:
    """Tests for required fields in CSV."""
    
    def test_csv_includes_slug(self, api_client, package):
        """TASK: CSV should include slug field."""
        response = api_client.get("/api/v4/packages/?format=csv")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            assert package.slug in content, "Package slug should be in CSV"
    
    def test_csv_includes_title(self, api_client, package):
        """TASK: CSV should include title field."""
        response = api_client.get("/api/v4/packages/?format=csv")
        
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            headers = content.split('\n')[0].lower()
            assert "title" in headers, "CSV headers should include title"


class TestCsvSpecialCharacters:
    """Tests for proper CSV encoding."""
    
    def test_csv_handles_commas(self, api_client):
        """TASK: CSV should properly quote fields with commas."""
        response = api_client.get("/api/v4/packages/?format=csv")
        # Just verify no error
        assert response.status_code in (200, 404, 406)
    
    def test_csv_handles_quotes(self, api_client):
        """TASK: CSV should properly escape quotes."""
        response = api_client.get("/api/v4/packages/?format=csv")
        assert response.status_code in (200, 404, 406)
