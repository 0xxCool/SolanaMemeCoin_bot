# smart_trading.py
"""
Smart Order Routing, Multi-DEX Aggregation und kritische Optimierungen
"""
import asyncio
import aiohttp
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
import heapq
from collections import defaultdict
import statistics

# Circuit Breaker Implementation
class CircuitBreaker:
    """Circuit Breaker Pattern für Fehlertoleranz"""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: int = 60,
                 expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise Exception(f"Circuit breaker is OPEN (failures: {self.failure_count})")
                
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
            
    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        self.state = 'CLOSED'
        
    def _on_failure(self):
        """Handle failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset"""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.recovery_timeout)

@dataclass
class DEXQuote:
    """Quote von einem DEX"""
    dex: str
    input_amount: int
    output_amount: int
    price_impact: float
    fee: float
    route: List[str]
    gas_estimate: int
    
    @property
    def effective_price(self) -> float:
        """Effektiver Preis inkl. Fees"""
        if self.input_amount == 0:
            return 0
        return (self.output_amount / self.input_amount) * (1 - self.fee)

class SmartOrderRouter:
    """
    Intelligenter Order Router für beste Ausführung über mehrere DEXs
    """
    
    def __init__(self):
        self.dexs = {
            'jupiter': JupiterDEX(),
            'raydium': RaydiumDEX(),
            'orca': OrcaDEX(),
            'serum': SerumDEX()
        }
        self.quote_cache = {}
        self.execution_stats = defaultdict(lambda: {
            'success': 0,
            'failed': 0,
            'avg_slippage': []
        })
        
    async def get_best_quote(self, 
                            input_mint: str, 
                            output_mint: str, 
                            amount: int,
                            slippage_bps: int = 100) -> Dict:
        """
        Holt beste Quote von allen DEXs
        """
        # Check cache
        cache_key = f"{input_mint}_{output_mint}_{amount}"
        if cache_key in self.quote_cache:
            cached = self.quote_cache[cache_key]
            if time.time() - cached['timestamp'] < 5:  # 5 seconds cache
                return cached['quote']
                
        # Get quotes from all DEXs in parallel
        quote_tasks = []
        for name, dex in self.dexs.items():
            task = self._get_quote_safe(dex, input_mint, output_mint, amount, slippage_bps)
            quote_tasks.append((name, task))
            
        # Gather results
        quotes = []
        for name, task in quote_tasks:
            try:
                quote = await task
                if quote:
                    quote['dex'] = name
                    quotes.append(quote)
            except Exception as e:
                print(f"Quote error from {name}: {e}")
                
        if not quotes:
            return None
            
        # Analyze and find best quote
        best_quote = self._analyze_quotes(quotes)
        
        # Consider splitting if beneficial
        split_quote = await self._check_split_routing(
            input_mint, output_mint, amount, quotes
        )
        
        if split_quote and self._is_split_beneficial(best_quote, split_quote):
            best_quote = split_quote
            
        # Cache result
        self.quote_cache[cache_key] = {
            'quote': best_quote,
            'timestamp': time.time()
        }
        
        return best_quote
        
    async def _get_quote_safe(self, dex, input_mint: str, 
                             output_mint: str, amount: int, 
                             slippage_bps: int) -> Optional[Dict]:
        """Get quote with error handling"""
        try:
            return await asyncio.wait_for(
                dex.get_quote(input_mint, output_mint, amount, slippage_bps),
                timeout=3.0
            )
        except:
            return None
            
    def _analyze_quotes(self, quotes: List[Dict]) -> Dict:
        """
        Analysiert Quotes und wählt beste aus
        """
        if not quotes:
            return None
            
        # Score each quote
        scored_quotes = []
        for quote in quotes:
            score = self._calculate_quote_score(quote)
            scored_quotes.append((score, quote))
            
        # Sort by score (higher is better)
        scored_quotes.sort(reverse=True, key=lambda x: x[0])
        
        best_quote = scored_quotes[0][1]
        
        # Add analysis data
        best_quote['alternatives'] = len(quotes) - 1
        best_quote['score'] = scored_quotes[0][0]
        
        # Calculate savings vs worst quote
        if len(scored_quotes) > 1:
            worst_output = min(q[1]['outputAmount'] for q in scored_quotes)
            best_output = best_quote['outputAmount']
            savings_pct = ((best_output - worst_output) / worst_output) * 100
            best_quote['savings_pct'] = savings_pct
            
        return best_quote
        
    def _calculate_quote_score(self, quote: Dict) -> float:
        """
        Berechnet Score für Quote
        Higher score = better quote
        """
        score = 100.0
        
        # Output amount (most important)
        output_factor = quote.get('outputAmount', 0) / 1e9  # Convert to SOL
        score += output_factor * 10
        
        # Price impact (negative score)
        price_impact = abs(quote.get('priceImpactPct', 0))
        score -= price_impact * 5
        
        # DEX reliability
        dex = quote.get('dex', '')
        reliability_scores = {
            'jupiter': 10,
            'raydium': 8,
            'orca': 8,
            'serum': 6
        }
        score += reliability_scores.get(dex, 0)
        
        # Route complexity (simpler is better)
        route_length = len(quote.get('route', []))
        if route_length > 0:
            score -= (route_length - 1) * 2  # Penalty for multi-hop
            
        # Historical success rate
        if dex in self.execution_stats:
            stats = self.execution_stats[dex]
            total = stats['success'] + stats['failed']
            if total > 0:
                success_rate = stats['success'] / total
                score += success_rate * 5
                
        return score
        
    async def _check_split_routing(self, input_mint: str, output_mint: str,
                                  amount: int, quotes: List[Dict]) -> Optional[Dict]:
        """
        Prüft ob Split-Routing besser wäre
        """
        if len(quotes) < 2:
            return None
            
        # Try splitting amount across top 2 DEXs
        split_amount = amount // 2
        
        # Get fresh quotes for split amounts
        split_quotes = []
        for quote in quotes[:2]:  # Top 2 quotes
            dex = self.dexs[quote['dex']]
            split_quote = await self._get_quote_safe(
                dex, input_mint, output_mint, split_amount, 100
            )
            if split_quote:
                split_quotes.append(split_quote)
                
        if len(split_quotes) == 2:
            total_output = sum(q['outputAmount'] for q in split_quotes)
            
            return {
                'type': 'SPLIT',
                'outputAmount': total_output,
                'splits': split_quotes,
                'dexs': [q['dex'] for q in split_quotes],
                'priceImpactPct': statistics.mean([q.get('priceImpactPct', 0) for q in split_quotes])
            }
            
        return None
        
    def _is_split_beneficial(self, single_quote: Dict, split_quote: Dict) -> bool:
        """Check if split routing is beneficial"""
        if not split_quote:
            return False
            
        # Split is beneficial if output is >1% better
        improvement = (split_quote['outputAmount'] - single_quote['outputAmount']) / single_quote['outputAmount']
        return improvement > 0.01
        
    async def execute_smart_swap(self, quote: Dict, keypair) -> Optional[str]:
        """
        Führt Swap mit Smart Routing aus
        """
        if quote['type'] == 'SPLIT':
            # Execute split trades in parallel
            tasks = []
            for split in quote['splits']:
                dex = self.dexs[split['dex']]
                tasks.append(dex.execute_swap(split, keypair))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Return first successful tx
            for result in results:
                if isinstance(result, str):
                    return result
                    
            return None
            
        else:
            # Single DEX execution
            dex = self.dexs[quote['dex']]
            return await dex.execute_swap(quote, keypair)
            
    def update_execution_stats(self, dex: str, success: bool, slippage: float = 0):
        """Update execution statistics"""
        if success:
            self.execution_stats[dex]['success'] += 1
            if slippage > 0:
                self.execution_stats[dex]['avg_slippage'].append(slippage)
        else:
            self.execution_stats[dex]['failed'] += 1

