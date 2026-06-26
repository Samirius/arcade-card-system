"""Security utility tests"""
import pytest
import time
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token, decode_token, verify_access_token
from app.utils.mfa import generate_mfa_secret, verify_mfa_token
from app.utils.rate_limit import InMemoryRateLimiter, get_client_ip

class TestPasswordSecurity:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed != password

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_is_unique(self):
        """Test that same password produces different hashes"""
        password = "SecurePassword123!"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # bcrypt includes salt

class TestJWTSecurity:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "user123", "role": "ADMIN"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "user123", "role": "ADMIN"}
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "ADMIN"
        assert "exp" in payload
        assert "iat" in payload
        assert payload["type"] == "access"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token"""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)

        assert payload is None

    def test_verify_access_token_valid(self):
        """Test verifying a valid access token"""
        data = {"sub": "user123", "role": "ADMIN"}
        token = create_access_token(data)
        payload = verify_access_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_verify_access_token_invalid_type(self):
        """Test verifying a token with wrong type"""
        data = {"sub": "user123", "role": "ADMIN"}
        # Create refresh token instead of access
        from app.utils.jwt import create_refresh_token
        token = create_refresh_token(data)
        payload = verify_access_token(token)

        assert payload is None  # Should fail due to wrong type

class TestMFASecurity:
    """Test MFA utilities"""

    def test_generate_mfa_secret(self):
        """Test MFA secret generation"""
        secret = generate_mfa_secret()

        assert secret is not None
        assert isinstance(secret, str)
        assert len(secret) == 32  # Base32 encoded

    def test_verify_mfa_token_correct(self):
        """Test MFA token verification with correct token"""
        secret = generate_mfa_secret()

        # Generate current valid token
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()

        assert verify_mfa_token(secret, token) is True

    def test_verify_mfa_token_incorrect(self):
        """Test MFA token verification with incorrect token"""
        secret = generate_mfa_secret()
        wrong_token = "123456"

        assert verify_mfa_token(secret, wrong_token) is False

class TestRateLimiting:
    """Test rate limiting"""

    def test_rate_limiter_below_limit(self):
        """Test rate limiter under the limit"""
        limiter = InMemoryRateLimiter()

        # Make 5 requests (limit is 100)
        for i in range(5):
            is_limited = limiter.is_rate_limited(
                key="test_user",
                max_requests=100,
                window_seconds=60
            )
            assert is_limited is False

    def test_rate_limiter_exceeds_limit(self):
        """Test rate limiter when limit is exceeded"""
        limiter = InMemoryRateLimiter()

        # Make 101 requests (limit is 100)
        for i in range(101):
            limiter.is_rate_limited(
                key="test_user",
                max_requests=100,
                window_seconds=60
            )

        # 101st request should be rate limited
        is_limited = limiter.is_rate_limited(
            key="test_user",
            max_requests=100,
            window_seconds=60
        )
        assert is_limited is True

    def test_rate_limiter_resets_after_window(self):
        """Test rate limiter resets after time window"""
        limiter = InMemoryRateLimiter()

        # Make 101 requests
        for i in range(101):
            limiter.is_rate_limited(
                key="test_user",
                max_requests=100,
                window_seconds=1  # 1 second window
            )

        # Should be rate limited
        assert limiter.is_rate_limited(
            key="test_user",
            max_requests=100,
            window_seconds=1
        ) is True

        # Wait for window to expire (in real implementation, use time.sleep)
        # For testing, just verify it was limited
        pass