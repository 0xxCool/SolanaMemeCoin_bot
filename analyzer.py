# analyzer_enhanced.py
"""
Enhanced Analyzer mit ML Prediction und Mempool Integration
Ersetzt das alte analyzer.py mit fortgeschrittenen Features
"""
import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
import json
import numpy as np

# Import original modules
from config import (
    scanner_filters, scoring_weights, trading_config,
    TOKEN_BLACKLIST, TRUSTED_DEPLOYERS,
    RUGCHECK_API_URL, BIRDEYE_API, DEXSCREENER_API,
    RPC_URL, BACKUP_RPC_URLS
)
import telegram_bot

# Import new ML and Mempool modules
import ml_predictor
from mempool_monitor import EarlySignal
from rate_limiter import APIRateLimiters

# Setup logging
logger = logging.getLogger(__name__)

# Globale Async Clients
async_clients = []
current_client_idx = 0

@dataclass
class EnhancedTokenMetrics:
    """Erweiterte Token Metriken mit ML Predictions"""
    # Basis Metriken (wie vorher)
    address: str
    symbol: str
    liquidity_usd: float = 0
    market_cap_usd: float = 0
    age_minutes: float = 0
    holder_count: int = 0
    top_10_percentage: float = 100
    volume_usd_5m: float = 0
    tx_count_5m: int = 0
    price_change_5m: float = 0
    risk_level: str = 'high'
    is_honeypot: bool = False
    lp_burned: bool = False
    deployer_trusted: bool = False
    score: float = 0
    dex_url: str = ""
    
    # Neue ML-basierte Metriken
    ml_predicted_return: float = 0
    ml_confidence: float = 0
    ml_risk_score: float = 0
    ml_recommended_action: str = "SKIP"
    ml_recommended_position: float = 0
    ml_predicted_peak_time: int = 30
    ml_exit_indicators: List[str] = None
    
    # Mempool Signale
    mempool_signals: List[str] = None
    whale_activity_detected: bool = False
    pending_large_buys: int = 0
    pending_large_sells: int = 0
    
    # Advanced Analytics
    momentum_score: float = 0
    volatility: float = 0
    buy_pressure: float = 0
    social_sentiment: float = 0
    pattern_signals: List[str] = None
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items()}
    
    def get_final_score(self) -> float:
        """Kombiniert alle Scores zu einem finalen Score"""
        # Basis Score (40%)
        base_weight = 0.4
        base_score = self.score * base_weight
        
        # ML Score (40%)
        ml_weight = 0.4
        ml_score = (self.ml_predicted_return * self.ml_confidence / 100) * ml_weight
        
        # Mempool Score (20%)
        mempool_weight = 0.2
        mempool_score = 0
        if self.pending_large_buys > self.pending_large_sells:
            mempool_score = min(100, self.pending_large_buys * 10) * mempool_weight
        
        return min(100, base_score + ml_score + mempool_score)

