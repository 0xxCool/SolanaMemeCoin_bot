# telegram_bot_enhanced.py
"""
Enhanced Telegram Bot mit vollständiger Live-Konfiguration
Alle Trading-Parameter über interaktive Buttons steuerbar
"""
import os
import asyncio
from typing import Dict, Any, List
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

    welcome_text = f"""
*🤖 Solana Ultra-Speed Trading Bot v2.0*

━━━━━━━━━━━━━━━━━━━━━━━
*Status:* {'🟢 ACTIVE' if scanner.running else '🔴 INACTIVE'}
*Chat ID:* `{chat_id}`
*Uptime:* {get_uptime()}
*Positions:* {len(trader.positions)}
━━━━━━━━━━━━━━━━━━━━━━━

*🎯 Quick Stats:*
• Total Alerts: {bot_stats['total_alerts']}
• Scanned Today: {bot_stats['total_scanned']}
• Win Rate: {get_win_rate():.1f}%
• Total P&L: {bot_stats['total_profit_sol']:+.4f} SOL

*🚀 Features:*
✅ Real-time WebSocket Scanner
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

# ============================================================================
# ENHANCED DASHBOARD
# ============================================================================

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Real-time Dashboard with Live Metrics"""
    from scanner import scanner

    # Calculate metrics
    uptime_hours = (time.time() - bot_stats['start_time']) / 3600
    win_rate = get_win_rate()
    avg_profit = get_avg_profit()

    # Active positions summary
    positions_text = ""
    total_invested = 0
    total_current_value = 0

    for addr, pos in trader.positions.items():
        profit_pct = ((pos.current_price - pos.entry_price) / pos.entry_price) * 100 if pos.current_price else 0
        total_invested += pos.amount_sol
        total_current_value += pos.amount_sol * (1 + profit_pct/100)

        emoji = "🟢" if profit_pct > 0 else "🔴"
        positions_text += f"{emoji} `{pos.symbol[:8]}` {profit_pct:+.1f}%\n"

    if not positions_text:
        positions_text = "_No active positions_"

    dashboard_text = f"""
*📊 LIVE DASHBOARD*
━━━━━━━━━━━━━━━━━━━━━━━

*🤖 Bot Status*
• Status: {'🟢 RUNNING' if scanner.running else '🔴 STOPPED'}
• Uptime: {uptime_hours:.1f}h
• Scanner Queue: {scanner.processing_queue.qsize()}
• Processed: {scanner.stats['processed']}

*💰 Trading Performance*
• Win Rate: {win_rate:.1f}% ({bot_stats['winning_trades']}/{bot_stats['total_trades']})
• Avg Profit: {avg_profit:+.2f}%
• Total P&L: {bot_stats['total_profit_sol']:+.4f} SOL
• Best Trade: {get_best_trade():+.2f}%

*💼 Active Positions ({len(trader.positions)})*
{positions_text}

*📊 Portfolio*
• Invested: {total_invested:.4f} SOL
• Current Value: {total_current_value:.4f} SOL
• Unrealized P&L: {(total_current_value - total_invested):+.4f} SOL

*⚙️ Current Settings*
• Auto-Buy: {'✅ ON' if user_settings['auto_buy_enabled'] else '❌ OFF'}
• Min Score: {user_settings['min_score']}
• Base Amount: {user_settings['base_trade_amount_sol']} SOL
• Stop Loss: {user_settings['initial_stop_loss']}%

_Updated: {datetime.now().strftime('%H:%M:%S')}_
    """

    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="dashboard"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings_main")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        dashboard_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ============================================================================
# SETTINGS MENU - LIVE CONFIGURATION
# ============================================================================

async def settings_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main Settings Menu"""
    keyboard = [
        [
            InlineKeyboardButton("🎯 Scanner Filters", callback_data="settings_scanner"),
            InlineKeyboardButton("💰 Trading", callback_data="settings_trading")
        ],
        [
            InlineKeyboardButton("📊 Profit Strategy", callback_data="settings_profit"),
            InlineKeyboardButton("🔔 Alerts", callback_data="settings_alerts")
        ],
        [
            InlineKeyboardButton("🚀 Quick Presets", callback_data="settings_presets"),
            InlineKeyboardButton("🔧 Advanced", callback_data="settings_advanced")
        ],
        [
            InlineKeyboardButton("💾 Save Config", callback_data="settings_save"),
            InlineKeyboardButton("🔄 Reset", callback_data="settings_reset")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"""
