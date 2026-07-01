import asyncio
import time
import httpx
from xml.etree import ElementTree

_cache = {}
_cache_ttl = {}

NEWS_FEEDS = {
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "Reuters Markets": "https://feeds.reuters.com/reuters/marketsNews",
    "Reuters Tech": "https://feeds.reuters.com/reuters/technologyNews",
    "CNBC Top": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "CNBC Markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "CNBC Finance": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "MarketWatch Top": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "MarketWatch Markets": "https://feeds.marketwatch.com/marketwatch/marketpulse/",
    "Investing.com": "https://www.investing.com/rss/news_285.rss",
    "Bloomberg via Google": "https://news.google.com/rss/search?q=stock+market+when:1d&hl=en-US&gl=US&ceid=US:en",
    "Seeking Alpha": "https://seekingalpha.com/market_currents.xml",
    "Financial Times": "https://www.ft.com/rss/home",
    "WSJ Markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "Barrons": "https://www.barrons.com/feed",
    "TheStreet": "https://www.thestreet.com/feeds/all.rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "DeFi Pulse": "https://defipulse.com/blog/feed",
}


def _parse_rss(xml_text: str, source: str) -> list[dict]:
    articles = []
    try:
        root = ElementTree.fromstring(xml_text)
        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            description = item.findtext("description", "")
            if title:
                articles.append(
                    {
                        "source": source,
                        "title": title.strip(),
                        "url": link.strip() if link else "",
                        "published": pub_date.strip() if pub_date else "",
                        "summary": description.strip()[:200] if description else "",
                    }
                )
    except ElementTree.ParseError:
        pass
    return articles


def _sentiment_from_headline(title: str) -> str:
    title_lower = title.lower()
    bullish_words = [
        "surge",
        "rally",
        "gain",
        "rise",
        "jump",
        "soar",
        "bull",
        "upgrade",
        "beat",
        "record high",
        "boom",
        "profit",
        "optimism",
        "recovery",
        "outperform",
        "breakout",
    ]
    bearish_words = [
        "crash",
        "drop",
        "fall",
        "plunge",
        "sink",
        "bear",
        "downgrade",
        "miss",
        "loss",
        "slump",
        "recession",
        "fear",
        "sell-off",
        "selloff",
        "warning",
        "risk",
        "collapse",
        "bankrupt",
    ]

    b_count = sum(1 for w in bullish_words if w in title_lower)
    s_count = sum(1 for w in bearish_words if w in title_lower)

    if b_count > s_count:
        return "bullish"
    elif s_count > b_count:
        return "bearish"
    return "neutral"


async def fetch_news() -> dict:
    now = time.time()
    cache_key = "news"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl.get(
        cache_key, 25
    ):
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    all_articles = []
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:

        async def fetch_one(name: str, url: str):
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    return _parse_rss(resp.text, name)
            except Exception:
                pass
            return []

        tasks = [fetch_one(name, url) for name, url in NEWS_FEEDS.items()]
        results = await asyncio.gather(*tasks)
        for r in results:
            all_articles.extend(r)

    for a in all_articles:
        a["sentiment"] = _sentiment_from_headline(a["title"])

    seen_titles = set()
    unique = []
    for a in all_articles:
        t = a["title"].lower().strip()
        if t not in seen_titles:
            seen_titles.add(t)
            unique.append(a)

    unique.sort(key=lambda x: x.get("published", ""), reverse=True)

    result = {
        "articles": unique[:100],
        "total": len(unique),
        "sources": list(NEWS_FEEDS.keys()),
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result
    _cache_ttl[cache_key] = 25

    return {k: v for k, v in result.items() if k != "_ts"}
