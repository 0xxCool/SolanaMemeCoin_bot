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
    
    async def get_quote(self, input_mint: str, output_mint: str, 
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Jupiter"""
        # Implementation
        return {}
        
    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Jupiter"""
        # Implementation
        return ""

class RaydiumDEX:
    """Raydium DEX Integration"""
    
    async def get_quote(self, input_mint: str, output_mint: str,
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Raydium"""
        # Implementation
        return {}
        
    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Raydium"""
        # Implementation
        return ""

class OrcaDEX:
    """Orca DEX Integration"""
    
    async def get_quote(self, input_mint: str, output_mint: str,
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Orca"""
        # Implementation
        return {}
        
    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Orca"""
        # Implementation
        return ""

class SerumDEX:
    """Serum DEX Integration"""
    
    async def get_quote(self, input_mint: str, output_mint: str,
                       amount: int, slippage_bps: int) -> Dict:
        """Get quote from Serum"""
        # Implementation
        return {}
        
    async def execute_swap(self, quote: Dict, keypair) -> str:
        """Execute swap on Serum"""
        # Implementation
        return ""

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