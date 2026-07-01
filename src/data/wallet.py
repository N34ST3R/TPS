import asyncio
import httpx
from src.data.cache import cache
from src.data.rate_limiter import rate_limiter
from src.store.config import SOLANA_RPC, BIRDEYE_API_KEY

BIRDEYE_API = "https://public-api.birdeye.so"


async def get_solana_balance(address: str) -> float:
    await rate_limiter.acquire("solana")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]}
    async with httpx.AsyncClient() as client:
        resp = await client.post(SOLANA_RPC, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        return result.get("value", 0) / 1e9


async def get_solana_tokens(address: str) -> list[dict]:
    await rate_limiter.acquire("solana")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"},
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(SOLANA_RPC, json=payload, timeout=10)
        resp.raise_for_status()
        accounts = resp.json().get("result", {}).get("value", [])
        tokens = []
        for acc in accounts:
            info = acc["account"]["data"]["parsed"]["info"]
            tokens.append(
                {
                    "mint": info["mint"],
                    "amount": float(info["tokenAmount"]["uiAmount"] or 0),
                    "decimals": info["tokenAmount"]["decimals"],
                }
            )
        return tokens


async def get_token_price(token_address: str) -> dict:
    if not BIRDEYE_API_KEY:
        return {"price": 0, "volume": 0}
    await rate_limiter.acquire("birdeye")
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BIRDEYE_API}/defi/token_overview",
            params={"address": token_address},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "symbol": data.get("symbol", "unknown"),
            "price": data.get("price", 0),
            "volume": data.get("volume24hUSD", 0),
            "liquidity": data.get("liquidity", 0),
        }


async def get_wallet_portfolio(address: str) -> dict:
    cache_key = f"wallet:{address}"
    cached = cache.get(cache_key, ttl=60)
    if cached:
        return cached

    sol_balance = await get_solana_balance(address)
    tokens = await get_solana_tokens(address)
    portfolio = {
        "address": address,
        "sol_balance": sol_balance,
        "tokens": tokens,
        "token_count": len(tokens),
    }
    cache.set(cache_key, portfolio)
    return portfolio
