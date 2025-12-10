"""
Benchmark test for: grid-lock-permissions

Task: Implement grid locking so locked grids cannot be modified.

Prompt:
Grids should have a lock feature. When a grid is locked, only admins should
be able to modify it. Add an 'is_locked' field to Grid model and implement
permission checks in GridViewSet to block edits on locked grids.
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestGridViewBaseline:
    """Baseline tests that verify existing grid view functionality."""
    
    def test_grid_detail_accessible_to_all(self, api_client, grid):
        """BASELINE: Grid detail should be publicly accessible."""
        url = f"/api/v4/grids/{grid.slug}/"
        response = api_client.get(url)
        assert response.status_code == 200
    
    def test_grid_list_accessible_to_all(self, api_client):
        """BASELINE: Grid list should be publicly accessible."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
    
    def test_anonymous_cannot_delete_grid(self, api_client, grid):
        """BASELINE: Anonymous users should not be able to delete grids."""
        url = f"/api/v4/grids/{grid.slug}/"
        response = api_client.delete(url)
        assert response.status_code in (401, 403, 405), "Anonymous delete should be blocked"
    
    def test_grid_returns_json(self, api_client, grid):
        """BASELINE: Grid detail should return valid JSON."""
        url = f"/api/v4/grids/{grid.slug}/"
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestLockedGridCannotBeEdited:
    """Tests that locked grids cannot be edited."""
    
    def test_locked_grid_edit_returns_403(self, authenticated_client, locked_grid):
        """TASK: Editing a locked grid should return 403."""
        url = f"/api/v4/grids/{locked_grid.slug}/"
        response = authenticated_client.patch(url, {"title": "Hacked"})
        assert response.status_code == 403, "Locked grid edit should return 403"
    
    def test_locked_grid_put_returns_403(self, authenticated_client, locked_grid):
        """TASK: PUT on a locked grid should return 403."""
        url = f"/api/v4/grids/{locked_grid.slug}/"
        response = authenticated_client.put(url, {"title": "Hacked"})
        assert response.status_code == 403, "Locked grid PUT should return 403"


class TestLockedGridStillViewable:
    """Tests that locked grids are still viewable."""
    
    def test_locked_grid_can_be_viewed(self, api_client, locked_grid):
        """TASK: Locked grids should still be viewable."""
        url = f"/api/v4/grids/{locked_grid.slug}/"
        response = api_client.get(url)
        assert response.status_code == 200, "Locked grid should be viewable"
    
    def test_locked_grid_appears_in_list(self, api_client, locked_grid):
        """TASK: Locked grids should appear in the list."""
        response = api_client.get("/api/v4/grids/")
        assert response.status_code == 200
        data = response.json()
        # Should find the locked grid in results
        if isinstance(data, dict) and "results" in data:
            slugs = [g.get("slug") for g in data["results"]]
        else:
            slugs = [g.get("slug") for g in data] if isinstance(data, list) else []
        assert locked_grid.slug in slugs, "Locked grid should appear in list"


class TestOnlyAdminCanLock:
    """Tests that only admins can lock grids."""
    
    def test_regular_user_cannot_lock_grid(self, authenticated_client, grid):
        """TASK: Regular users should not be able to lock grids."""
        url = f"/api/v4/grids/{grid.slug}/"
        response = authenticated_client.patch(url, {"is_locked": True})
        assert response.status_code == 403, "Regular users should not be able to lock"
    
    def test_admin_can_lock_grid(self, admin_client, grid):
        """TASK: Admins should be able to lock grids."""
        url = f"/api/v4/grids/{grid.slug}/"
        response = admin_client.patch(url, {"is_locked": True})
        assert response.status_code == 200, "Admin should be able to lock"


class TestAdminCanEditLockedGrid:
    """Tests that admins can still edit locked grids."""
    
    def test_admin_can_edit_locked_grid(self, admin_client, locked_grid):
        """TASK: Admins should be able to edit locked grids."""
        url = f"/api/v4/grids/{locked_grid.slug}/"
        response = admin_client.patch(url, {"title": "Admin Updated"})
        assert response.status_code == 200, "Admin should be able to edit locked grid"
    
    def test_admin_can_unlock_grid(self, admin_client, locked_grid):
        """TASK: Admins should be able to unlock grids."""
        url = f"/api/v4/grids/{locked_grid.slug}/"
        response = admin_client.patch(url, {"is_locked": False})
        assert response.status_code == 200, "Admin should be able to unlock"
