# validators.py
"""
Input validation utilities
"""
from typing import Any, Optional
import re

class ValidationError(Exception):
    """Custom validation error"""
    pass

class Validators:
    """Input validation utilities"""

    @staticmethod
    def validate_positive(value: float, name: str) -> float:
        """Validate positive number"""
        if value <= 0:
            raise ValidationError(f"{name} must be positive, got {value}")
        return value

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float,
                      name: str) -> float:
        """Validate value in range"""
        if not min_val <= value <= max_val:
            raise ValidationError(
                f"{name} must be between {min_val} and {max_val}, got {value}"
            )
        return value

    @staticmethod
    def validate_solana_address(address: str) -> str:
        """Validate Solana address format"""
        if not address or not isinstance(address, str):
            raise ValidationError("Address must be non-empty string")

        # Solana addresses are base58, 32-44 chars
        if not 32 <= len(address) <= 44:
            raise ValidationError(f"Invalid address length: {len(address)}")

        # Check base58 characters
        base58_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]+$')
        if not base58_pattern.match(address):
            raise ValidationError("Invalid base58 format")

        return address

    @staticmethod
    def validate_percentage(value: float, name: str) -> float:
        """Validate percentage (0-100)"""
        return Validators.validate_range(value, 0, 100, name)

    @staticmethod
    def validate_bps(value: int, name: str) -> int:
        """Validate basis points (0-10000)"""
        return int(Validators.validate_range(value, 0, 10000, name))
