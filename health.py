"""
Health check and monitoring endpoints
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from aiohttp import web

logger = logging.getLogger(__name__)

# Prometheus metrics
trades_total = Counter('trades_total', 'Total number of trades', ['action'])
tokens_scanned = Counter('tokens_scanned_total', 'Total tokens scanned')
tokens_analyzed = Counter('tokens_analyzed_total', 'Total tokens analyzed')
active_positions = Gauge('active_positions', 'Number of active positions')
wallet_balance = Gauge('wallet_balance_sol', 'Wallet balance in SOL')
trade_profit_loss = Histogram('trade_profit_loss', 'Trade profit/loss in SOL',
                               buckets=[0.1, 0.5, 1, 2, 5, 10, 25, 50, 100])
ai_confidence_score = Histogram('ai_confidence_score', 'AI confidence scores',
                                 buckets=[0, 20, 40, 60, 80, 90, 95, 100])


class HealthCheck:
    """Health check manager"""

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.is_healthy = True
        self.components_status = {
            "scanner": "unknown",
            "analyzer": "unknown",
            "trader": "unknown",
            "ai_engine": "unknown",
            "database": "unknown",
            "telegram_bot": "unknown"
        }

    def get_uptime(self) -> float:
        """Get uptime in seconds"""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def update_component_status(self, component: str, status: str):
        """Update component health status"""
        if component in self.components_status:
            self.components_status[component] = status
            logger.info(f"Component {component} status: {status}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        all_healthy = all(
            status in ["healthy", "unknown"]
            for status in self.components_status.values()
        )

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "uptime_seconds": self.get_uptime(),
            "timestamp": datetime.utcnow().isoformat(),
            "components": self.components_status
        }


# Global health check instance
health_check = HealthCheck()


async def health_endpoint(request):
    """Health check endpoint handler"""
    health_status = health_check.get_health_status()
    status_code = 200 if health_status["status"] == "healthy" else 503

    return web.json_response(health_status, status=status_code)


async def readiness_endpoint(request):
    """Readiness check endpoint handler"""
    # Check if critical components are ready
    critical_components = ["database", "scanner"]
    is_ready = all(
        health_check.components_status.get(comp) == "healthy"
        for comp in critical_components
    )

    return web.json_response({
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat()
    }, status=200 if is_ready else 503)


async def liveness_endpoint(request):
    """Liveness check endpoint handler"""
    # Simple liveness check - if we can respond, we're alive
    return web.json_response({
        "alive": True,
        "uptime_seconds": health_check.get_uptime(),
        "timestamp": datetime.utcnow().isoformat()
    })


async def metrics_endpoint(request):
    """Prometheus metrics endpoint handler"""
    metrics = generate_latest()
    return web.Response(body=metrics, content_type=CONTENT_TYPE_LATEST)


async def start_health_server(port: int = 8000):
    """Start health check HTTP server"""
    app = web.Application()
    app.router.add_get('/health', health_endpoint)
    app.router.add_get('/ready', readiness_endpoint)
    app.router.add_get('/alive', liveness_endpoint)
    app.router.add_get('/metrics', metrics_endpoint)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"Health check server started on port {port}")
    return runner


# Monitoring helper functions
def record_trade(action: str, profit_loss: float = 0.0):
    """Record a trade in metrics"""
    trades_total.labels(action=action).inc()
    if profit_loss != 0:
        trade_profit_loss.observe(profit_loss)


def record_token_scan():
    """Record a token scan"""
    tokens_scanned.inc()


def record_token_analysis():
    """Record a token analysis"""
    tokens_analyzed.inc()


def update_active_positions(count: int):
    """Update active positions count"""
    active_positions.set(count)


def update_wallet_balance(balance: float):
    """Update wallet balance"""
    wallet_balance.set(balance)


def record_ai_confidence(confidence: float):
    """Record AI confidence score"""
    ai_confidence_score.observe(confidence)