class MultiRegionRPC:
    """
    Multi-Region RPC Management für minimale Latenz
    """
    
    def __init__(self):
        self.regions = {
            'us_east': [
                'https://solana-mainnet.g.alchemy.com/v2/KEY',
                'https://rpc.helius.xyz/?api-key=KEY'
            ],
            'us_west': [
                'https://solana-api.projectserum.com',
                'https://api.mainnet-beta.solana.com'
            ],
            'eu': [
                'https://solana-mainnet.eu.chainstack.com/KEY',
                'https://rpc.ankr.com/solana'
            ],
            'asia': [
                'https://api.mainnet-beta.solana.com'
            ]
        }
        
        self.latency_map = {}
        self.health_status = {}
        self.current_best = None
        
    async def initialize(self):
        """Test all RPCs and determine best"""
        await self.test_all_rpcs()
        
        # Start monitoring task
        asyncio.create_task(self._monitor_health())
        
    async def test_all_rpcs(self):
        """Test latency for all RPCs"""
        tasks = []
        
        for region, rpcs in self.regions.items():
            for rpc in rpcs:
                tasks.append(self._test_rpc_latency(rpc, region))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Find best RPC
        valid_results = [r for r in results if isinstance(r, dict)]
        if valid_results:
            self.current_best = min(valid_results, key=lambda x: x['latency'])
            print(f"Best RPC: {self.current_best['url']} ({self.current_best['latency']:.0f}ms)")
            
    async def _test_rpc_latency(self, url: str, region: str) -> Dict:
        """Test single RPC latency"""
        try:
            start = time.time()
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }
                
                async with session.post(url, json=payload, timeout=2) as response:
                    if response.status == 200:
                        latency = (time.time() - start) * 1000
                        
                        result = {
                            'url': url,
                            'region': region,
                            'latency': latency,
                            'healthy': True
                        }
                        
                        self.latency_map[url] = latency
                        self.health_status[url] = True
                        
                        return result
                        
        except Exception as e:
            self.health_status[url] = False
            return {'url': url, 'healthy': False}
            
    async def get_fastest_rpc(self) -> str:
        """Get current fastest RPC"""
        if self.current_best and self.current_best['healthy']:
            return self.current_best['url']
            
        # Fallback
        for url, healthy in self.health_status.items():
            if healthy:
                return url
                
        # Last resort
        return "https://api.mainnet-beta.solana.com"
        
    async def _monitor_health(self):
        """Continuously monitor RPC health"""
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            await self.test_all_rpcs()