class EnhancedAnalyzer:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache = {}  # Cache für bereits analysierte Token
        self.pattern_detector = PatternDetector()
        self.social_analyzer = SocialSentimentAnalyzer()
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def ensure_initialized(self):
        """Stellt sicher, dass die Initialisierung durchgeführt wurde"""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return
            await self._initialize()
            self._initialized = True

    async def _initialize(self):
        """Initialisiert Async Clients und Session"""
        global async_clients

        try:
            # Erstelle mehrere RPC Clients für Load Balancing
            async_clients = [AsyncClient(RPC_URL)]
            for backup_url in BACKUP_RPC_URLS[:2]:  # Max 2 Backups
                try:
                    client = AsyncClient(backup_url)
                    async_clients.append(client)
                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"Could not connect to backup RPC {backup_url}: {e}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error connecting to {backup_url}: {e}",
                        exc_info=True
                    )
        finally:
            # Always create session, even if RPC setup partially failed
            if self.session is None:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5),
                    connector=aiohttp.TCPConnector(limit=100, limit_per_host=30)
                )
        
    async def analyze_token(self, pair_data: Dict[str, Any],
                          early_signal: Optional[EarlySignal] = None) -> Optional[EnhancedTokenMetrics]:
        """
        Hauptanalyse-Funktion mit ML und Mempool Integration
        """
        # Stelle sicher, dass die Initialisierung durchgeführt wurde
        await self.ensure_initialized()

        try:
            # Basis-Daten extrahieren
            metrics = EnhancedTokenMetrics(
                address=pair_data.get('baseToken', {}).get('address', ''),
                symbol=pair_data.get('baseToken', {}).get('symbol', ''),
                liquidity_usd=float(pair_data.get('liquidity', {}).get('usd', 0)),
                dex_url=pair_data.get('url', ''),
                age_minutes=(time.time() * 1000 - pair_data.get('pairCreatedAt', 0)) / 60000,
                ml_exit_indicators=[],
                mempool_signals=[],
                pattern_signals=[]
            )
            
            # Early Signal Integration
            if early_signal:
                metrics.mempool_signals.append(early_signal.signal_type)
                # Boost für early detection
                metrics.age_minutes = 0.1  # Very early
                
            # Stufe 1: Schnelle Basis-Filter
            if not await self._pass_basic_filters(metrics):
                return None
                
            # Parallel alle erweiterten Metriken abrufen
            tasks = [
                self._fetch_holder_metrics(metrics),
                self._fetch_volume_metrics(metrics, pair_data),
                self._fetch_security_check(metrics),
                self._fetch_price_metrics(metrics, pair_data),
                self._fetch_advanced_metrics(metrics),
                self._fetch_mempool_data(metrics),
                self._run_ml_prediction(metrics, pair_data),
                self._detect_patterns(metrics, pair_data),
                self._analyze_social_sentiment(metrics)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log errors but continue
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} error: {result}", exc_info=result)
            
            # Stufe 2: Erweiterte Filter
            if not await self._pass_advanced_filters(metrics):
                return None
                
            # Berechne finalen Score
            metrics.score = scoring_weights.calculate_score(metrics.to_dict())
            final_score = metrics.get_final_score()
            
            # ML-basierte Entscheidung
            if metrics.ml_recommended_action == "SKIP" and metrics.ml_confidence > 0.7:
                logger.info(f"ML empfiehlt SKIP für {metrics.symbol} (Confidence: {metrics.ml_confidence:.1%})")
                return None
                
            # Nur Token mit gutem finalem Score
            if final_score < scanner_filters.MIN_SCORE:
                logger.debug(f"Token {metrics.symbol} Final Score zu niedrig: {final_score:.1f}")
                return None
                
            # Pattern-basierte Warnung
            if "RUG_PATTERN" in metrics.pattern_signals:
                logger.warning(f"⚠️ Rug Pattern erkannt für {metrics.symbol}")
                metrics.risk_level = "critical"
                
            return metrics

        except Exception as e:
            logger.error(f"Enhanced Analyse Fehler: {e}", exc_info=True)
            return None
            
    async def _pass_basic_filters(self, metrics: EnhancedTokenMetrics) -> bool:
        """Stufe 1: Schnelle Basis-Filter"""
        # Blacklist Check
        if metrics.address in TOKEN_BLACKLIST:
            return False
            
        # Liquidität
        if not (scanner_filters.MIN_LIQUIDITY_USD <= 
                metrics.liquidity_usd <= 
                scanner_filters.MAX_LIQUIDITY_USD):
            return False
            
        # Alter (außer bei Early Signals)
        if "NEW_LP_CREATION" not in metrics.mempool_signals:
            if not (scanner_filters.MIN_AGE_MINUTES <= 
                    metrics.age_minutes <= 
                    scanner_filters.MAX_AGE_MINUTES):
                return False
            
        return True
        
    async def _pass_advanced_filters(self, metrics: EnhancedTokenMetrics) -> bool:
        """Stufe 2: Erweiterte Filter mit ML Integration"""
        # ML-basierte Filter
        if metrics.ml_risk_score > 0.8 and metrics.ml_confidence > 0.5:
            return False
            
        # Holder (relaxed für early tokens)
        if metrics.age_minutes > 2:  # Nur für ältere Token
            if not (scanner_filters.MIN_HOLDER_COUNT <= 
                    metrics.holder_count <= 
                    scanner_filters.MAX_HOLDER_COUNT):
                return False
            
        # Distribution
        if metrics.top_10_percentage > scanner_filters.MAX_TOP_10_PERCENTAGE:
            return False
            
        # Volume (relaxed für sehr neue Token)
        if metrics.age_minutes > 1:
            if metrics.volume_usd_5m < scanner_filters.MIN_VOLUME_USD:
                return False
            
        # Transaktionen
        if metrics.age_minutes > 2:
            if metrics.tx_count_5m < scanner_filters.MIN_TXS_COUNT:
                return False
            
        # Honeypot Check
        if metrics.is_honeypot:
            return False
            
        # High Risk Check (außer bei starken ML Signalen)
        if metrics.risk_level == 'critical' and metrics.ml_predicted_return < 100:
            return False
            
        return True
        
    async def _fetch_advanced_metrics(self, metrics: EnhancedTokenMetrics):
        """Holt erweiterte Metriken"""
        try:
            # Momentum berechnen
            metrics.momentum_score = await self._calculate_momentum(metrics.address)
            
            # Volatilität
            metrics.volatility = await self._calculate_volatility(metrics.address)
            
            # Buy Pressure
            metrics.buy_pressure = await self._calculate_buy_pressure(metrics.address)

        except Exception as e:
            logger.error(f"Advanced Metrics Error: {e}", exc_info=True)
            
    async def _fetch_mempool_data(self, metrics: EnhancedTokenMetrics):
        """Holt Daten aus dem Mempool Monitor"""
        try:
            from mempool_monitor import mempool_monitor
            
            if mempool_monitor:
                # Get pending transactions
                pending_txs = await mempool_monitor.get_pending_transactions(metrics.address)
                
                # Count large buys/sells
                for tx in pending_txs:
                    if tx.transaction_type.value == "LARGE_BUY":
                        metrics.pending_large_buys += 1
                    elif tx.transaction_type.value == "LARGE_SELL":
                        metrics.pending_large_sells += 1
                        
                # Whale activity
                if metrics.pending_large_buys > 2 or metrics.pending_large_sells > 2:
                    metrics.whale_activity_detected = True

        except Exception as e:
            logger.error(f"Mempool Data Error: {e}", exc_info=True)
            
    async def _run_ml_prediction(self, metrics: EnhancedTokenMetrics, pair_data: Dict):
        """Führt ML Prediction aus"""
        try:
            # Prepare data für ML Model
            ml_input = {
                'address': metrics.address,
                'liquidity_usd': metrics.liquidity_usd,
                'market_cap_usd': metrics.market_cap_usd,
                'age_minutes': metrics.age_minutes,
                'holder_count': metrics.holder_count,
                'top_10_percentage': metrics.top_10_percentage,
                'volume_usd_5m': metrics.volume_usd_5m,
                'tx_count_5m': metrics.tx_count_5m,
                'price_change_5m': metrics.price_change_5m,
                'holder_growth_rate': 0,  # Would calculate if we had history
                'buy_sell_ratio': 1,  # Placeholder
                'volatility': metrics.volatility,
                'volume_usd_1h': pair_data.get('volume', {}).get('h1', 0),
                'price_change_1h': pair_data.get('priceChange', {}).get('h1', 0),
                'gas_price': 5000  # Current gas price
            }
            
            # Get ML Prediction
            prediction = await ml_predictor.predict_token_performance(ml_input)
            
            # Update metrics
            metrics.ml_predicted_return = prediction.predicted_return
            metrics.ml_confidence = prediction.confidence
            metrics.ml_risk_score = prediction.risk_score
            metrics.ml_recommended_action = prediction.recommended_action
            metrics.ml_recommended_position = prediction.recommended_position_size
            metrics.ml_predicted_peak_time = prediction.predicted_peak_time
            metrics.ml_exit_indicators = prediction.exit_indicators

        except Exception as e:
            logger.error(f"ML Prediction Error: {e}", exc_info=True)
            # Set defaults on error
            metrics.ml_confidence = 0.1
            metrics.ml_recommended_action = "SKIP"
            
    async def _detect_patterns(self, metrics: EnhancedTokenMetrics, pair_data: Dict):
        """Erkennt Trading Patterns"""
        patterns = await self.pattern_detector.detect(metrics, pair_data)
        metrics.pattern_signals = patterns
        
    async def _analyze_social_sentiment(self, metrics: EnhancedTokenMetrics):
        """Analysiert Social Media Sentiment"""
        # Simplified - würde Twitter/Discord APIs verwenden
        metrics.social_sentiment = 0.5  # Neutral default
        
    async def _calculate_momentum(self, token_address: str) -> float:
        """Berechnet Momentum Score"""
        # Placeholder - würde Price History analysieren
        return 0.0
        
    async def _calculate_volatility(self, token_address: str) -> float:
        """Berechnet Volatilität"""
        # Placeholder - würde Standard Deviation berechnen
        return 0.0
        
    async def _calculate_buy_pressure(self, token_address: str) -> float:
        """Berechnet Buy Pressure"""
        # Placeholder - würde Buy/Sell Ratio analysieren
        return 0.5
        
    # Original methods from analyzer.py (kept for compatibility)
    async def _get_rpc_client(self) -> AsyncClient:
        """Rotiert zwischen verfügbaren RPC Clients"""
        global current_client_idx
        if not async_clients:
            await self._initialize()
        
        client = async_clients[current_client_idx % len(async_clients)]
        current_client_idx += 1
        return client
        
    async def _fetch_holder_metrics(self, metrics: EnhancedTokenMetrics):
        """Holt Holder-Statistiken mit optimierter RPC-Nutzung"""
        try:
            client = await self._get_rpc_client()
            token_pubkey = Pubkey.from_string(metrics.address)
            
            # Parallel abrufen
            largest_task = client.get_token_largest_accounts(token_pubkey)
            supply_task = client.get_token_supply(token_pubkey)
            
            largest_res, supply_res = await asyncio.gather(largest_task, supply_task)
            
            if not largest_res.value or not supply_res.value:
                return
                
            total_supply = int(supply_res.value.amount)
            if total_supply == 0:
                return
                
            # Top 10 Holder Percentage
            top_10_balance = sum(int(acc.amount) for acc in largest_res.value[:10])
            metrics.top_10_percentage = (top_10_balance / total_supply) * 100
            
            # Holder Count (Approximation)
            metrics.holder_count = len([acc for acc in largest_res.value if int(acc.amount) > 0])

        except Exception as e:
            logger.error(f"Holder-Metrik Fehler: {e}", exc_info=True)
            
    async def _fetch_volume_metrics(self, metrics: EnhancedTokenMetrics, pair_data: Dict):
        """Holt Volumen und Transaktions-Metriken"""
        try:
            # Aus pair_data extrahieren wenn vorhanden
            metrics.volume_usd_5m = float(pair_data.get('volume', {}).get('m5', 0))
            metrics.tx_count_5m = int(pair_data.get('txns', {}).get('m5', {}).get('buys', 0)) + \
                                 int(pair_data.get('txns', {}).get('m5', {}).get('sells', 0))
                                 
            # Zusätzlich von DexScreener API wenn nötig
            if metrics.volume_usd_5m == 0 and self.session:
                # ✅ Rate limiting
                await APIRateLimiters.dexscreener.acquire()
                async with self.session.get(
                    DEXSCREENER_API.format(metrics.address),
                    ssl=False
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('pairs'):
                            pair = data['pairs'][0]
                            metrics.volume_usd_5m = float(pair.get('volume', {}).get('m5', 0))

        except Exception as e:
            logger.error(f"Volume-Metrik Fehler: {e}", exc_info=True)
            
    async def _fetch_security_check(self, metrics: EnhancedTokenMetrics):
        """Führt Security Checks durch"""
        try:
            if not self.session:
                return

            # ✅ Rate limiting for RugCheck
            await APIRateLimiters.rugcheck.acquire()

            # RugCheck API
            async with self.session.get(
                RUGCHECK_API_URL.format(metrics.address),
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    metrics.risk_level = data.get('risk', 'high')
                    
                    # Honeypot Check aus den Details
                    if 'honeypot' in str(data).lower():
                        metrics.is_honeypot = True
                        
                    # LP Burn/Lock Check
                    if data.get('lpLocked') or data.get('lpBurned'):
                        metrics.lp_burned = True

        except Exception as e:
            logger.error(f"Security Check Fehler: {e}", exc_info=True)
            
    async def _fetch_price_metrics(self, metrics: EnhancedTokenMetrics, pair_data: Dict):
        """Berechnet Preis-Metriken und Momentum"""
        try:
            # Price Change aus pair_data
            price_change = pair_data.get('priceChange', {})
            metrics.price_change_5m = float(price_change.get('m5', 0))
            
            # Market Cap berechnen
            price_usd = float(pair_data.get('priceUsd', 0))
            if price_usd > 0:
                client = await self._get_rpc_client()
                supply_res = await client.get_token_supply(Pubkey.from_string(metrics.address))
                if supply_res.value:
                    total_supply = int(supply_res.value.amount) / (10 ** 9)  # Annahme: 9 Decimals
                    metrics.market_cap_usd = price_usd * total_supply

        except Exception as e:
            logger.error(f"Price-Metrik Fehler: {e}", exc_info=True)
            
    async def cleanup(self):
        """Cleanup Ressourcen - Idempotent (kann mehrmals sicher aufgerufen werden)"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                logger.warning(f"Session close warning: {e}")
            finally:
                self.session = None

        # Close all RPC clients
        global async_clients
        for client in async_clients:
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"RPC client close warning: {e}")
        async_clients = []  # Clear the list

        self._initialized = False

class PatternDetector:
    """Erkennt komplexe Trading Patterns"""
    
    def __init__(self):
        self.patterns = {
            'PUMP_AND_DUMP': self._detect_pump_dump,
            'ORGANIC_GROWTH': self._detect_organic_growth,
            'WHALE_ACCUMULATION': self._detect_whale_accumulation,
            'BREAKOUT': self._detect_breakout,
            'RUG_PATTERN': self._detect_rug_pattern,
            'FOMO_WAVE': self._detect_fomo_wave
        }
        
    async def detect(self, metrics: EnhancedTokenMetrics, pair_data: Dict) -> List[str]:
        """Führt alle Pattern Detections aus"""
        detected = []
        
        for name, detector in self.patterns.items():
            if await detector(metrics, pair_data):
                detected.append(name)
                
        return detected
        
    async def _detect_pump_dump(self, metrics: EnhancedTokenMetrics, pair_data: Dict) -> bool:
        """Erkennt Pump & Dump Pattern"""
        # Very new + high volume + high volatility
        if (metrics.age_minutes < 10 and
            metrics.volume_usd_5m > metrics.liquidity_usd * 0.5 and
            metrics.volatility > 0.3):
            # Additional check: high price change but low holder growth
            if metrics.price_change_5m > 50 and metrics.holder_count < 100:
                return True
        return False

    async def _detect_organic_growth(self, metrics: EnhancedTokenMetrics, pair_data: Dict) -> bool:
        """Erkennt organisches Wachstum"""
        # Steady growth + good holder distribution + consistent volume
        if (metrics.age_minutes > 15 and
            metrics.holder_count > 200 and
            metrics.top_10_percentage < 50 and
            metrics.volume_usd_5m > metrics.liquidity_usd * 0.1 and
            metrics.price_change_5m > 10 and metrics.price_change_5m < 100):
            return True
        return False

    async def _detect_whale_accumulation(self, metrics: EnhancedTokenMetrics, pair_data: Dict) -> bool:
        """Erkennt Whale Akkumulation"""
        # Large pending buys + low volatility + stable price
        if (metrics.pending_large_buys > 3 and
            metrics.pending_large_sells < 2 and
            metrics.whale_activity_detected and
            metrics.volatility < 0.2):
            return True
        return False

    async def _detect_breakout(self, metrics: EnhancedTokenMetrics, pair_data: Dict) -> bool:
        """Erkennt Breakout Pattern"""
        # High volume spike + strong price change + momentum
        if (metrics.volume_usd_5m > metrics.liquidity_usd * 0.3 and
            metrics.price_change_5m > 30 and
            metrics.momentum_score > 0.7 and
            metrics.buy_pressure > 0.6):
            return True
        return False

    async def _detect_rug_pattern(self, metrics: EnhancedTokenMetrics, pair_data: Dict) -> bool:
        """Erkennt potenzielle Rug Pull Pattern"""
        # Very high top holder concentration + suspicious deployer + low liquidity
        if (metrics.top_10_percentage > 80 and
            not metrics.deployer_trusted and
            not metrics.lp_burned and
            metrics.liquidity_usd < 5000):
            return True

        # Additional: sudden large sells pending
        if metrics.pending_large_sells > 5 and metrics.age_minutes < 30:
            return True

        return False

    async def _detect_fomo_wave(self, metrics: EnhancedTokenMetrics, pair_data: Dict) -> bool:
        """Erkennt FOMO Wave Pattern"""
        # Very high transaction count + rapid holder growth + social buzz
        if (metrics.tx_count_5m > 100 and
            metrics.volume_usd_5m > metrics.liquidity_usd * 0.4 and
            metrics.price_change_5m > 50 and
            metrics.social_sentiment > 0.7):
            return True
        return False

class SocialSentimentAnalyzer:
    """Analysiert Social Media Sentiment für Tokens"""

    def __init__(self):
        self.cache = {}

    async def analyze(self, token_address: str, symbol: str) -> float:
        """
        Analysiert Social Sentiment
        Returns: Score 0-1 (0=sehr negativ, 0.5=neutral, 1=sehr positiv)
        """
        # Placeholder - würde Twitter API, Discord, Telegram Gruppen etc. analysieren
        # Für jetzt: Neutral score
        return 0.5

# Global instance
analyzer = EnhancedAnalyzer()

# Backward compatibility alias
Analyzer = EnhancedAnalyzer