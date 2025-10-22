# auto_trader.py
"""
Intelligent Auto-Buy & Auto-Sell System
AI-powered autonomous trading with self-learning capabilities
"""
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

# Import AI Engine
from ai_engine import ai_engine, get_ai_recommendation, update_ai_with_trade_result
import trader
import telegram_bot_enhanced as tg_bot
from config import trading_config, profit_strategy

logger = logging.getLogger(__name__)

@dataclass
class AutoTradeSettings:
    """Settings for auto-trading"""
    # Auto-Buy
    auto_buy_enabled: bool = False
    auto_buy_min_score: float = 85
    auto_buy_min_confidence: float = 0.7
    auto_buy_max_risk: float = 0.3
    auto_buy_max_amount_sol: float = 0.2
    auto_buy_daily_limit_sol: float = 2.0

    # Auto-Sell
    auto_sell_enabled: bool = False
    auto_sell_profit_target: float = 50  # %
    auto_sell_stop_loss: float = 15  # %
    use_ai_exit: bool = True  # Use AI for exit decisions

    # AI Settings
    ai_mode: str = "aggressive"  # conservative, balanced, aggressive
    use_neural_network: bool = True
    use_reinforcement_learning: bool = True
    learning_enabled: bool = True


class AutoTrader:
    """
    Intelligent Auto-Trading System
    Combines AI predictions with risk management
    """
    def __init__(self):
        self.settings = AutoTradeSettings()
        self.active_monitors = {}  # token_address -> monitor_task
        self.daily_auto_buy_spent = 0
        self.daily_reset_time = time.time()

        # Performance tracking
        self.stats = {
            'auto_buys': 0,
            'auto_sells': 0,
            'auto_profit_sol': 0,
            'ai_accuracy': 0
        }

    async def process_token_alert(self, token_data: Dict) -> Optional[str]:
        """
        Process new token alert and decide if auto-buy
        Returns: transaction signature if bought, None otherwise
        """
        if not self.settings.auto_buy_enabled:
            return None

        # Reset daily limit
        if time.time() - self.daily_reset_time > 86400:
            self.daily_auto_buy_spent = 0
            self.daily_reset_time = time.time()

        # Check daily limit
        if self.daily_auto_buy_spent >= self.settings.auto_buy_daily_limit_sol:
            logger.info("Daily auto-buy limit reached")
            return None

        try:
            # Get AI recommendation
            ai_prediction = await get_ai_recommendation(token_data)

            # Decision logic
            should_buy = await self._should_auto_buy(token_data, ai_prediction)

            if should_buy:
                amount_sol = await self._calculate_buy_amount(ai_prediction)

                # Execute trade
                tx_sig = await self._execute_auto_buy(
                    token_data,
                    amount_sol,
                    ai_prediction
                )

                if tx_sig:
                    self.stats['auto_buys'] += 1
                    self.daily_auto_buy_spent += amount_sol

                    # Start monitoring position
                    await self._start_position_monitor(token_data, ai_prediction)

                    # Notify via Telegram
                    await tg_bot.send_message(
                        f"🤖 **AI AUTO-BUY**\n"
                        f"Token: {token_data.get('symbol', 'Unknown')}\n"
                        f"Amount: {amount_sol:.3f} SOL\n"
                        f"AI Score: {ai_prediction['confidence']*100:.1f}%\n"
                        f"Expected Return: {ai_prediction['predicted_return']:.1f}%\n"
                        f"TX: `{tx_sig[:16]}...`",
                        important=True
                    )

                return tx_sig

        except Exception as e:
            logger.error(f"Auto-buy error: {e}")

        return None

    async def _should_auto_buy(self, token_data: Dict, ai_prediction: Dict) -> bool:
        """
        Determine if should auto-buy based on AI prediction and settings
        """
        # Check AI confidence
        if ai_prediction['confidence'] < self.settings.auto_buy_min_confidence:
            return False

        # Check risk
        risk = ai_prediction['risk_analysis']['overall_risk']
        if risk > self.settings.auto_buy_max_risk:
            return False

        # Check predicted return
        if ai_prediction['predicted_return'] < self.settings.auto_buy_min_score:
            return False

        # Check action recommendation
        if ai_prediction['recommended_action'] == 'SKIP':
            return False

        # Additional safety checks
        if ai_prediction['risk_analysis']['rug_probability'] > 0.3:
            return False

        if ai_prediction['risk_analysis']['honeypot_probability'] > 0.2:
            return False

        return True

    async def _calculate_buy_amount(self, ai_prediction: Dict) -> float:
        """
        Calculate optimal buy amount based on AI prediction
        """
        # Base amount from AI recommendation
        suggested_amount = ai_prediction['buy_amount_sol']

        # Adjust based on confidence
        confidence_mult = ai_prediction['confidence']
        amount = suggested_amount * confidence_mult

        # Apply limits
        amount = min(amount, self.settings.auto_buy_max_amount_sol)
        amount = max(amount, 0.01)  # Minimum

        # Check daily limit
        remaining_daily = self.settings.auto_buy_daily_limit_sol - self.daily_auto_buy_spent
        amount = min(amount, remaining_daily)

        return amount

    async def _execute_auto_buy(self, token_data: Dict, amount_sol: float,
                                ai_prediction: Dict) -> Optional[str]:
        """
        Execute the auto-buy trade
        """
        try:
            # Use trader module
            position = await trader.trader.open_position(token_data, amount_sol)

            if position:
                # Record for AI learning
                token_data['ai_prediction'] = ai_prediction
                token_data['auto_buy_amount'] = amount_sol
                token_data['auto_buy_time'] = time.time()

                return position.entry_tx if hasattr(position, 'entry_tx') else "executed"

        except Exception as e:
            logger.error(f"Execute auto-buy error: {e}")

        return None

    async def _start_position_monitor(self, token_data: Dict, ai_prediction: Dict):
        """
        Start monitoring position for auto-sell
        """
        token_address = token_data.get('address')

        if not token_address or not self.settings.auto_sell_enabled:
            return

        # Create monitor task
        task = asyncio.create_task(
            self._monitor_position(token_address, token_data, ai_prediction)
        )

        self.active_monitors[token_address] = task

    async def _monitor_position(self, token_address: str, token_data: Dict,
                               ai_prediction: Dict):
        """
        Monitor position and auto-sell when conditions met
        """
        entry_price = None
        entry_time = time.time()
        highest_price = 0

        while token_address in trader.trader.positions:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds

                position = trader.trader.positions.get(token_address)
                if not position:
                    break

                current_price = position.last_price
                if not entry_price:
                    entry_price = position.entry_price

                # Track highest price
                if current_price > highest_price:
                    highest_price = current_price

                # Calculate P&L
                profit_pct = ((current_price - entry_price) / entry_price) * 100

                # Auto-sell logic
                should_sell, reason = await self._should_auto_sell(
                    profit_pct, highest_price, current_price,
                    entry_time, ai_prediction
                )

                if should_sell:
                    # Execute sell
                    success = await trader.trader.close_position(token_address, reason)

                    if success:
                        self.stats['auto_sells'] += 1
                        self.stats['auto_profit_sol'] += position.invested_sol * (profit_pct / 100)

                        # Learn from trade
                        if self.settings.learning_enabled:
                            duration_minutes = (time.time() - entry_time) / 60
                            await update_ai_with_trade_result(
                                token_data,
                                'BUY',
                                profit_pct,
                                int(duration_minutes)
                            )

                        # Notify
                        await tg_bot.send_message(
                            f"🤖 **AI AUTO-SELL**\n"
                            f"Token: {token_data.get('symbol')}\n"
                            f"Reason: {reason}\n"
                            f"P&L: {profit_pct:+.2f}%\n"
                            f"Duration: {int((time.time()-entry_time)/60)}min",
                            important=True
                        )

                    break

            except Exception as e:
                logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(10)

        # Cleanup
        if token_address in self.active_monitors:
            del self.active_monitors[token_address]

    async def _should_auto_sell(self, profit_pct: float, highest_price: float,
                                current_price: float, entry_time: float,
                                ai_prediction: Dict) -> tuple:
        """
        Determine if should auto-sell
        Returns: (should_sell: bool, reason: str)
        """
        # Stop loss
        if profit_pct <= -self.settings.auto_sell_stop_loss:
            return True, "STOP_LOSS"

        # Take profit target
        if profit_pct >= self.settings.auto_sell_profit_target:
            return True, "PROFIT_TARGET"

        # Trailing stop (20% from peak)
        if highest_price > 0:
            drawdown = ((highest_price - current_price) / highest_price) * 100
            if drawdown > 20 and profit_pct > 10:
                return True, "TRAILING_STOP"

        # Time-based exit (max 60 minutes default)
        time_held = (time.time() - entry_time) / 60
        if time_held > 60 and profit_pct < 10:
            return True, "TIME_LIMIT"

        # AI-based exit
        if self.settings.use_ai_exit:
            # Could query AI for exit recommendation
            # For now, simple rule: exit if predicted peak passed
            predicted_peak_time = ai_prediction.get('predicted_peak_time', 30)
            if time_held > predicted_peak_time and profit_pct < ai_prediction.get('predicted_return', 50) * 0.5:
                return True, "AI_EXIT"

        return False, ""

    def enable_auto_buy(self, enabled: bool):
        """Enable/disable auto-buy"""
        self.settings.auto_buy_enabled = enabled
        logger.info(f"Auto-buy: {'ENABLED' if enabled else 'DISABLED'}")

    def enable_auto_sell(self, enabled: bool):
        """Enable/disable auto-sell"""
        self.settings.auto_sell_enabled = enabled
        logger.info(f"Auto-sell: {'ENABLED' if enabled else 'DISABLED'}")

    def update_settings(self, **kwargs):
        """Update settings"""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                logger.info(f"Updated {key} = {value}")

    def get_stats(self) -> Dict:
        """Get auto-trading statistics"""
        return {
            **self.stats,
            'auto_buy_enabled': self.settings.auto_buy_enabled,
            'auto_sell_enabled': self.settings.auto_sell_enabled,
            'daily_spent': self.daily_auto_buy_spent,
            'daily_limit': self.settings.auto_buy_daily_limit_sol,
            'active_monitors': len(self.active_monitors)
        }


# Global instance
auto_trader = AutoTrader()

# Public API
async def process_token_for_auto_buy(token_data: Dict) -> Optional[str]:
    """Process token for potential auto-buy"""
    return await auto_trader.process_token_alert(token_data)

def toggle_auto_buy(enabled: bool):
    """Toggle auto-buy on/off"""
    auto_trader.enable_auto_buy(enabled)

def toggle_auto_sell(enabled: bool):
    """Toggle auto-sell on/off"""
    auto_trader.enable_auto_sell(enabled)

def update_auto_trader_settings(**kwargs):
    """Update auto-trader settings"""
    auto_trader.update_settings(**kwargs)

def get_auto_trader_stats() -> Dict:
    """Get auto-trader statistics"""
    return auto_trader.get_stats()
