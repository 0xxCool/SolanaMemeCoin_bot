"""
Unit tests for database module
"""
import pytest
import asyncio
from datetime import datetime


@pytest.mark.unit
class TestDatabase:
    """Test database operations"""

    @pytest.mark.asyncio
    async def test_database_init(self):
        """Test database initialization"""
        from database import Database

        db = Database(":memory:")
        await db.initialize()
        assert db is not None

    @pytest.mark.asyncio
    async def test_save_trade(self, mock_token_data):
        """Test saving trade to database"""
        from database import Database

        db = Database(":memory:")
        await db.initialize()

        trade_data = {
            "token_address": mock_token_data["address"],
            "symbol": mock_token_data["symbol"],
            "action": "BUY",
            "amount": 100.0,
            "price": mock_token_data["price"],
            "confidence_score": 75.5,
        }

        # This should not raise an exception
        try:
            await db.save_trade(**trade_data)
        except Exception as e:
            pytest.fail(f"save_trade raised exception: {e}")

    @pytest.mark.asyncio
    async def test_get_trade_history(self):
        """Test retrieving trade history"""
        from database import Database

        db = Database(":memory:")
        await db.initialize()

        # This should return a list (empty or with trades)
        try:
            history = await db.get_trade_history(limit=10)
            assert isinstance(history, list)
        except Exception as e:
            pytest.fail(f"get_trade_history raised exception: {e}")
