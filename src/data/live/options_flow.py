import time
import httpx

_cache = {}
_cache_ttl = 50


async def fetch_options_flow() -> dict:
    now = time.time()
    cache_key = "options"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    flow = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://www.barchart.com/proxies/core-api/v1/options/chain",
                params={
                    "symbol": "SPY",
                    "fields": "strikePrice,lastPrice,markPrice,bidPrice,askPrice,volume,openInterest,putCall,symbol,expirationDate",
                    "groupBy": "optionType",
                    "limit": 50,
                    "orderBy": "volume",
                    "orderDir": "desc",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    vol = item.get("volume", 0) or 0
                    oi = item.get("openInterest", 0) or 0
                    ratio = vol / oi if oi > 0 else 0

                    flow.append(
                        {
                            "symbol": item.get("symbol", "SPY"),
                            "strike": item.get("strikePrice", 0),
                            "expiry": item.get("expirationDate", ""),
                            "type": item.get("putCall", ""),
                            "price": item.get("lastPrice", 0),
                            "volume": vol,
                            "open_interest": oi,
                            "ratio": round(ratio, 2),
                            "unusual": ratio > 2.0,
                        }
                    )
        except Exception:
            pass

        if not flow:
            try:
                resp = await client.get(
                    "https://www.barchart.com/proxies/core-api/v1/options/chain",
                    params={
                        "symbol": "QQQ",
                        "fields": "strikePrice,lastPrice,volume,openInterest,putCall,symbol,expirationDate",
                        "limit": 30,
                        "orderBy": "volume",
                        "orderDir": "desc",
                    },
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", []):
                        vol = item.get("volume", 0) or 0
                        oi = item.get("openInterest", 0) or 0
                        flow.append(
                            {
                                "symbol": item.get("symbol", "QQQ"),
                                "strike": item.get("strikePrice", 0),
                                "expiry": item.get("expirationDate", ""),
                                "type": item.get("putCall", ""),
                                "price": item.get("lastPrice", 0),
                                "volume": vol,
                                "open_interest": oi,
                                "ratio": round(vol / oi, 2) if oi > 0 else 0,
                                "unusual": (vol / oi) > 2.0 if oi > 0 else False,
                            }
                        )
            except Exception:
                pass

    unusual_count = sum(1 for f in flow if f.get("unusual"))

    result = {
        "flow": flow[:30],
        "summary": {
            "total": len(flow),
            "unusual_count": unusual_count,
        },
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result

    return {k: v for k, v in result.items() if k != "_ts"}