class SlippagePredictor:
    """
    Dynamische Slippage Prediction basierend auf Orderbook und Liquidität
    """
    
    def __init__(self):
        self.history = deque(maxlen=1000)
        
    async def predict_slippage(self, 
                              token: str, 
                              amount_sol: float,
                              liquidity: float,
                              orderbook_depth: Optional[Dict] = None) -> int:
        """
        Predicts optimal slippage in basis points
        """
        # Base calculation
        liquidity_ratio = amount_sol / max(liquidity, 1)
        
        # Dynamic calculation based on liquidity ratio
        if liquidity_ratio < 0.001:
            base_slippage = 30  # 0.3%
        elif liquidity_ratio < 0.01:
            base_slippage = 50 + (liquidity_ratio * 5000)
        elif liquidity_ratio < 0.05:
            base_slippage = 100 + (liquidity_ratio * 2000)
        elif liquidity_ratio < 0.1:
            base_slippage = 200 + (liquidity_ratio * 3000)
        else:
            base_slippage = min(500, 100 + (liquidity_ratio * 5000))
            
        # Adjust based on orderbook if available
        if orderbook_depth:
            spread = orderbook_depth.get('spread_pct', 0)
            depth_ratio = amount_sol / orderbook_depth.get('depth_sol', 1)
            
            # Add spread
            base_slippage += spread * 100
            
            # Adjust for depth
            if depth_ratio > 0.1:
                base_slippage *= (1 + depth_ratio)
                
        # Learn from history
        adjustment = self._get_historical_adjustment(token, amount_sol)
        base_slippage *= adjustment
        
        return min(int(base_slippage), 1000)  # Max 10% slippage
        
    def _get_historical_adjustment(self, token: str, amount: float) -> float:
        """Get adjustment based on historical data"""
        # Find similar trades
        similar = [
            h for h in self.history
            if h['token'] == token and 
            abs(h['amount'] - amount) / amount < 0.2
        ]
        
        if not similar:
            return 1.0
            
        # Calculate average actual vs predicted
        ratios = [h['actual_slippage'] / h['predicted_slippage'] for h in similar]
        avg_ratio = statistics.mean(ratios)
        
        # Bounded adjustment
        return max(0.5, min(2.0, avg_ratio))
        
    def record_execution(self, token: str, amount: float, 
                        predicted: float, actual: float):
        """Record actual slippage for learning"""
        self.history.append({
            'token': token,
            'amount': amount,
            'predicted_slippage': predicted,
            'actual_slippage': actual,
            'timestamp': time.time()
        })

