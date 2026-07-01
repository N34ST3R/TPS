import asyncio
import time
import httpx

_cache = {}
_cache_ttl = 50


async def fetch_social() -> dict:
    now = time.time()
    cache_key = "social"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    posts = []
    sentiment_summary = {"bullish": 0, "bearish": 0, "neutral": 0}

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://www.reddit.com/r/wallstreetbets/hot.json?limit=25",
                headers={"User-Agent": "TradingScanner/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for child in data.get("data", {}).get("children", []):
                    post = child.get("data", {})
                    title = post.get("title", "")
                    score_val = post.get("score", 0)
                    num_comments = post.get("num_comments", 0)
                    permalink = post.get("permalink", "")
                    created = post.get("created_utc", 0)

                    sentiment = _analyze_sentiment(title)
                    sentiment_summary[sentiment] += 1

                    posts.append(
                        {
                            "source": "Reddit WSB",
                            "title": title,
                            "score": score_val,
                            "comments": num_comments,
                            "url": f"https://reddit.com{permalink}"
                            if permalink
                            else "",
                            "created": created,
                            "sentiment": sentiment,
                            "tickers": _extract_tickers(title),
                        }
                    )
        except Exception:
            pass

        try:
            resp = await client.get(
                "https://api.stocktwits.com/api/2/streams/trending.json",
                headers={"User-Agent": "TradingScanner/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for msg in data.get("messages", [])[:20]:
                    body = msg.get("body", "")
                    entities = msg.get("entities", {})
                    ticker_list = [
                        t.get("symbol", "") for t in entities.get("symbols", [])
                    ]
                    sentiment_val = entities.get("sentiment", {}).get(
                        "basic", "Neutral"
                    )

                    s = (
                        "bullish"
                        if "Bullish" in sentiment_val
                        else "bearish"
                        if "Bearish" in sentiment_val
                        else "neutral"
                    )
                    sentiment_summary[s] += 1

                    posts.append(
                        {
                            "source": "StockTwits",
                            "title": body[:200],
                            "tickers": ticker_list,
                            "sentiment": s,
                            "url": f"https://stocktwits.com/message/{msg.get('id', '')}",
                            "created": msg.get("created_at", ""),
                        }
                    )
        except Exception:
            pass

    posts.sort(
        key=lambda x: (
            x.get("score", 0) if isinstance(x.get("score"), (int, float)) else 0
        ),
        reverse=True,
    )

    result = {
        "posts": posts[:40],
        "sentiment_summary": sentiment_summary,
        "total": len(posts),
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result

    return {k: v for k, v in result.items() if k != "_ts"}


def _analyze_sentiment(text: str) -> str:
    text_lower = text.lower()
    bullish = [
        "call",
        "buy",
        "long",
        "bull",
        "moon",
        "rocket",
        "yolo",
        "to the moon",
        "bullish",
        "squeeze",
    ]
    bearish = [
        "put",
        "sell",
        "short",
        "bear",
        "crash",
        "dump",
        "tank",
        "bearish",
        "rug",
    ]
    b = sum(1 for w in bullish if w in text_lower)
    s = sum(1 for w in bearish if w in text_lower)
    if b > s:
        return "bullish"
    elif s > b:
        return "bearish"
    return "neutral"


def _extract_tickers(text: str) -> list[str]:
    import re

    return list(set(re.findall(r"\$([A-Z]{1,5})\b", text.upper())))
