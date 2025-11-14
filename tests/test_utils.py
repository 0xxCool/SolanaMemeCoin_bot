"""
Unit tests for utils module
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestUtils:
    """Test utility functions"""

    def test_format_price(self):
        """Test price formatting"""
        from utils import format_price

        assert format_price(0.001) == "0.0010"
        assert format_price(1.0) == "1.0000"
        assert format_price(1000.5) == "1000.5000"

    def test_calculate_percentage_change(self):
        """Test percentage change calculation"""
        from utils import calculate_percentage_change

        # 100% increase
        assert calculate_percentage_change(100, 200) == 100.0

        # 50% decrease
        assert calculate_percentage_change(100, 50) == -50.0

        # No change
        assert calculate_percentage_change(100, 100) == 0.0

    def test_validate_token_address(self):
        """Test token address validation"""
        from utils import validate_token_address

        # Valid Solana address (44 characters)
        valid_address = "So11111111111111111111111111111111111111112"
        assert validate_token_address(valid_address) == True

        # Invalid addresses
        assert validate_token_address("invalid") == False
        assert validate_token_address("") == False
        assert validate_token_address(None) == False

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism"""
        from utils import retry_on_failure

        call_count = 0

        @retry_on_failure(max_attempts=3, delay=0.1)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 3
