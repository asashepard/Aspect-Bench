"""
Benchmark test for: grid-json-export

Task: Add JSON export endpoint for grid data including FULL package data.

Prompt:
The grid detail endpoint currently includes package hyperlinks.
Create a dedicated export endpoint at /api/v4/grids/{slug}/export/ that
includes full nested package data (not just hyperlinks).
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestGridExportBaseline:
    """Baseline tests that verify existing grid functionality."""
    
    def test_grid_detail_returns_json(self, api_client, grid):
        """BASELINE: Grid detail should return JSON."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_grid_list_works(self, api_client):
        """BASELINE: Grid list should work."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
    
    def test_grid_has_slug(self, api_client, grid):
        """BASELINE: Grid response should have slug."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/")
        assert response.status_code == 200
        data = response.json()
        assert "slug" in data
    
    def test_grid_has_title(self, api_client, grid):
        """BASELINE: Grid response should have title."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/")
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
    
    def test_grid_has_packages_field(self, api_client, grid):
        """BASELINE: Grid already has packages field (as hyperlinks)."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/")
        assert response.status_code == 200
        data = response.json()
        assert "packages" in data


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestGridExportEndpointExists:
    """Tests for dedicated grid export endpoint."""
    
    def test_grid_export_endpoint_returns_200(self, api_client, grid):
        """TASK: Grid export endpoint should exist and return 200."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/export/")
        assert response.status_code == 200, "Export endpoint should exist at /api/v4/grids/{slug}/export/"
    
    def test_grid_export_endpoint_returns_json(self, api_client, grid):
        """TASK: Grid export endpoint should return JSON."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/export/")
        assert response.status_code == 200, "Export endpoint should exist"
        data = response.json()
        assert isinstance(data, dict), "Export should return JSON dict"


class TestGridExportIncludesNestedPackages:
    """Tests for nested package data in export."""
    
    def test_export_packages_are_dicts(self, api_client, grid):
        """TASK: Export packages should be dicts, not URLs."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/export/")
        assert response.status_code == 200, "Export endpoint required"
        
        data = response.json()
        assert "packages" in data, "Export should have packages"
        # If there are packages, they should be dicts not strings
        if data["packages"]:
            first_pkg = data["packages"][0]
            assert isinstance(first_pkg, dict), "Packages should be nested dicts, not hyperlinks"
    
    def test_export_package_has_title(self, api_client, grid):
        """TASK: Export packages should include title field."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/export/")
        assert response.status_code == 200, "Export endpoint required"
        
        data = response.json()
        if data.get("packages"):
            first_pkg = data["packages"][0]
            assert isinstance(first_pkg, dict), "Package should be a dict"
            assert "title" in first_pkg, "Package should have title"


class TestGridExportPackageDetails:
    """Tests for package detail fields in export."""
    
    def test_export_package_has_repo_url(self, api_client, grid):
        """TASK: Export packages should include repo_url."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/export/")
        assert response.status_code == 200, "Export endpoint required"
        
        data = response.json()
        if data.get("packages"):
            first_pkg = data["packages"][0]
            assert "repo_url" in first_pkg, "Package should have repo_url"
    
    def test_export_package_has_description(self, api_client, grid):
        """TASK: Export packages should include description."""
        response = api_client.get(f"/api/v4/grids/{grid.slug}/export/")
        assert response.status_code == 200, "Export endpoint required"
        
        data = response.json()
        if data.get("packages"):
            first_pkg = data["packages"][0]
            assert "description" in first_pkg, "Package should have description"
