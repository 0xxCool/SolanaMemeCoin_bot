"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        "RPC_ENDPOINT": "https://api.mainnet-beta.solana.com",
        "WALLET_ADDRESS": "test_wallet_address",
        "PRIVATE_KEY": "test_private_key",
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "test_chat_id",
        "MIN_LIQUIDITY": 5000,
        "MIN_VOLUME_24H": 10000,
        "MIN_HOLDERS": 50,
        "MAX_MARKET_CAP": 100000,
        "MIN_CONFIDENCE_SCORE": 60,
    }


@pytest.fixture
def mock_token_data():
    """Mock token data for testing"""
    return {
        "address": "So11111111111111111111111111111111111111112",
        "symbol": "TEST",
        "name": "Test Token",
        "liquidity": 10000,
        "volume_24h": 50000,
        "holders": 100,
        "market_cap": 50000,
        "price": 0.001,
    }
