# config.py
"""
High-Performance Solana Trading Bot - Erweiterte Konfiguration
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ==============================================================================
# API & RPC ENDPOINTS
# ==============================================================================
DEXSCREENER_WSS_URL = "wss://api.dexscreener.com/pair/realtime"
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
# Backup RPCs für Failover
BACKUP_RPC_URLS = [
    "https://solana-api.projectserum.com",
    "https://api.mainnet-beta.solana.com"
]

# API Endpoints
RUGCHECK_API_URL = "https://api.rugcheck.xyz/v1/tokens/{}/report"
JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
BIRDEYE_API = "https://public-api.birdeye.so/public/token_overview"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/{}"

# ==============================================================================
# SCANNER FILTER - MEHRSTUFIG
# ==============================================================================
@dataclass
class ScannerFilters:
    # Stufe 1: Basis-Filter (sehr schnell)
    MIN_LIQUIDITY_USD: float = 5000
    MAX_LIQUIDITY_USD: float = 500000  # Zu hohe Liquidität = weniger Gewinnpotential
    MIN_AGE_MINUTES: float = 0.5  # Mindestens 30 Sekunden alt
    MAX_AGE_MINUTES: float = 10   # Maximal 10 Minuten alt
    
    # Stufe 2: Token-Metriken
    MIN_HOLDER_COUNT: int = 50
    MAX_HOLDER_COUNT: int = 5000  # Zu viele Holder = bereits zu spät
    MAX_TOP_10_PERCENTAGE: float = 30  # Max 30% bei Top 10 Holdern
    MIN_LP_PERCENTAGE: float = 90  # Mindestens 90% der Liquidität im LP
    
    # Stufe 3: Erweiterte Analyse
    MIN_VOLUME_USD: float = 10000  # Mindestvolumen in 5 Minuten
    MIN_TXS_COUNT: int = 20  # Mindestens 20 Transaktionen
    MAX_PRICE_IMPACT_PERCENT: float = 2  # Max 2% Price Impact für unseren Trade
    MIN_SCORE: float = 70  # Minimum Score aus allen Metriken

# ==============================================================================
# TRADING PARAMETER
# ==============================================================================
@dataclass
class TradingConfig:
    # Position Sizing - Dynamisch basierend auf Score
    BASE_TRADE_AMOUNT_SOL: float = 0.05  # Basis-Betrag
    MAX_TRADE_AMOUNT_SOL: float = 0.5    # Maximum bei perfektem Score
    POSITION_SCALING: Dict[str, float] = None  # Score -> Multiplikator
    
    # Slippage - Dynamisch basierend auf Liquidität
    MIN_SLIPPAGE_BPS: int = 100  # 1% Minimum
    MAX_SLIPPAGE_BPS: int = 500  # 5% Maximum
    
    # Transaction Settings
    PRIORITY_FEE_LAMPORTS: int = 50000  # Priority Fee für schnellere Ausführung
    MAX_RETRIES: int = 3  # Maximale Wiederholungen bei Fehler
    RETRY_DELAY_MS: int = 500  # Verzögerung zwischen Retries
    
    # MEV Protection
    USE_MEV_PROTECTION: bool = True
    JITO_TIP_LAMPORTS: int = 10000  # Tip für Jito Bundle

    def __post_init__(self):
        if self.POSITION_SCALING is None:
            self.POSITION_SCALING = {
                90: 3.0,   # Score 90-100: 3x Basis
                80: 2.0,   # Score 80-89: 2x Basis
                70: 1.0,   # Score 70-79: 1x Basis
            }

# ==============================================================================
# PROFIT MANAGEMENT - INTELLIGENTE STRATEGIE
# ==============================================================================
@dataclass
class ProfitStrategy:
    # Multi-Level Take Profit mit dynamischen Zielen
    TAKE_PROFIT_LEVELS: List[Tuple[float, float]] = None  # [(multiplier, sell_percentage)]
    
    # Trailing Stop Loss - Adaptiv
    INITIAL_STOP_LOSS: float = 15  # Initial 15% Stop Loss
    TRAILING_ACTIVATION: float = 1.5  # Aktiviert bei 50% Gewinn
    TRAILING_PERCENTAGE: float = 20  # 20% vom Höchststand
    
    # Smart Exit Conditions
    VOLUME_DROP_THRESHOLD: float = 70  # Exit wenn Volume 70% fällt
    MOMENTUM_THRESHOLD: float = -5  # Exit bei -5% in 30 Sekunden
    MAX_HOLD_TIME_MINUTES: float = 60  # Maximale Haltezeit
    
    # Position Management
    PARTIAL_EXIT_ON_RESISTANCE: bool = True
    PYRAMID_ON_STRENGTH: bool = True  # Nachkaufen bei starker Performance
    MAX_PYRAMID_ENTRIES: int = 2

    def __post_init__(self):
        if self.TAKE_PROFIT_LEVELS is None:
            self.TAKE_PROFIT_LEVELS = [
                (1.5, 0.25),   # 50% Gewinn: Verkaufe 25%
                (2.0, 0.25),   # 100% Gewinn: Verkaufe weitere 25%
                (3.0, 0.25),   # 200% Gewinn: Verkaufe weitere 25%
                (5.0, 0.15),   # 400% Gewinn: Verkaufe weitere 15%
                # 10% bleiben für Moonshot
            ]

# ==============================================================================
# SCORING SYSTEM - GEWICHTETE BEWERTUNG
# ==============================================================================
@dataclass
class ScoringWeights:
    LIQUIDITY: float = 15
    HOLDERS: float = 20
    DISTRIBUTION: float = 25  # Wie gut verteilt
    VOLUME: float = 15
    MOMENTUM: float = 10
    SECURITY: float = 15
    
    def calculate_score(self, metrics: Dict) -> float:
        """Berechnet einen gewichteten Score von 0-100"""
        score = 0
        
        # Liquidität (optimal: 20k-100k)
        liq = metrics.get('liquidity_usd', 0)
        if 20000 <= liq <= 100000:
            score += self.LIQUIDITY
        elif 10000 <= liq <= 200000:
            score += self.LIQUIDITY * 0.5
            
        # Holder (optimal: 100-1000)
        holders = metrics.get('holder_count', 0)
        if 100 <= holders <= 1000:
            score += self.HOLDERS
        elif 50 <= holders <= 2000:
            score += self.HOLDERS * 0.5
            
        # Distribution (je niedriger top_10, desto besser)
        top_10 = metrics.get('top_10_percentage', 100)
        if top_10 < 20:
            score += self.DISTRIBUTION
        elif top_10 < 30:
            score += self.DISTRIBUTION * 0.7
        elif top_10 < 40:
            score += self.DISTRIBUTION * 0.4
            
        # Volume/Liquidity Ratio
        vol_liq_ratio = metrics.get('volume_usd', 0) / max(liq, 1)
        if vol_liq_ratio > 0.5:
            score += self.VOLUME
        elif vol_liq_ratio > 0.2:
            score += self.VOLUME * 0.5
            
        # Price Momentum (positive Bewegung)
        momentum = metrics.get('price_change_5m', 0)
        if 5 <= momentum <= 50:
            score += self.MOMENTUM
        elif 0 <= momentum <= 100:
            score += self.MOMENTUM * 0.5
            
        # Security Score
        risk = metrics.get('risk_level', 'high')
        if risk == 'low':
            score += self.SECURITY
        elif risk == 'medium':
            score += self.SECURITY * 0.5
            
        return min(score, 100)

# ==============================================================================
# MONITORING & ANALYTICS
# ==============================================================================
@dataclass
class MonitoringConfig:
    PRICE_CHECK_INTERVAL_MS: int = 1000  # 1 Sekunde für aktive Positionen
    IDLE_CHECK_INTERVAL_MS: int = 5000   # 5 Sekunden wenn keine Position
    
    # Metriken zum Tracken
    TRACK_METRICS: List[str] = None
    
    # Performance Tracking
    LOG_ALL_TRADES: bool = True
    SAVE_TO_DATABASE: bool = True
    DATABASE_PATH: str = "trades.db"
    
    # Alerts
    ALERT_ON_LARGE_MOVEMENT: float = 20  # Alert bei 20% Bewegung
    ALERT_ON_WHALE_ACTIVITY: bool = True

    def __post_init__(self):
        if self.TRACK_METRICS is None:
            self.TRACK_METRICS = [
                'entry_price', 'exit_price', 'holding_time',
                'max_drawdown', 'max_profit', 'volume_profile',
                'holder_changes', 'liquidity_changes'
            ]

# ==============================================================================
# INSTANZEN ERSTELLEN
# ==============================================================================
scanner_filters = ScannerFilters()
trading_config = TradingConfig()
profit_strategy = ProfitStrategy()
scoring_weights = ScoringWeights()
monitoring_config = MonitoringConfig()

# ==============================================================================
# BLACKLIST & WHITELIST
# ==============================================================================
TOKEN_BLACKLIST = set([
    "So11111111111111111111111111111111111111112",  # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
])

TRUSTED_DEPLOYERS = set([
    # Bekannte vertrauenswürdige Token-Deployer hier einfügen
])

# ==============================================================================
# ADVANCED FEATURES
# ==============================================================================
ENABLE_SNIPING_MODE = True  # Ultra-schneller Modus für neue Listings
ENABLE_ARBITRAGE_DETECTION = False  # Cross-DEX Arbitrage
ENABLE_COPY_TRADING = False  # Kopiere erfolgreiche Wallets
ENABLE_AI_ANALYSIS = False  # KI-basierte Mustererkennung