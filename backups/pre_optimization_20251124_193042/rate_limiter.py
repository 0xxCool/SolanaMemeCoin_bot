# rate_limiter.py
"""
Token bucket rate limiter for API calls
"""
import asyncio
import time
from typing import Dict, Optional

class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, calls_per_second: float):
        self.rate = calls_per_second
        self.tokens = calls_per_second
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait until a token is available"""
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.last_update = now

                # Add tokens based on elapsed time
                self.tokens = min(
                    self.rate,
                    self.tokens + elapsed * self.rate
                )

                if self.tokens >= 1:
                    self.tokens -= 1
                    return

                # Wait until next token
                sleep_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(sleep_time)

class APIRateLimiters:
    """Global rate limiters for all APIs"""

    dexscreener = RateLimiter(calls_per_second=10)  # 10/sec
    jupiter = RateLimiter(calls_per_second=10)      # 10/sec
    rugcheck = RateLimiter(calls_per_second=2)      # 2/sec (stricter)
    birdeye = RateLimiter(calls_per_second=5)       # 5/sec
    solana_rpc = RateLimiter(calls_per_second=100)  # 100/sec
