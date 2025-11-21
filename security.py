"""
Security module for encryption, validation, and audit logging
"""
import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages encryption, validation, and audit logging"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize security manager

        Args:
            secret_key: Secret key for encryption (from environment)
        """
        self.secret_key = secret_key or os.getenv("SECRET_KEY", "")
        if not self.secret_key:
            logger.warning("No SECRET_KEY set! Using default (INSECURE for production)")
            self.secret_key = "default_insecure_key_change_me"

        self.cipher = self._init_cipher()
        self.audit_log_path = Path("logs/audit.log")
        self.audit_log_path.parent.mkdir(exist_ok=True)

    def _init_cipher(self) -> Fernet:
        """Initialize Fernet cipher with derived key"""
        # Derive a key from the secret_key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'solana_bot_salt',  # In production, use random salt stored securely
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        return Fernet(key)

    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data

        Args:
            data: Plain text data to encrypt

        Returns:
            Encrypted data as string
        """
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data

        Args:
            encrypted_data: Encrypted data string

        Returns:
            Decrypted plain text
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    @staticmethod
    def validate_solana_address(address: str) -> bool:
        """
        Validate Solana wallet address

        Args:
            address: Wallet address to validate

        Returns:
            True if valid, False otherwise
        """
        if not address or not isinstance(address, str):
            return False

        # Solana addresses are base58 encoded, 32-44 characters
        if len(address) < 32 or len(address) > 44:
            return False

        # Check if it's a valid base58 string
        base58_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]+$')
        return bool(base58_pattern.match(address))

    @staticmethod
    def validate_amount(amount: float, min_amount: float = 0.0, max_amount: float = float('inf')) -> bool:
        """
        Validate transaction amount

        Args:
            amount: Amount to validate
            min_amount: Minimum allowed amount
            max_amount: Maximum allowed amount

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(amount, (int, float)):
            return False

        return min_amount <= amount <= max_amount

    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """
        Sanitize user input to prevent injection attacks

        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Truncate to max length
        text = str(text)[:max_length]

        # Remove potentially dangerous characters
        text = re.sub(r'[<>"\';]', '', text)

        return text.strip()

    def audit_log(self, event_type: str, details: Dict[str, Any], user_id: Optional[str] = None):
        """
        Log security-relevant events

        Args:
            event_type: Type of event (e.g., 'TRADE', 'CONFIG_CHANGE', 'AUTH_ATTEMPT')
            details: Event details
            user_id: Optional user identifier
        """
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id or "system",
                "details": details,
            }

            with open(self.audit_log_path, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')

            logger.info(f"Audit log: {event_type} - {user_id}")

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, list] = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed

        Args:
            identifier: Unique identifier (e.g., user_id, chat_id)

        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow().timestamp()

        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                ts for ts in self.requests[identifier]
                if now - ts < self.time_window
            ]
        else:
            self.requests[identifier] = []

        # Check if allowed
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        # Add new request
        self.requests[identifier].append(now)
        return True


# Global instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager
