"""
WebSocket API Server for Real-Time Synchronization
Synchronizes Windows App, Android App, and Telegram Bot
"""
import asyncio
import json
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from trader import trader
    from scanner import scanner
    from integration import integration_manager
    from auto_trader import auto_trader
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

app = FastAPI(title="Solana Trading Bot Sync API")

# Enable CORS for cross-platform access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            'windows': set(),
            'android': set(),
            'telegram': set()
        }

    async def connect(self, websocket: WebSocket, client_type: str):
        await websocket.accept()
        self.active_connections[client_type].add(websocket)

    def disconnect(self, websocket: WebSocket, client_type: str):
        self.active_connections[client_type].discard(websocket)

    async def broadcast(self, message: dict, exclude_type: str = None):
        """Broadcast message to all connected clients"""
        disconnected = []

        for client_type, connections in self.active_connections.items():
            if client_type == exclude_type:
                continue

            for connection in connections.copy():
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append((client_type, connection))

        # Remove disconnected clients
        for client_type, connection in disconnected:
            self.disconnect(connection, client_type)

    async def send_to_type(self, client_type: str, message: dict):
        """Send message to specific client type"""
        disconnected = []

        for connection in self.active_connections[client_type].copy():
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)

        # Remove disconnected
        for connection in disconnected:
            self.disconnect(connection, client_type)


manager = ConnectionManager()


@app.get("/")
async def root():
    return {"status": "Solana Trading Bot Sync API", "version": "1.0"}


@app.get("/api/status")
async def get_status():
    """Get current bot status"""
    if not CORE_AVAILABLE:
        return {"error": "Bot core not available"}

    return {
        "timestamp": datetime.now().isoformat(),
        "scanner_running": scanner.running if hasattr(scanner, 'running') else False,
        "positions_count": len(trader.positions) if hasattr(trader, 'positions') else 0,
        "total_pnl": float(trader.total_pnl) if hasattr(trader, 'total_pnl') else 0.0,
        "win_rate": float(trader.win_rate) if hasattr(trader, 'win_rate') else 0.0,
        "total_trades": trader.total_trades if hasattr(trader, 'total_trades') else 0,
        "auto_buy_enabled": auto_trader.settings.auto_buy_enabled if hasattr(auto_trader, 'settings') else False,
        "auto_sell_enabled": auto_trader.settings.auto_sell_enabled if hasattr(auto_trader, 'settings') else False
    }


@app.get("/api/positions")
async def get_positions():
    """Get current trading positions"""
    if not CORE_AVAILABLE or not hasattr(trader, 'positions'):
        return []

    positions = []
    for addr, pos in trader.positions.items():
        positions.append({
            'address': addr,
            'symbol': pos.symbol,
            'entry_price': float(pos.entry_price),
            'current_price': float(pos.current_price),
            'amount_sol': float(pos.amount_sol),
            'entry_time': pos.entry_time,
            'stop_loss': float(pos.stop_loss) if pos.stop_loss else 0,
            'take_profit': float(pos.take_profit) if pos.take_profit else 0,
            'pnl_pct': ((pos.current_price - pos.entry_price) / pos.entry_price) * 100 if pos.entry_price else 0
        })

    return positions


@app.post("/api/settings/update")
async def update_settings(settings: dict):
    """Update bot settings"""
    if not CORE_AVAILABLE:
        return {"success": False, "error": "Bot core not available"}

    try:
        # Update auto-trader settings
        if 'auto_buy_enabled' in settings:
            auto_trader.settings.auto_buy_enabled = settings['auto_buy_enabled']

        if 'auto_sell_enabled' in settings:
            auto_trader.settings.auto_sell_enabled = settings['auto_sell_enabled']

        if 'base_trade_amount_sol' in settings:
            from config import trading_config
            trading_config.BASE_TRADE_AMOUNT_SOL = float(settings['base_trade_amount_sol'])

        # Broadcast settings change to all clients
        await manager.broadcast({
            'type': 'settings_updated',
            'settings': settings,
            'timestamp': datetime.now().isoformat()
        })

        return {"success": True, "message": "Settings updated"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/trade/close/{token_address}")
async def close_position(token_address: str):
    """Close a trading position"""
    if not CORE_AVAILABLE:
        return {"success": False, "error": "Bot core not available"}

    try:
        success = await trader.close_position(token_address, "MANUAL_GUI")

        # Notify all clients
        await manager.broadcast({
            'type': 'position_closed',
            'token_address': token_address,
            'timestamp': datetime.now().isoformat()
        })

        return {"success": success}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.websocket("/ws/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, client_type)

    try:
        # Send initial status
        status = await get_status()
        await websocket.send_json({
            'type': 'initial_status',
            'data': status
        })

        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get('type') == 'update_settings':
                await update_settings(message.get('data', {}))

            elif message.get('type') == 'close_position':
                token_address = message.get('token_address')
                await close_position(token_address)

            # Broadcast to other clients
            await manager.broadcast({
                'type': 'client_action',
                'client_type': client_type,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }, exclude_type=client_type)

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_type)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_type)


async def status_broadcast_loop():
    """Periodically broadcast status to all clients"""
    while True:
        try:
            await asyncio.sleep(2)  # Every 2 seconds

            if CORE_AVAILABLE:
                status = await get_status()
                positions = await get_positions()

                await manager.broadcast({
                    'type': 'status_update',
                    'status': status,
                    'positions': positions,
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            print(f"Broadcast loop error: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup"""
    asyncio.create_task(status_broadcast_loop())
    print("✅ Sync API Server started")


def start_server(host: str = "0.0.0.0", port: int = 8765):
    """Start the API server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