# DEX Implementations
class JupiterDEX:
    """Jupiter DEX Integration"""

    def __init__(self):
        self.api_url = "https://quote-api.jup.ag/v6"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session

    async def get_quote(self, input_mint: str, output_mint: str,
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Jupiter"""
        try:
            session = await self._get_session()
            url = f"{self.api_url}/quote"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': slippage_bps
            }

            async with session.get(url, params=params, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'dex': 'jupiter',
                        'input_amount': amount,
                        'output_amount': int(data.get('outAmount', 0)),
                        'price_impact': float(data.get('priceImpactPct', 0)),
                        'route': data.get('routePlan', []),
                        'quote_response': data
                    }
        except Exception as e:
            print(f"Jupiter quote error: {e}")
        return {}

    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Jupiter"""
        try:
            session = await self._get_session()
            # Jupiter swap API endpoint
            swap_url = f"{self.api_url}/swap"

            swap_payload = {
                'quoteResponse': quote.get('quote_response', {}),
                'userPublicKey': str(keypair.pubkey()),
                'wrapUnwrapSOL': True
            }

            async with session.post(swap_url, json=swap_payload, ssl=False) as response:
                if response.status == 200:
                    swap_data = await response.json()
                    # Return the swap transaction (would need to sign and send)
                    return swap_data.get('swapTransaction', '')
        except Exception as e:
            print(f"Jupiter swap error: {e}")
        return ""

    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()

class RaydiumDEX:
    """Raydium DEX Integration"""

    def __init__(self):
        self.api_url = "https://api.raydium.io/v2"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session

    async def get_quote(self, input_mint: str, output_mint: str,
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Raydium"""
        try:
            session = await self._get_session()
            url = f"{self.api_url}/swap/quote"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippage': slippage_bps / 10000  # Convert bps to decimal
            }

            async with session.get(url, params=params, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'dex': 'raydium',
                        'input_amount': amount,
                        'output_amount': int(data.get('outputAmount', 0)),
                        'price_impact': float(data.get('priceImpact', 0)),
                        'route': [data.get('poolId', '')],
                        'quote_response': data
                    }
        except Exception as e:
            print(f"Raydium quote error: {e}")
        return {}

    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Raydium"""
        try:
            # Raydium requires direct transaction building
            # This is a simplified placeholder
            print("Raydium swap would be executed here")
            return ""
        except Exception as e:
            print(f"Raydium swap error: {e}")
        return ""

    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()

class OrcaDEX:
    """Orca DEX Integration"""

    def __init__(self):
        self.api_url = "https://api.orca.so"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session

    async def get_quote(self, input_mint: str, output_mint: str,
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Orca"""
        try:
            session = await self._get_session()
            url = f"{self.api_url}/v1/quote"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippage': slippage_bps / 10000
            }

            async with session.get(url, params=params, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'dex': 'orca',
                        'input_amount': amount,
                        'output_amount': int(data.get('outAmount', 0)),
                        'price_impact': float(data.get('priceImpact', 0)),
                        'route': data.get('route', []),
                        'quote_response': data
                    }
        except Exception as e:
            print(f"Orca quote error: {e}")
        return {}

    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Orca"""
        try:
            # Orca swap execution would go here
            print("Orca swap would be executed here")
            return ""
        except Exception as e:
            print(f"Orca swap error: {e}")
        return ""

    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()

class SerumDEX:
    """Serum DEX Integration"""

    def __init__(self):
        # Serum is now mostly deprecated in favor of OpenBook
        # But keeping for compatibility
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session

    async def get_quote(self, input_mint: str, output_mint: str,
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Serum/OpenBook"""
        try:
            # Serum/OpenBook requires on-chain orderbook reads
            # This is a simplified placeholder
            print("Serum quote would require orderbook reads")
            return {}
        except Exception as e:
            print(f"Serum quote error: {e}")
        return {}

    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Serum"""
        try:
            # Serum swap would build and send transaction
            print("Serum swap would be executed here")
            return ""
        except Exception as e:
            print(f"Serum swap error: {e}")
        return ""

    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global Instances
smart_router = SmartOrderRouter()
multi_rpc = MultiRegionRPC()
slippage_predictor = SlippagePredictor()

# Initialize everything
async def initialize_smart_trading():
    """Initialize all smart trading components"""
    print("🚀 Initializing Smart Trading Components...")
    
    # Initialize Multi-Region RPC
    await multi_rpc.initialize()
    
    print("✅ Smart Trading initialized")

# Public APIs
async def get_best_quote(input_mint: str, output_mint: str, amount_sol: float) -> Dict:
    """Get best quote across all DEXs"""
    amount_lamports = int(amount_sol * 1e9)
    return await smart_router.get_best_quote(input_mint, output_mint, amount_lamports)

async def execute_smart_trade(quote: Dict, keypair) -> str:
    """Execute trade with smart routing"""
    return await smart_router.execute_smart_swap(quote, keypair)

async def predict_optimal_slippage(token: str, amount_sol: float, liquidity: float) -> int:
    """Predict optimal slippage"""
    return await slippage_predictor.predict_slippage(token, amount_sol, liquidity)

async def get_fastest_rpc() -> str:
    """Get current fastest RPC endpoint"""
    return await multi_rpc.get_fastest_rpc()

# Position Management Classes
@dataclass
class Position:
    """Represents an active trading position"""
    token_address: str
    symbol: str
    entry_price: float
    entry_time: float
    amount_sol: float
    amount_tokens: int
    stop_loss: float = 0
    take_profit: float = 0
    current_price: float = 0
    unrealized_pnl: float = 0
    status: str = "OPEN"  # OPEN, CLOSED, STOPPED

    def update_pnl(self, current_price: float):
        """Updates unrealized PnL"""
        self.current_price = current_price
        price_change = (current_price - self.entry_price) / self.entry_price
        self.unrealized_pnl = self.amount_sol * price_change

    def should_stop_loss(self) -> bool:
        """Check if stop loss should trigger"""
        if self.stop_loss > 0 and self.current_price <= self.stop_loss:
            return True
        return False

    def should_take_profit(self) -> bool:
        """Check if take profit should trigger"""
        if self.take_profit > 0 and self.current_price >= self.take_profit:
            return True
        return False

class Trader:
    """
    Main Trader class for position management and trade execution
    """

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.keypair = None
        self.sol_balance: float = 0
        self.total_pnl: float = 0
        self.win_rate: float = 0
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.is_initialized = False

    async def initialize(self, keypair):
        """Initialize trader with keypair"""
        self.keypair = keypair
        self.is_initialized = True
        print(f"✅ Trader initialized for wallet: {str(keypair.pubkey())[:8]}...")

    async def open_position(self, token_metrics, amount_sol: float) -> Optional[Position]:
        """
        Opens a new trading position

        Args:
            token_metrics: EnhancedTokenMetrics from analyzer
            amount_sol: Amount in SOL to invest

        Returns:
            Position object if successful, None otherwise
        """
        try:
            if not self.is_initialized:
                print("❌ Trader not initialized")
                return None

            # Get quote for the trade
            quote = await get_best_quote(
                input_mint="So11111111111111111111111111111111111111112",  # SOL
                output_mint=token_metrics.address,
                amount_sol=amount_sol
            )

            if not quote or quote.get('output_amount', 0) == 0:
                print(f"❌ No valid quote for {token_metrics.symbol}")
                return None

            # Calculate stop loss and take profit based on ML predictions
            entry_price = quote.get('output_amount', 0) / (amount_sol * 1e9)
            stop_loss_pct = 0.15  # -15% stop loss
            take_profit_pct = token_metrics.ml_predicted_return / 100 if token_metrics.ml_predicted_return > 0 else 0.5

            position = Position(
                token_address=token_metrics.address,
                symbol=token_metrics.symbol,
                entry_price=entry_price,
                entry_time=time.time(),
                amount_sol=amount_sol,
                amount_tokens=quote.get('output_amount', 0),
                stop_loss=entry_price * (1 - stop_loss_pct),
                take_profit=entry_price * (1 + take_profit_pct),
                current_price=entry_price
            )

            # Execute the trade
            tx_signature = await execute_smart_trade(quote, self.keypair)

            if tx_signature:
                self.positions[token_metrics.address] = position
                print(f"✅ Opened position in {token_metrics.symbol}")
                print(f"   Entry: ${entry_price:.8f}")
                print(f"   Amount: {amount_sol} SOL")
                print(f"   Stop Loss: ${position.stop_loss:.8f}")
                print(f"   Take Profit: ${position.take_profit:.8f}")
                return position
            else:
                print(f"❌ Trade execution failed for {token_metrics.symbol}")
                return None

        except Exception as e:
            print(f"❌ Error opening position: {e}")
            return None

    async def close_position(self, token_address: str, reason: str = "MANUAL") -> bool:
        """
        Closes an existing position

        Args:
            token_address: Token address to close
            reason: Reason for closing (MANUAL, STOP_LOSS, TAKE_PROFIT, TIMEOUT)

        Returns:
            True if successful, False otherwise
        """
        try:
            if token_address not in self.positions:
                print(f"❌ No position found for {token_address}")
                return False

            position = self.positions[token_address]

            # Get quote to sell
            quote = await get_best_quote(
                input_mint=token_address,
                output_mint="So11111111111111111111111111111111111111112",  # SOL
                amount_sol=position.amount_tokens / 1e9
            )

            if not quote:
                print(f"❌ No quote available to close {position.symbol}")
                return False

            # Execute sell
            tx_signature = await execute_smart_trade(quote, self.keypair)

            if tx_signature:
                # Calculate final PnL
                exit_sol = quote.get('output_amount', 0) / 1e9
                pnl = exit_sol - position.amount_sol
                pnl_pct = (pnl / position.amount_sol) * 100

                # Update stats
                position.status = "CLOSED"
                self.total_pnl += pnl
                self.total_trades += 1
                if pnl > 0:
                    self.winning_trades += 1
                self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0

                # Record trade
                self.trade_history.append({
                    'symbol': position.symbol,
                    'entry_price': position.entry_price,
                    'exit_price': position.current_price,
                    'entry_time': position.entry_time,
                    'exit_time': time.time(),
                    'hold_time': time.time() - position.entry_time,
                    'amount_sol': position.amount_sol,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': reason
                })

                print(f"✅ Closed position in {position.symbol}")
                print(f"   Reason: {reason}")
                print(f"   PnL: {pnl:.4f} SOL ({pnl_pct:+.2f}%)")

                # Remove from active positions
                del self.positions[token_address]
                return True
            else:
                print(f"❌ Failed to execute sell for {position.symbol}")
                return False

        except Exception as e:
            print(f"❌ Error closing position: {e}")
            return False

    async def update_positions(self):
        """Updates all active positions and checks for stop loss / take profit"""
        for token_address, position in list(self.positions.items()):
            try:
                # Get current price (simplified - would query actual price)
                # In real implementation, fetch from DexScreener or on-chain
                current_price = position.current_price  # Placeholder

                position.update_pnl(current_price)

                # Check stop loss
                if position.should_stop_loss():
                    print(f"⚠️ Stop loss triggered for {position.symbol}")
                    await self.close_position(token_address, "STOP_LOSS")

                # Check take profit
                elif position.should_take_profit():
                    print(f"✅ Take profit triggered for {position.symbol}")
                    await self.close_position(token_address, "TAKE_PROFIT")

                # Check timeout (default 1 hour)
                elif time.time() - position.entry_time > 3600:
                    print(f"⏰ Position timeout for {position.symbol}")
                    await self.close_position(token_address, "TIMEOUT")

            except Exception as e:
                print(f"Error updating position {position.symbol}: {e}")

    def get_active_positions(self) -> List[Position]:
        """Returns list of active positions"""
        return list(self.positions.values())

    def get_stats(self) -> Dict:
        """Returns trading statistics"""
        return {
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': self.win_rate,
            'active_positions': len(self.positions),
            'sol_balance': self.sol_balance
        }

# Global trader instance
trader = Trader()