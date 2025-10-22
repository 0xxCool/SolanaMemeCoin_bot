# main.py
"""
Solana Ultra High-Performance Trading Bot v2.0
Main Entry Point mit optimierter Startup-Sequenz
"""
import asyncio
import os
import sys
import signal
import logging
from dotenv import load_dotenv
from typing import Optional
import time
from telegram import Update

import telegram_bot
from scanner import scanner
from analyzer import analyzer
from trader import trader

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.scanner_task: Optional[asyncio.Task] = None
        self.telegram_app = None
        self.running = False
        self.start_time = time.time()
        
    async def initialize(self):
        """Initialisiert alle Bot-Komponenten"""
        logger.info("🚀 Initialisiere Solana Trading Bot v2.0...")
        
        # Lade Environment Variables
        load_dotenv()
        
        # Validiere kritische Environment Variables
        required_vars = {
            'PRIVATE_KEY': 'Wallet Private Key',
            'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
            'TELEGRAM_CHAT_ID': 'Telegram Chat ID',
            'RPC_URL': 'Solana RPC Endpoint'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"  - {var}: {description}")
                
        if missing_vars:
            error_msg = "❌ Fehlende Environment Variables:\n" + "\n".join(missing_vars)
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.info("✅ Environment Variables geladen")
        
        # Initialisiere Telegram Bot
        try:
            self.telegram_app = telegram_bot.setup_bot()
            logger.info("✅ Telegram Bot initialisiert")
        except Exception as e:
            logger.error(f"❌ Telegram Bot Fehler: {e}")
            raise
            
        # Warte auf Trader & Analyzer Initialisierung
        logger.info("🔄 Initialisiere Trading Module...")
        await asyncio.sleep(2)  # Gibt Zeit für Async Initialization
        
        # Sende Start-Nachricht
        await telegram_bot.send_message(
            f"""
*🚀 Bot Gestartet!*

Version: 2.0 Enhanced
Mode: High-Performance
Scanner: WebSocket Streaming
Trading: MEV Protected

Verwende /start für das Hauptmenü.
            """,
            important=True
        )
        
        self.running = True
        logger.info("✅ Bot vollständig initialisiert")
        
    async def start_scanner(self):
        """Startet den WebSocket Scanner"""
        logger.info("🔄 Starte Scanner...")
        
        try:
            self.scanner_task = asyncio.create_task(scanner.start())
            logger.info("✅ Scanner gestartet")
            
            await telegram_bot.send_message(
                "📡 *Scanner aktiviert*\n"
                "Überwache Solana Blockchain in Echtzeit...",
                important=True
            )
        except Exception as e:
            logger.error(f"❌ Scanner Start Fehler: {e}")
            await telegram_bot.send_message(
                f"❌ Scanner Fehler: {str(e)[:100]}",
                important=True
            )
            
    async def run(self):
        """Haupt-Loop"""
        try:
            # Initialisiere Bot
            await self.initialize()
            
            # Starte Scanner automatisch
            await self.start_scanner()
            
            # Starte Telegram Bot
            logger.info("🔄 Starte Telegram Bot Polling...")
            
            # Run both Telegram polling and periodic tasks
            await asyncio.gather(
                self.telegram_app.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                ),
                self.periodic_tasks(),
                return_exceptions=True
            )
            
        except KeyboardInterrupt:
            logger.info("⚠️ Keyboard Interrupt empfangen")
        except Exception as e:
            logger.error(f"❌ Kritischer Fehler: {e}")
            await telegram_bot.send_message(
                f"❌ *Bot Fehler:*\n`{str(e)[:200]}`",
                important=True
            )
        finally:
            await self.shutdown()
            
    async def periodic_tasks(self):
        """Führt periodische Aufgaben aus"""
        while self.running:
            try:
                # Alle 5 Minuten: Status Update
                await asyncio.sleep(300)
                
                uptime = (time.time() - self.start_time) / 60
                status_msg = f"""
*📊 Status Update*

Uptime: {uptime:.0f} min
Positions: {len(trader.positions)}
Scanner Queue: {scanner.processing_queue.qsize()}
                """
                
                # Nur senden wenn Positionen vorhanden
                if trader.positions:
                    await telegram_bot.send_message(status_msg, important=True)
                    
            except Exception as e:
                logger.error(f"Periodic Task Fehler: {e}")
                await asyncio.sleep(60)
                
    async def shutdown(self):
        """Sauberes Herunterfahren"""
        logger.info("🛑 Fahre Bot herunter...")
        self.running = False
        
        # Stoppe Scanner
        if self.scanner_task:
            await scanner.stop()
            
        # Schließe alle Positionen wenn gewünscht
        if trader.positions:
            await telegram_bot.send_message(
                f"⚠️ *{len(trader.positions)} offene Positionen!*\n"
                "Verwende /sell <address> um manuell zu schließen.",
                important=True
            )
            
        # Cleanup
        await analyzer.cleanup()
        await trader.cleanup()
        
        # Sende Shutdown Message
        await telegram_bot.send_message(
            "🛑 *Bot gestoppt*\n"
            f"Laufzeit: {(time.time() - self.start_time) / 60:.0f} Minuten",
            important=True
        )
        
        logger.info("✅ Bot sauber heruntergefahren")

def handle_signal(signum, frame):
    """Signal Handler für sauberes Shutdown"""
    logger.info(f"Signal {signum} empfangen")
    raise KeyboardInterrupt

async def main():
    """Main Entry Point"""
    # Setup Signal Handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Erstelle und starte Bot
    bot = TradingBot()
    await bot.run()

if __name__ == '__main__':
    # Python Version Check
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ erforderlich!")
        sys.exit(1)
        
    # Platform-spezifische Event Loop Policy (Windows)
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )
        
    # Starte Bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Auf Wiedersehen!")
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
        sys.exit(1)