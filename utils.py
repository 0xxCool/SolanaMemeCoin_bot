# utils.py
"""
Utility Functions und Helpers für den Trading Bot
"""
import asyncio
import time
import hashlib
import hmac
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, ROUND_DOWN
import aiohttp
import orjson
from solders.pubkey import Pubkey
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# FORMATIERUNG & DISPLAY
# ==============================================================================

def format_number(value: float, decimals: int = 2, 
                  use_suffix: bool = True) -> str:
    """
    Formatiert Zahlen für bessere Lesbarkeit
    """
    if use_suffix:
        if value >= 1_000_000:
            return f"{value/1_000_000:.{decimals}f}M"
        elif value >= 1_000:
            return f"{value/1_000:.{decimals}f}K"
    return f"{value:,.{decimals}f}"

def format_percentage(value: float, decimals: int = 2, 
                     show_sign: bool = True) -> str:
    """
    Formatiert Prozentsätze
    """
    if show_sign and value > 0:
        return f"+{value:.{decimals}f}%"
    return f"{value:.{decimals}f}%"

def format_sol_amount(lamports: int) -> str:
    """
    Konvertiert Lamports zu SOL mit Formatierung
    """
    sol = lamports / 1e9
    return f"{sol:.4f} SOL"

def format_time_ago(timestamp: float) -> str:
    """
    Formatiert Zeitstempel zu "vor X Minuten/Stunden"
    """
    diff = time.time() - timestamp
    
    if diff < 60:
        return f"{int(diff)}s ago"
    elif diff < 3600:
        return f"{int(diff/60)}m ago"
    elif diff < 86400:
        return f"{int(diff/3600)}h ago"
    else:
        return f"{int(diff/86400)}d ago"

# ==============================================================================
# VALIDATION & CHECKS
# ==============================================================================

def is_valid_solana_address(address: str) -> bool:
    """
    Validiert Solana Adresse
    """
    try:
        Pubkey.from_string(address)
        return True
    except:
        return False

def is_honeypot_pattern(token_data: Dict) -> bool:
    """
    Erkennt typische Honeypot-Muster
    """
    indicators = 0
    
    # Check für verdächtige Patterns
    if token_data.get('sell_count', 0) == 0 and token_data.get('buy_count', 0) > 10:
        indicators += 2  # Keine Verkäufe = sehr verdächtig
        
    # Extreme Holder Konzentration
    if token_data.get('top_holder_percent', 0) > 50:
        indicators += 1
        
    # Zu perfekte Distribution (oft Fake)
    holders = token_data.get('holders', [])
    if holders and all(h['balance'] == holders[0]['balance'] for h in holders[:10]):
        indicators += 1
        
    return indicators >= 2

def calculate_risk_score(metrics: Dict) -> str:
    """
    Berechnet Risiko-Level basierend auf Metriken
    """
    risk_points = 0
    
    # Liquidität
    if metrics.get('liquidity_usd', 0) < 10000:
        risk_points += 2
    elif metrics.get('liquidity_usd', 0) < 20000:
        risk_points += 1
        
    # Holder
    if metrics.get('holder_count', 0) < 50:
        risk_points += 2
    elif metrics.get('holder_count', 0) < 100:
        risk_points += 1
        
    # Top Holder Concentration
    if metrics.get('top_10_percentage', 100) > 40:
        risk_points += 2
    elif metrics.get('top_10_percentage', 100) > 30:
        risk_points += 1
        
    # Age
    if metrics.get('age_minutes', 0) < 2:
        risk_points += 1
        
    # Risk Level
    if risk_points >= 5:
        return 'EXTREME'
    elif risk_points >= 3:
        return 'HIGH'
    elif risk_points >= 1:
        return 'MEDIUM'
    else:
        return 'LOW'

# ==============================================================================
# CALCULATIONS
# ==============================================================================

def calculate_price_impact(liquidity: float, trade_amount: float) -> float:
    """
    Schätzt Price Impact basierend auf Liquidität
    """
    if liquidity <= 0:
        return 100.0
        
    # Vereinfachte Constant Product Formula
    # Real impact = (trade_amount / (liquidity + trade_amount)) * 100
    impact = (trade_amount / (liquidity * 2)) * 100
    
    # Adjustierung für Slippage
    return min(impact * 1.5, 100.0)

def calculate_optimal_gas(network_congestion: float = 0.5) -> int:
    """
    Berechnet optimale Gas Fees basierend auf Netzwerk-Auslastung
    """
    base_fee = 5000  # Base Priority Fee
    
    if network_congestion > 0.8:
        return base_fee * 4
    elif network_congestion > 0.6:
        return base_fee * 2
    elif network_congestion > 0.4:
        return int(base_fee * 1.5)
    else:
        return base_fee

def calculate_position_size(score: float, risk_tolerance: float = 1.0,
                           wallet_balance: float = 1.0) -> float:
    """
    Berechnet optimale Position Size mit Kelly Criterion
    """
    # Kelly Formula: f = (p * b - q) / b
    # p = Wahrscheinlichkeit zu gewinnen (basierend auf Score)
    # b = Odds (angenommene 2:1)
    # q = Wahrscheinlichkeit zu verlieren
    
    p = min(score / 100, 0.8)  # Max 80% Gewinn-Wahrscheinlichkeit
    q = 1 - p
    b = 2  # 2:1 Reward:Risk Ratio
    
    kelly_fraction = (p * b - q) / b
    kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap bei 25%
    
    # Adjustiere für Risk Tolerance
    position_size = wallet_balance * kelly_fraction * risk_tolerance
    
    # Minimum und Maximum
    return max(0.01, min(position_size, 0.5))

