#!/usr/bin/env python3
"""
Optimierter Scanner für NEUE Solana Pairs
Verwendet bessere API Endpoints
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Set, Optional
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NewPairsScanner:
    """Scanner optimiert für brandneue Pairs"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_pairs: Set[str] = set()
        self.running = False
        
    async def start(self, callback):
        """Startet Scanner"""
        self.running = True
        
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            },
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
        logger.info("🚀 Neuer Pairs Scanner gestartet!")
        logger.info("🎯 Suche nach brandneuen Solana Memecoins...")
        
        try:
            while self.running:
                # Methode 1: Suche nach spezifischen neuen Tokens
                await self._scan_new_tokens(callback)
                
                # Methode 2: Checke beliebte DEXes
                await self._scan_dex_pairs(callback)
                
                await asyncio.sleep(10)  # Alle 10 Sekunden
                
        except KeyboardInterrupt:
            logger.info("⚠️ Gestoppt")
        finally:
            if self.session:
                await self.session.close()
    
    async def _scan_new_tokens(self, callback):
        """Scannt nach neuen Tokens mit besserer Query"""
        
        # Verschiedene Suchbegriffe die oft in neuen Memecoins vorkommen
        search_terms = ['pump', 'moon', 'inu', 'pepe', 'doge', 'cat', 'bonk']
        
        for term in search_terms[:2]:  # Nur 2 pro Durchlauf
            try:
                url = f"https://api.dexscreener.com/latest/dex/search"
                params = {'q': term}
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        # Filter Solana + neu
                        new_count = 0
                        for pair in pairs:
                            if pair.get('chainId') != 'solana':
                                continue
                            
                            pair_address = pair.get('pairAddress')
                            if not pair_address or pair_address in self.seen_pairs:
                                continue
                            
                            created_at = pair.get('pairCreatedAt', 0)
                            if created_at:
                                age_minutes = (time.time() * 1000 - created_at) / 60000
                                
                                if age_minutes < 60:  # Jünger als 1 Stunde
                                    symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                                    liquidity = pair.get('liquidity', {}).get('usd', 0)
                                    
                                    logger.info(f"✨ GEFUNDEN: {symbol} (Alter: {age_minutes:.1f}min, "
                                              f"Liq: ${liquidity:,.0f})")
                                    
                                    self.seen_pairs.add(pair_address)
                                    new_count += 1
                                    await callback(pair)
                        
                        if new_count > 0:
                            logger.info(f"   └─ {new_count} neue Pairs aus '{term}' Suche")
                    
                    elif response.status == 429:
                        logger.warning("⚠️ Rate Limited - warte...")
                        await asyncio.sleep(30)
                        break
                
                await asyncio.sleep(2)  # Pause zwischen Suchen
                
            except Exception as e:
                logger.error(f"Error bei '{term}': {e}")
    
    async def _scan_dex_pairs(self, callback):
        """Scannt spezifische DEX Pairs"""
        
        # Beliebte Solana DEXes
        dexes = ['raydium', 'orca', 'meteora']
        
        for dex in dexes[:1]:  # Nur 1 pro Durchlauf
            try:
                # Suche nach DEX-spezifischen Pairs
                url = f"https://api.dexscreener.com/latest/dex/search"
                params = {'q': dex}
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get('pairs', [])
                        
                        # Filter nur Solana + sehr neue
                        for pair in pairs[:10]:  # Top 10
                            if pair.get('chainId') != 'solana':
                                continue
                            
                            pair_address = pair.get('pairAddress')
                            if not pair_address or pair_address in self.seen_pairs:
                                continue
                            
                            created_at = pair.get('pairCreatedAt', 0)
                            if created_at:
                                age_minutes = (time.time() * 1000 - created_at) / 60000
                                
                                if age_minutes < 120:  # Jünger als 2 Stunden
                                    symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
                                    liquidity = pair.get('liquidity', {}).get('usd', 0)
                                    
                                    logger.info(f"🎯 {dex.upper()}: {symbol} (Alter: {age_minutes:.1f}min)")
                                    
                                    self.seen_pairs.add(pair_address)
                                    await callback(pair)
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error bei {dex}: {e}")
    
    async def stop(self):
        self.running = False
        if self.session:
            await self.session.close()


async def main():
    scanner = NewPairsScanner()
    
    async def handle_pair(pair: Dict):
        symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
        address = pair.get('pairAddress', '')[:8]
        liquidity = pair.get('liquidity', {}).get('usd', 0)
        
        print(f"\n{'='*60}")
        print(f"🚨 NEUES PAIR ERKANNT!")
        print(f"   Symbol: {symbol}")
        print(f"   Pair: {address}...")
        print(f"   Liquidity: ${liquidity:,.0f}")
        print(f"{'='*60}\n")
    
    await scanner.start(handle_pair)


if __name__ == "__main__":
    asyncio.run(main())
