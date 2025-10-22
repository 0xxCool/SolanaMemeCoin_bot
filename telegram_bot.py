# telegram_bot.py
"""
Enhanced Telegram Bot mit detaillierten Alerts und Controls
"""
import os
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import json

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    Bot, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

import trader
from config import trading_config, profit_strategy

# Bot Instance
telegram_app: Application = None
bot_instance: Bot = None

# User Settings (könnte in DB gespeichert werden)
user_settings = {
    'alerts_enabled': True,
    'min_score_alert': 70,
    'auto_buy_enabled': False,
    'max_auto_buy_sol': 0.1,
}

# Trade History
trade_history = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start Command - Zeigt Bot Menü"""
    chat_id = update.effective_chat.id
    
    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("💼 Positions", callback_data="positions")],
        [InlineKeyboardButton("📈 History", callback_data="history")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("🚀 Start Scanner", callback_data="start_scanner")],
        [InlineKeyboardButton("⏹️ Stop Scanner", callback_data="stop_scanner")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
*🚀 Solana Ultra-Speed Trading Bot*

Chat ID: `{chat_id}`
Version: 2.0 Enhanced
Status: ✅ Online

*Features:*
• WebSocket Real-time Streaming
• Multi-layer Token Analysis  
• MEV Protected Trading
• Smart Position Management
• Dynamic Risk Sizing

Wähle eine Option:
        """,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt aktuellen Bot Status"""
    from scanner import scanner
    
    # Sammle Status Info
    status_text = f"""
*📊 Bot Status*

*Scanner:*
• Status: {'🟢 Active' if scanner.running else '🔴 Inactive'}
• Processed: {scanner.stats['processed']} pairs
• Queue: {scanner.processing_queue.qsize()} pending
• Cache: {len(scanner.processed_pairs)} pairs

*Trading:*
• Active Positions: {len(trader.trader.positions)}
• Total Invested: {sum(p.invested_sol for p in trader.trader.positions.values()):.3f} SOL
• Today's Trades: {len([t for t in trade_history if t['timestamp'] > datetime.now().timestamp() - 86400])}

*Performance:*
• Win Rate: {calculate_win_rate():.1f}%
• Avg Profit: {calculate_avg_profit():.2f}%
• Best Trade: {get_best_trade():.2f}%

