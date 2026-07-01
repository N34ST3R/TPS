import asyncio
import time
import httpx
from xml.etree import ElementTree

_cache = {}
_cache_ttl = 240


async def fetch_calendar() -> dict:
    now = time.time()
    cache_key = "calendar"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    events = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                headers={"User-Agent": "TradingScanner/1.0"},
            )
            if resp.status_code == 200:
                for item in resp.json():
                    events.append(
                        {
                            "title": item.get("title", ""),
                            "country": item.get("country", ""),
                            "date": item.get("date", ""),
                            "time": item.get("time", ""),
                            "impact": item.get("impact", "").lower(),
                            "forecast": item.get("forecast", ""),
                            "previous": item.get("previous", ""),
                            "actual": item.get("actual", ""),
                        }
                    )
        except Exception:
            pass

        if not events:
            try:
                feeds = [
                    (
                        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
                        "Yahoo Finance",
                    ),
                ]
                for url, src in feeds:
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        root = ElementTree.fromstring(resp.text)
                        for item in root.iter("item"):
                            title = item.findtext("title", "")
                            pub = item.findtext("pubDate", "")
                            if title:
                                events.append(
                                    {
                                        "title": title.strip(),
                                        "country": "US",
                                        "date": pub.strip() if pub else "",
                                        "time": "",
                                        "impact": "medium",
                                        "forecast": "",
                                        "previous": "",
                                        "actual": "",
                                    }
                                )
            except Exception:
                pass

    events.sort(key=lambda x: x.get("date", ""), reverse=True)

    result = {
        "events": events[:30],
        "total": len(events),
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result

    return {k: v for k, v in result.items() if k != "_ts"}
