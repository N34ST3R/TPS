import asyncio
import httpx
from src.data.cache import cache
from src.data.rate_limiter import rate_limiter

GAMMA_API = "https://gamma-api.polymarket.com"


async def fetch_markets(query: str = None, limit: int = 20) -> list[dict]:
    cache_key = f"polymarket:{query}:{limit}"
    cached = cache.get(cache_key, ttl=60)
    if cached is not None:
        return cached

    await rate_limiter.acquire("polymarket")
    params = {"limit": limit, "active": "true", "closed": "false"}
    if query:
        params["tag"] = query

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GAMMA_API}/markets", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    cache.set(cache_key, data)
    return data


async def fetch_market_by_id(market_id: str) -> dict:
    await rate_limiter.acquire("polymarket")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GAMMA_API}/markets/{market_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()


async def get_active_markets() -> list[dict]:
    return await fetch_markets(limit=50)
