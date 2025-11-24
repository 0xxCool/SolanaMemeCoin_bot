# dexscreener_http_scanner.py
"""
Alternative Scanner-Implementierung mit HTTP Polling statt WebSocket
Umgeht das 403 Problem komplett
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Set, List, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class DexScreenerHTTPScanner:
    """
    Scanner der die öffentliche DexScreener REST API verwendet
    VORTEIL: Kein WebSocket = Kein Cloudflare Problem
    NACHTEIL: Nicht Echtzeit, aber für neue Pairs ausreichend
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_pairs: Set[str] = set()
        self.running = False
        self.base_url = "https://api.dexscreener.com/latest/dex"
        
        # Tracking
        self.last_check = datetime.now()
        self.pairs_found = 0
        
    async def start(self, callback):
        """
        Startet Scanner mit HTTP Polling
        
        Args:
            callback: Async function(pair_data) für gefundene Pairs
        """
        self.running = True
        
        # Erstelle Session mit realistischen Headers
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://dexscreener.com/',
            },
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
        logger.info("🔍 HTTP Scanner gestartet - Polling für neue Pairs...")
        
        try:
            while self.running:
                await self._scan_new_pairs(callback)
                
                # Polling-Intervall: 3-5 Sekunden (nicht zu aggressiv wegen Rate Limiting)
                await asyncio.sleep(3)
                
        finally:
            if self.session:
                await self.session.close()
    
    async def _scan_new_pairs(self, callback):
        """Scannt nach neuen Pairs"""
        
        try:
            # Methode 1: Search API mit Solana Filter
            url = f"{self.base_url}/search?q=solana"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    pairs = data.get('pairs', [])
                    new_pairs = 0
                    
                    for pair in pairs:
                        pair_address = pair.get('pairAddress')
                        
                        # Nur neue Pairs
                        if pair_address and pair_address not in self.seen_pairs:
                            
                            # Check ob wirklich neu (< 10 Minuten)
                            created_at = pair.get('pairCreatedAt', 0)
                            age_minutes = (time.time() * 1000 - created_at) / 60000
                            
                            if age_minutes < 10:  # Nur sehr neue Pairs
                                self.seen_pairs.add(pair_address)
                                new_pairs += 1
                                self.pairs_found += 1
                                
                                # Callback mit Pair-Daten
                                await callback(pair)
                    
                    if new_pairs > 0:
                        logger.info(f"✨ {new_pairs} neue Pairs gefunden (Total: {self.pairs_found})")
                
                elif response.status == 429:
                    logger.warning("⚠️ Rate Limit erreicht - warte 30 Sekunden")
                    await asyncio.sleep(30)
                
                else:
                    logger.warning(f"⚠️ HTTP {response.status}")
        
        except Exception as e:
            logger.error(f"Scan error: {e}")
    
    async def _get_pair_details(self, chain: str, pair_address: str) -> Optional[Dict]:
        """Holt detaillierte Pair-Informationen"""
        url = f"{self.base_url}/pairs/{chain}/{pair_address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('pair')
        except Exception as e:
            logger.error(f"Error getting pair details: {e}")
        
        return None
    
    async def stop(self):
        """Stoppe Scanner"""
        logger.info("🛑 Stoppe HTTP Scanner...")
        self.running = False
        
        if self.session:
            await self.session.close()


# ============================================================================
# METHODE 2: Token-specific Monitoring
# ============================================================================

class TokenMonitor:
    """
    Monitort spezifische Tokens für Trading-Signale
    Ergänzung zum Pair Scanner
    """
    
    def __init__(self):
        self.session = None
        self.monitored_tokens: Set[str] = set()
    
    async def add_token(self, token_address: str):
        """Füge Token zum Monitoring hinzu"""
        self.monitored_tokens.add(token_address)
        logger.info(f"📍 Monitoring Token: {token_address[:8]}...")
    
    async def get_token_data(self, token_address: str) -> Optional[Dict]:
        """Holt aktuelle Token-Daten"""
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Gibt alle Pairs für diesen Token zurück
                    return data.get('pairs', [])
        except Exception as e:
            logger.error(f"Error getting token data: {e}")
        
        return None
    
    async def monitor_loop(self, callback):
        """Monitort alle tracked Tokens"""
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'},
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
        try:
            while True:
                for token in list(self.monitored_tokens):
                    pairs = await self.get_token_data(token)
                    
                    if pairs:
                        for pair in pairs:
                            await callback(pair)
                
                await asyncio.sleep(5)  # Check alle 5 Sekunden
        
        finally:
            await self.session.close()


# ============================================================================
# METHODE 3: DEX-Aggregator APIs (Backup)
# ============================================================================

class AlternativeDataSources:
    """
    Weitere Datenquellen als Backup zu DexScreener
    """
    
    @staticmethod
    async def birdeye_new_tokens():
        """BirdEye API für neue Solana Tokens"""
        # Erfordert API Key
        url = "https://public-api.birdeye.so/defi/v2/tokens/new"
        # Implementation...
    
    @staticmethod
    async def jupiter_tokens():
        """Jupiter Token List"""
        url = "https://token.jup.ag/strict"
        # Implementation...
    
    @staticmethod
    async def coingecko_new_listings():
        """CoinGecko für neue Listings"""
        url = "https://api.coingecko.com/api/v3/coins/list/new"
        # Implementation...


# ============================================================================
# HYBRID SCANNER: Kombiniert mehrere Methoden
# ============================================================================

class HybridDataScanner:
    """
    Kombiniert HTTP Polling + Token Monitoring + Alternative Sources
    """
    
    def __init__(self):
        self.http_scanner = DexScreenerHTTPScanner()
        self.token_monitor = TokenMonitor()
        self.callback = None
    
    async def start(self, callback):
        """Startet alle Scanner parallel"""
        self.callback = callback
        
        tasks = [
            self.http_scanner.start(self._handle_new_pair),
            self.token_monitor.monitor_loop(callback),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _handle_new_pair(self, pair_data: Dict):
        """Handle neue Pairs und füge zum Monitoring hinzu"""
        # Callback für weitere Analyse
        await self.callback(pair_data)
        
        # Füge Token zum Monitoring hinzu
        token_address = pair_data.get('baseToken', {}).get('address')
        if token_address:
            await self.token_monitor.add_token(token_address)


# ============================================================================
# INTEGRATION
# ============================================================================

async def replace_websocket_scanner():
    """
    Ersetze den bestehenden WebSocket Scanner
    """
    
    scanner = DexScreenerHTTPScanner()
    
    async def process_pair(pair_data: Dict):
        """Integriere mit bestehendem Analyzer"""
        from analyzer import analyzer
        await analyzer.analyze_token(pair_data)
    
    await scanner.start(process_pair)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    async def main():
        scanner = DexScreenerHTTPScanner()
        
        async def print_pair(pair):
            symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
            liquidity = pair.get('liquidity', {}).get('usd', 0)
            print(f"📊 New Pair: {symbol} | Liquidity: ${liquidity:,.0f}")
        
        await scanner.start(print_pair)
    
    asyncio.run(main())
