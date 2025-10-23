# integration.py
"""
Complete Integration Module - Connects all components
Ensures AI Engine, Auto-Trader, Scanner, Analyzer work together
"""
import asyncio
import logging
from typing import Dict, Optional

# Import all components
try:
    from ai_engine import ai_engine, get_ai_recommendation, update_ai_with_trade_result, get_ai_stats
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logging.warning("AI Engine not available")

try:
    from auto_trader import auto_trader, process_token_for_auto_buy, toggle_auto_buy, toggle_auto_sell
    AUTO_TRADER_AVAILABLE = True
except ImportError:
    AUTO_TRADER_AVAILABLE = False
    logging.warning("Auto-Trader not available")

import scanner
import analyzer
import trader
from config import scanner_filters

logger = logging.getLogger(__name__)


class IntegrationManager:
    """
    Central Integration Manager
    Connects all bot components and manages data flow
    """
    def __init__(self):
        self.ai_enabled = AI_AVAILABLE
        self.auto_trader_enabled = AUTO_TRADER_AVAILABLE
        self.initialized = False

        # Statistics
        self.stats = {
            'tokens_analyzed': 0,
            'ai_predictions': 0,
            'auto_buys': 0,
            'auto_sells': 0,
            'manual_trades': 0
        }

    async def initialize(self):
        """Initialize all components"""
        logger.info("🔄 Initializing Integration Manager...")

        # Check AI availability
        if self.ai_enabled:
            logger.info("✅ AI Engine available")
        else:
            logger.warning("⚠️ AI Engine not available - using fallback")

        # Check Auto-Trader
        if self.auto_trader_enabled:
            logger.info("✅ Auto-Trader available")
        else:
            logger.warning("⚠️ Auto-Trader not available")

        self.initialized = True
        logger.info("✅ Integration Manager initialized")

    async def process_new_token(self, token_data: Dict) -> Optional[str]:
        """
        Complete processing pipeline for new token
        1. Analyzer evaluates
        2. AI predicts (if enabled)
        3. Auto-trader decides (if enabled)
        4. Returns: tx_signature if traded, None otherwise
        """
        try:
            self.stats['tokens_analyzed'] += 1

            # Step 1: Basic Analysis
            analysis = await analyzer.analyze_token(token_data)
            if not analysis:
                return None

            # Apply basic filters
            if not self._passes_basic_filters(analysis):
                logger.debug(f"Token {token_data.get('symbol')} failed basic filters")
                return None

            # Step 2: AI Prediction (if enabled)
            ai_prediction = None
            if self.ai_enabled:
                try:
                    ai_prediction = await get_ai_recommendation(token_data)
                    self.stats['ai_predictions'] += 1

                    # Merge AI prediction into analysis
                    analysis['ai_prediction'] = ai_prediction
                    analysis['ai_confidence'] = ai_prediction.get('confidence', 0)
                    analysis['ai_recommended_action'] = ai_prediction.get('recommended_action', 'SKIP')

                except Exception as e:
                    logger.error(f"AI prediction error: {e}")

            # Step 3: Auto-Trading Decision (if enabled)
            if self.auto_trader_enabled and auto_trader.settings.auto_buy_enabled:
                try:
                    tx_sig = await process_token_for_auto_buy(token_data)
                    if tx_sig:
                        self.stats['auto_buys'] += 1
                        logger.info(f"✅ Auto-buy executed: {token_data.get('symbol')}")
                        return tx_sig
                except Exception as e:
                    logger.error(f"Auto-trader error: {e}")

            # Step 4: Send alert for manual decision (if auto-trading disabled)
            if not auto_trader.settings.auto_buy_enabled:
                await self._send_manual_alert(token_data, analysis, ai_prediction)

            return None

        except Exception as e:
            logger.error(f"Token processing error: {e}")
            return None

    def _passes_basic_filters(self, analysis: Dict) -> bool:
        """Apply basic filters before AI processing"""
        # Score threshold
        if analysis.get('score', 0) < scanner_filters.MIN_SCORE:
            return False

        # Liquidity check
        if analysis.get('liquidity_usd', 0) < scanner_filters.MIN_LIQUIDITY_USD:
            return False

        # Risk level check
        if analysis.get('risk_level') == 'HIGH':
            return False

        return True

    async def _send_manual_alert(self, token_data: Dict, analysis: Dict, ai_prediction: Optional[Dict]):
        """Send alert for manual trading decision"""
        try:
            import telegram_bot

            # Build alert message
            alert_data = {
                **token_data,
                **analysis
            }

            if ai_prediction:
                alert_data['ai_recommendation'] = ai_prediction

            await telegram_bot.send_alert(alert_data)

        except Exception as e:
            logger.error(f"Alert sending error: {e}")

    async def record_trade_outcome(self, token_address: str, action: str,
                                   entry_price: float, exit_price: float,
                                   duration_seconds: int):
        """
        Record trade outcome and update AI
        """
        try:
            # Calculate return
            actual_return = ((exit_price - entry_price) / entry_price) * 100

            # Get original token data (would need to be stored)
            # For now, create minimal data structure
            token_data = {
                'address': token_address,
                'entry_price': entry_price,
                'exit_price': exit_price
            }

            # Update AI with outcome (if enabled)
            if self.ai_enabled:
                await update_ai_with_trade_result(
                    token_data,
                    action,
                    actual_return,
                    duration_seconds // 60  # Convert to minutes
                )

            # Update stats
            if action.startswith('AUTO_'):
                self.stats['auto_sells'] += 1
            else:
                self.stats['manual_trades'] += 1

            logger.info(f"Trade outcome recorded: {actual_return:+.2f}% in {duration_seconds}s")

        except Exception as e:
            logger.error(f"Trade outcome recording error: {e}")

    def get_integration_stats(self) -> Dict:
        """Get integration statistics"""
        stats = self.stats.copy()

        if self.ai_enabled:
            stats['ai_stats'] = asyncio.run(get_ai_stats())

        if self.auto_trader_enabled:
            stats['auto_trader_stats'] = auto_trader.get_stats()

        return stats


# Global instance
integration_manager = IntegrationManager()


# Public API
async def initialize_integration():
    """Initialize integration manager"""
    await integration_manager.initialize()


async def process_token(token_data: Dict) -> Optional[str]:
    """Process new token through complete pipeline"""
    return await integration_manager.process_new_token(token_data)


async def record_trade(token_address: str, action: str, entry_price: float,
                      exit_price: float, duration_seconds: int):
    """Record trade outcome"""
    await integration_manager.record_trade_outcome(
        token_address, action, entry_price, exit_price, duration_seconds
    )


def get_stats() -> Dict:
    """Get integration statistics"""
    return integration_manager.get_integration_stats()
