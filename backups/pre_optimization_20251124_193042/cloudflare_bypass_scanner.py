# cloudflare_bypass_scanner.py
"""
WebSocket Scanner mit Cloudflare Bypass über Playwright
Löst das 403 Problem durch echte Browser-Session
"""
import asyncio
import json
import logging
from typing import Dict, Optional
from playwright.async_api import async_playwright, Page, WebSocket as PlaywrightWebSocket

logger = logging.getLogger(__name__)

class CloudflareBypassScanner:
    """Scanner der Cloudflare umgeht durch echten Browser"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page: Optional[Page] = None
        self.ws_connection: Optional[PlaywrightWebSocket] = None
        self.running = False
        self.message_handler = None
        
    async def start(self, message_callback):
        """
        Startet Scanner mit Cloudflare Bypass
        
        Args:
            message_callback: Async function(message) zum Verarbeiten der Messages
        """
        self.running = True
        self.message_handler = message_callback
        
        try:
            # 1. Starte Playwright Browser
            logger.info("🌐 Starte Playwright Browser...")
            self.playwright = await async_playwright().start()
            
            # Verwende Chromium (oder Firefox/WebKit)
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Headless für Server
                args=[
                    '--disable-blink-features=AutomationControlled',  # Verstecke Automation
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            # 2. Erstelle neue Browser Page mit realistischem Context
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Europe/Berlin',
            )
            
            self.page = await context.new_page()
            
            # 3. Navigiere zu DexScreener Website (triggert Cloudflare Challenge)
            logger.info("🔐 Löse Cloudflare Challenge...")
            await self.page.goto('https://dexscreener.com/solana', wait_until='networkidle')
            
            # Warte kurz, damit Cloudflare-Cookies gesetzt werden
            await asyncio.sleep(2)
            
            logger.info("✅ Cloudflare Challenge gelöst! Cookies erhalten.")
            
            # 4. Öffne WebSocket-Verbindung im Browser-Context
            await self._connect_websocket()
            
            # 5. Keep-Alive Loop
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Scanner Fehler: {e}", exc_info=True)
            raise
        finally:
            await self.stop()
    
    async def _connect_websocket(self):
        """Verbinde zu WebSocket im Browser-Context"""
        
        # Listen for WebSocket connections
        async def on_websocket(ws: PlaywrightWebSocket):
            url = ws.url
            logger.info(f"🔌 WebSocket verbunden: {url}")
            
            # Filter nur DexScreener WebSockets
            if 'dexscreener.com' in url:
                self.ws_connection = ws
                
                # Listen for messages
                ws.on("framereceived", lambda payload: asyncio.create_task(
                    self._handle_ws_message(payload)
                ))
                
                ws.on("framesent", lambda payload: logger.debug(f"📤 Sent: {payload[:100]}"))
                
                ws.on("close", lambda: logger.warning("⚠️ WebSocket geschlossen"))
        
        self.page.on("websocket", on_websocket)
        
        # Trigger WebSocket connection durch JavaScript
        logger.info("🔌 Öffne WebSocket zu DexScreener...")
        
        ws_script = """
        async () => {
            const ws = new WebSocket('wss://io.dexscreener.com/dex/screener');
            
            ws.onopen = () => {
                console.log('WebSocket connected!');
                
                // Subscribe zu Solana Pairs
                ws.send(JSON.stringify({
                    method: 'subscribe',
                    params: ['newPairs', 'solana']
                }));
            };
            
            ws.onmessage = (event) => {
                // Messages werden automatisch von Playwright gecaptured
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            // Keep reference
            window.__dexscreener_ws = ws;
        }
        """
        
        await self.page.evaluate(ws_script)
        
        # Warte auf WebSocket-Verbindung
        await asyncio.sleep(2)
        
        if self.ws_connection:
            logger.info("✅ WebSocket erfolgreich verbunden!")
        else:
            raise Exception("❌ WebSocket-Verbindung fehlgeschlagen")
    
    async def _handle_ws_message(self, payload):
        """Verarbeite WebSocket Message"""
        try:
            # Decode payload
            if isinstance(payload, bytes):
                message = payload.decode('utf-8')
            else:
                message = payload
            
            # Parse JSON
            data = json.loads(message)
            
            # Rufe Message Handler auf
            if self.message_handler:
                await self.message_handler(data)
                
        except json.JSONDecodeError:
            logger.debug(f"Non-JSON message: {payload[:100]}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def stop(self):
        """Beende Scanner sauber"""
        logger.info("🛑 Stoppe Scanner...")
        self.running = False
        
        if self.page:
            await self.page.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        logger.info("✅ Scanner gestoppt")


# ============================================================================
# INTEGRATION IN BESTEHENDEN CODE
# ============================================================================

async def integrate_cloudflare_bypass():
    """
    Ersetze die bestehende WebSocket-Verbindung durch Playwright-basierte Lösung
    """
    from scanner import scanner  # Importiere existierenden Scanner
    
    # Erstelle Cloudflare Bypass Scanner
    cf_scanner = CloudflareBypassScanner()
    
    async def message_callback(data: Dict):
        """Forward messages zum bestehenden Scanner"""
        # Simuliere WebSocket Message Format
        message = json.dumps(data)
        await scanner._handle_message(message)
    
    # Starte mit Bypass
    await cf_scanner.start(message_callback)


# ============================================================================
# ALTERNATIVE: HYBRID-ANSATZ
# ============================================================================

class HybridScanner:
    """
    Hybrid-Scanner der zwischen Playwright und websockets wechselt
    """
    
    def __init__(self):
        self.use_playwright = True  # Default zu Playwright wegen Cloudflare
        self.cf_scanner = None
        self.ws_scanner = None
        
    async def start(self):
        """Starte mit automatischer Fallback-Logik"""
        
        if self.use_playwright:
            try:
                logger.info("🎭 Versuche Playwright (Cloudflare Bypass)...")
                self.cf_scanner = CloudflareBypassScanner()
                await self.cf_scanner.start(self._handle_message)
                
            except Exception as e:
                logger.warning(f"⚠️ Playwright fehlgeschlagen: {e}")
                logger.info("🔄 Fallback zu Standard WebSocket...")
                self.use_playwright = False
        
        if not self.use_playwright:
            # Fallback zu Standard WebSocket
            from scanner import scanner
            await scanner.start()
    
    async def _handle_message(self, data: Dict):
        """Verarbeite Message"""
        # Deine Message-Verarbeitung hier
        pass


# ============================================================================
# VERWENDUNG
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Teste Cloudflare Bypass
    async def main():
        scanner = CloudflareBypassScanner()
        
        async def print_message(data):
            print(f"📨 Received: {json.dumps(data, indent=2)[:200]}...")
        
        await scanner.start(print_message)
    
    asyncio.run(main())