*⚙️ SETTINGS MENU*
━━━━━━━━━━━━━━━━━━━━━━━

*Current Configuration:*

*🎯 Scanner Filters*
• Min Liquidity: ${user_settings['min_liquidity_usd']:,}
• Min Score: {user_settings['min_score']}
• Age Range: {user_settings['min_age_minutes']}-{user_settings['max_age_minutes']} min

*💰 Trading*
• Auto-Buy: {'✅ ON' if user_settings['auto_buy_enabled'] else '❌ OFF'}
• Base Amount: {user_settings['base_trade_amount_sol']} SOL
• Max Amount: {user_settings['max_trade_amount_sol']} SOL

*📊 Profit Strategy*
• Stop Loss: {user_settings['initial_stop_loss']}%
• Trailing: {user_settings['trailing_percentage']}%
• Max Hold: {user_settings['max_hold_time_minutes']} min

*🔔 Alerts*
• Enabled: {'✅' if user_settings['alerts_enabled'] else '❌'}
• Min Score: {user_settings['min_score_alert']}

_Select a category to configure_
    """

    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def settings_scanner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scanner Filter Configuration"""
    keyboard = [
        [
            InlineKeyboardButton(f"💧 Min Liq: ${user_settings['min_liquidity_usd']:,}",
                               callback_data="adjust_min_liquidity"),
            InlineKeyboardButton(f"💧 Max Liq: ${user_settings['max_liquidity_usd']:,}",
                               callback_data="adjust_max_liquidity")
        ],
        [
            InlineKeyboardButton(f"⏱ Min Age: {user_settings['min_age_minutes']}m",
                               callback_data="adjust_min_age"),
            InlineKeyboardButton(f"⏱ Max Age: {user_settings['max_age_minutes']}m",
                               callback_data="adjust_max_age")
        ],
        [
            InlineKeyboardButton(f"👥 Min Holders: {user_settings['min_holder_count']}",
                               callback_data="adjust_min_holders"),
            InlineKeyboardButton(f"📊 Min Score: {user_settings['min_score']}",
                               callback_data="adjust_min_score")
        ],
        [
            InlineKeyboardButton(f"📈 Min Volume: ${user_settings['min_volume_usd']:,}",
                               callback_data="adjust_min_volume"),
            InlineKeyboardButton(f"💎 Max Top10: {user_settings['max_top_10_percentage']}%",
                               callback_data="adjust_max_top10")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"""
*🎯 SCANNER FILTER SETTINGS*
━━━━━━━━━━━━━━━━━━━━━━━

*Current Filters:*
• Min Liquidity: ${user_settings['min_liquidity_usd']:,}
• Max Liquidity: ${user_settings['max_liquidity_usd']:,}
• Age Range: {user_settings['min_age_minutes']}-{user_settings['max_age_minutes']} min
• Min Holders: {user_settings['min_holder_count']}
• Max Holders: {user_settings['max_holder_count']}
• Max Top 10%: {user_settings['max_top_10_percentage']}%
• Min Volume: ${user_settings['min_volume_usd']:,}
• Min Score: {user_settings['min_score']}

*💡 Tips:*
• Lower liquidity = Higher risk/reward
• Younger tokens = More volatility
• Higher score = More selective

_Click a parameter to adjust_
    """

    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def settings_trading(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trading Parameters Configuration"""
    keyboard = [
        [
            InlineKeyboardButton(
                f"🤖 Auto-Buy: {'✅ ON' if user_settings['auto_buy_enabled'] else '❌ OFF'}",
                callback_data="toggle_auto_buy"
            )
        ],
        [
            InlineKeyboardButton(f"💰 Base Amount: {user_settings['base_trade_amount_sol']} SOL",
                               callback_data="adjust_base_amount"),
            InlineKeyboardButton(f"💎 Max Amount: {user_settings['max_trade_amount_sol']} SOL",
                               callback_data="adjust_max_amount")
        ],
        [
            InlineKeyboardButton(f"📊 Auto-Buy Min Score: {user_settings['auto_buy_min_score']}",
                               callback_data="adjust_autobuy_score"),
            InlineKeyboardButton(f"💸 Max Auto SOL: {user_settings['max_auto_buy_sol']}",
                               callback_data="adjust_max_auto_sol")
        ],
        [
            InlineKeyboardButton(f"📉 Min Slippage: {user_settings['min_slippage_bps']/100}%",
                               callback_data="adjust_min_slippage"),
            InlineKeyboardButton(f"📈 Max Slippage: {user_settings['max_slippage_bps']/100}%",
                               callback_data="adjust_max_slippage")
        ],
        [
            InlineKeyboardButton(f"🛡 MEV Protection: {'✅' if user_settings['use_mev_protection'] else '❌'}",
                               callback_data="toggle_mev_protection")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"""
*💰 TRADING SETTINGS*
━━━━━━━━━━━━━━━━━━━━━━━

*Position Sizing:*
• Base Amount: {user_settings['base_trade_amount_sol']} SOL
• Max Amount: {user_settings['max_trade_amount_sol']} SOL
• Scaling: Dynamic (based on score)

*Auto-Buy Settings:*
• Enabled: {'✅ ON' if user_settings['auto_buy_enabled'] else '❌ OFF'}
• Min Score: {user_settings['auto_buy_min_score']}
• Max Per Trade: {user_settings['max_auto_buy_sol']} SOL

*Slippage:*
• Min: {user_settings['min_slippage_bps']/100}%
• Max: {user_settings['max_slippage_bps']/100}%
• Mode: Dynamic (adapts to liquidity)

*Advanced:*
• MEV Protection: {'✅ ON' if user_settings['use_mev_protection'] else '❌ OFF'}
• Priority Fee: {user_settings['priority_fee_lamports']} lamports

_Click a parameter to adjust_
    """

    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def settings_profit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Profit Strategy Configuration"""
    keyboard = [
        [
            InlineKeyboardButton(f"🛑 Stop Loss: {user_settings['initial_stop_loss']}%",
                               callback_data="adjust_stop_loss"),
            InlineKeyboardButton(f"📈 Trailing: {user_settings['trailing_percentage']}%",
                               callback_data="adjust_trailing")
        ],
        [
            InlineKeyboardButton(f"🚀 Activation: {user_settings['trailing_activation']}x",
                               callback_data="adjust_trail_activation"),
            InlineKeyboardButton(f"⏱ Max Hold: {user_settings['max_hold_time_minutes']}m",
                               callback_data="adjust_max_hold")
        ],
        [
            InlineKeyboardButton("📊 Take Profit Levels", callback_data="adjust_tp_levels")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get TP levels from profit_strategy
    tp_text = "\n".join([
        f"  • {(mult-1)*100:.0f}% profit → Sell {pct*100:.0f}%"
        for mult, pct in profit_strategy.TAKE_PROFIT_LEVELS
    ])

    text = f"""
*📊 PROFIT STRATEGY SETTINGS*
━━━━━━━━━━━━━━━━━━━━━━━

*Stop Loss:*
• Initial: {user_settings['initial_stop_loss']}%
• Type: Trailing (adaptive)
• Activation: {user_settings['trailing_activation']}x
• Trailing: {user_settings['trailing_percentage']}% from peak

*Take Profit Levels:*
{tp_text}

*Exit Conditions:*
• Max Hold Time: {user_settings['max_hold_time_minutes']} minutes
• Volume Drop: Auto-detect
• Momentum Loss: Auto-detect

*💡 Strategy:*
This uses a smart multi-level exit strategy that secures profits while letting winners run.

_Click a parameter to adjust_
    """

    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def settings_presets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick Strategy Presets"""
    keyboard = [
        [
            InlineKeyboardButton("🔥 AGGRESSIVE", callback_data="preset_aggressive"),
            InlineKeyboardButton("⚖️ BALANCED", callback_data="preset_balanced")
        ],
        [
            InlineKeyboardButton("🛡 CONSERVATIVE", callback_data="preset_conservative"),
            InlineKeyboardButton("⚡ SCALPING", callback_data="preset_scalping")
        ],
        [
            InlineKeyboardButton("🎯 SNIPING", callback_data="preset_sniping"),
            InlineKeyboardButton("💎 HODL", callback_data="preset_hodl")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """
*🚀 QUICK PRESETS*
━━━━━━━━━━━━━━━━━━━━━━━

*🔥 AGGRESSIVE*
High risk, high reward. Early entries, larger positions.
• Risk: ⭐⭐⭐⭐⭐
• Reward: 5-10x potential
• Win Rate: ~30-40%

*⚖️ BALANCED*
Good risk/reward ratio. Proven approach.
• Risk: ⭐⭐⭐
• Reward: 2-3x potential
• Win Rate: ~50-60%

*🛡 CONSERVATIVE*
Low risk, steady gains. Focus on quality.
• Risk: ⭐⭐
• Reward: 1.5-2x potential
• Win Rate: ~60-70%

*⚡ SCALPING*
Quick in/out. Many small profits.
• Risk: ⭐⭐
• Reward: 1.2-1.5x potential
• Win Rate: ~70%+

*🎯 SNIPING*
Ultra-early entries. Highest risk/reward.
• Risk: ⭐⭐⭐⭐⭐
• Reward: 10-50x potential
• Win Rate: ~20-30%

*💎 HODL*
Long-term holds. Let winners run.
• Risk: ⭐⭐⭐
• Reward: 3-5x potential
• Win Rate: ~40-50%

_Select a preset to apply_
    """

    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ============================================================================
# PARAMETER ADJUSTMENT HANDLERS
# ============================================================================

async def handle_parameter_adjustment(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     parameter: str, options: List[Any]) -> None:
    """Generic parameter adjustment handler"""
    keyboard = []

    # Create buttons for each option
    for option in options:
        keyboard.append([InlineKeyboardButton(
            str(option),
            callback_data=f"set_{parameter}_{option}"
        )])

    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="settings_scanner")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        f"*Select {parameter.replace('_', ' ').title()}:*\n\nCurrent: {user_settings.get(parameter, 'N/A')}",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def apply_preset(preset_name: str):
    """Apply a strategy preset"""
    presets = {
        'aggressive': {
            'min_liquidity_usd': 2000,
            'max_liquidity_usd': 50000,
            'min_age_minutes': 0.1,
            'max_age_minutes': 2,
            'min_holder_count': 20,
            'min_score': 65,
            'base_trade_amount_sol': 0.02,
            'max_trade_amount_sol': 0.3,
            'initial_stop_loss': 25,
            'trailing_percentage': 30,
            'max_hold_time_minutes': 15
        },
        'balanced': {
            'min_liquidity_usd': 10000,
            'max_liquidity_usd': 200000,
            'min_age_minutes': 1,
            'max_age_minutes': 5,
            'min_holder_count': 100,
            'min_score': 70,
            'base_trade_amount_sol': 0.05,
            'max_trade_amount_sol': 0.3,
            'initial_stop_loss': 15,
            'trailing_percentage': 20,
            'max_hold_time_minutes': 30
        },
        'conservative': {
            'min_liquidity_usd': 20000,
            'max_liquidity_usd': 500000,
            'min_age_minutes': 2,
            'max_age_minutes': 10,
            'min_holder_count': 200,
            'min_score': 80,
            'base_trade_amount_sol': 0.1,
            'max_trade_amount_sol': 0.5,
            'initial_stop_loss': 10,
            'trailing_percentage': 15,
            'max_hold_time_minutes': 60
        },
        'scalping': {
            'min_liquidity_usd': 15000,
            'max_liquidity_usd': 300000,
            'min_age_minutes': 1,
            'max_age_minutes': 5,
            'min_holder_count': 150,
            'min_score': 75,
            'base_trade_amount_sol': 0.03,
            'max_trade_amount_sol': 0.2,
            'initial_stop_loss': 8,
            'trailing_percentage': 10,
            'max_hold_time_minutes': 10
        },
        'sniping': {
            'min_liquidity_usd': 1000,
            'max_liquidity_usd': 20000,
            'min_age_minutes': 0.05,
            'max_age_minutes': 1,
            'min_holder_count': 10,
            'min_score': 60,
            'base_trade_amount_sol': 0.01,
            'max_trade_amount_sol': 0.1,
            'initial_stop_loss': 30,
            'trailing_percentage': 40,
            'max_hold_time_minutes': 5
        },
        'hodl': {
            'min_liquidity_usd': 50000,
            'max_liquidity_usd': 1000000,
            'min_age_minutes': 5,
            'max_age_minutes': 30,
            'min_holder_count': 500,
            'min_score': 85,
            'base_trade_amount_sol': 0.2,
            'max_trade_amount_sol': 1.0,
            'initial_stop_loss': 20,
            'trailing_percentage': 25,
            'max_hold_time_minutes': 240
        }
    }

    if preset_name in presets:
        user_settings.update(presets[preset_name])
        # Update global config
        update_global_config()
        return True
    return False

def update_global_config():
    """Update global config from user_settings"""
    # Update scanner_filters
    cfg.scanner_filters.MIN_LIQUIDITY_USD = user_settings['min_liquidity_usd']
    cfg.scanner_filters.MAX_LIQUIDITY_USD = user_settings['max_liquidity_usd']
    cfg.scanner_filters.MIN_AGE_MINUTES = user_settings['min_age_minutes']
    cfg.scanner_filters.MAX_AGE_MINUTES = user_settings['max_age_minutes']
    cfg.scanner_filters.MIN_HOLDER_COUNT = user_settings['min_holder_count']
    cfg.scanner_filters.MIN_SCORE = user_settings['min_score']
    cfg.scanner_filters.MIN_VOLUME_USD = user_settings['min_volume_usd']
    cfg.scanner_filters.MAX_TOP_10_PERCENTAGE = user_settings['max_top_10_percentage']

    # Update trading_config
    cfg.trading_config.BASE_TRADE_AMOUNT_SOL = user_settings['base_trade_amount_sol']
    cfg.trading_config.MAX_TRADE_AMOUNT_SOL = user_settings['max_trade_amount_sol']
    cfg.trading_config.MIN_SLIPPAGE_BPS = user_settings['min_slippage_bps']
    cfg.trading_config.MAX_SLIPPAGE_BPS = user_settings['max_slippage_bps']
    cfg.trading_config.USE_MEV_PROTECTION = user_settings['use_mev_protection']
    cfg.trading_config.PRIORITY_FEE_LAMPORTS = user_settings['priority_fee_lamports']

    # Update profit_strategy
    cfg.profit_strategy.INITIAL_STOP_LOSS = user_settings['initial_stop_loss']
    cfg.profit_strategy.TRAILING_ACTIVATION = user_settings['trailing_activation']
    cfg.profit_strategy.TRAILING_PERCENTAGE = user_settings['trailing_percentage']
    cfg.profit_strategy.MAX_HOLD_TIME_MINUTES = user_settings['max_hold_time_minutes']

# ============================================================================
# CALLBACK HANDLER - ROUTER
# ============================================================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced callback handler with all actions"""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Navigation
    if data == "start":
        await start(update, context)
    elif data == "dashboard":
        await dashboard(update, context)
    elif data == "settings_main":
        await settings_main(update, context)
    elif data == "settings_scanner":
        await settings_scanner(update, context)
    elif data == "settings_trading":
        await settings_trading(update, context)
    elif data == "settings_profit":
        await settings_profit(update, context)
    elif data == "settings_presets":
        await settings_presets(update, context)

    # Presets
    elif data.startswith("preset_"):
        preset_name = data.replace("preset_", "")
        if await apply_preset(preset_name):
            await query.answer(f"✅ {preset_name.upper()} preset applied!", show_alert=True)
            await settings_main(update, context)
        else:
            await query.answer("❌ Preset not found!", show_alert=True)

    # Toggles
    elif data == "toggle_auto_buy":
        user_settings['auto_buy_enabled'] = not user_settings['auto_buy_enabled']
        update_global_config()
        await settings_trading(update, context)

    elif data == "toggle_mev_protection":
        user_settings['use_mev_protection'] = not user_settings['use_mev_protection']
        update_global_config()
        await settings_trading(update, context)

    # Emergency Stop
    elif data == "emergency_stop":
        keyboard = [
            [
                InlineKeyboardButton("⚠️ YES, STOP EVERYTHING", callback_data="confirm_emergency_stop"),
                InlineKeyboardButton("❌ Cancel", callback_data="start")
            ]
        ]
        await query.edit_message_text(
            "*🚨 EMERGENCY STOP*\n\nThis will:\n• Stop the scanner\n• Cancel pending orders\n• Keep positions open\n\nAre you sure?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "confirm_emergency_stop":
        from scanner import scanner
        if scanner.running:
            await scanner.stop()
        await query.answer("🛑 Bot stopped!", show_alert=True)
        await start(update, context)

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