# ==============================================================================
# ASYNC HELPERS
# ==============================================================================

async def retry_async(func, max_retries: int = 3, 
                     delay: float = 1.0, backoff: float = 2.0):
    """
    Retry Wrapper für Async Functions
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (backoff ** attempt)
                logger.warning(f"Retry {attempt + 1}/{max_retries} nach {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Alle {max_retries} Versuche fehlgeschlagen")
                
    raise last_exception

async def run_with_timeout(coro, timeout: float, default=None):
    """
    Führt Coroutine mit Timeout aus
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Timeout nach {timeout}s")
        return default

class RateLimiter:
    """
    Rate Limiter für API Calls
    """
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = asyncio.Lock()
        
    async def acquire(self):
        """Wartet bis ein Call erlaubt ist"""
        async with self.lock:
            now = time.time()
            # Entferne alte Calls
            self.calls = [t for t in self.calls if now - t < self.time_window]
            
            # Warte wenn Limit erreicht
            if len(self.calls) >= self.max_calls:
                sleep_time = self.time_window - (now - self.calls[0]) + 0.1
                await asyncio.sleep(sleep_time)
                return await self.acquire()
                
            self.calls.append(now)

# ==============================================================================
# CACHE & PERFORMANCE
# ==============================================================================

class AsyncCache:
    """
    Async Cache mit TTL
    """
    def __init__(self, ttl: float = 60):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
        
    async def get(self, key: str) -> Optional[Any]:
        """Holt Wert aus Cache"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
        
    async def set(self, key: str, value: Any):
        """Speichert Wert im Cache"""
        self.cache[key] = (value, time.time())
        
    async def clear_expired(self):
        """Entfernt abgelaufene Einträge"""
        now = time.time()
        expired = [k for k, (_, t) in self.cache.items() if now - t >= self.ttl]
        for key in expired:
            del self.cache[key]

# ==============================================================================
# NETWORK & API
# ==============================================================================

async def fetch_with_retry(session: aiohttp.ClientSession, url: str,
                          **kwargs) -> Optional[Dict]:
    """
    Fetch mit automatischem Retry und Error Handling
    """
    for attempt in range(3):
        try:
            async with session.get(url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate Limited
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.warning(f"HTTP {response.status} für {url}")
        except Exception as e:
            logger.error(f"Fetch Error: {e}")
            if attempt < 2:
                await asyncio.sleep(1)
                
    return None

def create_signature(secret: str, payload: str) -> str:
    """
    Erstellt HMAC Signatur für API Calls
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# ==============================================================================
# TRADING HELPERS
# ==============================================================================

def calculate_slippage(current_price: float, entry_price: float) -> float:
    """
    Berechnet tatsächliche Slippage
    """
    if entry_price == 0:
        return 0
    return abs((current_price - entry_price) / entry_price) * 100

def normalize_token_amount(amount: int, decimals: int) -> Decimal:
    """
    Normalisiert Token Amount mit korrekten Decimals
    """
    return Decimal(amount) / Decimal(10 ** decimals)

def denormalize_token_amount(amount: Decimal, decimals: int) -> int:
    """
    Konvertiert zurück zu Raw Amount
    """
    return int(amount * Decimal(10 ** decimals))

@lru_cache(maxsize=128)
def get_token_decimals(token_address: str) -> int:
    """
    Cached Token Decimals Lookup
    """
    # Standard Tokens
    known_tokens = {
        "So11111111111111111111111111111111111111112": 9,  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6,  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,  # USDT
    }
    
    return known_tokens.get(token_address, 9)  # Default 9

# ==============================================================================
# MONITORING & ALERTS
# ==============================================================================

class PerformanceMonitor:
    """
    Überwacht Bot Performance
    """
    def __init__(self):
        self.metrics = {
            'api_calls': 0,
            'api_errors': 0,
            'trades_executed': 0,
            'trades_failed': 0,
            'alerts_sent': 0,
            'positions_monitored': 0,
            'total_profit': 0.0,
            'start_time': time.time()
        }
        
    def increment(self, metric: str, value: float = 1):
        """Erhöht Metrik"""
        if metric in self.metrics:
            self.metrics[metric] += value
            
    def get_uptime(self) -> float:
        """Gibt Uptime in Stunden zurück"""
        return (time.time() - self.metrics['start_time']) / 3600
        
    def get_success_rate(self) -> float:
        """Berechnet Erfolgsrate"""
        total = self.metrics['trades_executed'] + self.metrics['trades_failed']
        if total == 0:
            return 0
        return (self.metrics['trades_executed'] / total) * 100
        
    def get_summary(self) -> Dict:
        """Gibt Zusammenfassung zurück"""
        return {
            'uptime_hours': self.get_uptime(),
            'success_rate': self.get_success_rate(),
            **self.metrics
        }

# Globale Monitor Instanz
monitor = PerformanceMonitor()

# ==============================================================================
# EXPORT
# ==============================================================================

__all__ = [
    'format_number',
    'format_percentage', 
    'format_sol_amount',
    'format_time_ago',
    'is_valid_solana_address',
    'is_honeypot_pattern',
    'calculate_risk_score',
    'calculate_price_impact',
    'calculate_optimal_gas',
    'calculate_position_size',
    'retry_async',
    'run_with_timeout',
    'RateLimiter',
    'AsyncCache',
    'fetch_with_retry',
    'create_signature',
    'calculate_slippage',
    'normalize_token_amount',
    'denormalize_token_amount',
    'get_token_decimals',
    'PerformanceMonitor',
    'monitor'
]