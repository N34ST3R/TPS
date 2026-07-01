import asyncio
import time
import yfinance as yf

_cache = {}
_cache_ttl = 60

ANALYST_TICKERS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "TSLA",
    "META",
    "AMD",
    "NFLX",
    "JPM",
    "JNJ",
    "V",
    "XOM",
    "UNH",
    "WMT",
    "PG",
    "MA",
    "HD",
    "CVX",
    "COST",
]


async def fetch_analyst() -> dict:
    now = time.time()
    cache_key = "analyst"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    ratings = []

    def _fetch():
        for ticker in ANALYST_TICKERS:
            try:
                t = yf.Ticker(ticker)
                info = t.info
                if not info or info.get("quoteType") is None:
                    continue

                target_low = info.get("targetLowPrice") or 0
                target_high = info.get("targetHighPrice") or 0
                target_mean = info.get("targetMeanPrice") or 0
                target_median = info.get("targetMedianPrice") or 0
                num_analysts = info.get("numberOfAnalystOpinions") or 0
                rec = info.get("recommendationKey", "")

                strong_buy = info.get("strongBuy") or 0
                buy = info.get("buy") or 0
                hold = info.get("hold") or 0
                sell = info.get("sell") or 0
                strong_sell = info.get("strongSell") or 0

                recent_actions = []
                try:
                    upgrades = t.upgrades_downgrades
                    if upgrades is not None and not upgrades.empty:
                        for _, row in upgrades.head(5).iterrows():
                            firm = str(row.get("Firm", ""))
                            action = (
                                str(row.get("Action", ""))
                                + " "
                                + str(row.get("ToGrade", ""))
                            )
                            recent_actions.append(
                                {"firm": firm, "action": action.strip()}
                            )
                except Exception:
                    pass

                if num_analysts > 0:
                    ratings.append(
                        {
                            "ticker": ticker,
                            "target_low": round(float(target_low), 2),
                            "target_high": round(float(target_high), 2),
                            "target_mean": round(float(target_mean), 2),
                            "target_median": round(float(target_median), 2),
                            "num_analysts": int(num_analysts),
                            "recommendation": rec,
                            "strong_buy": int(strong_buy),
                            "buy": int(buy),
                            "hold": int(hold),
                            "sell": int(sell),
                            "strong_sell": int(strong_sell),
                            "recent_actions": recent_actions,
                        }
                    )
            except Exception:
                pass

    await asyncio.to_thread(_fetch)

    result = {"ratings": ratings, "total": len(ratings), "updated_at": now}
    result["_ts"] = now
    _cache[cache_key] = result
    return {k: v for k, v in result.items() if k != "_ts"}
