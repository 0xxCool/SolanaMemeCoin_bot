# scanner.py
"""
Ultra-Fast WebSocket Scanner mit Priorisierung und Batch-Processing
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

from config import DEXSCREENER_WSS_URL, ENABLE_SNIPING_MODE
import analyzer
import telegram_bot

# ✅ Setup logging
logger = logging.getLogger(__name__)

@dataclass(order=True)
class PriorityPair:
    """Priorisierte Pair für Processing Queue"""
    priority: float
    pair_data: Dict = field(compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)

class HighPerformanceScanner:
    def __init__(self):
        # ✅ Use Dict with timestamps instead of Set to prevent memory leak
        self.processed_pairs: Dict[str, float] = {}  # address -> timestamp
        self.processed_pairs_max_size = 10000  # Keep last 10k
        self.processed_pairs_max_age = 3600   # 1 hour
        self.processing_queue = asyncio.Queue(maxsize=1000)
        self.priority_queue: List[PriorityPair] = []
        self.workers: List[asyncio.Task] = []
        self.stats = {
            'received': 0,
            'processed': 0,
            'filtered': 0,
            'alerts_sent': 0
        }
        self.running = False
        
    async def start(self):
        """Startet Scanner mit mehreren Worker-Threads"""
        self.running = True
        
        # Starte Worker für parallele Verarbeitung
        num_workers = 5  # 5 parallele Analyzer
        for i in range(num_workers):
            worker = asyncio.create_task(self._process_worker(f"Worker-{i}"))
            self.workers.append(worker)
            
        # Starte Stats Reporter
        asyncio.create_task(self._stats_reporter())
        
        # Starte WebSocket Connection
        await self._websocket_loop()
        
    async def _websocket_loop(self):
        """Haupt WebSocket Loop mit Auto-Reconnect"""
        subscribe_messages = [
            {
                "method": "subscribe",
                "params": ["newPairs", "solana"]
            }
        ]
        
        # Im Sniping Mode auch auf Liquidity Events hören
        if ENABLE_SNIPING_MODE:
            subscribe_messages.append({
                "method": "subscribe", 
                "params": ["liquidityEvents", "solana"]
            })
        
        backoff = 1
        
        while self.running:
            try:
                async with websockets.connect(
                    DEXSCREENER_WSS_URL,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ) as websocket:

                    logger.info(f"✅ WebSocket verbunden. Subscribing zu {len(subscribe_messages)} Events...")

                    # Subscribe zu allen Events
                    for msg in subscribe_messages:
                        await websocket.send(json.dumps(msg))

                    backoff = 1  # Reset backoff bei erfolgreicher Verbindung

                    # Message Processing Loop
                    async for message in websocket:
                        asyncio.create_task(self._handle_message(message))

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"⚠️ WebSocket Verbindung geschlossen: {e}")
            except Exception as e:
                logger.error(f"❌ WebSocket Fehler: {e}", exc_info=True)

            # Exponential Backoff für Reconnect
            wait_time = min(backoff, 30)
            logger.info(f"🔄 Reconnect in {wait_time} Sekunden...")
            await asyncio.sleep(wait_time)
            backoff *= 2
            
    async def _handle_message(self, message: str):
        """Verarbeitet eingehende WebSocket Messages"""
        try:
            data = json.loads(message)
            self.stats['received'] += 1
            
            # Verschiedene Event Types
            event_type = data.get('type', '')
            
            if event_type == 'pair' and data.get('network') == 'solana':
                await self._handle_new_pair(data.get('pair', {}))
                
            elif event_type == 'liquidityAdd' and ENABLE_SNIPING_MODE:
                # Liquidity Add Events für Ultra-Early Detection
                await self._handle_liquidity_event(data)
                
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Message Handler Fehler: {e}", exc_info=True)
            
    def _add_processed_pair(self, pair_address: str):
        """Add pair to processed cache with size/age management"""
        current_time = time.time()

        # Clean old entries if needed
        if len(self.processed_pairs) >= self.processed_pairs_max_size:
            self._cleanup_old_pairs(current_time)

        self.processed_pairs[pair_address] = current_time

    def _cleanup_old_pairs(self, current_time: float):
        """Remove old entries to prevent memory leak"""
        # Remove entries older than max_age
        to_remove = [
            addr for addr, ts in self.processed_pairs.items()
            if current_time - ts > self.processed_pairs_max_age
        ]

        for addr in to_remove:
            del self.processed_pairs[addr]

        # If still too many, remove oldest 20%
        if len(self.processed_pairs) >= self.processed_pairs_max_size:
            sorted_pairs = sorted(
                self.processed_pairs.items(),
                key=lambda x: x[1]
            )
            remove_count = len(sorted_pairs) // 5  # Remove 20%
            for addr, _ in sorted_pairs[:remove_count]:
                del self.processed_pairs[addr]

    def _is_already_processed(self, pair_address: str) -> bool:
        """Check if pair was already processed"""
        if pair_address in self.processed_pairs:
            return True
        return False

    async def _handle_new_pair(self, pair_data: Dict):
        """Verarbeitet neue Pair Events"""
        if not pair_data:
            return

        pair_address = pair_data.get('pairAddress', '')
        if not pair_address or self._is_already_processed(pair_address):  # ✅ Use new method
            return

        # Skip SOL selbst
        base_token = pair_data.get('baseToken', {}).get('address', '')
        if base_token == "So11111111111111111111111111111111111111112":
            return

        self._add_processed_pair(pair_address)  # ✅ Use new method
        
        # Schnelle Vor-Priorisierung basierend auf Liquidität
        liquidity = float(pair_data.get('liquidity', {}).get('usd', 0))
        
        # Priority Score (höher = besser)
        priority = self._calculate_priority(pair_data)
        
        # In Priority Queue einreihen
        priority_pair = PriorityPair(
            priority=-priority,  # Negative für Max-Heap Verhalten
            pair_data=pair_data
        )
        
        await self.processing_queue.put(priority_pair)
        
    async def _handle_liquidity_event(self, event_data: Dict):
        """Verarbeitet Liquidity Events für frühe Erkennung"""
        # Implementierung für Ultra-Early Detection
        # Kann Token erkennen bevor sie auf DexScreener erscheinen
        pass
        
    def _calculate_priority(self, pair_data: Dict) -> float:
        """
        Berechnet Priorität für Processing Queue
        Höhere Werte = höhere Priorität
        """
        priority = 0.0
        
        # Liquidität (Sweet Spot: 10k-50k)
        liquidity = float(pair_data.get('liquidity', {}).get('usd', 0))
        if 10000 <= liquidity <= 50000:
            priority += 50
        elif 5000 <= liquidity <= 100000:
            priority += 25
            
        # Alter (je neuer desto besser)
        age_ms = time.time() * 1000 - pair_data.get('pairCreatedAt', 0)
        if age_ms < 60000:  # < 1 Minute
            priority += 40
        elif age_ms < 300000:  # < 5 Minuten
            priority += 20
            
        # Volume (frühe Aktivität ist gut)
        volume = float(pair_data.get('volume', {}).get('m5', 0))
        if volume > 10000:
            priority += 30
        elif volume > 5000:
            priority += 15
            
        # Transaction Count
        tx_count = int(pair_data.get('txns', {}).get('m5', {}).get('buys', 0))
        if tx_count > 20:
            priority += 20
        elif tx_count > 10:
            priority += 10
            
        return priority
        
    async def _process_worker(self, worker_name: str):
        """Worker Thread mit graceful shutdown"""
        logger.info(f"🚀 {worker_name} gestartet")

        try:
            while self.running:
                try:
                    # ✅ Shorter timeout to check self.running more frequently
                    priority_pair = await asyncio.wait_for(
                        self.processing_queue.get(),
                        timeout=0.5  # Reduced from 1.0
                    )

                    # Check if still running before processing
                    if not self.running:
                        logger.info(f"{worker_name} stopping, putting item back in queue")
                        await self.processing_queue.put(priority_pair)
                        break

                    # Analysiere Pair (mit Integration Layer)
                    start_time = time.time()

                    # Try using integration layer first (includes AI & Auto-Trading)
                    try:
                        from integration import process_token
                        await process_token(priority_pair.pair_data)
                    except ImportError:
                        # Fallback to traditional analyzer
                        await analyzer.analyze_streamed_pair(priority_pair.pair_data)

                    process_time = time.time() - start_time
                    self.stats['processed'] += 1

                    if process_time > 1:
                        logger.warning(f"⚠️ Langsame Analyse: {process_time:.2f}s")

                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    logger.info(f"{worker_name} cancelled")
                    break
                except Exception as e:
                    logger.error(f"Worker {worker_name} Fehler: {e}", exc_info=True)

        finally:
            logger.info(f"👋 {worker_name} shut down")
                
    async def _stats_reporter(self):
        """Zeigt regelmäßig Statistiken"""
        while self.running:
            await asyncio.sleep(60)  # Jede Minute

            logger.info(
                f"📊 Scanner Stats: received={self.stats['received']}, "
                f"processed={self.stats['processed']}, queue={self.processing_queue.qsize()}, "
                f"cache={len(self.processed_pairs)} pairs"
            )

            # Reset Stats
            self.stats['received'] = 0
            self.stats['processed'] = 0
            
    async def stop(self, timeout: float = 10.0):
        """Gracefully stop scanner"""
        logger.info("🛑 Initiating graceful shutdown...")

        # Step 1: Stop accepting new work
        self.running = False

        # Step 2: Wait for workers to finish current tasks
        logger.info(f"Waiting for {len(self.workers)} workers to finish (timeout: {timeout}s)...")

        try:
            # Give workers time to finish current tasks
            await asyncio.wait_for(
                asyncio.gather(*self.workers, return_exceptions=True),
                timeout=timeout
            )
            logger.info("✅ All workers finished gracefully")

        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Workers did not finish in {timeout}s, forcing shutdown")

            # Step 3: Force cancel if timeout
            for worker in self.workers:
                if not worker.done():
                    worker.cancel()

            # Wait for cancellations
            await asyncio.gather(*self.workers, return_exceptions=True)

        # Step 4: Process remaining queue items
        remaining = self.processing_queue.qsize()
        if remaining > 0:
            logger.warning(f"⚠️ {remaining} items left in queue (not processed)")

        # Step 5: Cleanup
        await analyzer.cleanup()

        logger.info("✅ Scanner stopped cleanly")

# Globale Scanner Instanz
scanner = HighPerformanceScanner()

async def run_scanner_stream():
    """Entry Point für Main"""
    try:
        await scanner.start()
    except Exception as e:
        logger.error(f"Scanner Fatal Error: {e}", exc_info=True)
        await scanner.stop()