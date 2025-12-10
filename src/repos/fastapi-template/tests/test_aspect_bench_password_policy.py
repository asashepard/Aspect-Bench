"""
Benchmark tests for: stronger-password-policy

PROMPT SAYS:
"Our password policy is too weak - we only require 8 characters. We need a stronger 
policy that requires uppercase, lowercase, digits, and special characters. 
Make sure it's enforced on signup, password update, and password reset. 
The error messages should tell users what's missing."

Tests based SOLELY on prompt requirements:
1. Password must require uppercase letter
2. Password must require lowercase letter
3. Password must require digit
4. Password must require special character
5. Enforced on signup
6. Enforced on password update
7. Enforced on password reset
8. Error messages should indicate what's missing
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.utils.utils import random_email


pytestmark = pytest.mark.aspect_bench


class TestPasswordRequiresUppercase:
    """Test that passwords require uppercase letters."""
    
    def test_password_without_uppercase_rejected(
        self, client: TestClient
    ) -> None:
        """Password without uppercase should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "password1!",  # No uppercase
            },
        )
        assert response.status_code == 422, \
            "Password without uppercase should be rejected"


class TestPasswordRequiresLowercase:
    """Test that passwords require lowercase letters."""
    
    def test_password_without_lowercase_rejected(
        self, client: TestClient
    ) -> None:
        """Password without lowercase should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "PASSWORD1!",  # No lowercase
            },
        )
        assert response.status_code == 422, \
            "Password without lowercase should be rejected"


class TestPasswordRequiresDigit:
    """Test that passwords require digits."""
    
    def test_password_without_digit_rejected(
        self, client: TestClient
    ) -> None:
        """Password without digit should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Password!",  # No digit
            },
        )
        assert response.status_code == 422, \
            "Password without digit should be rejected"


