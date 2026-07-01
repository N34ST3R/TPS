import asyncio
import time
from collections import defaultdict


class RateLimiter:
    def __init__(self):
        self._limits = {
            "yahoo": {"interval": 0.5, "tokens": 2, "max": 2},
            "webull": {"interval": 1.0, "tokens": 1, "max": 1},
            "polymarket": {"interval": 0.1, "tokens": 10, "max": 10},
            "solana": {"interval": 0.1, "tokens": 10, "max": 10},
            "birdeye": {"interval": 0.2, "tokens": 5, "max": 5},
            "scraper": {"interval": 1.0, "tokens": 2, "max": 2},
        }
        self._last_refill = defaultdict(time.time)

    async def acquire(self, source: str):
        if source not in self._limits:
            return
        limit = self._limits[source]
        now = time.time()
        elapsed = now - self._last_refill[source]
        limit["tokens"] = min(
            limit["max"], limit["tokens"] + elapsed / limit["interval"]
        )
        self._last_refill[source] = now
        if limit["tokens"] < 1:
            wait = (1 - limit["tokens"]) * limit["interval"]
            await asyncio.sleep(wait)
            limit["tokens"] = 0
        else:
            limit["tokens"] -= 1


rate_limiter = RateLimiter()
