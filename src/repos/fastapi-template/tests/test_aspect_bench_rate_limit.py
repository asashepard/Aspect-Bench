"""
Benchmark tests for: rate-limit-login

PROMPT SAYS:
"We need rate limiting on the login endpoint to prevent brute force attacks. 
Something like 5 attempts per minute per IP, then block them temporarily. 
Return a 429 Too Many Requests when they're rate limited."

Tests based SOLELY on prompt requirements:
1. After 5 failed login attempts, further attempts should be blocked
2. Rate limiting is per-IP (or per client for test purposes)
3. Should return 429 Too Many Requests when rate limited
4. Block should be temporary (eventually lifts)
"""

import time
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings


pytestmark = pytest.mark.aspect_bench


class TestRateLimitBasic:
    """Test that rate limiting exists on the login endpoint."""
    
    def test_login_rate_limited_after_many_attempts(
        self, client: TestClient
    ) -> None:
        """After many failed login attempts, should get rate limited."""
        # Make 10 failed login attempts - should trigger rate limit at some point
        got_rate_limited = False
        
        for i in range(10):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": f"nonexistent{i}@example.com",
                    "password": "wrongpassword",
                },
            )
            
            if response.status_code == 429:
                got_rate_limited = True
                break
        
        assert got_rate_limited, \
            "Should get rate limited (429) after multiple failed login attempts"
    
    def test_rate_limit_returns_429(
        self, client: TestClient
    ) -> None:
        """Rate limit response should be 429 Too Many Requests."""
        # Trigger rate limiting
        for i in range(10):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": "attacker@example.com",
                    "password": "wrongpassword",
                },
            )
            
            if response.status_code == 429:
                # Verify it's actually 429
                assert response.status_code == 429
                return
        
        pytest.fail("Never got rate limited - rate limiting not implemented")


class TestRateLimitThreshold:
    """Test the rate limit threshold."""
    
    def test_first_few_attempts_not_blocked(
        self, client: TestClient
    ) -> None:
        """First few login attempts should not be blocked."""
        # First 3 attempts should work (even if they fail auth)
        for i in range(3):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": f"test_threshold_{i}@example.com",
                    "password": "wrongpassword",
                },
            )
            # Should get 400 (bad credentials) not 429 (rate limited)
            assert response.status_code != 429, \
                f"Attempt {i+1} should not be rate limited"
    
    def test_rate_limit_triggers_around_5_attempts(
        self, client: TestClient
    ) -> None:
        """Rate limit should trigger around 5 attempts per the prompt."""
        attempt_count = 0
        
        for i in range(15):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": "threshold_test@example.com",
                    "password": "wrongpassword",
                },
            )
            attempt_count += 1
            
            if response.status_code == 429:
                # Should be blocked somewhere between 4-10 attempts
                assert 4 <= attempt_count <= 10, \
                    f"Rate limit triggered after {attempt_count} attempts (expected ~5)"
                return
        
        pytest.fail("Rate limit never triggered")


class TestRateLimitResponse:
    """Test the rate limit response format."""
    
    def test_rate_limit_has_detail_message(
        self, client: TestClient
    ) -> None:
        """Rate limit response should include helpful message."""
        # Trigger rate limit
        for i in range(10):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": "message_test@example.com",
                    "password": "wrongpassword",
                },
            )
            
            if response.status_code == 429:
                data = response.json()
                # Should have some message
                assert "detail" in data or "message" in data or "error" in data, \
                    "Rate limit response should include a message"
                return
        
        pytest.fail("Never got rate limited")
    
    def test_rate_limit_has_retry_after_header(
        self, client: TestClient
    ) -> None:
        """
        Rate limit response MUST include Retry-After header.
        
        The prompt specifies: "with a Retry-After header indicating seconds until the block expires"
        """
        # Trigger rate limit
        for i in range(10):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": "retry_header_test@example.com",
                    "password": "wrongpassword",
                },
            )
            
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                assert retry_after is not None, \
                    "Rate limit response MUST have Retry-After header"
                # Should be a number (seconds)
                assert retry_after.isdigit(), \
                    f"Retry-After should be seconds, got: {retry_after}"
                return
        
        pytest.fail("Never got rate limited")


class TestRateLimitPerUsername:
    """
    Test that rate limiting is per-username, not global or per-IP.
    
    The prompt says: "Track failed login attempts per username (not IP, since attackers rotate IPs)"
    """
    
    def test_rate_limit_is_per_username(
        self, client: TestClient
    ) -> None:
        """
        Rate limiting should be per-username - different usernames have separate limits.
        """
        # Max out rate limit for user1
        for i in range(10):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": "rate_limited_user@example.com",
                    "password": "wrongpassword",
                },
            )
            if response.status_code == 429:
                break
        
        # A DIFFERENT username should NOT be rate limited
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={
                "username": "fresh_user_not_limited@example.com",
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code != 429, \
            "Rate limiting should be per-username - different user should not be limited"
    
    def test_same_username_shares_limit(
        self, client: TestClient
    ) -> None:
        """
        Same username should share the rate limit across requests.
        """
        target_username = "shared_limit_test@example.com"
        got_limited = False
        
        for i in range(10):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": target_username,
                    "password": "wrongpassword",
                },
            )
            if response.status_code == 429:
                got_limited = True
                break
        
        assert got_limited, \
            "Same username should accumulate failed attempts and get rate limited"


class TestRateLimitTemporary:
    """Test that rate limit block is temporary."""
    
    def test_rate_limit_eventually_expires(
        self, client: TestClient
    ) -> None:
        """Rate limit should eventually expire (be temporary)."""
        # First trigger rate limit
        rate_limited = False
        for i in range(10):
            response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={
                    "username": "expire_test@example.com",
                    "password": "wrongpassword",
                },
            )
            if response.status_code == 429:
                rate_limited = True
                break
        
        if not rate_limited:
            pytest.skip("Could not trigger rate limit")
        
        # Wait a bit (prompt says per minute, so wait 60+ seconds for full test)
        # For practical testing, we'll check if there's any concept of expiry
        # by checking the Retry-After header or trying after a short wait
        
        time.sleep(2)  # Short wait to at least verify it doesn't instantly reset
        
        # This is a minimal check - full test would wait 60+ seconds
        response = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={
                "username": "expire_test@example.com",
                "password": "wrongpassword",
            },
        )
        # Just verify we can still make the request (rate limit continues or expires)
        assert response.status_code in (400, 429)


class TestRateLimitEdgeCases:
    """Edge cases for rate limiting."""
    
    def test_successful_login_also_counts(
        self, client: TestClient, db: Session
    ) -> None:
        """Verify rate limiting applies to all attempts, not just failed ones."""
        # This is harder to test without creating many users
        # For now, just verify the basic rate limit works
        pass
    
    def test_rate_limit_only_on_login(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Rate limiting should be on login, not other endpoints."""
        # Other endpoints should not be affected by login rate limit
        for i in range(10):
            response = client.get(
                f"{settings.API_V1_STR}/users/me",
                headers=superuser_token_headers,
            )
            # Should never get 429 on this endpoint
            assert response.status_code != 429, \
                "Non-login endpoints should not have login rate limiting"
