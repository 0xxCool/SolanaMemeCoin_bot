# scanner_websocket_optimized.py
"""
Optimierter WebSocket Scanner für DexScreener
Mit Proxy-Rotation, Fallback und echter Echtzeit-Performance

Performance:
- WebSocket: 50-200ms Latenz
- Fallback HTTP: 5-10s Latenz (parallel)
- Automatic Failover
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import aiohttp
import websockets
from collections import deque

from config import (
    DEXSCREENER_WSS_URLS,
    DEXSCREENER_WSS_HEADERS,
)
import telegram_bot

logger = logging.getLogger(__name__)

# ==============================================================================
# PROXY CONFIGURATION
# ==============================================================================
# Option 1: Residential Proxies (empfohlen für Cloudflare)
ROTATING_PROXIES = [
    # Format: "http://user:pass@proxy:port"
    # Beispiele (ersetze mit echten Proxies):
    # "http://user:pass@proxy1.smartproxy.com:12345",
    # "http://user:pass@proxy2.smartproxy.com:12345",
]

# Option 2: Free Proxies (weniger zuverlässig)
FREE_PROXIES = [
    "http://proxy-list.download:8080",
    # Mehr von: https://free-proxy-list.net/
]

# ==============================================================================
# OPTIMIZED SCANNER CLASS
# ==============================================================================

@dataclass
class ScannerMetrics:
    """Scanner Performance Metrics"""
    messages_received: int = 0
    pairs_processed: int = 0
    alerts_sent: int = 0
    websocket_reconnects: int = 0
    http_fallback_cycles: int = 0
    avg_latency_ms: float = 0
    last_message_time: float = 0

class OptimizedWebSocketScanner:
    """
    High-Performance WebSocket Scanner mit Fallback
    
    Features:
    - Echtes WebSocket-Streaming (wenn möglich)
    - Proxy-Rotation für Cloudflare-Bypass
    - Paralleles HTTP-Polling als Fallback
    - Automatic Reconnection
    - Performance Monitoring
    """
    
    def __init__(self):
        self.running = False
        self.metrics = ScannerMetrics()
        self.processing_queue = asyncio.Queue(maxsize=500)
        self.seen_pairs: Set[str] = set()
        self.workers: List[asyncio.Task] = []
        
        # WebSocket state
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._current_proxy_idx = 0
        
        # HTTP Fallback state
        self._http_tasks: List[asyncio.Task] = []
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # Performance tracking
        self._latency_buffer = deque(maxlen=100)
        self._last_stats_report = time.time()
        
    # ==========================================================================
    # MAIN ENTRY POINT
    # ==========================================================================
    
    async def start(self):
        """
        Startet Scanner mit intelligenter Strategie:
        1. Versuche WebSocket (mit Proxy-Rotation)
        2. Bei Fehler: Fallback zu parallel HTTP
        3. Monitoring & Auto-Recovery
        """
        self.running = True
        logger.info("🚀 Starte Optimized Scanner...")
        
        # HTTP Session vorbereiten (für Fallback)
        self._http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0',
                'Accept': 'application/json',
            }
        )
        
        # Starte Worker für Pair-Processing
        num_workers = 4
        for i in range(num_workers):
            worker = asyncio.create_task(self._process_worker(f"Worker-{i}"))
            self.workers.append(worker)
        
        # Starte Stats Reporter
        asyncio.create_task(self._stats_reporter())
        
        # Hauptloop: WebSocket mit Fallback
        while self.running:
            try:
                # Strategie 1: WebSocket (beste Performance)
                logger.info("📡 Versuche WebSocket-Verbindung...")
                await self._websocket_loop_with_proxies()
                
            except Exception as e:
                logger.warning(f"⚠️ WebSocket fehlgeschlagen: {e}")
                logger.info("🔄 Wechsle zu HTTP-Fallback...")
                
                # Strategie 2: HTTP Fallback (parallel)
                try:
                    await self._parallel_http_fallback()
                except Exception as e2:
                    logger.error(f"❌ Auch HTTP-Fallback fehlgeschlagen: {e2}")
                    await asyncio.sleep(30)  # Wait before retry
    
    async def stop(self):
        """Sauberes Shutdown"""
        logger.info("🛑 Stoppe Scanner...")
        self.running = False
        
        # Stoppe WebSocket
        if self._websocket:
            await self._websocket.close()
        
        # Stoppe HTTP Session
        if self._http_session:
            await self._http_session.close()
        
        # Stoppe Worker
        for worker in self.workers:
            worker.cancel()
        
        logger.info("✅ Scanner gestoppt")
    
    # ==========================================================================
    # WEBSOCKET IMPLEMENTATION (PREFERRED)
    # ==========================================================================
    
    async def _websocket_loop_with_proxies(self):
        """
        WebSocket Loop mit Proxy-Rotation
        Versucht verschiedene Proxies um Cloudflare zu umgehen
        """
        proxies_to_try = ROTATING_PROXIES if ROTATING_PROXIES else [None]
        
        for attempt, proxy in enumerate(proxies_to_try * 3):  # 3 Durchläufe
            try:
                logger.info(f"🔌 WebSocket Verbindungsversuch #{attempt + 1}")
                if proxy:
                    logger.info(f"   └─ Via Proxy: {proxy[:20]}...")
                
                # Verbinde zu WebSocket
                ws_url = DEXSCREENER_WSS_URLS[0]  # Hauptendpoint
                
                # WebSocket verbinden (mit oder ohne Proxy)
                extra_headers = DEXSCREENER_WSS_HEADERS.copy()
                
                if proxy:
                    # Mit Proxy (erfordert proxy-capable websockets)
                    # Hinweis: Standard websockets lib unterstützt keine HTTP Proxies
                    # Lösung: Nutze aiohttp WebSocket über Proxy
                    async with self._http_session.ws_connect(
                        ws_url,
                        headers=extra_headers,
                        proxy=proxy
                    ) as ws:
                        logger.info("✅ WebSocket verbunden (via Proxy)!")
                        await self._process_websocket_stream(ws)
                else:
                    # Ohne Proxy (direkter Versuch)
                    async with websockets.connect(
                        ws_url,
                        extra_headers=extra_headers,
                        ping_interval=20,
                        ping_timeout=10,
                    ) as ws:
                        logger.info("✅ WebSocket verbunden (direkt)!")
                        await self._process_websocket_stream(ws)
                
            except websockets.exceptions.InvalidStatusCode as e:
                if e.status_code == 403:
                    logger.warning(f"⚠️ Cloudflare Block (403) - Proxy {attempt + 1}")
                    continue
                raise
            
            except Exception as e:
                logger.warning(f"⚠️ WebSocket Fehler: {e}")
                if attempt < len(proxies_to_try) * 3 - 1:
                    await asyncio.sleep(5)  # Wait before retry
                    continue
                raise
        
        raise Exception("Alle WebSocket-Versuche fehlgeschlagen")
    
    async def _process_websocket_stream(self, ws):
        """
        Verarbeitet eingehende WebSocket-Nachrichten
        Dies ist der HAUPTLOOP für Echtzeit-Streaming
        """
        self.metrics.last_message_time = time.time()
        message_count = 0
        
        try:
            async for raw_message in ws:
                if not self.running:
                    break
                
                message_count += 1
                start_time = time.time()
                
                try:
                    # Parse message
                    if isinstance(raw_message, str):
                        data = json.loads(raw_message)
                    else:
                        data = json.loads(raw_message.data)
                    
                    # Handle different message types
                    if 'pairs' in data:
                        for pair in data['pairs']:
                            await self._handle_new_pair(pair, source="websocket")
                    
                    elif 'pair' in data:
                        await self._handle_new_pair(data['pair'], source="websocket")
                    
                    # Update metrics
                    latency_ms = (time.time() - start_time) * 1000
                    self._latency_buffer.append(latency_ms)
                    self.metrics.messages_received += 1
                    self.metrics.last_message_time = time.time()
                    
                    # Log every 100 messages
                    if message_count % 100 == 0:
                        avg_latency = sum(self._latency_buffer) / len(self._latency_buffer)
                        logger.info(
                            f"📊 WebSocket: {message_count} Nachrichten | "
                            f"Latenz: {avg_latency:.1f}ms"
                        )
                
                except json.JSONDecodeError:
                    logger.debug("Invalid JSON in WebSocket message")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ WebSocket-Verbindung geschlossen")
            self.metrics.websocket_reconnects += 1
        
        except Exception as e:
            logger.error(f"❌ WebSocket Stream Error: {e}")
            raise
    
    # ==========================================================================
    # HTTP FALLBACK (WENN WEBSOCKET NICHT GEHT)
    # ==========================================================================
    
    async def _parallel_http_fallback(self):
        """
        Parallele HTTP-Polling Strategie
        3 APIs gleichzeitig abfragen für maximale Coverage
        """
        logger.info("🔄 Starte Parallel HTTP Fallback...")
        
        # Starte alle APIs parallel
        tasks = [
            asyncio.create_task(self._http_poll_token_profiles()),
            asyncio.create_task(self._http_poll_solana_pairs()),
            asyncio.create_task(self._http_poll_search()),
        ]
        self._http_tasks = tasks
        
        try:
            await asyncio.gather(*tasks)
        finally:
            # Cleanup
            for task in tasks:
                if not task.done():
                    task.cancel()
    
    async def _http_poll_token_profiles(self):
        """Pollt Token Profiles API"""
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                start_time = time.time()
                
                async with self._http_session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        profiles = data if isinstance(data, list) else []
                        
                        new_count = 0
                        for profile in profiles[:30]:
                            if profile.get('chainId') == 'solana':
                                token_addr = profile.get('tokenAddress')
                                if token_addr and token_addr not in self.seen_pairs:
                                    self.seen_pairs.add(token_addr)
                                    new_count += 1
                                    
                                    # Konvertiere zu Pair-Format
                                    pair_data = {
                                        'chainId': 'solana',
                                        'pairAddress': token_addr,
                                        'baseToken': {
                                            'symbol': profile.get('symbol', 'UNKNOWN'),
                                            'address': token_addr
                                        },
                                        'pairCreatedAt': int(time.time() * 1000),
                                        'liquidity': {'usd': 0},
                                        'from_api': 'token_profiles'
                                    }
                                    
                                    await self._handle_new_pair(pair_data, source="http_profiles")
                        
                        latency = (time.time() - start_time) * 1000
                        if new_count > 0:
                            logger.info(
                                f"📡 Token Profiles: Cycle #{cycle} | "
                                f"Found {new_count} new | "
                                f"Latency: {latency:.0f}ms"
                            )
                    
                    elif resp.status == 429:
                        logger.warning("⚠️ Rate limit - warte 60s")
                        await asyncio.sleep(60)
                        continue
                
                # Cycle delay
                await asyncio.sleep(5)  # 5s statt 15s!
                
            except Exception as e:
                logger.error(f"HTTP Profiles Error: {e}")
                await asyncio.sleep(10)
    
    async def _http_poll_solana_pairs(self):
        """Pollt Solana Pairs API"""
        url = "https://api.dexscreener.com/latest/dex/pairs/solana"
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                start_time = time.time()
                
                async with self._http_session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get('pairs', [])
                        
                        # Sortiere nach Alter
                        pairs.sort(key=lambda p: p.get('pairCreatedAt', 0), reverse=True)
                        
                        new_count = 0
                        for pair in pairs[:30]:
                            pair_addr = pair.get('pairAddress')
                            if pair_addr and pair_addr not in self.seen_pairs:
                                self.seen_pairs.add(pair_addr)
                                new_count += 1
                                
                                pair['from_api'] = 'solana_pairs'
                                await self._handle_new_pair(pair, source="http_pairs")
                        
                        latency = (time.time() - start_time) * 1000
                        if new_count > 0:
                            logger.info(
                                f"📡 Solana Pairs: Cycle #{cycle} | "
                                f"Found {new_count} new | "
                                f"Latency: {latency:.0f}ms"
                            )
                    
                    elif resp.status == 429:
                        await asyncio.sleep(60)
                        continue
                
                await asyncio.sleep(7)  # Leicht höherer Delay
                
            except Exception as e:
                logger.error(f"HTTP Pairs Error: {e}")
                await asyncio.sleep(10)
    
    async def _http_poll_search(self):
        """Pollt Search API mit rotating queries"""
        search_terms = ['pump', 'moon', 'pepe', 'doge', 'sol']
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                query = search_terms[cycle % len(search_terms)]
                url = "https://api.dexscreener.com/latest/dex/search"
                
                async with self._http_session.get(url, params={'q': query}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get('pairs', [])
                        
                        new_count = 0
                        for pair in pairs:
                            if pair.get('chainId') != 'solana':
                                continue
                            
                            pair_addr = pair.get('pairAddress')
                            if pair_addr and pair_addr not in self.seen_pairs:
                                self.seen_pairs.add(pair_addr)
                                new_count += 1
                                
                                pair['from_api'] = 'search'
                                await self._handle_new_pair(pair, source="http_search")
                        
                        if new_count > 0:
                            logger.info(f"🔍 Search '{query}': Found {new_count} new")
                    
                    elif resp.status == 429:
                        await asyncio.sleep(60)
                        continue
                
                await asyncio.sleep(10)  # Längerer Delay für Search
                
            except Exception as e:
                logger.error(f"HTTP Search Error: {e}")
                await asyncio.sleep(10)
    
    # ==========================================================================
    # PAIR PROCESSING
    # ==========================================================================
    
    async def _handle_new_pair(self, pair_data: Dict, source: str = "unknown"):
        """
        Verarbeitet ein neues Pair
        - Validierung
        - Queue für Analyzer
        - Metrics Update
        """
        try:
            pair_address = pair_data.get('pairAddress')
            if not pair_address:
                return
            
            # Basic validation
            chain_id = pair_data.get('chainId')
            if chain_id != 'solana':
                return
            
            # Add to processing queue
            await self.processing_queue.put({
                'pair_data': pair_data,
                'source': source,
                'timestamp': time.time()
            })
            
            self.metrics.pairs_processed += 1
            
            # Log (nur bei WebSocket oder ersten HTTP-Finds)
            if source == "websocket" or self.metrics.pairs_processed % 10 == 0:
                symbol = pair_data.get('baseToken', {}).get('symbol', 'UNKNOWN')
                logger.info(f"✨ New Pair [{source}]: {symbol} ({pair_address[:8]}...)")
        
        except Exception as e:
            logger.error(f"Error handling pair: {e}")
    
    async def _process_worker(self, name: str):
        """Worker der Pairs aus Queue verarbeitet"""
        logger.info(f"👷 {name} gestartet")
        
        while self.running:
            try:
                # Hole Pair aus Queue
                item = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )
                
                pair_data = item['pair_data']
                source = item['source']
                
                # Hier würde der Analyzer kommen
                # from analyzer import analyzer
                # result = await analyzer.analyze_token(pair_data)
                
                # Placeholder: Simuliere Verarbeitung
                await asyncio.sleep(0.1)
                
                # Mark task done
                self.processing_queue.task_done()
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"{name} error: {e}")
    
    # ==========================================================================
    # MONITORING & STATS
    # ==========================================================================
    
    async def _stats_reporter(self):
        """Periodische Stats-Reports"""
        while self.running:
            await asyncio.sleep(60)  # Every minute
            
            # Calculate metrics
            uptime = time.time() - self._last_stats_report
            msgs_per_sec = self.metrics.messages_received / uptime if uptime > 0 else 0
            
            avg_latency = 0
            if self._latency_buffer:
                avg_latency = sum(self._latency_buffer) / len(self._latency_buffer)
            
            time_since_last = time.time() - self.metrics.last_message_time
            
            # Log stats
            logger.info(
                f"\n📊 Scanner Stats:\n"
                f"   Messages: {self.metrics.messages_received} ({msgs_per_sec:.1f}/s)\n"
                f"   Pairs: {self.metrics.pairs_processed}\n"
                f"   Alerts: {self.metrics.alerts_sent}\n"
                f"   Queue: {self.processing_queue.qsize()}\n"
                f"   Latency: {avg_latency:.1f}ms\n"
                f"   Last msg: {time_since_last:.0f}s ago\n"
                f"   Reconnects: {self.metrics.websocket_reconnects}"
            )
            
            # Sende zu Telegram (optional)
            if self.metrics.pairs_processed > 0:
                await telegram_bot.send_message(
                    f"📊 Scanner: {self.metrics.pairs_processed} Pairs | "
                    f"Latency: {avg_latency:.0f}ms",
                    important=False
                )
            
            # Reset für nächstes Intervall
            self._last_stats_report = time.time()

# ==============================================================================
# GLOBALE INSTANZ
# ==============================================================================
scanner = OptimizedWebSocketScanner()

# ==============================================================================
# USAGE EXAMPLE
# ==============================================================================
if __name__ == '__main__':
    import sys
    
    async def main():
        """Test Scanner"""
        try:
            await scanner.start()
        except KeyboardInterrupt:
            print("\n👋 Stopping scanner...")
            await scanner.stop()
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
