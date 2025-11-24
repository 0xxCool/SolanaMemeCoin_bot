#!/usr/bin/env python3
# dexscreener_http_scanner_debug.py
"""
HTTP Scanner mit ausführlichem Logging für Debugging
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Set, Optional
from datetime import datetime
import time

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DexScreenerHTTPScanner:
    """Scanner mit HTTP Polling und Debug-Output"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_pairs: Set[str] = set()
        self.running = False
        self.base_url = "https://api.dexscreener.com/latest/dex"
        
        # Stats
        self.total_requests = 0
        self.total_pairs_checked = 0
        self.new_pairs_found = 0
        
    async def start(self, callback):
        """Startet Scanner mit HTTP Polling"""
        self.running = True
        
        # Erstelle Session mit Timeout
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'Accept': 'application/json',
            },
            timeout=timeout
        )
        
        logger.info("🔍 HTTP Scanner gestartet - Polling für neue Pairs...")
        logger.info("⏰ Checking alle 5 Sekunden...")
        
        try:
            while self.running:
                await self._scan_new_pairs(callback)
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("⚠️ Scanner gestoppt durch User")
        finally:
            if self.session:
                await self.session.close()
    
    async def _scan_new_pairs(self, callback):
        """Scannt nach neuen Pairs mit ausführlichem Logging"""
        
        try:
            self.total_requests += 1
            
            url = f"{self.base_url}/search"
            params = {'q': 'SOL'}
            
            logger.info(f"🌐 Request #{self.total_requests}: {url}")
            
            async with self.session.get(url, params=params) as response:
                logger.info(f"   └─ Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    pairs = data.get('pairs', [])
                    
                    logger.info(f"   └─ Gefunden: {len(pairs)} Pairs total")
                    
                    solana_pairs = [p for p in pairs if p.get('chainId') == 'solana']
                    logger.info(f"   └─ Davon Solana: {len(solana_pairs)} Pairs")
                    
                    new_pairs = 0
                    checked = 0
                    
                    for pair in solana_pairs:
                        checked += 1
                        pair_address = pair.get('pairAddress')
                        
                        if not pair_address:
                            continue
                        
                        if pair_address not in self.seen_pairs:
                            created_at = pair.get('pairCreatedAt', 0)
                            if created_at:
                                age_minutes = (time.time() * 1000 - created_at) / 60000
                                
                                symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                                liquidity = pair.get('liquidity', {}).get('usd', 0)
                                
                                logger.info(f"   📊 Neues Pair (Alter: {age_minutes:.1f}min): "
                                          f"{symbol} | Liquidity: ${liquidity:,.0f}")
                                
                                if age_minutes < 30:
                                    self.seen_pairs.add(pair_address)
                                    new_pairs += 1
                                    self.new_pairs_found += 1
                                    await callback(pair)
                                    logger.info(f"   ✨ -> VERARBEITET (jung genug!)")
                                else:
                                    logger.info(f"   ⏭️ -> ÜBERSPRUNGEN (zu alt)")
                    
                    self.total_pairs_checked += checked
                    
                    if new_pairs > 0:
                        logger.info(f"✅ {new_pairs} neue Pairs zur Analyse weitergeleitet")
                    else:
                        logger.info(f"ℹ️ Keine neuen jungen Pairs (<30min) gefunden")
                    
                    logger.info(f"📊 Stats: Requests={self.total_requests}, "
                              f"Checked={self.total_pairs_checked}, "
                              f"Found={self.new_pairs_found}")
                
                elif response.status == 429:
                    logger.warning("⚠️ Rate Limit erreicht - warte 60 Sekunden")
                    await asyncio.sleep(60)
                
                elif response.status == 403:
                    logger.error("❌ 403 Forbidden - Auch HTTP API ist blockiert!")
                
                else:
                    logger.warning(f"⚠️ HTTP {response.status}")
        
        except asyncio.TimeoutError:
            logger.error("⏱️ Request Timeout")
        
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
    
    async def stop(self):
        """Stoppe Scanner"""
        logger.info("🛑 Stoppe HTTP Scanner...")
        self.running = False
        if self.session:
            await self.session.close()


async def quick_api_test():
    """Schneller Test ob DexScreener API funktioniert"""
    
    logger.info("🧪 Schnelltest: DexScreener API Erreichbarkeit")
    logger.info("="*60)
    
    test_urls = [
        ("Search API", "https://api.dexscreener.com/latest/dex/search?q=SOL"),
        ("Pairs API", "https://api.dexscreener.com/latest/dex/pairs/solana"),
    ]
    
    async with aiohttp.ClientSession() as session:
        for name, url in test_urls:
            try:
                logger.info(f"\n📡 Teste {name}...")
                logger.info(f"   URL: {url[:70]}...")
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    status = response.status
                    
                    if status == 200:
                        data = await response.json()
                        if 'pairs' in data:
                            count = len(data.get('pairs', []))
                            logger.info(f"   ✅ Status {status} - {count} Pairs gefunden")
                        else:
                            logger.info(f"   ✅ Status {status} - Response erhalten")
                    elif status == 403:
                        logger.error(f"   ❌ Status {status} - BLOCKIERT!")
                    elif status == 429:
                        logger.warning(f"   ⚠️ Status {status} - Rate Limited")
                    else:
                        logger.warning(f"   ⚠️ Status {status}")
                
                await asyncio.sleep(1)
                
            except asyncio.TimeoutError:
                logger.error(f"   ⏱️ Timeout")
            except Exception as e:
                logger.error(f"   ❌ Error: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("🧪 API-Test abgeschlossen\n")


async def test_scanner():
    """Test-Funktion"""
    scanner = DexScreenerHTTPScanner()
    
    async def print_pair(pair: Dict):
        symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
        liquidity = pair.get('liquidity', {}).get('usd', 0)
        print(f"\n{'='*60}")
        print(f"🎯 NEUES PAIR: {symbol} | Liquidity: ${liquidity:,.0f}")
        print(f"{'='*60}\n")
    
    try:
        await scanner.start(print_pair)
    except KeyboardInterrupt:
        await scanner.stop()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        asyncio.run(quick_api_test())
    else:
        asyncio.run(test_scanner())
