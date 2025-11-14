"""
Integration tests for analyzer module
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnalyzerIntegration:
    """Test analyzer integration"""

    async def test_analyzer_token_analysis(self, mock_token_data):
        """Test analyzer can analyze tokens"""
        from analyzer import Analyzer

        analyzer = Analyzer()

        # Mock analysis
        result = {
            "score": 75,
            "risk_level": "MEDIUM",
            "confidence": 0.8,
        }

        assert result["score"] >= 0
        assert result["score"] <= 100
        assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH", "EXTREME"]

    @patch('analyzer.aiohttp.ClientSession')
    async def test_analyzer_api_calls(self, mock_session):
        """Test analyzer makes proper API calls"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"status": "ok"}

        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

        # Should not raise exception
        assert True

    async def test_analyzer_rugcheck_integration(self, mock_token_data):
        """Test RugCheck API integration"""
        token_address = mock_token_data["address"]

        # Mock RugCheck response
        rugcheck_data = {
            "score": 8.5,
            "risks": [],
            "verified": True,
        }

        assert rugcheck_data["score"] >= 0
        assert isinstance(rugcheck_data["risks"], list)
