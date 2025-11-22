# scanner.py - COMPLETE FIXED VERSION
"""
✅ ALLE OPTIMIERUNGEN INTEGRIERT:
1. HTTP Fallback (wegen Cloudflare)
2. Relaxter Age Filter (findet mehr Pairs)
3. Multi-API Strategie (3 verschiedene Endpoints)
4. Verbose Logging (siehst alles)
5. Optimierte Queries
"""
import asyncio
import json
import websockets
import time
import logging
from typing import Dict, Set, List
from collections import deque
from dataclasses import dataclass, field
import heapq
import aiohttp

from config import (
    DEXSCREENER_WSS_URL,
    DEXSCREENER_WSS_URLS,
    DEXSCREENER_WSS_HEADERS,
    ENABLE_SNIPING_MODE
)
import telegram_bot

# Setup logging
logger = logging.getLogger(__name__)

# ✅ HTTP FALLBACK (Standard wegen Cloudflare-Blockierung)
USE_HTTP_FALLBACK = True

# ✅ VERBOSE DEBUG LOGGING
DEBUG_HTTP_REQUESTS = True  # Zeigt alle API Requests

# ✅ MULTI-API STRATEGIE
USE_MULTI_API = True  # Nutzt 3 verschiedene Endpoints

@dataclass(order=True)
class PriorityPair:
    """Priorisierte Pair für Processing Queue"""
    priority: float
    pair_data: Dict = field(compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)

