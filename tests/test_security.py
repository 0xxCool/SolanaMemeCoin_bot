"""
Security tests
"""
import pytest
from security import SecurityManager, RateLimiter


@pytest.mark.security
class TestSecurity:
    """Test security features"""

    def test_encryption_decryption(self):
        """Test data encryption and decryption"""
        security = SecurityManager(secret_key="test_secret_key_12345")

        original_data = "sensitive_private_key_data"
        encrypted = security.encrypt(original_data)

        assert encrypted != original_data
        assert len(encrypted) > len(original_data)

        decrypted = security.decrypt(encrypted)
        assert decrypted == original_data

    def test_validate_solana_address(self):
        """Test Solana address validation"""
        # Valid address
        valid_address = "So11111111111111111111111111111111111111112"
        assert SecurityManager.validate_solana_address(valid_address) == True

        # Invalid addresses
        assert SecurityManager.validate_solana_address("invalid") == False
        assert SecurityManager.validate_solana_address("") == False
        assert SecurityManager.validate_solana_address(None) == False
        assert SecurityManager.validate_solana_address("a" * 100) == False

    def test_validate_amount(self):
        """Test amount validation"""
        # Valid amounts
        assert SecurityManager.validate_amount(100.0) == True
        assert SecurityManager.validate_amount(0.01, min_amount=0.01) == True

        # Invalid amounts
        assert SecurityManager.validate_amount(-10.0) == False
        assert SecurityManager.validate_amount(1000.0, max_amount=500.0) == False
        assert SecurityManager.validate_amount("not_a_number") == False

    def test_sanitize_input(self):
        """Test input sanitization"""
        # Test SQL injection attempt
        dangerous_input = "'; DROP TABLE users; --"
        sanitized = SecurityManager.sanitize_input(dangerous_input)
        assert "'" not in sanitized
        assert ";" not in sanitized

        # Test XSS attempt
        xss_input = "<script>alert('XSS')</script>"
        sanitized = SecurityManager.sanitize_input(xss_input)
        assert "<" not in sanitized
        assert ">" not in sanitized

        # Test length limit
        long_input = "a" * 2000
        sanitized = SecurityManager.sanitize_input(long_input, max_length=100)
        assert len(sanitized) <= 100

    def test_audit_log(self):
        """Test audit logging"""
        security = SecurityManager()

        # Should not raise exception
        security.audit_log(
            event_type="TEST_EVENT",
            details={"action": "test", "value": 123},
            user_id="test_user"
        )

    def test_rate_limiter(self):
        """Test rate limiting"""
        limiter = RateLimiter(max_requests=3, time_window=60)

        user_id = "test_user_123"

        # First 3 requests should be allowed
        assert limiter.is_allowed(user_id) == True
        assert limiter.is_allowed(user_id) == True
        assert limiter.is_allowed(user_id) == True

        # 4th request should be denied
        assert limiter.is_allowed(user_id) == False

        # Different user should be allowed
        assert limiter.is_allowed("other_user") == True
