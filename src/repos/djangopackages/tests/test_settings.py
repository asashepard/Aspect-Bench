"""
Minimal Django test settings for Aspect Code benchmark tests.

This avoids loading the full production settings which require many dependencies.
Tests use a minimal in-memory SQLite setup.
"""

import os
import sys
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent

# Path calculation:
# BASE_DIR = src/repos/djangopackages/tests
# parent = src/repos/djangopackages
# parent.parent = src/repos
# parent.parent.parent = src
# parent.parent.parent.parent = project root (aspect-code-bench)
PROJECT_ROOT = BASE_DIR.parent.parent.parent.parent
DJANGOPACKAGES_ROOT = PROJECT_ROOT / "repos" / "djangopackages"  # repos/djangopackages/
if str(DJANGOPACKAGES_ROOT) not in sys.path:
    sys.path.insert(0, str(DJANGOPACKAGES_ROOT))

SECRET_KEY = "test-secret-key-for-aspect-code-benchmarks-only"
DEBUG = True
ALLOWED_HOSTS = ["*"]
SITE_ID = 1
TEST_MODE = True

# Django Packages specific settings
PACKAGINATOR_HELP_TEXT = {
    "REPO_URL": "Enter your project repo hosting URL here.",
    "PYPI_URL": "What PyPI uses to index your package.",
}
PACKAGINATOR_SEARCH_PREFIX = "django"
RESTRICT_PACKAGE_EDITORS = False
RESTRICT_GRID_EDITORS = False
DOCS_URL = "https://docs.djangopackages.org"
FRAMEWORK_TITLE = "Django"
SITE_TITLE = "Django Packages"
PACKAGE_SCORE_MIN = -500
SUPPORTED_REPO = ["bitbucket", "github", "gitlab", "codeberg", "forgejo"]
GITLAB_TOKEN = ""
GITHUB_API_SECRET = ""
GITHUB_APP_ID = ""
GITHUB_TOKEN = ""
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap3"
CRISPY_TEMPLATE_PACK = "bootstrap3"
WAFFLE_CREATE_MISSING_SWITCHES = True
WAFFLE_CREATE_MISSING_FLAGS = True
MAINTENANCE_MODE = None
LOGIN_REDIRECT_URL = "/"
AUTH_PROFILE_MODULE = "profiles.Profile"
LOGIN_URL = "/auth/login/github/"
CACHE_TIMEOUT = 60 * 60
ADMIN_URL_BASE = "admin/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "rest_framework",
]

# Add all djangopackages apps - needed because urls.py imports them
DJANGOPACKAGES_APPS = [
    "package",
    "grid", 
    "searchv2",
    "profiles",
    "apiv4",
    "core",
    "blog",
    "classifiers",
    "favorites",
    "feeds",
    "homepage",
    "products",
    "apiv3",
]

for app in DJANGOPACKAGES_APPS:
    try:
        __import__(app)
        INSTALLED_APPS.append(app)
    except ImportError:
        pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Database - use in-memory SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Password validation - disabled for speed
AUTH_PASSWORD_VALIDATORS = []

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework settings - match real djangopackages settings
# Uses LimitOffsetPagination by default - task is to switch to PageNumberPagination
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# Cache - use dummy cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Logging - minimal
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
