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

# ✅ Configure logging FIRST (before any imports that use it)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Now safe to import everything else
from dotenv import load_dotenv
from typing import Optional, Any
import time
from telegram import Update

import telegram_bot
from scanner import scanner
from analyzer import analyzer
from trader import trader

# Import Health Check and Security modules
try:
    from health import start_health_server, health_check, record_trade
    from security import get_security_manager
    HEALTH_AVAILABLE = True
except ImportError:
    HEALTH_AVAILABLE = False
    logger.warning("⚠️ Health check module not available")  # ✅ Now safe!

# Import Integration Layer (AI + Auto-Trading)
try:
    from integration import initialize_integration, integration_manager
    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    logger.warning("⚠️ Integration module not available - running without AI")

class TradingBot:
    def __init__(self):
        self.scanner_task: Optional[asyncio.Task] = None
        self.telegram_app = None
        self.telegram_initialized = False  # Track if telegram was fully initialized
        self.running = False
        self.start_time = time.time()
        self.health_runner: Optional[Any] = None
        self.security_manager = None

    async def initialize(self):
        """Initialisiert alle Bot-Komponenten"""
        logger.info("🚀 Initialisiere Solana Trading Bot v2.0...")

        # Lade Environment Variables
        load_dotenv()

        # Initialize Security Manager
        if HEALTH_AVAILABLE:
            try:
                self.security_manager = get_security_manager()
                logger.info("✅ Security Manager initialisiert")
                self.security_manager.audit_log(
                    "BOT_START",
                    {"version": "2.0", "timestamp": time.time()}
                )
            except Exception as e:
                logger.warning(f"⚠️ Security Manager warning: {e}")
        
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
            
        # Initialisiere Analyzer
        logger.info("🔄 Initialisiere Analyzer...")
        try:
            await analyzer.ensure_initialized()
            logger.info("✅ Analyzer initialisiert")
        except Exception as e:
            logger.error(f"❌ Analyzer Initialisierung fehlgeschlagen: {e}")
            raise

        # Initialisiere Trader mit Wallet aus Environment
        logger.info("🔄 Initialisiere Trading Module...")
        try:
            await trader.initialize()  # Loads keypair from PRIVATE_KEY env var
            logger.info("✅ Trader initialisiert")
        except Exception as e:
            logger.error(f"❌ Trader Initialisierung fehlgeschlagen: {e}")
            raise

        # Initialisiere Integration Layer (AI + Auto-Trading)
        if INTEGRATION_AVAILABLE:
            try:
                await initialize_integration()
                logger.info("✅ AI & Auto-Trading initialisiert")
            except Exception as e:
                logger.warning(f"⚠️ Integration initialization warning: {e}")

        # Start Health Check Server
        if HEALTH_AVAILABLE:
            try:
                self.health_runner = await start_health_server(port=8000)
                health_check.update_component_status("database", "healthy")
                logger.info("✅ Health Check Server gestartet auf Port 8000")
            except Exception as e:
                logger.warning(f"⚠️ Health Check Server warning: {e}")

        # Sende Start-Nachricht
        ai_status = "✅ Active" if INTEGRATION_AVAILABLE else "⚠️ Disabled"
        health_status = "✅ Active" if HEALTH_AVAILABLE else "⚠️ Disabled"
        await telegram_bot.send_message(
            f"""
*🚀 Bot Gestartet!*

Version: 2.0 Enhanced + AI
Mode: High-Performance
Scanner: WebSocket Streaming
Trading: MEV Protected
AI Engine: {ai_status}
Health Checks: {health_status}
Security: ✅ Active

Verwende /start für das Hauptmenü.
Health: http://localhost:8000/health
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

            # Update health status
            if HEALTH_AVAILABLE:
                health_check.update_component_status("scanner", "healthy")

            await telegram_bot.send_message(
                "📡 *Scanner aktiviert*\n"
                "Überwache Solana Blockchain in Echtzeit...",
                important=True
            )
        except Exception as e:
            logger.error(f"❌ Scanner Start Fehler: {e}")
            if HEALTH_AVAILABLE:
                health_check.update_component_status("scanner", "unhealthy")

            await telegram_bot.send_message(
                f"❌ Scanner Fehler: {str(e)[:100]}",
                important=True
            )
            
    async def run(self):
        """Haupt-Loop"""
        try:
            # Initialisiere Bot
            await self.initialize()

            # ✅ Initialisiere Telegram Application explizit
            logger.info("🔄 Initialisiere Telegram Application...")
            await self.telegram_app.initialize()
            await self.telegram_app.start()
            self.telegram_initialized = True
            logger.info("✅ Telegram Application bereit")

            # Starte Scanner automatisch
            await self.start_scanner()

            # ✅ Starte Telegram Bot Polling manuell (ohne run_polling)
            logger.info("🔄 Starte Telegram Bot Polling...")
            await self.telegram_app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

            # Run periodic tasks in background
            asyncio.create_task(self.periodic_tasks())

            # Keep the bot running
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("⚠️ Keyboard Interrupt empfangen")
        except Exception as e:
            logger.error(f"❌ Kritischer Fehler: {e}", exc_info=True)
            try:
                await telegram_bot.send_message(
                    f"❌ *Bot Fehler:*\n`{str(e)[:200]}`",
                    important=True
                )
            except Exception as send_err:
                logger.warning(f"⚠️ Telegram error notification failed: {send_err}")
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

        # Audit log shutdown
        if HEALTH_AVAILABLE and self.security_manager:
            try:
                self.security_manager.audit_log(
                    "BOT_SHUTDOWN",
                    {
                        "uptime_seconds": time.time() - self.start_time,
                        "open_positions": len(trader.positions)
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Audit log warning: {e}")

        # Sende Shutdown Message (vor dem Stoppen des Telegram Bots)
        try:
            await telegram_bot.send_message(
                "🛑 *Bot gestoppt*\n"
                f"Laufzeit: {(time.time() - self.start_time) / 60:.0f} Minuten",
                important=True
            )
        except Exception as e:
            logger.warning(f"⚠️ Shutdown message warning: {e}")

        # Stoppe Scanner
        if self.scanner_task:
            try:
                await scanner.stop()
            except Exception as e:
                logger.warning(f"⚠️ Scanner stop warning: {e}")

        # Schließe alle Positionen wenn gewünscht
        if trader.positions:
            try:
                await telegram_bot.send_message(
                    f"⚠️ *{len(trader.positions)} offene Positionen!*\n"
                    "Verwende /sell <address> um manuell zu schließen.",
                    important=True
                )
            except Exception as e:
                logger.warning(f"⚠️ Position warning message failed: {e}")

        # Cleanup Components
        try:
            from analyzer import analyzer
            if hasattr(analyzer, 'cleanup'):
                await analyzer.cleanup()
                logger.info("✅ Analyzer cleanup abgeschlossen")
        except Exception as e:
            logger.warning(f"⚠️ Analyzer cleanup warning: {e}")

        try:
            await trader.cleanup()
            logger.info("✅ Trader cleanup abgeschlossen")
        except Exception as e:
            logger.warning(f"⚠️ Trader cleanup warning: {e}")

        # Stop health check server
        if HEALTH_AVAILABLE and self.health_runner:
            try:
                await self.health_runner.cleanup()
                logger.info("✅ Health Check Server gestoppt")
            except Exception as e:
                logger.warning(f"⚠️ Health Check cleanup warning: {e}")

        # ✅ Stoppe Telegram Application sauber (only if it was fully initialized)
        if self.telegram_app and self.telegram_initialized:
            try:
                logger.info("🔄 Stoppe Telegram Bot...")
                # Stop updater/polling
                if self.telegram_app.updater and self.telegram_app.updater.running:
                    await self.telegram_app.updater.stop()
                # Stop application
                await self.telegram_app.stop()
                # Shutdown application
                await self.telegram_app.shutdown()
                logger.info("✅ Telegram Bot gestoppt")
            except Exception as e:
                logger.warning(f"⚠️ Telegram shutdown warning: {e}")

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