"""
Pytest configuration for Aspect Code benchmark tests - Django Packages.

These tests are designed to work with pytest and the REST framework test client.
"""

import sys
import os
from pathlib import Path

import pytest

# Path setup - must happen before Django is loaded
TESTS_DIR = Path(__file__).parent  # src/repos/djangopackages/tests
REPO_HARNESS_DIR = TESTS_DIR.parent  # src/repos/djangopackages
REPOS_DIR = REPO_HARNESS_DIR.parent  # src/repos
HARNESS_DIR = REPOS_DIR.parent  # src/
PROJECT_ROOT = HARNESS_DIR.parent  # Project root
DJANGOPACKAGES_ROOT = PROJECT_ROOT / "repos" / "djangopackages"  # repos/djangopackages/

# Add tests dir FIRST (so test_settings is found before djangopackages settings.py)
# Then add djangopackages root for app imports
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(DJANGOPACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(DJANGOPACKAGES_ROOT))

# Set Django settings module BEFORE importing Django
# Use fully qualified module path to avoid conflicts with djangopackages/settings.py
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"

# Now import and setup Django
import django
django.setup()

# Create database tables for testing
# We use migrate with fake to bypass PostgreSQL-specific migrations
from django.db import connection
from django.core.management import call_command

def create_test_tables():
    """Create minimal tables needed for tests."""
    # First, try normal migration with syncdb
    try:
        call_command('migrate', '--run-syncdb', verbosity=0)
        return
    except Exception:
        pass
    
    # If that fails, create tables manually
    with connection.cursor() as cursor:
        # Check if tables exist, if not create them
        tables_sql = """
        CREATE TABLE IF NOT EXISTS auth_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(150) NOT NULL UNIQUE,
            email VARCHAR(254),
            password VARCHAR(128),
            is_staff BOOLEAN DEFAULT 0,
            is_superuser BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            first_name VARCHAR(150) DEFAULT '',
            last_name VARCHAR(150) DEFAULT '',
            date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        );
        
        CREATE TABLE IF NOT EXISTS package_category (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(100),
            slug VARCHAR(50) UNIQUE,
            description TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified DATETIME DEFAULT CURRENT_TIMESTAMP,
            show_pypi BOOLEAN DEFAULT 1
        );
        
        CREATE TABLE IF NOT EXISTS package_package (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255),
            slug VARCHAR(50) UNIQUE,
            description TEXT DEFAULT '',
            repo_url VARCHAR(200) DEFAULT '',
            repo_host VARCHAR(30) DEFAULT '',
            pypi_url VARCHAR(200) DEFAULT '',
            category_id INTEGER,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by_id INTEGER,
            last_modified_by_id INTEGER,
            repo_description TEXT DEFAULT '',
            repo_watchers INTEGER DEFAULT 0,
            repo_forks INTEGER DEFAULT 0,
            pypi_version VARCHAR(50) DEFAULT '',
            pypi_downloads INTEGER DEFAULT 0,
            pypi_classifiers TEXT,
            pypi_info TEXT,
            pypi_license VARCHAR(100),
            pypi_licenses TEXT,
            pypi_requires_python VARCHAR(100),
            markers TEXT,
            supports_python3 BOOLEAN,
            participants TEXT DEFAULT '',
            favorite_count INTEGER DEFAULT 0,
            commit_list TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            documentation_url VARCHAR(200) DEFAULT '',
            last_fetched DATETIME,
            date_deprecated DATETIME,
            date_repo_archived DATETIME,
            deprecated_by_id INTEGER,
            deprecates_package_id INTEGER,
            last_exception TEXT,
            last_exception_at DATETIME,
            last_exception_count INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS grid_grid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(100),
            slug VARCHAR(50) UNIQUE,
            description TEXT DEFAULT '',
            is_locked BOOLEAN DEFAULT 0,
            header BOOLEAN DEFAULT 1,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS grid_gridpackage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grid_id INTEGER,
            package_id INTEGER,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(grid_id, package_id)
        );
        
        CREATE TABLE IF NOT EXISTS django_content_type (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_label VARCHAR(100),
            model VARCHAR(100),
            UNIQUE(app_label, model)
        );
        
        CREATE TABLE IF NOT EXISTS package_commit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER,
            commit_date DATETIME,
            commit_hash VARCHAR(150),
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS package_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER,
            number VARCHAR(100) DEFAULT '',
            downloads INTEGER DEFAULT 0,
            license VARCHAR(100),
            licenses TEXT,
            hidden BOOLEAN DEFAULT 0,
            upload_time DATETIME,
            development_status INTEGER DEFAULT 0,
            supports_python3 BOOLEAN DEFAULT 0,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS searchv2_searchv2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type VARCHAR(40) DEFAULT '',
            title VARCHAR(100) DEFAULT '',
            title_no_prefix VARCHAR(100) DEFAULT '',
            slug VARCHAR(50) UNIQUE,
            slug_no_prefix VARCHAR(50) DEFAULT '',
            clean_title VARCHAR(100) DEFAULT '',
            description TEXT DEFAULT '',
            category VARCHAR(50) DEFAULT '',
            absolute_url VARCHAR(255) DEFAULT '',
            repo_watchers INTEGER DEFAULT 0,
            repo_forks INTEGER DEFAULT 0,
            pypi_downloads INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            usage INTEGER DEFAULT 0,
            participants TEXT DEFAULT '',
            last_committed DATETIME,
            last_released DATETIME,
            weight INTEGER DEFAULT 0,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        for statement in tables_sql.strip().split(';'):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except Exception:
                    pass

# Create the tables
create_test_tables()

pytestmark = pytest.mark.aspect_bench


@pytest.fixture(scope="session")
def django_db_setup():
    """Database already set up at module load - this is a no-op fixture."""
    pass


@pytest.fixture
def api_client(django_db_setup):
    """Create an API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def db_setup(django_db_setup):
    """Ensure database is set up (alias for compatibility)."""
    return True