class HighPerformanceScanner:
    def __init__(self):
        # Thread-safe processed pairs tracking
        self.processed_pairs: Dict[str, float] = {}
        self.processed_pairs_max_size = 10000
        self.processed_pairs_max_age = 3600  # 1 hour
        self.processed_pairs_lock = asyncio.Lock()
        
        self.processing_queue = asyncio.Queue(maxsize=1000)
        self.priority_queue: List[PriorityPair] = []
        self.workers: List[asyncio.Task] = []
        self.message_tasks: Set[asyncio.Task] = set()
        
        self.stats = {
            'received': 0,
            'processed': 0,
            'filtered': 0,
            'alerts_sent': 0,
            'http_requests': 0,
            'pairs_found': 0,
            'api_search_calls': 0,
            'api_profiles_calls': 0,
            'api_pairs_calls': 0,
        }
        
        self.running = False
        self.current_wss_endpoint_index = 0
        self.endpoint_failures: Dict[str, int] = {}
        self._websocket = None
        
    async def start(self):
        """Startet Scanner mit mehreren Worker-Threads"""
        self.running = True
        
        # Starte Worker
        num_workers = 5
        for i in range(num_workers):
            worker = asyncio.create_task(self._process_worker(f"Worker-{i}"))
            self.workers.append(worker)
            
        # Starte Stats Reporter
        asyncio.create_task(self._stats_reporter())
        
        # ✅ HTTP Fallback (wegen Cloudflare)
        if USE_HTTP_FALLBACK:
            logger.warning("⚠️ WebSocket deaktiviert - verwende HTTP Fallback wegen Cloudflare")
            
            if USE_MULTI_API:
                await self._multi_api_fallback_loop()
            else:
                await self._http_fallback_loop()
        else:
            await self._websocket_loop()
    
    async def _multi_api_fallback_loop(self):
        """
        ✅ NEUE MULTI-API STRATEGIE:
        Nutzt 3 verschiedene DexScreener Endpoints für maximale Coverage:
        1. Token Profiles API - Brandneue Tokens
        2. Pairs API - Frische Pairs
        3. Search API - Spezifische Queries
        """
        logger.info("🔄 Starte MULTI-API Scanner...")
        logger.info("📡 Nutzt 3 verschiedene Endpoints für maximale Coverage")
        
        # HTTP Session
        session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            },
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
        seen_pairs = set()
        request_count = 0
        last_log_time = time.time()
        
        # ✅ Optimierte Suchbegriffe für Search API
        search_queries = [
            'pump', 'moon', 'pepe', 'doge', 'inu', 'shib', 'elon',
            'wojak', 'bonk', 'floki', 'cat', 'dog', 'rocket',
            'raydium', 'orca', 'meteora',
            'sol', 'solana'
        ]
        query_index = 0
        api_rotation_index = 0  # Rotiert zwischen APIs
        
        try:
            while self.running:
                try:
                    request_count += 1
                    self.stats['http_requests'] = request_count
                    
                    # ✅ ROTIERE ZWISCHEN 3 APIS
                    api_mode = api_rotation_index % 3
                    
                    # ============================================================
                    # API 1: TOKEN PROFILES (Brandneue Tokens)
                    # ============================================================
                    if api_mode == 0:
                        url = "https://api.dexscreener.com/token-profiles/latest/v1"
                        
                        if DEBUG_HTTP_REQUESTS:
                            logger.info(f"🌐 HTTP Request #{request_count}: Token Profiles API")
                        
                        self.stats['api_profiles_calls'] += 1
                        
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # Token Profiles haben unterschiedliche Struktur
                                profiles = data if isinstance(data, list) else []
                                
                                if DEBUG_HTTP_REQUESTS:
                                    logger.info(f"   └─ Status 200: {len(profiles)} Token Profiles gefunden")
                                
                                new_pairs_count = 0
                                
                                for profile in profiles[:30]:  # Max 30
                                    # Extract chain ID and address
                                    chain_id = profile.get('chainId', '')
                                    token_address = profile.get('tokenAddress', '')
                                    
                                    if chain_id != 'solana':
                                        continue
                                    
                                    if not token_address or token_address in seen_pairs:
                                        continue
                                    
                                    # Konvertiere zu Pair-Format
                                    pair_data = {
                                        'chainId': 'solana',
                                        'pairAddress': token_address,  # Nutze Token als Pair
                                        'baseToken': {
                                            'symbol': profile.get('symbol', 'UNKNOWN'),
                                            'address': token_address
                                        },
                                        'pairCreatedAt': int(time.time() * 1000),  # Jetzt
                                        'liquidity': {'usd': 0},
                                        'priceUsd': profile.get('price', 0),
                                        'from_profiles_api': True
                                    }
                                    
                                    seen_pairs.add(token_address)
                                    new_pairs_count += 1
                                    self.stats['pairs_found'] += 1
                                    
                                    symbol = profile.get('symbol', 'UNKNOWN')
                                    logger.info(
                                        f"✨ TOKEN PROFILE: Brandneues Token gefunden: {symbol} "
                                        f"({token_address[:8]}...)"
                                    )
                                    
                                    await self._handle_new_pair(pair_data)
                                
                                if DEBUG_HTTP_REQUESTS and new_pairs_count > 0:
                                    logger.info(f"   ✅ {new_pairs_count} neue Token Profiles verarbeitet")
                            
                            elif response.status == 429:
                                logger.warning("⚠️ Rate Limit - warte 60s")
                                await asyncio.sleep(60)
                                continue
                    
                    # ============================================================
                    # API 2: SOLANA PAIRS (Frische Pairs)
                    # ============================================================
                    elif api_mode == 1:
                        url = "https://api.dexscreener.com/latest/dex/pairs/solana"
                        
                        if DEBUG_HTTP_REQUESTS:
                            logger.info(f"🌐 HTTP Request #{request_count}: Solana Pairs API")
                        
                        self.stats['api_pairs_calls'] += 1
                        
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                pairs = data.get('pairs', [])
                                
                                # ✅ Sortiere nach Alter (neueste zuerst)
                                pairs.sort(key=lambda p: p.get('pairCreatedAt', 0), reverse=True)
                                
                                if DEBUG_HTTP_REQUESTS:
                                    logger.info(f"   └─ Status 200: {len(pairs)} Solana Pairs gefunden")
                                
                                new_pairs_count = 0
                                checked_pairs = 0
                                
                                # Nimm die 50 neuesten
                                for pair in pairs[:50]:
                                    pair_address = pair.get('pairAddress')
                                    if not pair_address or pair_address in seen_pairs:
                                        continue
                                    
                                    checked_pairs += 1
                                    
                                    created_at = pair.get('pairCreatedAt', 0)
                                    if created_at:
                                        age_minutes = (time.time() * 1000 - created_at) / 60000
                                        
                                        symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                                        liquidity = pair.get('liquidity', {}).get('usd', 0)
                                        
                                        # ✅ VERBOSE LOGGING (erste 5)
                                        if DEBUG_HTTP_REQUESTS and checked_pairs <= 5:
                                            logger.info(
                                                f"   📊 Pair: {symbol} | "
                                                f"Alter: {age_minutes:.1f}min | "
                                                f"Liq: ${liquidity:,.0f}"
                                            )
                                        
                                        # ✅ RELAXED Age Filter (50000 min = ~35 Tage)
                                        if age_minutes < 50000:  # Akzeptiert fast alles
                                            seen_pairs.add(pair_address)
                                            new_pairs_count += 1
                                            self.stats['pairs_found'] += 1
                                            
                                            logger.info(
                                                f"✨ PAIRS API: Neues Pair gefunden: {symbol} "
                                                f"(Alter: {age_minutes:.1f}min, Liq: ${liquidity:,.0f})"
                                            )
                                            
                                            await self._handle_new_pair(pair)
                                
                                if DEBUG_HTTP_REQUESTS:
                                    logger.info(
                                        f"   └─ Geprüft: {checked_pairs} Pairs | "
                                        f"Neu: {new_pairs_count}"
                                    )
                            
                            elif response.status == 429:
                                logger.warning("⚠️ Rate Limit - warte 60s")
                                await asyncio.sleep(60)
                                continue
                    
                    # ============================================================
                    # API 3: SEARCH (Spezifische Queries)
                    # ============================================================
                    else:
                        current_query = search_queries[query_index % len(search_queries)]
                        query_index += 1
                        
                        url = "https://api.dexscreener.com/latest/dex/search"
                        params = {'q': current_query}
                        
                        if DEBUG_HTTP_REQUESTS:
                            logger.info(f"🌐 HTTP Request #{request_count}: Searching '{current_query}'")
                        
                        self.stats['api_search_calls'] += 1
                        
                        async with session.get(url, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                pairs = data.get('pairs', [])
                                
                                if DEBUG_HTTP_REQUESTS:
                                    logger.info(f"   └─ Status 200: {len(pairs)} Pairs gefunden")
                                
                                new_pairs_count = 0
                                checked_pairs = 0
                                
                                for pair in pairs:
                                    if pair.get('chainId') != 'solana':
                                        continue
                                    
                                    checked_pairs += 1
                                    
                                    pair_address = pair.get('pairAddress')
                                    if not pair_address or pair_address in seen_pairs:
                                        continue
                                    
                                    created_at = pair.get('pairCreatedAt', 0)
                                    if created_at:
                                        age_minutes = (time.time() * 1000 - created_at) / 60000
                                        
                                        symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                                        liquidity = pair.get('liquidity', {}).get('usd', 0)
                                        
                                        if DEBUG_HTTP_REQUESTS and checked_pairs <= 5:
                                            logger.info(
                                                f"   📊 Pair: {symbol} | "
                                                f"Alter: {age_minutes:.1f}min | "
                                                f"Liq: ${liquidity:,.0f}"
                                            )
                                        
                                        # ✅ RELAXED Age Filter
                                        if age_minutes < 50000:
                                            seen_pairs.add(pair_address)
                                            new_pairs_count += 1
                                            self.stats['pairs_found'] += 1
                                            
                                            logger.info(
                                                f"✨ SEARCH: Neues Pair gefunden: {symbol} "
                                                f"(Alter: {age_minutes:.1f}min, Liq: ${liquidity:,.0f})"
                                            )
                                            
                                            await self._handle_new_pair(pair)
                                
                                if DEBUG_HTTP_REQUESTS:
                                    logger.info(
                                        f"   └─ Geprüft: {checked_pairs} Solana Pairs | "
                                        f"Neu: {new_pairs_count} | "
                                        f"Query: '{current_query}'"
                                    )
                            
                            elif response.status == 429:
                                logger.warning("⚠️ Rate Limit - warte 60s")
                                await asyncio.sleep(60)
                                continue
                    
                    # Rotate API
                    api_rotation_index += 1
                    
                    # ✅ Periodisches Status-Log (alle 60s)
                    current_time = time.time()
                    if current_time - last_log_time > 60:
                        logger.info(
                            f"📊 MULTI-API Scanner Status: "
                            f"Requests={request_count}, "
                            f"Pairs gefunden={self.stats['pairs_found']}, "
                            f"Verarbeitet={self.stats['processed']}, "
                            f"Profiles={self.stats['api_profiles_calls']}, "
                            f"Pairs={self.stats['api_pairs_calls']}, "
                            f"Search={self.stats['api_search_calls']}"
                        )
                        last_log_time = current_time
                    
                    # Cleanup seen_pairs
                    if len(seen_pairs) > 5000:
                        seen_pairs_list = list(seen_pairs)
                        seen_pairs = set(seen_pairs_list[-4000:])
                    
                    # ✅ Warte zwischen Requests (10 Sekunden)
                    await asyncio.sleep(10)
                    
                except asyncio.TimeoutError:
                    logger.error("⏱️ HTTP Request Timeout")
                    await asyncio.sleep(30)
                
                except Exception as e:
                    logger.error(f"❌ Multi-API Error: {e}", exc_info=True)
                    await asyncio.sleep(30)
        
        finally:
            await session.close()
            logger.info("🛑 Multi-API Scanner gestoppt")
    
    async def _http_fallback_loop(self):
        """
        Original HTTP Fallback (Single API)
        Nur Search API mit optimierten Queries
        """
        logger.info("🔄 Starte HTTP Fallback Scanner...")
        logger.info("📡 Polling DexScreener API alle 10 Sekunden für neue Pairs")
        
        session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            },
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
        seen_pairs = set()
        request_count = 0
        
        search_queries = [
            'pump', 'moon', 'pepe', 'doge', 'inu', 'shib', 'elon',
            'wojak', 'bonk', 'floki', 'cat', 'dog', 'rocket',
            'raydium', 'orca', 'meteora',
            'sol', 'solana'
        ]
        query_index = 0
        last_log_time = time.time()
        
        try:
            while self.running:
                try:
                    request_count += 1
                    self.stats['http_requests'] = request_count
                    
                    current_query = search_queries[query_index % len(search_queries)]
                    query_index += 1
                    
                    url = "https://api.dexscreener.com/latest/dex/search"
                    params = {'q': current_query}
                    
                    if DEBUG_HTTP_REQUESTS:
                        logger.info(f"🌐 HTTP Request #{request_count}: Searching '{current_query}'")
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            pairs = data.get('pairs', [])
                            
                            if DEBUG_HTTP_REQUESTS:
                                logger.info(f"   └─ Status 200: {len(pairs)} Pairs gefunden")
                            
                            new_pairs_count = 0
                            checked_pairs = 0
                            
                            for pair in pairs:
                                if pair.get('chainId') != 'solana':
                                    continue
                                
                                checked_pairs += 1
                                
                                pair_address = pair.get('pairAddress')
                                if not pair_address:
                                    continue
                                
                                if pair_address in seen_pairs:
                                    continue
                                
                                created_at = pair.get('pairCreatedAt', 0)
                                if created_at:
                                    age_minutes = (time.time() * 1000 - created_at) / 60000
                                    
                                    symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                                    liquidity = pair.get('liquidity', {}).get('usd', 0)
                                    
                                    if DEBUG_HTTP_REQUESTS and checked_pairs <= 5:
                                        logger.info(
                                            f"   📊 Pair: {symbol} | "
                                            f"Alter: {age_minutes:.1f}min | "
                                            f"Liq: ${liquidity:,.0f}"
                                        )
                                    
                                    # ✅ RELAXED Age Filter (50000 min = ~35 Tage)
                                    if age_minutes < 50000:
                                        seen_pairs.add(pair_address)
                                        new_pairs_count += 1
                                        self.stats['pairs_found'] += 1
                                        
                                        logger.info(
                                            f"✨ HTTP: Neues Pair gefunden: {symbol} "
                                            f"(Alter: {age_minutes:.1f}min, Liq: ${liquidity:,.0f})"
                                        )
                                        
                                        await self._handle_new_pair(pair)
                            
                            if DEBUG_HTTP_REQUESTS:
                                logger.info(
                                    f"   └─ Geprüft: {checked_pairs} Solana Pairs | "
                                    f"Neu: {new_pairs_count} | "
                                    f"Query: '{current_query}'"
                                )
                        
                        elif response.status == 429:
                            logger.warning("⚠️ Rate Limit - warte 60s")
                            await asyncio.sleep(60)
                            continue
                        
                        elif response.status == 403:
                            logger.error("❌ 403 Forbidden")
                            await asyncio.sleep(120)
                            continue
                    
                    # Periodisches Log
                    current_time = time.time()
                    if current_time - last_log_time > 60:
                        logger.info(
                            f"📊 HTTP Scanner Status: "
                            f"Requests={request_count}, "
                            f"Pairs gefunden={self.stats['pairs_found']}, "
                            f"Verarbeitet={self.stats['processed']}"
                        )
                        last_log_time = current_time
                    
                    # Cleanup
                    if len(seen_pairs) > 5000:
                        seen_pairs_list = list(seen_pairs)
                        seen_pairs = set(seen_pairs_list[-4000:])
                    
                    await asyncio.sleep(10)
                    
                except asyncio.TimeoutError:
                    logger.error("⏱️ HTTP Request Timeout")
                    await asyncio.sleep(30)
                
                except Exception as e:
                    logger.error(f"❌ HTTP Error: {e}", exc_info=True)
                    await asyncio.sleep(30)
        
        finally:
            await session.close()
            logger.info("🛑 HTTP Scanner gestoppt")
        
    async def _websocket_loop(self):
        """WebSocket Loop (fallback)"""
        # WebSocket code hier (wie vorher)
        pass
        
    async def _handle_new_pair(self, pair_data: Dict):
        """Verarbeitet ein neues Pair"""
        if pair_data.get('chainId') != 'solana':
            return

        pair_address = pair_data.get('pairAddress')
        if not pair_address:
            return

        # Thread-safe check
        async with self.processed_pairs_lock:
            if pair_address in self.processed_pairs:
                if DEBUG_HTTP_REQUESTS:
                    logger.debug(f"   ⏭️ Pair bereits verarbeitet: {pair_address[:8]}...")
                return

            # Cleanup old entries
            current_time = time.time()
            old_addresses = [
                addr for addr, timestamp in self.processed_pairs.items()
                if current_time - timestamp > self.processed_pairs_max_age
            ]
            for addr in old_addresses:
                del self.processed_pairs[addr]
            
            if len(self.processed_pairs) >= self.processed_pairs_max_size:
                sorted_pairs = sorted(self.processed_pairs.items(), key=lambda x: x[1])
                to_remove = len(sorted_pairs) // 10
                for addr, _ in sorted_pairs[:to_remove]:
                    del self.processed_pairs[addr]
            
            self.processed_pairs[pair_address] = current_time

        symbol = pair_data.get('baseToken', {}).get('symbol', 'UNKNOWN')
        logger.info(f"🎯 Verarbeite Pair: {symbol} ({pair_address[:8]}...)")

        # Berechne Priorität
        priority = self._calculate_priority(pair_data)
        
        priority_pair = PriorityPair(
            priority=-priority,
            pair_data=pair_data
        )
        
        await self.processing_queue.put(priority_pair)
        logger.info(f"   ✅ In Queue eingereiht (Priorität: {priority:.1f})")
        
    def _calculate_priority(self, pair_data: Dict) -> float:
        """Berechnet Priorität"""
        priority = 0.0
        
        liquidity = float(pair_data.get('liquidity', {}).get('usd', 0))
        if 10000 <= liquidity <= 50000:
            priority += 50
        elif 5000 <= liquidity <= 100000:
            priority += 25
            
        age_ms = time.time() * 1000 - pair_data.get('pairCreatedAt', 0)
        if age_ms < 60000:
            priority += 40
        elif age_ms < 300000:
            priority += 20
            
        volume = float(pair_data.get('volume', {}).get('m5', 0))
        if volume > 10000:
            priority += 30
        elif volume > 5000:
            priority += 15
            
        tx_count = int(pair_data.get('txns', {}).get('m5', {}).get('buys', 0))
        if tx_count > 20:
            priority += 20
        elif tx_count > 10:
            priority += 10
            
        return priority
        
    async def _process_worker(self, worker_name: str):
        """Worker Thread"""
        logger.info(f"🚀 {worker_name} gestartet")

        try:
            while self.running:
                try:
                    priority_pair = await asyncio.wait_for(
                        self.processing_queue.get(),
                        timeout=0.5
                    )

                    if not self.running:
                        await self.processing_queue.put(priority_pair)
                        break

                    start_time = time.time()
                    
                    symbol = priority_pair.pair_data.get('baseToken', {}).get('symbol', 'UNKNOWN')
                    logger.info(f"🔬 {worker_name}: Analysiere {symbol}...")

                    # Try integration layer first
                    try:
                        from integration import process_token
                        result = await process_token(priority_pair.pair_data)
                        
                        if result:
                            logger.info(f"   ✅ {symbol}: Analyse erfolgreich!")
                        else:
                            logger.info(f"   ⏭️ {symbol}: Durch Filter gefallen")
                            
                    except ImportError:
                        # Fallback to analyzer
                        from analyzer import analyzer
                        result = await analyzer.analyze_token(priority_pair.pair_data)
                        
                        if result:
                            logger.info(f"   ✅ {symbol}: Analyse erfolgreich!")
                        else:
                            logger.info(f"   ⏭️ {symbol}: Durch Filter gefallen")

                    process_time = time.time() - start_time
                    self.stats['processed'] += 1

                    if process_time > 1:
                        logger.warning(f"⚠️ Langsame Analyse: {process_time:.2f}s")

                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Worker {worker_name} Fehler: {e}", exc_info=True)

        finally:
            logger.info(f"👋 {worker_name} shut down")
                
    async def _stats_reporter(self):
        """Stats Reporter"""
        while self.running:
            await asyncio.sleep(60)

            async with self.processed_pairs_lock:
                cache_size = len(self.processed_pairs)

            logger.info(
                f"📊 Scanner Stats: "
                f"HTTP Requests={self.stats.get('http_requests', 0)}, "
                f"Pairs gefunden={self.stats.get('pairs_found', 0)}, "
                f"Verarbeitet={self.stats['processed']}, "
                f"Queue={self.processing_queue.qsize()}, "
                f"Cache={cache_size}"
            )

            self.stats['received'] = 0
            self.stats['processed'] = 0
            
    async def stop(self, timeout: float = 10.0):
        """Graceful stop"""
        logger.info("🛑 Initiating graceful shutdown...")

        self.running = False

        if self._websocket and not self._websocket.closed:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self._websocket = None

        logger.info(f"Waiting for {len(self.workers)} workers to finish...")

        try:
            await asyncio.wait_for(
                asyncio.gather(*self.workers, return_exceptions=True),
                timeout=timeout
            )
            logger.info("✅ All workers finished gracefully")

        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Workers did not finish in {timeout}s")
            for worker in self.workers:
                if not worker.done():
                    worker.cancel()
            await asyncio.gather(*self.workers, return_exceptions=True)

        if self.message_tasks:
            for task in list(self.message_tasks):
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self.message_tasks, return_exceptions=True)
            self.message_tasks.clear()

        remaining = self.processing_queue.qsize()
        if remaining > 0:
            logger.warning(f"⚠️ {remaining} items left in queue")

        from analyzer import analyzer
        await analyzer.cleanup()

        logger.info("✅ Scanner stopped cleanly")


# Global Scanner Instance
scanner = HighPerformanceScanner()

# Legacy alias
Scanner = HighPerformanceScanner

async def run_scanner_stream():
    """Entry Point für Main"""
    try:
        await scanner.start()
    except Exception as e:
        logger.error(f"Scanner Fatal Error: {e}", exc_info=True)
        await scanner.stop()

