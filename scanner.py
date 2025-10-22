# scanner.py
"""
Ultra-Fast WebSocket Scanner mit Priorisierung und Batch-Processing
"""
import asyncio
import json
import websockets
import time
from typing import Dict, Set, List
from collections import deque
from dataclasses import dataclass, field
import heapq

from config import DEXSCREENER_WSS_URL, ENABLE_SNIPING_MODE
import analyzer
import telegram_bot

@dataclass(order=True)
class PriorityPair:
    """Priorisierte Pair für Processing Queue"""
    priority: float
    pair_data: Dict = field(compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)

class HighPerformanceScanner:
    def __init__(self):
        self.processed_pairs: Set[str] = set()
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
                    
                    print(f"✅ WebSocket verbunden. Subscribing zu {len(subscribe_messages)} Events...")
                    
                    # Subscribe zu allen Events
                    for msg in subscribe_messages:
                        await websocket.send(json.dumps(msg))
                    
                    backoff = 1  # Reset backoff bei erfolgreicher Verbindung
                    
                    # Message Processing Loop
                    async for message in websocket:
                        asyncio.create_task(self._handle_message(message))
                        
            except websockets.exceptions.ConnectionClosed as e:
                print(f"⚠️ WebSocket Verbindung geschlossen: {e}")
            except Exception as e:
                print(f"❌ WebSocket Fehler: {e}")
                
            # Exponential Backoff für Reconnect
            wait_time = min(backoff, 30)
            print(f"🔄 Reconnect in {wait_time} Sekunden...")
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
            print(f"Message Handler Fehler: {e}")
            
    async def _handle_new_pair(self, pair_data: Dict):
        """Verarbeitet neue Pair Events"""
        if not pair_data:
            return
            
        pair_address = pair_data.get('pairAddress', '')
        if not pair_address or pair_address in self.processed_pairs:
            return
            
        # Skip SOL selbst
        base_token = pair_data.get('baseToken', {}).get('address', '')
        if base_token == "So11111111111111111111111111111111111111112":
            return
            
        self.processed_pairs.add(pair_address)
        
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
        """Worker Thread für Pair Processing"""
        print(f"🚀 {worker_name} gestartet")
        
        while self.running:
            try:
                # Warte auf nächstes Pair mit Timeout
                priority_pair = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=1.0
                )
                
                # Analysiere Pair
                start_time = time.time()
                await analyzer.analyze_streamed_pair(priority_pair.pair_data)
                
                process_time = time.time() - start_time
                self.stats['processed'] += 1
                
                if process_time > 1:
                    print(f"⚠️ Langsame Analyse: {process_time:.2f}s")
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Worker {worker_name} Fehler: {e}")
                
    async def _stats_reporter(self):
        """Zeigt regelmäßig Statistiken"""
        while self.running:
            await asyncio.sleep(60)  # Jede Minute
            
            print(f"""
            📊 Scanner Statistiken (1 Min):
            Empfangen: {self.stats['received']}
            Verarbeitet: {self.stats['processed']}
            Queue: {self.processing_queue.qsize()}
            Cache: {len(self.processed_pairs)} Pairs
            """)
            
            # Reset Stats
            self.stats['received'] = 0
            self.stats['processed'] = 0
            
    async def stop(self):
        """Stoppt Scanner sauber"""
        print("🛑 Stopping Scanner...")
        self.running = False
        
        # Warte auf Worker
        for worker in self.workers:
            worker.cancel()
            
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Cleanup
        await analyzer.analyzer.cleanup()

# Globale Scanner Instanz
scanner = HighPerformanceScanner()

async def run_scanner_stream():
    """Entry Point für Main"""
    try:
        await scanner.start()
    except Exception as e:
        print(f"Scanner Fatal Error: {e}")
        await scanner.stop()