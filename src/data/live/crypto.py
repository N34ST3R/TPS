import time
import httpx

_cache = {}
_cache_ttl = 25


async def fetch_crypto() -> dict:
    now = time.time()
    cache_key = "crypto"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    coins = []
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 20,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "1h,24h,7d",
                },
            )
            if resp.status_code == 200:
                for c in resp.json():
                    coins.append(
                        {
                            "id": c.get("id", ""),
                            "symbol": c.get("symbol", "").upper(),
                            "name": c.get("name", ""),
                            "price": c.get("current_price", 0),
                            "market_cap": c.get("market_cap", 0),
                            "volume_24h": c.get("total_volume", 0),
                            "change_1h": c.get(
                                "price_change_percentage_1h_in_currency", 0
                            )
                            or 0,
                            "change_24h": c.get("price_change_percentage_24h", 0) or 0,
                            "change_7d": c.get(
                                "price_change_percentage_7d_in_currency", 0
                            )
                            or 0,
                            "rank": c.get("market_cap_rank", 0),
                            "image": c.get("image", ""),
                        }
                    )
        except Exception:
            pass

    result = {
        "coins": coins,
        "total": len(coins),
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result

    return {k: v for k, v in result.items() if k != "_ts"}
