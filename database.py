# database.py
"""
Database Handler für Trade History und Performance Analytics
"""
import aiosqlite
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import os

class TradeDatabase:
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
        
    async def initialize(self):
        """Erstellt Database und Tables"""
        self.conn = await aiosqlite.connect(self.db_path)
        
        # Trades Table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                token_address TEXT NOT NULL,
                symbol TEXT,
                trade_type TEXT NOT NULL,  -- 'BUY' or 'SELL'
                amount_sol REAL,
                token_amount REAL,
                price REAL,
                tx_id TEXT UNIQUE,
                profit_sol REAL,
                profit_percent REAL,
                position_data TEXT,  -- JSON
                metrics TEXT  -- JSON
            )
        """)
        
        # Positions Table (für aktive Positionen)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                token_address TEXT PRIMARY KEY,
                symbol TEXT,
                entry_time REAL,
                entry_price REAL,
                invested_sol REAL,
                current_amount REAL,
                highest_price REAL,
                lowest_price REAL,
                last_update REAL,
                metrics TEXT  -- JSON
            )
        """)
        
        # Performance Stats Table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_trades INTEGER,
                profitable_trades INTEGER,
                total_volume_sol REAL,
                total_profit_sol REAL,
                best_trade_profit REAL,
                worst_trade_loss REAL,
                win_rate REAL,
                avg_hold_time_minutes REAL
            )
        """)
        
        # Alerts Log
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                token_address TEXT,
                symbol TEXT,
                score REAL,
                action_taken TEXT,  -- 'BOUGHT', 'IGNORED', 'AUTO_BUY'
                metrics TEXT  -- JSON
            )
        """)
        
        # Create Indexes
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_token ON trades(token_address)"
        )
        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC)"
        )
        
        await self.conn.commit()
        
    async def record_trade(self, trade_data: Dict[str, Any]) -> int:
        """Speichert einen Trade"""
        try:
            cursor = await self.conn.execute("""
                INSERT INTO trades (
                    timestamp, token_address, symbol, trade_type,
                    amount_sol, token_amount, price, tx_id,
                    profit_sol, profit_percent, position_data, metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data.get('timestamp', datetime.now().timestamp()),
                trade_data['token_address'],
                trade_data.get('symbol', ''),
                trade_data['trade_type'],
                trade_data.get('amount_sol', 0),
                trade_data.get('token_amount', 0),
                trade_data.get('price', 0),
                trade_data.get('tx_id', ''),
                trade_data.get('profit_sol', 0),
                trade_data.get('profit_percent', 0),
                json.dumps(trade_data.get('position_data', {})),
                json.dumps(trade_data.get('metrics', {}))
            ))
            
            await self.conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            print(f"Database Error (record_trade): {e}")
            return -1
            
    async def update_position(self, position_data: Dict[str, Any]):
        """Aktualisiert eine aktive Position"""
        try:
            await self.conn.execute("""
                INSERT OR REPLACE INTO positions (
                    token_address, symbol, entry_time, entry_price,
                    invested_sol, current_amount, highest_price,
                    lowest_price, last_update, metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data['token_address'],
                position_data.get('symbol', ''),
                position_data.get('entry_time', 0),
                position_data.get('entry_price', 0),
                position_data.get('invested_sol', 0),
                position_data.get('current_amount', 0),
                position_data.get('highest_price', 0),
                position_data.get('lowest_price', float('inf')),
                datetime.now().timestamp(),
                json.dumps(position_data.get('metrics', {}))
            ))
            
            await self.conn.commit()
            
        except Exception as e:
            print(f"Database Error (update_position): {e}")
            
    async def remove_position(self, token_address: str):
        """Entfernt eine geschlossene Position"""
        try:
            await self.conn.execute(
                "DELETE FROM positions WHERE token_address = ?",
                (token_address,)
            )
            await self.conn.commit()
        except Exception as e:
            print(f"Database Error (remove_position): {e}")
            
    async def record_alert(self, alert_data: Dict[str, Any]):
        """Speichert einen Alert"""
        try:
            await self.conn.execute("""
                INSERT INTO alerts (
                    timestamp, token_address, symbol, score,
                    action_taken, metrics
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert_data.get('timestamp', datetime.now().timestamp()),
                alert_data['token_address'],
                alert_data.get('symbol', ''),
                alert_data.get('score', 0),
                alert_data.get('action_taken', 'IGNORED'),
                json.dumps(alert_data.get('metrics', {}))
            ))
            
            await self.conn.commit()
            
        except Exception as e:
            print(f"Database Error (record_alert): {e}")
            
    async def get_trade_history(self, limit: int = 100, 
                               token_address: Optional[str] = None) -> List[Dict]:
        """Holt Trade History"""
        query = """
            SELECT * FROM trades
            WHERE 1=1
        """
        params = []
        
        if token_address:
            query += " AND token_address = ?"
            params.append(token_address)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        
        trades = []
        for row in rows:
            trade = dict(row)
            trade['position_data'] = json.loads(trade.get('position_data', '{}'))
            trade['metrics'] = json.loads(trade.get('metrics', '{}'))
            trades.append(trade)
            
        return trades
        
    async def get_performance_stats(self, days: int = 7) -> Dict[str, Any]:
        """Berechnet Performance Statistiken"""
        since = datetime.now().timestamp() - (days * 86400)
        
        # Hole alle Trades im Zeitraum
        cursor = await self.conn.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as wins,
                SUM(profit_sol) as total_profit,
                AVG(profit_percent) as avg_profit_pct,
                MAX(profit_sol) as best_trade,
                MIN(profit_sol) as worst_trade,
                SUM(amount_sol) as total_volume
            FROM trades
            WHERE timestamp > ? AND trade_type = 'SELL'
        """, (since,))
        
        stats = dict(await cursor.fetchone())
        
        # Berechne Win Rate
        if stats['total_trades'] > 0:
            stats['win_rate'] = (stats['wins'] / stats['total_trades']) * 100
        else:
            stats['win_rate'] = 0
            
        # Hole aktive Positionen
        cursor = await self.conn.execute(
            "SELECT COUNT(*) as active_positions FROM positions"
        )
        active = await cursor.fetchone()
        stats['active_positions'] = active['active_positions']
        
        return stats
        
    async def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """Holt die profitabelsten Trades"""
        cursor = await self.conn.execute("""
            SELECT 
                token_address,
                symbol,
                profit_sol,
                profit_percent,
                timestamp,
                tx_id
            FROM trades
            WHERE trade_type = 'SELL' AND profit_sol > 0
            ORDER BY profit_percent DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in await cursor.fetchall()]
        
    async def update_daily_stats(self):
        """Aktualisiert tägliche Statistiken"""
        today = datetime.now().date().isoformat()
        
        # Berechne Stats für heute
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        
        cursor = await self.conn.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as profitable,
                SUM(amount_sol) as volume,
                SUM(profit_sol) as profit,
                MAX(profit_sol) as best,
                MIN(profit_sol) as worst
            FROM trades
            WHERE timestamp > ? AND trade_type = 'SELL'
        """, (start_of_day,))
        
        stats = dict(await cursor.fetchone())
        
        # Win Rate
        win_rate = 0
        if stats['total_trades'] > 0:
            win_rate = (stats['profitable'] / stats['total_trades']) * 100
            
        # Speichere/Update Daily Stats
        await self.conn.execute("""
            INSERT OR REPLACE INTO daily_stats (
                date, total_trades, profitable_trades,
                total_volume_sol, total_profit_sol,
                best_trade_profit, worst_trade_loss,
                win_rate, avg_hold_time_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            today,
            stats['total_trades'] or 0,
            stats['profitable'] or 0,
            stats['volume'] or 0,
            stats['profit'] or 0,
            stats['best'] or 0,
            stats['worst'] or 0,
            win_rate,
            0  # TODO: Calculate avg hold time
        ))
        
        await self.conn.commit()
        
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Löscht alte Daten"""
        cutoff = datetime.now().timestamp() - (days_to_keep * 86400)
        
        await self.conn.execute(
            "DELETE FROM trades WHERE timestamp < ?",
            (cutoff,)
        )
        await self.conn.execute(
            "DELETE FROM alerts WHERE timestamp < ?",
            (cutoff,)
        )
        
        await self.conn.commit()
        
    async def close(self):
        """Schließt Database Connection"""
        if self.conn:
            await self.conn.close()

# Globale Database Instanz
db = TradeDatabase()

# Helper Functions für einfachen Zugriff
async def init_database():
    """Initialisiert die Database"""
    await db.initialize()

async def log_trade(trade_data: Dict):
    """Loggt einen Trade"""
    return await db.record_trade(trade_data)

async def get_stats(days: int = 7) -> Dict:
    """Holt Performance Stats"""
    return await db.get_performance_stats(days)