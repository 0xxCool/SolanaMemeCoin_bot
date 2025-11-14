"""
Unit tests for config module
"""
import pytest
import os
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestConfig:
    """Test configuration loading and validation"""

    def test_config_loads_from_env(self, mock_config):
        """Test that configuration loads from environment variables"""
        with patch.dict(os.environ, mock_config):
            from config import Config
            config = Config()
            assert config.RPC_ENDPOINT == mock_config["RPC_ENDPOINT"]
            assert config.MIN_LIQUIDITY == mock_config["MIN_LIQUIDITY"]

    def test_config_has_required_fields(self):
        """Test that config has all required fields"""
        from config import Config
        config = Config()

        required_fields = [
            'RPC_ENDPOINT',
            'MIN_LIQUIDITY',
            'MIN_VOLUME_24H',
            'MIN_HOLDERS',
        ]

        for field in required_fields:
            assert hasattr(config, field), f"Config missing required field: {field}"

    def test_config_validation(self):
        """Test configuration validation"""
        from config import Config
        config = Config()

        # Test numeric validations
        if hasattr(config, 'MIN_LIQUIDITY'):
            assert isinstance(config.MIN_LIQUIDITY, (int, float))
            assert config.MIN_LIQUIDITY >= 0

        if hasattr(config, 'MIN_CONFIDENCE_SCORE'):
            assert isinstance(config.MIN_CONFIDENCE_SCORE, (int, float))
            assert 0 <= config.MIN_CONFIDENCE_SCORE <= 100
