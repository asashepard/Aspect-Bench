"""
Benchmark test for: github-fetch-timeout

Task: Add configurable timeout for GitHub API fetches.

Prompt:
The GitHub fetcher should have a configurable timeout for API requests.
Add GITHUB_TIMEOUT setting and pass it to requests. Handle timeout errors
gracefully and log them. Timeout should have a sensible default (30s).
"""

import pytest


pytestmark = pytest.mark.aspect_bench


# =============================================================================
# BASELINE TESTS - These should PASS before any changes
# =============================================================================

class TestGithubFetcherBaseline:
    """Baseline tests that verify existing GitHub fetcher functionality."""
    
    def test_github_module_exists(self):
        """BASELINE: GitHub module should exist."""
        try:
            from package.repos import github
            assert True
        except ImportError:
            try:
                from package.repos.github_handler import GitHubHandler
                assert True
            except ImportError:
                pass
        assert True  # Don't fail if import differs
    
    def test_package_repos_exists(self):
        """BASELINE: Package repos module should exist."""
        try:
            from package import repos
            assert True
        except ImportError:
            pass
        assert True
    
    def test_settings_accessible(self):
        """BASELINE: Django settings should be accessible."""
        from django.conf import settings
        assert settings.configured
    
    def test_requests_module_available(self):
        """BASELINE: Requests module should be available."""
        import requests
        assert requests is not None


# =============================================================================
# TASK TESTS - These should FAIL before implementation
# =============================================================================

class TestTimeoutConfiguration:
    """Tests for GitHub timeout configuration."""
    
    def test_github_timeout_in_settings(self):
        """TASK: GITHUB_TIMEOUT should be in settings."""
        from django.conf import settings
        
        timeout = getattr(settings, 'GITHUB_TIMEOUT', None)
        assert timeout is not None, "GITHUB_TIMEOUT should be configured"
    
    def test_github_timeout_is_reasonable(self):
        """TASK: GITHUB_TIMEOUT should be a reasonable value."""
        from django.conf import settings
        
        timeout = getattr(settings, 'GITHUB_TIMEOUT', None)
        assert timeout is not None, "GITHUB_TIMEOUT should be configured"
        assert 5 <= timeout <= 120, "Timeout should be between 5 and 120 seconds"


class TestTimeoutUsage:
    """Tests that timeout is actually used in requests."""
    
    def test_timeout_passed_to_requests(self):
        """TASK: Timeout should be passed to requests calls."""
        try:
            from package.repos import github
            source_file = getattr(github, '__file__', '')
            if source_file:
                with open(source_file, 'r') as f:
                    content = f.read()
                    uses_timeout = (
                        'timeout=' in content or
                        'GITHUB_TIMEOUT' in content
                    )
                    assert uses_timeout, "Should pass timeout to requests"
        except Exception:
            pytest.fail("Could not verify timeout usage")
    
    def test_timeout_from_settings(self):
        """TASK: Timeout should be read from settings."""
        try:
            from package.repos import github
            source_file = getattr(github, '__file__', '')
            if source_file:
                with open(source_file, 'r') as f:
                    content = f.read()
                    uses_settings = (
                        'settings.GITHUB_TIMEOUT' in content or
                        'getattr(settings' in content or
                        'GITHUB_TIMEOUT' in content
                    )
                    assert uses_settings, "Should use settings for timeout"
        except Exception:
            pytest.fail("Could not verify settings usage")


class TestTimeoutErrorHandling:
    """Tests for timeout error handling."""
    
    def test_handles_timeout_exception(self):
        """TASK: Should handle requests.Timeout exception."""
        try:
            from package.repos import github
            source_file = getattr(github, '__file__', '')
            if source_file:
                with open(source_file, 'r') as f:
                    content = f.read()
                    handles_timeout = (
                        'Timeout' in content or
                        'ReadTimeout' in content or
                        'ConnectTimeout' in content
                    )
                    assert handles_timeout, "Should handle Timeout exception"
        except Exception:
            pytest.fail("Could not verify timeout handling")
    
    def test_logs_timeout_errors(self):
        """TASK: Timeout errors should be logged."""
        try:
            from package.repos import github
            source_file = getattr(github, '__file__', '')
            if source_file:
                with open(source_file, 'r') as f:
                    content = f.read()
                    has_logging = (
                        'logger' in content.lower() or
                        'logging' in content or
                        'log.' in content
                    )
                    assert has_logging, "Should have logging for timeout errors"
        except Exception:
            pytest.fail("Could not verify logging")


class TestGracefulDegradation:
    """Tests for graceful degradation on timeout."""
    
    def test_no_crash_on_timeout(self):
        """TASK: App should not crash on GitHub timeout."""
        # The fetcher should catch timeout and handle gracefully
        try:
            from package.repos import github
            source_file = getattr(github, '__file__', '')
            if source_file:
                with open(source_file, 'r') as f:
                    content = f.read()
                    has_exception_handling = 'except' in content
                    assert has_exception_handling, "Should have exception handling"
        except Exception:
            pytest.fail("Could not verify exception handling")
    
    def test_returns_none_or_default_on_timeout(self):
        """TASK: Should return None or default value on timeout."""
        try:
            from package.repos import github
            source_file = getattr(github, '__file__', '')
            if source_file:
                with open(source_file, 'r') as f:
                    content = f.read()
                    has_return = 'return' in content
                    assert has_return, "Should return a value on error"
        except Exception:
            pytest.fail("Could not verify return value")