@pytest.fixture
def user(django_db_setup):
    """Create a regular user for testing."""
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(
        username="testuser",
        defaults={"email": "testuser@example.com"}
    )
    user.set_password("testpass123")
    user.save()
    return user


@pytest.fixture
def admin_user(django_db_setup):
    """Create an admin/superuser for testing."""
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@example.com",
            "is_staff": True,
            "is_superuser": True,
        }
    )
    user.set_password("adminpass123")
    user.save()
    return user


@pytest.fixture
def authenticated_client(api_client, user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Create an admin-authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def owner_user(django_db_setup):
    """Create a user who owns a package."""
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(
        username="owner",
        defaults={"email": "owner@example.com"}
    )
    user.set_password("ownerpass123")
    user.save()
    return user


@pytest.fixture
def owner_client(django_db_setup, owner_user):
    """Create an API client authenticated as package owner."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=owner_user)
    return client


# Mock fixtures for model objects that may not be available
class MockModel:
    """Mock model for testing when Django models aren't available."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.fixture
def category(django_db_setup):
    """Create a test category using raw SQL."""
    from django.db import connection
    from package.models import Category
    
    with connection.cursor() as cursor:
        # Insert or get category using raw SQL
        cursor.execute(
            "INSERT OR IGNORE INTO package_category (title, slug, description, show_pypi) VALUES ('Test Category', 'test-category', 'A test category', 1)"
        )
    
    # Return the category object
    try:
        return Category.objects.get(slug="test-category")
    except Exception:
        return MockModel(id=1, pk=1, slug="test-category", title="Test Category")


@pytest.fixture
def package(django_db_setup, category):
    """Create a test package using raw SQL."""
    from django.db import connection
    from package.models import Package
    
    cat_id = category.pk if hasattr(category, 'pk') else 1
    
    with connection.cursor() as cursor:
        # Insert package using raw SQL (bypassing model save which uses PostgreSQL features)
        cursor.execute(
            f"INSERT OR IGNORE INTO package_package (title, slug, category_id, repo_url, repo_host) VALUES ('Test Package', 'test-package', {cat_id}, 'https://github.com/test/test-package', '')"
        )
    
    # Return the package object
    try:
        return Package.objects.get(slug="test-package")
    except Exception:
        return MockModel(id=1, pk=1, slug="test-package", title="Test Package")


@pytest.fixture
def grid(django_db_setup):
    """Create a test grid using raw SQL."""
    from django.db import connection
    from grid.models import Grid
    
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT OR IGNORE INTO grid_grid (title, slug, description, is_locked, header) VALUES ('Test Grid', 'test-grid', 'A test grid', 0, 1)"
        )
    
    try:
        return Grid.objects.get(slug="test-grid")
    except Exception:
        return MockModel(id=1, pk=1, slug="test-grid", title="Test Grid", is_locked=False)


@pytest.fixture
def locked_grid(django_db_setup):
    """Create a locked test grid using raw SQL."""
    from django.db import connection
    from grid.models import Grid
    
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT OR IGNORE INTO grid_grid (title, slug, description, is_locked, header) VALUES ('Locked Grid', 'locked-grid', 'A locked grid', 1, 1)"
        )
    
    try:
        return Grid.objects.get(slug="locked-grid")
    except Exception:
        return MockModel(id=1, pk=1, slug="locked-grid", title="Locked Grid", is_locked=True)
