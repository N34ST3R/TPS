import time
import httpx

_cache = {}
_cache_ttl = 240


async def fetch_analyst() -> dict:
    now = time.time()
    cache_key = "analyst"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    ratings = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        popular = [
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
        ]

        for ticker in popular[:5]:
            try:
                resp = await client.get(
                    f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}",
                    params={
                        "modules": "upgradeDowngradeHistory,recommendationTrend,defaultKeyStatistics,financialData"
                    },
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    data = resp.json().get("quoteSummary", {}).get("result", [{}])[0]

                    stats = data.get("defaultKeyStatistics", {})
                    fin = data.get("financialData", {})
                    history = data.get("upgradeDowngradeHistory", {}).get("history", [])

                    target_low = stats.get("targetLowPrice", {}).get("raw", 0) or 0
                    target_high = stats.get("targetHighPrice", {}).get("raw", 0) or 0
                    target_mean = stats.get("targetMeanPrice", {}).get("raw", 0) or 0
                    target_median = (
                        stats.get("targetMedianPrice", {}).get("raw", 0) or 0
                    )
                    num_analysts = (
                        stats.get("numberOfAnalystOpinions", {}).get("raw", 0) or 0
                    )
                    rec = data.get("recommendationTrend", {}).get("trend", [{}])
                    rec_summary = rec[0] if rec else {}

                    recent_actions = []
                    for h in history[:5]:
                        firm = h.get("firm", "")
                        action = (
                            h.get("fromGrade", "") + " -> " + h.get("toGrade", "")
                            if h.get("toGrade")
                            else h.get("action", "")
                        )
                        date = h.get("epochGradeDate", 0)
                        recent_actions.append(
                            {
                                "firm": firm,
                                "action": action,
                                "date": date,
                            }
                        )

                    ratings.append(
                        {
                            "ticker": ticker,
                            "target_low": round(target_low, 2),
                            "target_high": round(target_high, 2),
                            "target_mean": round(target_mean, 2),
                            "target_median": round(target_median, 2),
                            "num_analysts": int(num_analysts),
                            "recommendation": rec_summary.get("recommendationKey", ""),
                            "strong_buy": int(rec_summary.get("strongBuy", 0) or 0),
                            "buy": int(rec_summary.get("buy", 0) or 0),
                            "hold": int(rec_summary.get("hold", 0) or 0),
                            "sell": int(rec_summary.get("sell", 0) or 0),
                            "strong_sell": int(rec_summary.get("strongSell", 0) or 0),
                            "recent_actions": recent_actions,
                        }
                    )
            except Exception:
                pass

    result = {
        "ratings": ratings,
        "total": len(ratings),
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result

    return {k: v for k, v in result.items() if k != "_ts"}