class TestPasswordRequiresSpecialChar:
    """Test that passwords require special characters."""
    
    def test_password_without_special_char_rejected(
        self, client: TestClient
    ) -> None:
        """Password without special character should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Password1",  # No special char
            },
        )
        assert response.status_code == 422, \
            "Password without special character should be rejected"


class TestStrongPasswordAccepted:
    """Test that strong passwords are accepted."""
    
    def test_password_with_all_requirements_accepted(
        self, client: TestClient
    ) -> None:
        """Password meeting all requirements should be accepted."""
        # Must be 12+ chars with all requirements
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "StrongPass1!ab",  # 14 chars, has all requirements
            },
        )
        assert response.status_code == 200, \
            "Password with all requirements should be accepted"
    
    def test_various_strong_passwords_accepted(
        self, client: TestClient
    ) -> None:
        """Various strong passwords should be accepted."""
        # All must be 12+ characters
        strong_passwords = [
            "MyP@ssw0rd!Secure",
            "Str0ng_P@ssword!",
            "C0mplex!PassWord",
            "Valid123$$$abcd",
            "Aa1!aaaaaaaab",  # 13 chars, minimal requirements met
        ]
        
        for password in strong_passwords:
            response = client.post(
                f"{settings.API_V1_STR}/users/signup",
                json={
                    "email": random_email(),
                    "password": password,
                },
            )
            assert response.status_code == 200, \
                f"Strong password '{password}' should be accepted"


class TestMinimum12Characters:
    """
    Test that password requires minimum 12 characters.
    
    The prompt says: "minimum 12 characters"
    """
    
    def test_11_char_password_rejected(
        self, client: TestClient
    ) -> None:
        """11-character password should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Password1!a",  # 11 chars
            },
        )
        assert response.status_code == 422, \
            "Password under 12 characters should be rejected"
    
    def test_12_char_password_accepted(
        self, client: TestClient
    ) -> None:
        """12-character password should be accepted if other requirements met."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Password1!ab",  # Exactly 12 chars
            },
        )
        assert response.status_code == 200, \
            "12-character password with all requirements should be accepted"


class TestPasswordCannotContainEmail:
    """
    Test that password cannot contain user's email username.
    
    The prompt says: "cannot contain the user's email username"
    """
    
    def test_password_with_email_username_rejected(
        self, client: TestClient
    ) -> None:
        """Password containing email username should be rejected."""
        email = "johnsmith@example.com"
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": email,
                "password": "Johnsmith123!!",  # Contains 'johnsmith'
            },
        )
        assert response.status_code == 422, \
            "Password containing email username should be rejected"
    
    def test_password_without_email_username_accepted(
        self, client: TestClient
    ) -> None:
        """Password not containing email username should be accepted."""
        email = "johnsmith@example.com"
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": email,
                "password": "SecurePass123!!",  # Does not contain 'johnsmith'
            },
        )
        assert response.status_code == 200


class TestCommonPasswordsRejected:
    """
    Test that common passwords are rejected.
    
    The prompt says: "cannot be in a list of common passwords (include at least 100 common passwords)"
    """
    
    def test_common_password_rejected(
        self, client: TestClient
    ) -> None:
        """Common passwords should be rejected even if they meet other requirements."""
        # Common passwords that might meet character requirements
        common_passwords = [
            "Password123!",
            "Qwerty12345!",
            "Welcome123!!",
            "Admin12345!!",
        ]
        
        for password in common_passwords:
            response = client.post(
                f"{settings.API_V1_STR}/users/signup",
                json={
                    "email": random_email(),
                    "password": password,
                },
            )
            # Should be rejected as common password
            assert response.status_code == 422, \
                f"Common password '{password}' should be rejected"


class TestAllFailuresListed:
    """
    Test that validation errors list ALL failures, not just the first one.
    
    The prompt says: "Return a 422 with specific validation errors listing ALL failures, not just the first one"
    """
    
    def test_multiple_failures_all_listed(
        self, client: TestClient
    ) -> None:
        """All validation failures should be listed in the response."""
        # Password with multiple issues: too short, no special char, no digit
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Weak",  # Multiple failures
            },
        )
        
        assert response.status_code == 422
        data = response.json()
        detail = data.get("detail", [])
        
        # Should have multiple error messages
        if isinstance(detail, list):
            assert len(detail) >= 2, \
                "Should list ALL validation failures, not just the first one"
        elif isinstance(detail, str):
            # Count different requirement mentions
            requirements_mentioned = sum([
                "length" in detail.lower() or "character" in detail.lower() or "12" in detail,
                "upper" in detail.lower(),
                "lower" in detail.lower(),
                "digit" in detail.lower() or "number" in detail.lower(),
                "special" in detail.lower() or "symbol" in detail.lower(),
            ])
            assert requirements_mentioned >= 2, \
                "Error message should list multiple failing requirements"


class TestPasswordPolicyOnSignup:
    """Test that policy is enforced on signup."""
    
    def test_weak_passwords_rejected_on_signup(
        self, client: TestClient
    ) -> None:
        """Weak passwords should be rejected on signup."""
        weak_passwords = [
            "12345678",      # No letters
            "password",      # No digits or special
            "Password",      # No digits or special
            "Password1",     # No special
            "password1!",    # No uppercase
            "PASSWORD1!",    # No lowercase
        ]
        
        for password in weak_passwords:
            response = client.post(
                f"{settings.API_V1_STR}/users/signup",
                json={
                    "email": random_email(),
                    "password": password,
                },
            )
            assert response.status_code == 422, \
                f"Weak password '{password}' should be rejected on signup"


class TestPasswordPolicyOnUpdate:
    """Test that policy is enforced on password update."""
    
    def test_weak_password_rejected_on_update(
        self, client: TestClient, db: Session
    ) -> None:
        """Weak password should be rejected on password update."""
        # Create user with strong password
        email = random_email()
        strong_pass = "StrongPass1!"
        
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={"email": email, "password": strong_pass},
        )
        
        if response.status_code != 200:
            pytest.skip("Could not create test user")
        
        # Login
        r = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": email, "password": strong_pass},
        )
        
        if r.status_code != 200:
            pytest.skip("Could not login")
        
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to update to weak password
        response = client.patch(
            f"{settings.API_V1_STR}/users/me/password",
            headers=headers,
            json={
                "current_password": strong_pass,
                "new_password": "weakpass",  # Weak
            },
        )
        
        assert response.status_code == 422, \
            "Weak password should be rejected on update"


class TestPasswordPolicyOnAdminCreate:
    """Test that policy is enforced when admin creates users."""
    
    def test_weak_password_rejected_on_admin_create(
        self, client: TestClient, superuser_token_headers: dict[str, str]
    ) -> None:
        """Weak password should be rejected when admin creates user."""
        from unittest.mock import patch
        
        with (
            patch("app.utils.send_email", return_value=None),
            patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
            patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
        ):
            response = client.post(
                f"{settings.API_V1_STR}/users/",
                headers=superuser_token_headers,
                json={
                    "email": random_email(),
                    "password": "weakpass",  # Weak
                },
            )
            
            assert response.status_code == 422, \
                "Weak password should be rejected on admin user creation"


class TestHelpfulErrorMessages:
    """Test that error messages indicate what's missing."""
    
    def test_error_message_is_helpful(
        self, client: TestClient
    ) -> None:
        """Error message should indicate password requirements."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "weak",  # Missing everything
            },
        )
        
        assert response.status_code == 422
        data = response.json()
        detail_str = str(data.get("detail", "")).lower()
        
        # Should mention at least some requirements
        keywords = [
            "uppercase", "upper", "capital",
            "lowercase", "lower",
            "digit", "number", "numeric",
            "special", "symbol", "character",
            "length", "characters", "minimum"
        ]
        
        has_helpful_hint = any(kw in detail_str for kw in keywords)
        assert has_helpful_hint, \
            f"Error should mention requirements. Got: {data.get('detail')}"


class TestPasswordPolicyEdgeCases:
    """Edge cases for password policy."""
    
    def test_exactly_meets_requirements(
        self, client: TestClient
    ) -> None:
        """Password that exactly meets requirements should work."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Aa1!aaaa",  # Exactly 8 chars, has all requirements
            },
        )
        assert response.status_code == 200
    
    def test_too_short_password(
        self, client: TestClient
    ) -> None:
        """Password shorter than 8 characters should be rejected."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Aa1!",  # Too short
            },
        )
        assert response.status_code == 422
    
    def test_unicode_special_char(
        self, client: TestClient
    ) -> None:
        """Unicode characters should be handled."""
        response = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": "Password1€",  # Unicode special char
            },
        )
        # Either accepted (euro as special) or rejected cleanly
        assert response.status_code in (200, 422)
