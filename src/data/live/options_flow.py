import asyncio
import time
import yfinance as yf

_cache = {}
_cache_ttl = 60

OPTIONS_TICKERS = [
    "SPY",
    "QQQ",
    "AAPL",
    "NVDA",
    "TSLA",
    "AMZN",
    "META",
    "MSFT",
    "GOOGL",
    "AMD",
]


async def fetch_options_flow() -> dict:
    now = time.time()
    cache_key = "options"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    flow = []

    def _fetch():
        for ticker in OPTIONS_TICKERS:
            try:
                t = yf.Ticker(ticker)
                exps = t.options
                if not exps:
                    continue
                expiry = exps[0]
                chain = t.option_chain(expiry)

                calls = chain.calls
                puts = chain.puts

                for _, row in calls.iterrows():
                    vol = int(row.get("volume", 0) or 0)
                    oi = int(row.get("openInterest", 0) or 0)
                    ratio = round(vol / oi, 2) if oi > 0 else 0
                    flow.append(
                        {
                            "symbol": ticker,
                            "strike": float(row.get("strike", 0)),
                            "expiry": expiry,
                            "type": "call",
                            "price": round(
                                float(
                                    row.get("lastPrice", 0) or row.get("ask", 0) or 0
                                ),
                                2,
                            ),
                            "volume": vol,
                            "open_interest": oi,
                            "ratio": ratio,
                            "unusual": ratio > 2.0 and vol > 100,
                            "bid": round(float(row.get("bid", 0) or 0), 2),
                            "ask": round(float(row.get("ask", 0) or 0), 2),
                            "implied_volatility": round(
                                float(row.get("impliedVolatility", 0) or 0), 4
                            ),
                        }
                    )

                for _, row in puts.iterrows():
                    vol = int(row.get("volume", 0) or 0)
                    oi = int(row.get("openInterest", 0) or 0)
                    ratio = round(vol / oi, 2) if oi > 0 else 0
                    flow.append(
                        {
                            "symbol": ticker,
                            "strike": float(row.get("strike", 0)),
                            "expiry": expiry,
                            "type": "put",
                            "price": round(
                                float(
                                    row.get("lastPrice", 0) or row.get("ask", 0) or 0
                                ),
                                2,
                            ),
                            "volume": vol,
                            "open_interest": oi,
                            "ratio": ratio,
                            "unusual": ratio > 2.0 and vol > 100,
                            "bid": round(float(row.get("bid", 0) or 0), 2),
                            "ask": round(float(row.get("ask", 0) or 0), 2),
                            "implied_volatility": round(
                                float(row.get("impliedVolatility", 0) or 0), 4
                            ),
                        }
                    )
            except Exception:
                pass

    await asyncio.to_thread(_fetch)

    flow.sort(key=lambda x: x.get("volume", 0), reverse=True)
    unusual_count = sum(1 for f in flow if f.get("unusual"))

    result = {
        "flow": flow[:100],
        "summary": {"total": len(flow), "unusual_count": unusual_count},
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result
    return {k: v for k, v in result.items() if k != "_ts"}
