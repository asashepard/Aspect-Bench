"""
Benchmark test for: package-edit-permissions

Task: Implement permission check so only package owners/maintainers can edit.

Prompt:
Package editing should be restricted to owners and maintainers. Currently
anyone can edit. Add permission checks to PackageViewSet to verify the user
is an owner or maintainer before allowing edit/delete operations.
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestPackageViewBaseline:
    """Baseline tests that verify existing package view functionality."""
    
    def test_package_detail_accessible_to_all(self, api_client, package):
        """BASELINE: Package detail should be publicly accessible."""
        url = f"/api/v4/packages/{package.slug}/"
        response = api_client.get(url)
        assert response.status_code == 200
    
    def test_package_list_accessible_to_all(self, api_client):
        """BASELINE: Package list should be publicly accessible."""
        response = api_client.get("/api/v4/packages/")
        assert response.status_code == 200
    
    def test_anonymous_cannot_delete_package(self, api_client, package):
        """BASELINE: Anonymous users should not be able to delete packages."""
        url = f"/api/v4/packages/{package.slug}/"
        response = api_client.delete(url)
        # Should be 401, 403, or 405
        assert response.status_code in (401, 403, 405), "Anonymous delete should be blocked"
    
    def test_authenticated_user_can_view_packages(self, authenticated_client, package):
        """BASELINE: Authenticated users should be able to view packages."""
        url = f"/api/v4/packages/{package.slug}/"
        response = authenticated_client.get(url)
        assert response.status_code == 200


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestNonOwnerCannotEdit:
    """Tests that non-owners cannot edit packages."""
    
    def test_non_owner_cannot_edit_package(self, authenticated_client, package):
        """TASK: Non-owners should not be able to edit packages."""
        url = f"/api/v4/packages/{package.slug}/"
        response = authenticated_client.patch(url, {"title": "Hacked"})
        # Should be 403 forbidden (not 200 or 405)
        assert response.status_code == 403, "Non-owner edit should return 403"
    
    def test_non_owner_cannot_put_package(self, authenticated_client, package):
        """TASK: Non-owners should not be able to PUT packages."""
        url = f"/api/v4/packages/{package.slug}/"
        response = authenticated_client.put(url, {"title": "Hacked"})
        assert response.status_code == 403, "Non-owner PUT should return 403"


class TestOwnerCanEdit:
    """Tests that owners can edit their packages."""
    
    def test_owner_can_edit_package(self, owner_client, package):
        """TASK: Package owners should be able to edit."""
        url = f"/api/v4/packages/{package.slug}/"
        response = owner_client.patch(url, {"title": "Updated by Owner"})
        # Owner should get 200
        assert response.status_code == 200, "Owner should be able to edit"
    
    def test_owner_edit_persists(self, owner_client, package):
        """TASK: Owner edits should persist."""
        url = f"/api/v4/packages/{package.slug}/"
        new_title = "Owner Updated Title"
        response = owner_client.patch(url, {"title": new_title})
        
        if response.status_code == 200:
            # Verify the change persisted
            get_response = owner_client.get(url)
            assert new_title in str(get_response.json())


class TestAdminPermissions:
    """Tests for admin permissions on packages."""
    
    def test_admin_can_edit_any_package(self, admin_client, package):
        """TASK: Admins should be able to edit any package."""
        url = f"/api/v4/packages/{package.slug}/"
        response = admin_client.patch(url, {"title": "Updated by Admin"})
        # Admin should get 200
        assert response.status_code == 200, "Admin should be able to edit any package"
    
    def test_admin_can_delete_any_package(self, admin_client, package):
        """TASK: Admins should be able to delete any package."""
        url = f"/api/v4/packages/{package.slug}/"
        response = admin_client.delete(url)
        # Admin should get 204 or 200
        assert response.status_code in (200, 204), "Admin should be able to delete"


class TestEditRequiresAuth:
    """Tests that edit operations require authentication."""
    
    def test_anonymous_edit_returns_401(self, api_client, package):
        """TASK: Anonymous edit should return 401 specifically."""
        url = f"/api/v4/packages/{package.slug}/"
        response = api_client.patch(url, {"title": "Hacked"})
        assert response.status_code == 401, "Anonymous edit should return 401"
    
    def test_anonymous_put_returns_401(self, api_client, package):
        """TASK: Anonymous PUT should return 401 specifically."""
        url = f"/api/v4/packages/{package.slug}/"
        response = api_client.put(url, {"title": "Hacked"})
        assert response.status_code == 401, "Anonymous PUT should return 401"
