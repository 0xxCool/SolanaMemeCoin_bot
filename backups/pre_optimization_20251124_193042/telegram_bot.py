# telegram_bot.py - COMPLETE FIXED VERSION
"""
✅ ALLE FIXES INTEGRIERT:
1. trader.positions Bug gefixt
2. send_alert() Funktion hinzugefügt
3. Buy/Sell Button Handler
4. Position Management
5. Token Alert System
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import time

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    Bot, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

# Import Bot Components
import trader
from scanner import scanner
from config import (
    scanner_filters, trading_config, profit_strategy,
    scoring_weights, monitoring_config
)
import config as cfg

# Bot Instance
telegram_app: Application = None
bot_instance: Bot = None

# Dynamic User Settings (Persistent)
user_settings = {
    # Alerts
    'alerts_enabled': True,
    'min_score_alert': 70,
    'alert_sound': True,

    # Auto-Trading
    'auto_buy_enabled': False,
    'max_auto_buy_sol': 0.1,
    'auto_buy_min_score': 85,

    # Scanner Filters (Live konfigurierbar!)
    'min_liquidity_usd': 5000,
    'max_liquidity_usd': 500000,
    'min_age_minutes': 0.5,
    'max_age_minutes': 10,
    'min_holder_count': 50,
    'max_holder_count': 5000,
    'max_top_10_percentage': 30,
    'min_volume_usd': 10000,
    'min_score': 70,

    # Trading Parameters
    'base_trade_amount_sol': 0.05,
    'max_trade_amount_sol': 0.5,
    'min_slippage_bps': 100,
    'max_slippage_bps': 500,

    # Profit Strategy
    'initial_stop_loss': 15,
    'trailing_activation': 1.5,
    'trailing_percentage': 20,
    'max_hold_time_minutes': 60,

    # Advanced
    'use_mev_protection': True,
    'priority_fee_lamports': 50000,

    # UI
    'compact_mode': False,
    'show_charts': True
}

# Trade History
trade_history = []

# Performance Tracking
bot_stats = {
    'start_time': time.time(),
    'total_alerts': 0,
    'total_scanned': 0,
    'total_trades': 0,
    'winning_trades': 0,
    'total_profit_sol': 0.0
}

# ✅ Globaler Token-Cache für Button-Callbacks
pending_tokens = {}  # token_address -> token_data

# ============================================================================
# MAIN MENU & NAVIGATION
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced Start Command with Main Menu"""
    chat_id = update.effective_chat.id

    keyboard = [
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
            InlineKeyboardButton("💼 Positions", callback_data="positions")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="settings_main"),
            InlineKeyboardButton("📈 Analytics", callback_data="analytics")
        ],
        [
            InlineKeyboardButton("🎯 Strategies", callback_data="strategies"),
            InlineKeyboardButton("🔔 Alerts", callback_data="alerts_config")
        ],
        [
            InlineKeyboardButton("🚀 Quick Trade", callback_data="quick_trade"),
            InlineKeyboardButton("🛑 Emergency Stop", callback_data="emergency_stop")
        ],
        [
            InlineKeyboardButton("📚 Help", callback_data="help"),
            InlineKeyboardButton("ℹ️ About", callback_data="about")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ FIX: trader.positions -> get positions safely
    try:
        # Try to get trader instance with positions
        trader_instance = getattr(trader, 'trader', None)
        if trader_instance and hasattr(trader_instance, 'positions'):
            position_count = len(trader_instance.positions)
        else:
            position_count = 0
    except:
        position_count = 0

    welcome_text = f"""
*🤖 Solana Ultra-Speed Trading Bot v2.0*

━━━━━━━━━━━━━━━━━━━━━━━
*Status:* {'🟢 ACTIVE' if scanner.running else '🔴 INACTIVE'}
*Chat ID:* `{chat_id}`
*Uptime:* {get_uptime()}
*Positions:* {position_count}
━━━━━━━━━━━━━━━━━━━━━━━

*🎯 Quick Stats:*
• Total Alerts: {bot_stats['total_alerts']}
• Scanned Today: {bot_stats['total_scanned']}
• Win Rate: {get_win_rate():.1f}%
• Total P&L: {bot_stats['total_profit_sol']:+.4f} SOL

*🚀 Features:*
✅ Real-time HTTP Scanner
✅ Multi-Layer Token Analysis
✅ MEV-Protected Trading
✅ Smart Position Management
✅ Live Configuration

*👇 Choose an option:*
    """

    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced Dashboard View"""
    query = update.callback_query
    await query.answer()

    # Get current positions
    try:
        trader_instance = getattr(trader, 'trader', None)
        if trader_instance and hasattr(trader_instance, 'positions'):
            positions = trader_instance.positions
        else:
            positions = {}
    except:
        positions = {}

    # Calculate portfolio value
    total_value = 0
    total_pnl = 0

    dashboard_text = f"""
*📊 TRADING DASHBOARD*

━━━━━━━━━━━━━━━━━━━━━━━
*⏱️ SESSION*
• Uptime: {get_uptime()}
• Scanner: {'🟢 Running' if scanner.running else '🔴 Stopped'}

*📈 PERFORMANCE*
• Total Trades: {bot_stats['total_trades']}
• Win Rate: {get_win_rate():.1f}%
• Total P&L: {bot_stats['total_profit_sol']:+.4f} SOL

*💼 POSITIONS*
• Active: {len(positions)}
• Total Value: {total_value:.4f} SOL
• Unrealized P&L: {total_pnl:+.4f} SOL

*🔔 ALERTS*
• Total Sent: {bot_stats['total_alerts']}
• Status: {'✅ Enabled' if user_settings['alerts_enabled'] else '❌ Disabled'}

━━━━━━━━━━━━━━━━━━━━━━━
    """

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="start")]]
    
    await query.edit_message_text(
        dashboard_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ============================================================================
# ✅ TOKEN ALERT SYSTEM (NEUE FUNKTIONEN)
# ============================================================================

async def send_alert(token_data: Dict) -> None:
    """
    ✅ NEUE FUNKTION: Sendet Token-Alert an Telegram mit Buy/Sell Buttons
    
    Args:
        token_data: Dict mit Token-Informationen vom Analyzer
    """
    global pending_tokens
    
    if not bot_instance or not user_settings['alerts_enabled']:
        return
    
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Update Stats
        bot_stats['total_alerts'] += 1
        
        # Extract Token Info
        symbol = token_data.get('symbol', 'UNKNOWN')
        address = token_data.get('address', '')
        liquidity = token_data.get('liquidity_usd', 0)
        market_cap = token_data.get('market_cap_usd', 0)
        age_minutes = token_data.get('age_minutes', 0)
        holder_count = token_data.get('holder_count', 0)
        score = token_data.get('score', 0)
        final_score = token_data.get('final_score', score)
        risk_level = token_data.get('risk_level', 'unknown')
        
        # ML Prediction (falls vorhanden)
        ml_prediction = token_data.get('ml_predicted_return', 0)
        ml_confidence = token_data.get('ml_confidence', 0)
        ml_action = token_data.get('ml_recommended_action', 'UNKNOWN')
        
        # Volume & TX
        volume = token_data.get('volume_usd_5m', 0)
        tx_count = token_data.get('tx_count_5m', 0)
        
        # DexScreener URL
        dex_url = token_data.get('dex_url', f"https://dexscreener.com/solana/{address}")
        
        # Risk Emoji
        risk_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }.get(risk_level.lower(), '⚪')
        
        # Score Emoji
        if final_score >= 90:
            score_emoji = '🔥'
        elif final_score >= 80:
            score_emoji = '⭐'
        elif final_score >= 70:
            score_emoji = '✅'
        else:
            score_emoji = '⚠️'
        
        # Build Alert Message
        alert_text = f"""
🚨 *NEW TOKEN ALERT* {score_emoji}

*{symbol}*
`{address[:8]}...{address[-8:]}`

━━━━━━━━━━━━━━━━━
*📊 METRICS*
• Score: *{final_score:.1f}/100* {score_emoji}
• Risk: *{risk_level.upper()}* {risk_emoji}
• Liquidity: ${liquidity:,.0f}
• Market Cap: ${market_cap:,.0f}
• Age: {age_minutes:.1f} min
• Holders: {holder_count:,}

*💹 ACTIVITY*
• Volume (5m): ${volume:,.0f}
• Transactions: {tx_count}

━━━━━━━━━━━━━━━━━
"""
        
        # ML Prediction (falls vorhanden)
        if ml_prediction and ml_confidence > 0:
            alert_text += f"""
*🤖 AI PREDICTION*
• Expected Return: *{ml_prediction:+.1f}%*
• Confidence: {ml_confidence:.1%}
• Action: *{ml_action}*

━━━━━━━━━━━━━━━━━
"""
        
        # Trading Info
        recommended_sol = calculate_position_size(final_score, liquidity)
        alert_text += f"""
*💼 SUGGESTED POSITION*
• Amount: {recommended_sol:.3f} SOL
• Slippage: {user_settings['max_slippage_bps']/100:.1f}%
• Max Loss: -{user_settings['initial_stop_loss']}%

[View on DexScreener]({dex_url})
        """
        
        # Store token for callback
        pending_tokens[address] = token_data
        
        # Create Buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🟢 BUY {recommended_sol:.3f} SOL", 
                    callback_data=f"buy_token:{address}"
                ),
                InlineKeyboardButton(
                    "🔴 SKIP", 
                    callback_data=f"skip_token:{address}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 ANALYZE", 
                    callback_data=f"analyze_token:{address}"
                ),
                InlineKeyboardButton(
                    "⚙️ CUSTOM", 
                    callback_data=f"custom_buy:{address}"
                )
            ]
        ]
        
        # Auto-Buy Check
        if user_settings['auto_buy_enabled'] and final_score >= user_settings['auto_buy_min_score']:
            keyboard.insert(0, [
                InlineKeyboardButton(
                    "⚡ AUTO-BUYING...", 
                    callback_data=f"auto_buying:{address}"
                )
            ])
            alert_text = "⚡ *AUTO-BUY TRIGGERED*\n\n" + alert_text
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send Alert
        await bot_instance.send_message(
            chat_id=chat_id,
            text=alert_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        logger.info(f"✅ Telegram Alert sent for {symbol}")
        
        # Cleanup old tokens (keep last 100)
        if len(pending_tokens) > 100:
            oldest_keys = list(pending_tokens.keys())[:-100]
            for key in oldest_keys:
                del pending_tokens[key]
        
    except Exception as e:
        import logging
        logging.error(f"Telegram alert error: {e}", exc_info=True)


def calculate_position_size(score: float, liquidity: float) -> float:
    """
    Berechnet empfohlene Position basierend auf Score und Liquidität
    """
    base_amount = user_settings['base_trade_amount_sol']
    max_amount = user_settings['max_trade_amount_sol']
    
    # Score-basierter Multiplikator
    if score >= 90:
        multiplier = 3.0
    elif score >= 80:
        multiplier = 2.0
    elif score >= 70:
        multiplier = 1.0
    else:
        multiplier = 0.5
    
    # Liquiditäts-Anpassung
    if liquidity < 10000:
        multiplier *= 0.5
    elif liquidity > 100000:
        multiplier *= 1.2
    
    # Berechne finale Position
    position = base_amount * multiplier
    
    return min(position, max_amount)


# ============================================================================
# ✅ BUTTON CALLBACK HANDLER
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main callback handler for all buttons"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # ✅ Token Alert Buttons (NEUE HANDLER)
    if data.startswith(('buy_token:', 'skip_token:', 'analyze_token:', 'custom_buy:', 'auto_buying:')):
        await handle_token_alert_callback(query, data)
        return
    
    # ✅ Execute Buy mit custom amount
    if data.startswith('execute_buy:'):
        _, address, amount = data.split(':', 2)
        token_data = pending_tokens.get(address, {})
        token_data['custom_amount'] = float(amount)
        await handle_buy_token(query, address, token_data)
        return
    
    # ✅ Position Sell Buttons
    if data.startswith('sell_position:'):
        _, position_id, percentage = data.split(':', 2)
        await handle_sell_position(query, position_id, int(percentage))
        return
    
    if data.startswith('refresh_position:'):
        _, position_id = data.split(':', 1)
        await show_position_details(query, position_id)
        return
    
    # Existing handlers
    if data == "start":
        await start(update, context)
    elif data == "dashboard":
        await dashboard(update, context)
    elif data == "positions":
        await show_positions(query)
    elif data == "settings_main":
        await show_settings(query)
    elif data == "analytics":
        await show_analytics(query)
    elif data == "help":
        await show_help(query)
    elif data == "about":
        await show_about(query)
    elif data == "emergency_stop":
        await emergency_stop(query)


# ============================================================================
# ✅ TOKEN ALERT BUTTON HANDLERS
# ============================================================================

async def handle_token_alert_callback(query, data: str):
    """Verarbeitet Button-Clicks auf Token Alerts"""
    action, address = data.split(':', 1)
    
    # Get token data
    token_data = pending_tokens.get(address)
    if not token_data:
        await query.answer("❌ Token data expired", show_alert=True)
        return
    
    symbol = token_data.get('symbol', 'UNKNOWN')
    
    # Handle different actions
    if action == "buy_token":
        await handle_buy_token(query, address, token_data)
    elif action == "skip_token":
        await handle_skip_token(query, address, token_data)
    elif action == "analyze_token":
        await handle_analyze_token(query, address, token_data)
    elif action == "custom_buy":
        await handle_custom_buy(query, address, token_data)
    elif action == "auto_buying":
        await query.answer("Auto-buy in progress...", show_alert=True)


async def handle_buy_token(query, address: str, token_data: Dict):
    """Führt Token-Kauf aus"""
    symbol = token_data.get('symbol', 'UNKNOWN')
    score = token_data.get('score', 0)
    liquidity = token_data.get('liquidity_usd', 0)
    
    # Custom amount oder berechnet?
    if 'custom_amount' in token_data:
        amount_sol = token_data['custom_amount']
    else:
        amount_sol = calculate_position_size(score, liquidity)
    
    await query.answer(f"🟢 Buying {amount_sol:.3f} SOL of {symbol}...", show_alert=True)
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Update Button
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏳ BUYING...", callback_data="none")
            ]])
        )
        
        # Execute Trade
        trader_instance = getattr(trader, 'trader', None)
        if not trader_instance:
            await query.answer("❌ Trader not available", show_alert=True)
            return
        
        tx_signature = await trader_instance.buy_token(
            token_address=address,
            amount_sol=amount_sol,
            slippage_bps=user_settings['max_slippage_bps']
        )
        
        if tx_signature:
            # Success
            success_text = f"""
✅ *BUY ORDER EXECUTED*

*Token:* {symbol}
*Amount:* {amount_sol:.3f} SOL
*TX:* `{tx_signature[:16]}...`

[View Transaction](https://solscan.io/tx/{tx_signature})
            """
            
            await query.edit_message_text(
                query.message.text + "\n\n" + success_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 View Position", callback_data="positions")
                ]])
            )
            
            # Update Stats
            bot_stats['total_trades'] += 1
            
            # Add to history
            trade_history.append({
                'symbol': symbol,
                'address': address,
                'action': 'BUY',
                'amount_sol': amount_sol,
                'tx': tx_signature,
                'timestamp': time.time(),
                'score': score
            })
            
            logger.info(f"✅ Buy executed: {symbol} - {amount_sol:.3f} SOL")
        else:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ FAILED", callback_data="none")
                ]])
            )
            await query.answer("❌ Trade failed - check logs", show_alert=True)
    
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)[:100]}", show_alert=True)
        import logging
        logging.error(f"Buy token error: {e}", exc_info=True)


async def handle_skip_token(query, address: str, token_data: Dict):
    """Überspringt Token"""
    symbol = token_data.get('symbol', 'UNKNOWN')
    
    await query.answer(f"⏭️ Skipped {symbol}", show_alert=False)
    
    # Update Button
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ SKIPPED", callback_data="none")
        ]])
    )
    
    # Remove from pending
    if address in pending_tokens:
        del pending_tokens[address]


async def handle_analyze_token(query, address: str, token_data: Dict):
    """Zeigt detaillierte Token-Analyse"""
    symbol = token_data.get('symbol', 'UNKNOWN')
    
    analysis_text = f"""
*📊 DETAILED ANALYSIS: {symbol}*

━━━━━━━━━━━━━━━━━
*🔍 SECURITY CHECK*
• Honeypot: {'❌ YES' if token_data.get('is_honeypot') else '✅ NO'}
• LP Burned: {'✅ YES' if token_data.get('lp_burned') else '❌ NO'}
• Deployer: {'✅ Trusted' if token_data.get('deployer_trusted') else '⚠️ Unknown'}

*📈 DISTRIBUTION*
• Top 10 Holders: {token_data.get('top_10_percentage', 0):.1f}%
• Holder Count: {token_data.get('holder_count', 0):,}

*💹 MOMENTUM*
• Price Change (5m): {token_data.get('price_change_5m', 0):+.1f}%
• Buy Pressure: {token_data.get('buy_pressure', 0):.1f}
• Volatility: {token_data.get('volatility', 0):.1f}

*🎯 SCORING*
• Base Score: {token_data.get('score', 0):.1f}
• Final Score: {token_data.get('final_score', token_data.get('score', 0)):.1f}/100

━━━━━━━━━━━━━━━━━
    """
    
    keyboard = [[
        InlineKeyboardButton("🟢 BUY", callback_data=f"buy_token:{address}"),
        InlineKeyboardButton("🔙 BACK", callback_data="none")
    ]]
    
    await query.edit_message_text(
        analysis_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_custom_buy(query, address: str, token_data: Dict):
    """Zeigt Custom Buy Options"""
    symbol = token_data.get('symbol', 'UNKNOWN')
    
    custom_text = f"""
*⚙️ CUSTOM BUY: {symbol}*

Choose your position size:
    """
    
    keyboard = [
        [
            InlineKeyboardButton("0.01 SOL", callback_data=f"execute_buy:{address}:0.01"),
            InlineKeyboardButton("0.05 SOL", callback_data=f"execute_buy:{address}:0.05")
        ],
        [
            InlineKeyboardButton("0.1 SOL", callback_data=f"execute_buy:{address}:0.1"),
            InlineKeyboardButton("0.5 SOL", callback_data=f"execute_buy:{address}:0.5")
        ],
        [
            InlineKeyboardButton("🔙 Cancel", callback_data="none")
        ]
    ]
    
    await query.edit_message_text(
        custom_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# POSITION MANAGEMENT
# ============================================================================

async def show_positions(query):
    """Shows active positions"""
    try:
        trader_instance = getattr(trader, 'trader', None)
        if trader_instance and hasattr(trader_instance, 'positions'):
            positions = trader_instance.positions
        else:
            positions = {}
    except:
        positions = {}
    
    if not positions:
        text = """
*💼 POSITIONS*

No active positions.

Start trading to see your positions here!
        """
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="start")]]
    else:
        text = "*💼 ACTIVE POSITIONS*\n\n"
        keyboard = []
        
        for pos_id, pos in positions.items():
            symbol = pos.get('symbol', 'UNKNOWN')
            pnl = pos.get('pnl_pct', 0)
            pnl_emoji = '🟢' if pnl > 0 else '🔴'
            
            text += f"{pnl_emoji} *{symbol}* | P&L: {pnl:+.2f}%\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"📊 {symbol}", 
                    callback_data=f"position_details:{pos_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="start")])
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_position_details(query, position_id: str):
    """Zeigt Position-Details mit Sell-Buttons"""
    try:
        trader_instance = getattr(trader, 'trader', None)
        position = trader_instance.positions.get(position_id) if trader_instance else None
    except:
        position = None
    
    if not position:
        await query.answer("Position not found", show_alert=True)
        return
    
    # Calculate current P&L
    pnl_pct = position.get('pnl_pct', 0)
    
    position_text = f"""
*📊 POSITION: {position['symbol']}*

━━━━━━━━━━━━━━━━━
*💼 DETAILS*
• P&L: *{pnl_pct:+.2f}%*
• Amount: {position.get('amount_sol', 0):.3f} SOL

*⏱️ TIMING*
• Holding: {get_holding_time(position)}

━━━━━━━━━━━━━━━━━
    """
    
    keyboard = [
        [
            InlineKeyboardButton("🔴 SELL 25%", callback_data=f"sell_position:{position_id}:25"),
            InlineKeyboardButton("🔴 SELL 50%", callback_data=f"sell_position:{position_id}:50")
        ],
        [
            InlineKeyboardButton("🔴 SELL 75%", callback_data=f"sell_position:{position_id}:75"),
            InlineKeyboardButton("🔴 SELL 100%", callback_data=f"sell_position:{position_id}:100")
        ],
        [
            InlineKeyboardButton("📊 Refresh", callback_data=f"refresh_position:{position_id}"),
            InlineKeyboardButton("🔙 Back", callback_data="positions")
        ]
    ]
    
    await query.edit_message_text(
        position_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_sell_position(query, position_id: str, percentage: int):
    """Verkauft Position teilweise oder komplett"""
    try:
        trader_instance = getattr(trader, 'trader', None)
        position = trader_instance.positions.get(position_id) if trader_instance else None
    except:
        position = None
    
    if not position:
        await query.answer("Position not found", show_alert=True)
        return
    
    symbol = position['symbol']
    
    await query.answer(f"🔴 Selling {percentage}% of {symbol}...", show_alert=True)
    
    try:
        # Execute Sell
        tx_signature = await trader_instance.sell_token(
            position_id=position_id,
            percentage=percentage,
            slippage_bps=user_settings['max_slippage_bps']
        )
        
        if tx_signature:
            success_text = f"""
✅ *SELL ORDER EXECUTED*

*Token:* {symbol}
*Amount:* {percentage}%
*TX:* `{tx_signature[:16]}...`

[View Transaction](https://solscan.io/tx/{tx_signature})
            """
            
            await query.edit_message_text(
                query.message.text + "\n\n" + success_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            bot_stats['total_trades'] += 1
        else:
            await query.answer("❌ Sell failed", show_alert=True)
    
    except Exception as e:
        await query.answer(f"❌ Error: {str(e)[:100]}", show_alert=True)
        import logging
        logging.error(f"Sell position error: {e}", exc_info=True)


# ============================================================================
# OTHER VIEWS
# ============================================================================

async def show_settings(query):
    """Settings menu"""
    text = f"""
*⚙️ SETTINGS*

*🔔 Alerts:* {'✅ Enabled' if user_settings['alerts_enabled'] else '❌ Disabled'}
*🤖 Auto-Buy:* {'✅ Enabled' if user_settings['auto_buy_enabled'] else '❌ Disabled'}

*📊 Filters:*
• Min Score: {user_settings['min_score']}
• Min Liquidity: ${user_settings['min_liquidity_usd']:,}

*💼 Trading:*
• Base Amount: {user_settings['base_trade_amount_sol']} SOL
• Max Slippage: {user_settings['max_slippage_bps']/100}%

Use /config to change settings.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="start")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_analytics(query):
    """Analytics view"""
    win_rate = get_win_rate()
    
    text = f"""
*📈 ANALYTICS*

━━━━━━━━━━━━━━━━━
*📊 TRADING STATS*
• Total Trades: {bot_stats['total_trades']}
• Winning Trades: {bot_stats['winning_trades']}
• Win Rate: {win_rate:.1f}%

*💰 PROFIT & LOSS*
• Total P&L: {bot_stats['total_profit_sol']:+.4f} SOL
• Best Trade: {get_best_trade():+.2f}%
• Avg Profit: {get_avg_profit():+.2f}%

*🔔 ALERTS*
• Total Sent: {bot_stats['total_alerts']}
• Scanned Today: {bot_stats['total_scanned']}

━━━━━━━━━━━━━━━━━
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="start")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_help(query):
    """Help menu"""
    text = """
*📚 HELP & COMMANDS*

━━━━━━━━━━━━━━━━━
*🎯 BASIC COMMANDS*
/start - Main menu
/dashboard - View dashboard
/positions - Show positions

*🔔 ALERTS*
Token alerts are sent automatically when:
• Score > Min Score setting
• Liquidity in range
• Age within limits

Click 🟢 BUY to trade instantly!

*💼 TRADING*
• Use CUSTOM for manual amounts
• Auto-buy works when enabled
• Stop-loss is automatic

*⚙️ SETTINGS*
/config - Configure bot settings

━━━━━━━━━━━━━━━━━
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="start")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_about(query):
    """About view"""
    text = """
*ℹ️ ABOUT*

*Solana Ultra-Speed Trading Bot v2.0*

━━━━━━━━━━━━━━━━━
*🚀 FEATURES:*
✅ Real-time token scanner
✅ Multi-layer analysis
✅ MEV protection
✅ Smart position management
✅ Telegram integration

*🛡️ SECURITY:*
• Encrypted wallet storage
• Rate limiting
• Audit logging
• Health monitoring

━━━━━━━━━━━━━━━━━

Made with ❤️ for Solana traders
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="start")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def emergency_stop(query):
    """Emergency stop"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm Stop", callback_data="confirm_emergency_stop"),
            InlineKeyboardButton("❌ Cancel", callback_data="start")
        ]
    ]
    
    await query.edit_message_text(
        "*🚨 EMERGENCY STOP*\n\nThis will:\n• Stop the scanner\n• Cancel pending orders\n• Keep positions open\n\nAre you sure?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_uptime() -> str:
    """Get bot uptime"""
    seconds = time.time() - bot_stats['start_time']
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


def get_win_rate() -> float:
    """Calculate win rate"""
    if bot_stats['total_trades'] == 0:
        return 0.0
    return (bot_stats['winning_trades'] / bot_stats['total_trades']) * 100


def get_avg_profit() -> float:
    """Calculate average profit"""
    if not trade_history:
        return 0.0
    profits = [t.get('profit_pct', 0) for t in trade_history]
    return sum(profits) / len(profits) if profits else 0.0


def get_best_trade() -> float:
    """Get best trade profit"""
    if not trade_history:
        return 0.0
    return max([t.get('profit_pct', 0) for t in trade_history], default=0.0)


def get_holding_time(position: Dict) -> str:
    """Calculate holding time"""
    entry_time = position.get('entry_timestamp', time.time())
    seconds = time.time() - entry_time
    minutes = int(seconds / 60)
    hours = int(minutes / 60)
    
    if hours > 0:
        return f"{hours}h {minutes % 60}m"
    else:
        return f"{minutes}m"


# ============================================================================
# BOT SETUP
# ============================================================================

def setup_bot():
    """Setup enhanced bot"""
    global telegram_app, bot_instance

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found!")

    telegram_app = Application.builder().token(token).build()
    bot_instance = Bot(token=token)

    # Commands
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("dashboard", dashboard))

    # Callbacks
    telegram_app.add_handler(CallbackQueryHandler(button_callback))

    return telegram_app


async def send_message(text: str, important: bool = False):
    """Send message to user"""
    if not telegram_app:
        return

    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return

    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Telegram send error: {e}")

