# mempool_monitor.py
"""
Advanced Mempool Monitoring für Ultra-Early Token Detection
Scannt pending Transactions für neue Opportunities
"""
import asyncio
import websockets
import json
import time
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import base64
from solders.transaction import VersionedTransaction
from solders.pubkey import Pubkey
from solders.instruction import Instruction
import aiohttp
from enum import Enum

# Raydium & Orca Program IDs
RAYDIUM_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
RAYDIUM_CLMM = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
ORCA_WHIRLPOOL = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
SERUM_DEX = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
JUPITER_V6 = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

# Token Program
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

class TransactionType(Enum):
    """Transaction Kategorien"""
    LP_CREATION = "LP_CREATION"
    LARGE_BUY = "LARGE_BUY"
    LARGE_SELL = "LARGE_SELL"
    WHALE_MOVEMENT = "WHALE_MOVEMENT"
    TOKEN_MINT = "TOKEN_MINT"
    BURN_LIQUIDITY = "BURN_LIQUIDITY"
    RUG_SIGNAL = "RUG_SIGNAL"
    UNKNOWN = "UNKNOWN"

@dataclass
class MempoolTransaction:
    """Repräsentiert eine Mempool Transaction"""
    signature: str
    transaction_type: TransactionType
    program_id: str
    accounts: List[str]
    amount_sol: float = 0
    token_mint: Optional[str] = None
    priority_fee: int = 0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    
@dataclass
class EarlySignal:
    """Frühe Signale aus dem Mempool"""
    signal_type: str  # NEW_LP, WHALE_BUY, etc
    token_address: str
    confidence: float  # 0-1
    data: Dict
    action_required: bool
    timestamp: float = field(default_factory=time.time)