*System:*
• RPC Clients: {len(trader.trader.clients)}
• Wallet Balance: {await get_wallet_balance():.4f} SOL
    """
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            status_text, 
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )

async def positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt aktuelle Positionen"""
    positions = trader.trader.positions
    
    if not positions:
        text = "*💼 Keine aktiven Positionen*"
    else:
        text = "*💼 Aktive Positionen:*\n\n"
        
        for addr, pos in positions.items():
            profit_pct = ((pos.last_price - pos.entry_price) / pos.entry_price) * 100 if pos.last_price else 0
            
            text += f"""
*{pos.symbol}*
• Entry: ${pos.entry_price:.8f}
• Current: ${pos.last_price:.8f}
• P&L: {profit_pct:+.2f}%
• Invested: {pos.invested_sol:.3f} SOL
• High: ${pos.highest_price:.8f}
• Hold Time: {((time.time() - pos.entry_time) / 60):.1f} min
• [Chart](https://dexscreener.com/solana/{addr})

"""
            
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, 
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt Trade History"""
    recent_trades = trade_history[-10:]  # Letzte 10 Trades
    
    if not recent_trades:
        text = "*📈 Keine Trade History*"
    else:
        text = "*📈 Letzte Trades:*\n\n"
        
        for trade in recent_trades:
            text += f"""
{trade['symbol']} - {trade['type']}
• Amount: {trade['amount']:.3f} SOL
• P&L: {trade['profit']:+.4f} SOL ({trade['profit_pct']:+.1f}%)
• Time: {datetime.fromtimestamp(trade['timestamp']).strftime('%H:%M')}
"""
            
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN
    )

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt Settings Menü"""
    keyboard = [
        [InlineKeyboardButton(
            f"🔔 Alerts: {'ON' if user_settings['alerts_enabled'] else 'OFF'}", 
            callback_data="toggle_alerts"
        )],
        [InlineKeyboardButton(
            f"🎯 Min Score: {user_settings['min_score_alert']}", 
            callback_data="set_min_score"
        )],
        [InlineKeyboardButton(
            f"🤖 Auto-Buy: {'ON' if user_settings['auto_buy_enabled'] else 'OFF'}", 
            callback_data="toggle_auto_buy"
        )],
        [InlineKeyboardButton(
            f"💰 Max Auto: {user_settings['max_auto_buy_sol']} SOL", 
            callback_data="set_max_auto"
        )],
        [InlineKeyboardButton("⬅️ Back", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "*⚙️ Bot Settings*\n\nWähle eine Einstellung:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verarbeitet Button Callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Navigation
    if data == "status":
        await status(update, context)
    elif data == "positions":
        await positions(update, context)
    elif data == "history":
        await history(update, context)
    elif data == "settings":
        await settings_menu(update, context)
        
    # Scanner Controls
    elif data == "start_scanner":
        from scanner import scanner
        if not scanner.running:
            asyncio.create_task(scanner.start())
            await query.edit_message_text("✅ Scanner gestartet!")
        else:
            await query.edit_message_text("Scanner läuft bereits!")
            
    elif data == "stop_scanner":
        from scanner import scanner
        if scanner.running:
            await scanner.stop()
            await query.edit_message_text("⏹️ Scanner gestoppt!")
        else:
            await query.edit_message_text("Scanner läuft nicht!")
            
    # Settings
    elif data == "toggle_alerts":
        user_settings['alerts_enabled'] = not user_settings['alerts_enabled']
        await settings_menu(update, context)
        
    elif data == "toggle_auto_buy":
        user_settings['auto_buy_enabled'] = not user_settings['auto_buy_enabled']
        await settings_menu(update, context)
        
    # Trading Actions
    elif data.startswith("buy_"):
        token_address = data.split("_")[1]
        amount = float(data.split("_")[2]) if len(data.split("_")) > 2 else None
        
        await query.edit_message_text("🔄 Kaufe Token...")
        asyncio.create_task(trader.execute_buy(token_address, amount))
        
    elif data.startswith("sell_"):
        parts = data.split("_")
        token_address = parts[1]
        percentage = float(parts[2]) if len(parts) > 2 else 1.0
        
        await query.edit_message_text(f"🔄 Verkaufe {percentage*100:.0f}%...")
        asyncio.create_task(trader.execute_sell(token_address, percentage))
        
    elif data.startswith("ignore_"):
        await query.edit_message_text("⏭️ Token ignoriert")

async def manual_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manueller Kauf Command"""
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text(
                "Usage: /buy <token_address> [amount_sol]"
            )
            return
            
        token_address = args[0]
        amount = float(args[1]) if len(args) > 1 else None
        
        await update.message.reply_text("🔄 Starte manuellen Kauf...")
        asyncio.create_task(trader.execute_buy(token_address, amount))
        
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {e}")

async def manual_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manueller Verkauf Command"""
    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text(
                "Usage: /sell <token_address> [percentage]"
            )
            return
            
        token_address = args[0]
        percentage = float(args[1]) / 100 if len(args) > 1 else 1.0
        
        await update.message.reply_text(f"🔄 Verkaufe {percentage*100:.0f}%...")
        asyncio.create_task(trader.execute_sell(token_address, percentage))
        
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler: {e}")

async def send_alert(analysis_data: Dict[str, Any]):
    """
    Sendet formatierte Alerts mit umfassenden Daten
    """
    if not telegram_app or not user_settings['alerts_enabled']:
        return
        
    # Check minimum score
    if analysis_data.get('score', 0) < user_settings['min_score_alert']:
        return
        
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
        
    # Format Alert Message
    priority = analysis_data.get('priority', 'NORMAL')
    emoji = "🔥" if priority == "HIGH" else "🎯"
    
    text = f"""
{emoji} *New Opportunity Found!*

*Token:* `{analysis_data['symbol']}`
*Score:* {analysis_data['score']:.0f}/100 {'⭐' * int(analysis_data['score']/20)}

*📊 Metrics:*
• Liquidity: ${analysis_data['liquidity_usd']:,.0f}
• Market Cap: ${analysis_data.get('market_cap_usd', 0):,.0f}
• Age: {analysis_data['age_minutes']:.1f} min
• Holders: {analysis_data['holder_count']}
• Top 10: {analysis_data['top_10_percentage']:.1f}%

*📈 Activity:*
• Volume 5m: ${analysis_data.get('volume_usd_5m', 0):,.0f}
• TXs 5m: {analysis_data.get('tx_count_5m', 0)}
• Price Δ 5m: {analysis_data.get('price_change_5m', 0):+.1f}%

*🛡️ Security:*
• Risk: {analysis_data['risk_level']}
• Honeypot: {'❌ Yes' if analysis_data.get('is_honeypot') else '✅ No'}
• LP Burned: {'✅ Yes' if analysis_data.get('lp_burned') else '⚠️ No'}

*💰 Suggested Position:* {analysis_data.get('position_size_sol', 0.1):.3f} SOL

*📊 Charts:*
[DexScreener]({analysis_data.get('dex_url', '#')}) | [DexTools](https://www.dextools.io/app/en/solana/pair-explorer/{analysis_data['address']})
    """
    
    # Create Action Buttons
    keyboard = []
    
    # Auto-Buy wenn aktiviert und Score hoch genug
    if user_settings['auto_buy_enabled'] and analysis_data['score'] >= 85:
        amount = min(
            analysis_data.get('position_size_sol', 0.1),
            user_settings['max_auto_buy_sol']
        )
        asyncio.create_task(trader.execute_buy(analysis_data['address'], amount))
        
        keyboard.append([
            InlineKeyboardButton(
                f"✅ Auto-Buying {amount:.3f} SOL...", 
                callback_data="none"
            )
        ])
    else:
        # Manual Buy Options
        suggested = analysis_data.get('position_size_sol', 0.1)
        keyboard.extend([
            [InlineKeyboardButton(
                f"🚀 Buy {suggested:.3f} SOL", 
                callback_data=f"buy_{analysis_data['address']}_{suggested}"
            )],
            [
                InlineKeyboardButton(
                    "💰 0.05 SOL", 
                    callback_data=f"buy_{analysis_data['address']}_0.05"
                ),
                InlineKeyboardButton(
                    "💰 0.1 SOL", 
                    callback_data=f"buy_{analysis_data['address']}_0.1"
                ),
                InlineKeyboardButton(
                    "💰 0.2 SOL", 
                    callback_data=f"buy_{analysis_data['address']}_0.2"
                ),
            ],
            [InlineKeyboardButton(
                "⏭️ Ignore", 
                callback_data=f"ignore_{analysis_data['address']}"
            )]
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send Alert
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    await bot.send_message(
        chat_id=chat_id, 
        text=text, 
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def send_message(text: str, important: bool = False):
    """Sendet einfache Status Messages"""
    if not telegram_app:
        return
        
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
        
    # Filtere unwichtige Nachrichten
    if not important and not user_settings.get('verbose', False):
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

def setup_bot():
    """Initialisiert den Bot"""
    global telegram_app, bot_instance
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN nicht gefunden!")
        
    telegram_app = Application.builder().token(token).build()
    bot_instance = Bot(token=token)
    
    # Commands
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("positions", positions))
    telegram_app.add_handler(CommandHandler("history", history))
    telegram_app.add_handler(CommandHandler("buy", manual_buy))
    telegram_app.add_handler(CommandHandler("sell", manual_sell))
    
    # Callbacks
    telegram_app.add_handler(CallbackQueryHandler(button_callback))
    
    return telegram_app

# Helper Functions
def calculate_win_rate() -> float:
    """Berechnet Win Rate"""
    if not trade_history:
        return 0.0
        
    wins = len([t for t in trade_history if t.get('profit', 0) > 0])
    return (wins / len(trade_history)) * 100

def calculate_avg_profit() -> float:
    """Berechnet durchschnittlichen Profit"""
    if not trade_history:
        return 0.0
        
    profits = [t.get('profit_pct', 0) for t in trade_history]
    return sum(profits) / len(profits) if profits else 0

def get_best_trade() -> float:
    """Findet besten Trade"""
    if not trade_history:
        return 0.0
        
    return max([t.get('profit_pct', 0) for t in trade_history], default=0)

async def get_wallet_balance() -> float:
    """Holt Wallet Balance"""
    try:
        client = await trader.trader._get_client()
        result = await client.get_balance(trader.trader.keypair.pubkey())
        return result.value / 1e9
    except:
        return 0.0

def record_trade(trade_data: Dict):
    """Speichert Trade in History"""
    global trade_history
    trade_history.append({
        **trade_data,
        'timestamp': time.time()
    })
    
    # Behalte nur letzte 100 Trades
    if len(trade_history) > 100:
        trade_history = trade_history[-100:]