class MempoolMonitor:
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.ws_url = rpc_url.replace("https", "wss").replace("http", "ws")
        
        # Tracking
        self.monitored_programs = {
            RAYDIUM_V4, RAYDIUM_CLMM, ORCA_WHIRLPOOL, 
            SERUM_DEX, JUPITER_V6, TOKEN_PROGRAM
        }
        self.pending_txs: deque = deque(maxlen=10000)
        self.processed_signatures: Set[str] = set()
        
        # Pattern Detection
        self.lp_creation_patterns = {}
        self.whale_wallets: Set[str] = set()
        self.suspicious_patterns = deque(maxlen=1000)
        
        # Stats
        self.stats = {
            'total_monitored': 0,
            'lp_creations': 0,
            'large_trades': 0,
            'signals_sent': 0
        }
        
        # Websocket connection
        self.websocket = None
        self.running = False
        
        # Session für HTTP calls
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Signal Callbacks
        self.signal_callbacks = []
        
    async def start(self):
        """Startet Mempool Monitoring"""
        print("🔍 Starting Mempool Monitor...")
        self.running = True
        
        # Initialize HTTP Session
        self.session = aiohttp.ClientSession()
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_program_transactions()),
            asyncio.create_task(self._monitor_slot_updates()),
            asyncio.create_task(self._analyze_patterns()),
            asyncio.create_task(self._stats_reporter())
        ]
        
        await asyncio.gather(*tasks)
        
    async def _monitor_program_transactions(self):
        """
        Überwacht Transactions für spezifische Programme
        """
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    
                    # Subscribe to all monitored programs
                    for program_id in self.monitored_programs:
                        await self._subscribe_to_program(program_id)
                        
                    print(f"✅ Subscribed to {len(self.monitored_programs)} programs")
                    
                    # Process incoming messages
                    async for message in websocket:
                        asyncio.create_task(self._process_notification(message))
                        
            except websockets.exceptions.ConnectionClosed:
                print("⚠️ Mempool WebSocket disconnected, reconnecting...")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"❌ Mempool Monitor Error: {e}")
                await asyncio.sleep(5)
                
    async def _subscribe_to_program(self, program_id: str):
        """
        Subscribes to a specific program's transactions
        """
        subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "programSubscribe",
            "params": [
                program_id,
                {
                    "encoding": "base64",
                    "commitment": "processed",  # Get transactions ASAP
                    "filters": []
                }
            ]
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(subscription))
            
    async def _monitor_slot_updates(self):
        """
        Monitors slot updates for timing analysis
        """
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # Subscribe to slot updates
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "slotSubscribe",
                        "params": []
                    }))
                    
                    async for message in ws:
                        data = json.loads(message)
                        if 'params' in data:
                            slot = data['params']['result']['slot']
                            # Use slot info for timing predictions
                            await self._update_slot_timing(slot)
                            
            except Exception as e:
                print(f"Slot Monitor Error: {e}")
                await asyncio.sleep(5)
                
    async def _process_notification(self, message: str):
        """
        Verarbeitet eingehende Transaction Notifications
        """
        try:
            data = json.loads(message)
            self.stats['total_monitored'] += 1
            
            if 'params' not in data:
                return
                
            result = data['params']['result']
            
            # Parse transaction
            tx_data = result.get('transaction', {})
            signature = result.get('signature', '')
            
            if signature in self.processed_signatures:
                return
                
            self.processed_signatures.add(signature)
            
            # Decode transaction
            tx_info = await self._decode_transaction(tx_data, signature)
            
            if tx_info:
                # Store in pending queue
                self.pending_txs.append(tx_info)
                
                # Check for important patterns
                signal = await self._check_for_signals(tx_info)
                if signal:
                    await self._emit_signal(signal)
                    
        except Exception as e:
            print(f"Process Notification Error: {e}")
            
    async def _decode_transaction(self, tx_data: Dict, signature: str) -> Optional[MempoolTransaction]:
        """
        Dekodiert eine Transaction und extrahiert relevante Infos
        """
        try:
            # Decode base64 transaction
            if isinstance(tx_data, str):
                tx_bytes = base64.b64decode(tx_data)
                tx = VersionedTransaction.from_bytes(tx_bytes)
            else:
                tx_bytes = base64.b64decode(tx_data.get('data', [''])[0])
                tx = VersionedTransaction.from_bytes(tx_bytes)
                
            # Extract instructions
            instructions = tx.message.instructions if hasattr(tx.message, 'instructions') else []
            
            if not instructions:
                return None
                
            # Analyze first instruction (usually the main one)
            main_instruction = instructions[0]
            program_id = str(tx.message.account_keys[main_instruction.program_id_index])
            
            # Determine transaction type
            tx_type = await self._determine_transaction_type(
                program_id, main_instruction, tx.message.account_keys
            )
            
            if tx_type == TransactionType.UNKNOWN:
                return None
                
            # Extract token mint if applicable
            token_mint = await self._extract_token_mint(
                program_id, main_instruction, tx.message.account_keys
            )
            
            # Calculate SOL amount
            amount_sol = await self._calculate_sol_amount(tx)
            
            # Check priority fee
            priority_fee = self._extract_priority_fee(tx)
            
            return MempoolTransaction(
                signature=signature,
                transaction_type=tx_type,
                program_id=program_id,
                accounts=[str(key) for key in tx.message.account_keys],
                amount_sol=amount_sol,
                token_mint=token_mint,
                priority_fee=priority_fee,
                metadata={
                    'instruction_count': len(instructions),
                    'is_versioned': hasattr(tx, 'version')
                }
            )
            
        except Exception as e:
            # Silently skip decode errors (many irrelevant txs)
            return None
            
    async def _determine_transaction_type(self, program_id: str, 
                                         instruction: Any, 
                                         account_keys: List) -> TransactionType:
        """
        Bestimmt den Transaction Type basierend auf Pattern
        """
        # Check for LP Creation
        if program_id in [RAYDIUM_V4, RAYDIUM_CLMM]:
            # Raydium LP Creation Pattern
            if len(instruction.accounts) > 15:  # LP creation has many accounts
                return TransactionType.LP_CREATION
                
        elif program_id == ORCA_WHIRLPOOL:
            # Orca Whirlpool Creation
            if self._is_whirlpool_creation(instruction):
                return TransactionType.LP_CREATION
                
        # Check for large trades
        elif program_id == JUPITER_V6:
            # Could be large buy/sell
            return await self._analyze_jupiter_swap(instruction, account_keys)
            
        # Check for token minting
        elif program_id == TOKEN_PROGRAM:
            if self._is_token_mint(instruction):
                return TransactionType.TOKEN_MINT
                
        return TransactionType.UNKNOWN
        
    def _is_whirlpool_creation(self, instruction: Any) -> bool:
        """
        Prüft ob es eine Whirlpool Creation ist
        """
        # Whirlpool creation has specific instruction discriminator
        try:
            data = instruction.data
            if len(data) > 8:
                discriminator = data[:8]
                # Known Whirlpool init discriminator
                if discriminator == bytes([0x95, 0xbb, 0x81, 0xfa, 0xaf, 0x23, 0xba, 0x59]):
                    return True
        except:
            pass
        return False
        
    def _is_token_mint(self, instruction: Any) -> bool:
        """
        Prüft ob es ein Token Mint ist
        """
        try:
            # Token mint instruction is usually 1 byte with value 0
            return len(instruction.data) == 1 and instruction.data[0] == 0
        except:
            return False
            
    async def _analyze_jupiter_swap(self, instruction: Any, 
                                   account_keys: List) -> TransactionType:
        """
        Analysiert Jupiter Swap für Buy/Sell Detection
        """
        # Check input/output tokens
        # If SOL -> Token = BUY
        # If Token -> SOL = SELL
        
        try:
            accounts = instruction.accounts
            if len(accounts) > 2:
                # Simplified check - would need more sophisticated parsing
                first_account = str(account_keys[accounts[0]])
                if "So11111" in first_account:  # SOL
                    return TransactionType.LARGE_BUY
                else:
                    return TransactionType.LARGE_SELL
        except:
            pass
            
        return TransactionType.UNKNOWN
        
    async def _extract_token_mint(self, program_id: str, 
                                 instruction: Any, 
                                 account_keys: List) -> Optional[str]:
        """
        Extrahiert Token Mint Address
        """
        try:
            # For LP creations, mint is usually in specific position
            if program_id in [RAYDIUM_V4, RAYDIUM_CLMM]:
                # Raydium: Token mint at index 8 and 9
                if len(instruction.accounts) > 9:
                    return str(account_keys[instruction.accounts[8]])
                    
            elif program_id == ORCA_WHIRLPOOL:
                # Orca: Different position
                if len(instruction.accounts) > 2:
                    return str(account_keys[instruction.accounts[2]])
                    
        except:
            pass
            
        return None
        
    async def _calculate_sol_amount(self, tx: VersionedTransaction) -> float:
        """
        Berechnet SOL Amount in Transaction
        """
        try:
            # Look for SOL transfer instructions
            for instruction in tx.message.instructions:
                program_id = str(tx.message.account_keys[instruction.program_id_index])
                
                # System program transfer
                if program_id == "11111111111111111111111111111111":
                    # Decode transfer amount
                    if len(instruction.data) >= 12:
                        # First 4 bytes = instruction type
                        # Next 8 bytes = lamports
                        lamports = int.from_bytes(instruction.data[4:12], 'little')
                        return lamports / 1e9
                        
        except:
            pass
            
        return 0
        
    def _extract_priority_fee(self, tx: VersionedTransaction) -> int:
        """
        Extrahiert Priority Fee aus Transaction
        """
        try:
            # Look for ComputeBudget program
            compute_budget_program = "ComputeBudget111111111111111111111111111111"
            
            for instruction in tx.message.instructions:
                program_id = str(tx.message.account_keys[instruction.program_id_index])
                
                if program_id == compute_budget_program:
                    # Parse compute unit price
                    if len(instruction.data) >= 9:
                        # Instruction type 3 = SetComputeUnitPrice
                        if instruction.data[0] == 3:
                            return int.from_bytes(instruction.data[1:9], 'little')
                            
        except:
            pass
            
        return 0
        
    async def _check_for_signals(self, tx: MempoolTransaction) -> Optional[EarlySignal]:
        """
        Prüft ob Transaction ein wichtiges Signal ist
        """
        # New LP Creation - HIGHEST PRIORITY
        if tx.transaction_type == TransactionType.LP_CREATION and tx.token_mint:
            # Check if it's a new token
            if not await self._is_known_token(tx.token_mint):
                return EarlySignal(
                    signal_type="NEW_LP_CREATION",
                    token_address=tx.token_mint,
                    confidence=0.9,
                    data={
                        'program': tx.program_id,
                        'initial_liquidity': tx.amount_sol,
                        'signature': tx.signature
                    },
                    action_required=True
                )
                
        # Large Buy Signal
        elif tx.transaction_type == TransactionType.LARGE_BUY and tx.amount_sol > 1:
            return EarlySignal(
                signal_type="WHALE_BUY",
                token_address=tx.token_mint or "unknown",
                confidence=0.7,
                data={
                    'amount_sol': tx.amount_sol,
                    'priority_fee': tx.priority_fee,
                    'accounts': tx.accounts[:5]  # First 5 accounts
                },
                action_required=tx.amount_sol > 5  # Action if > 5 SOL
            )
            
        # Suspicious Pattern Detection
        elif await self._is_suspicious_pattern(tx):
            return EarlySignal(
                signal_type="SUSPICIOUS_ACTIVITY",
                token_address=tx.token_mint or "unknown",
                confidence=0.5,
                data={
                    'pattern': 'potential_rug',
                    'signature': tx.signature
                },
                action_required=False
            )
            
        return None
        
    async def _is_known_token(self, token_mint: str) -> bool:
        """
        Prüft ob Token bereits bekannt ist
        """
        # Check gegen bekannte Token Liste
        known_tokens = {
            "So11111111111111111111111111111111111111112",  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            # ... more known tokens
        }
        
        if token_mint in known_tokens:
            return True
            
        # Check age via RPC
        try:
            if self.session:
                # Get token info
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getAccountInfo",
                    "params": [token_mint, {"encoding": "jsonParsed"}]
                }
                
                async with self.session.post(self.rpc_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        # If account exists and is old, it's known
                        if data.get('result', {}).get('value'):
                            return True
                            
        except:
            pass
            
        return False
        
    async def _is_suspicious_pattern(self, tx: MempoolTransaction) -> bool:
        """
        Erkennt verdächtige Pattern
        """
        # High priority fee for unknown token
        if tx.priority_fee > 100000 and tx.token_mint:
            if not await self._is_known_token(tx.token_mint):
                return True
                
        # Multiple similar transactions in short time
        recent_similar = [
            t for t in self.pending_txs
            if t.token_mint == tx.token_mint 
            and abs(t.timestamp - tx.timestamp) < 1
        ]
        
        if len(recent_similar) > 5:
            return True
            
        return False
        
    async def _emit_signal(self, signal: EarlySignal):
        """
        Sendet Signal an alle Callbacks
        """
        self.stats['signals_sent'] += 1
        
        # Log signal
        print(f"""
        🚨 EARLY SIGNAL DETECTED!
        Type: {signal.signal_type}
        Token: {signal.token_address[:8]}...
        Confidence: {signal.confidence:.1%}
        Action Required: {signal.action_required}
        Data: {signal.data}
        """)
        
        # Call all registered callbacks
        for callback in self.signal_callbacks:
            asyncio.create_task(callback(signal))
            
    def register_signal_callback(self, callback):
        """
        Registriert Callback für Signals
        """
        self.signal_callbacks.append(callback)
        
    async def _analyze_patterns(self):
        """
        Analysiert Pattern in Mempool Transactions
        """
        while self.running:
            await asyncio.sleep(5)  # Every 5 seconds
            
            if len(self.pending_txs) < 10:
                continue
                
            # Analyze recent transactions
            recent_txs = list(self.pending_txs)[-100:]  # Last 100
            
            # Find patterns
            patterns = await self._find_patterns(recent_txs)
            
            if patterns:
                for pattern in patterns:
                    print(f"📊 Pattern gefunden: {pattern}")
                    
    async def _find_patterns(self, transactions: List[MempoolTransaction]) -> List[Dict]:
        """
        Findet Pattern in Transactions
        """
        patterns = []
        
        # Pattern 1: Rapid LP Creations
        lp_creations = [
            tx for tx in transactions 
            if tx.transaction_type == TransactionType.LP_CREATION
        ]
        
        if len(lp_creations) > 3:
            # Multiple LPs in short time = potential pump wave
            patterns.append({
                'type': 'LP_CREATION_WAVE',
                'count': len(lp_creations),
                'tokens': [tx.token_mint for tx in lp_creations if tx.token_mint]
            })
            
        # Pattern 2: Whale Accumulation
        large_buys = [
            tx for tx in transactions
            if tx.transaction_type == TransactionType.LARGE_BUY
            and tx.amount_sol > 1
        ]
        
        # Group by token
        token_buys = {}
        for buy in large_buys:
            if buy.token_mint:
                token_buys[buy.token_mint] = token_buys.get(buy.token_mint, 0) + buy.amount_sol
                
        # Check for accumulation
        for token, total_sol in token_buys.items():
            if total_sol > 10:  # More than 10 SOL accumulated
                patterns.append({
                    'type': 'WHALE_ACCUMULATION',
                    'token': token,
                    'total_sol': total_sol
                })
                
        return patterns
        
    async def _update_slot_timing(self, slot: int):
        """
        Updates slot timing for latency calculations
        """
        # Track slot progression for timing analysis
        pass
        
    async def _stats_reporter(self):
        """
        Periodische Stats
        """
        while self.running:
            await asyncio.sleep(60)  # Every minute
            
            print(f"""
            📊 Mempool Monitor Stats:
            Monitored: {self.stats['total_monitored']}
            LP Creations: {self.stats['lp_creations']}
            Large Trades: {self.stats['large_trades']}
            Signals: {self.stats['signals_sent']}
            Queue: {len(self.pending_txs)}
            """)
            
    async def get_pending_transactions(self, token_mint: str) -> List[MempoolTransaction]:
        """
        Gibt pending Transactions für einen Token zurück
        """
        return [
            tx for tx in self.pending_txs
            if tx.token_mint == token_mint
        ]
        
    async def stop(self):
        """
        Stoppt Mempool Monitor
        """
        print("🛑 Stopping Mempool Monitor...")
        self.running = False
        
        if self.websocket:
            await self.websocket.close()
            
        if self.session:
            await self.session.close()

# Global Instance
mempool_monitor = None

async def initialize_mempool_monitor(rpc_url: str):
    """Initialisiert Mempool Monitor"""
    global mempool_monitor
    mempool_monitor = MempoolMonitor(rpc_url)
    return mempool_monitor

async def start_mempool_monitoring():
    """Startet Mempool Monitoring"""
    if mempool_monitor:
        await mempool_monitor.start()
        
async def register_for_signals(callback):
    """Registriert Callback für Early Signals"""
    if mempool_monitor:
        mempool_monitor.register_signal_callback(callback)