import asyncio
import time
import httpx
import re
from typing import Optional

_cache = {}
_cache_ttl = {}

STOCKS_TO_TRACK = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "TSLA",
    "BRK-B",
    "UNH",
    "JNJ",
    "V",
    "XOM",
    "WMT",
    "JPM",
    "PG",
    "MA",
    "HD",
    "CVX",
    "MRK",
    "ABBV",
    "LLY",
    "PEP",
    "KO",
    "AVGO",
    "COST",
    "TMO",
    "MCD",
    "CSCO",
    "ACN",
    "ABT",
    "DHR",
    "NKE",
    "ORCL",
    "TXN",
    "PM",
    "UPS",
    "CRM",
    "AMD",
    "QCOM",
    "INTC",
    "BA",
    "NFLX",
    "DIS",
    "PYPL",
    "ADBE",
    "CMCSA",
    "NEE",
    "BMY",
    "HON",
    "UNP",
    "LOW",
    "MS",
    "GS",
    "CAT",
    "BLK",
    "AXP",
    "ISRG",
    "ADI",
    "MDLZ",
    "GILD",
    "SYK",
    "CB",
    "PLD",
    "ZTS",
    "MMC",
    "CI",
    "SCHW",
    "SO",
    "DUK",
    "ICE",
    "USB",
    "PNC",
    "TFC",
    "BBT",
    "STI",
    "FITB",
    "Key",
    "CFG",
    "MTB",
    "HBAN",
    "OXY",
    "COP",
    "EOG",
    "SLB",
    "MPC",
    "PSX",
    "VLO",
    "PXD",
    "DVN",
    "FANG",
    "PLTR",
    "SOFI",
    "RIVN",
    "LCID",
    "NIO",
    "XPEV",
    "BABA",
    "PDD",
    "JD",
    "BIDU",
    "COIN",
    "MSTR",
    "SQ",
    "SHOP",
    "SNOW",
    "NET",
    "DDOG",
    "CRWD",
    "ZS",
    "PANW",
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "VTI",
    "VOO",
    "ARKK",
    "XLF",
    "XLE",
    "XLK",
]

INSIDER_URLS = [
    "http://openinsider.com/screener?s=&o=&pl=0&ph=&ll=&lh=&fd=0&fdr=&td=0&tdr=&fiedr=&fddr=&fddays=0&fdays=0&tdays=0&is498=1&is498=1&pre498=1&is498c498=1&coession=&count=100&act=&cnt=100&page=0",
    "http://openinsider.com/screener?s=&o=&pl=0&ph=&ll=&lh=&fd=0&fdr=&td=0&tdr=&fiedr=&fddr=&fddays=0&fdays=0&tdays=0&is498=1&is498=1&pre498=1&is498c498=1&coession=&count=100&act=&cnt=100&page=1",
    "http://openinsider.com/screener?s=&o=&pl=0&ph=&ll=&lh=&fd=0&fdr=&td=0&tdr=&fiedr=&fddr=&fddays=0&fdays=0&tdays=0&is498=1&is498=1&pre498=1&is498c498=1&coession=&count=100&act=&cnt=100&page=2",
]

SEC_FILINGS_URL = "https://efts.sec.gov/LATEST/search-index?q=%22Form+4%22&dateRange=custom&startdt={start}&enddt={end}&forms=4"


def _parse_openinsider(html: str) -> list[dict]:
    trades = []
    rows = re.findall(r"<tr[^>]*class='[^']*'[^>]*>(.*?)</tr>", html, re.DOTALL)
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) >= 10:

            def clean(c):
                return re.sub(r"<[^>]+>", "", c).strip()

            ticker = clean(cells[1])
            insider_name = clean(cells[3])
            title = clean(cells[4])
            trade_type = clean(cells[5])
            price = clean(cells[6])
            qty = clean(cells[7])
            owned = clean(cells[8])
            delta = clean(cells[9])
            value = clean(cells[10]) if len(cells) > 10 else ""
            date = clean(cells[2]) if len(cells) > 2 else ""

            if ticker:
                trades.append(
                    {
                        "ticker": ticker,
                        "insider": insider_name,
                        "title": title,
                        "trade_type": trade_type,
                        "price": price,
                        "shares": qty,
                        "owned": owned,
                        "delta_ownership": delta,
                        "value": value,
                        "date": date,
                        "source": "OpenInsider",
                    }
                )
    return trades


async def fetch_insider() -> dict:
    now = time.time()
    cache_key = "insider"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl.get(
        cache_key, 45
    ):
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    all_trades = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for url in INSIDER_URLS:
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    all_trades.extend(_parse_openinsider(resp.text))
            except Exception:
                pass

            if len(all_trades) >= 200:
                break

        for ticker in STOCKS_TO_TRACK[:20]:
            try:
                url = f"http://openinsider.com/{ticker}"
                resp = await client.get(
                    url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8
                )
                if resp.status_code == 200:
                    new_trades = _parse_openinsider(resp.text)
                    for t in new_trades:
                        t["source"] = f"OpenInsider ({ticker})"
                    all_trades.extend(new_trades)
            except Exception:
                pass

    seen = set()
    unique = []
    for t in all_trades:
        key = (
            t.get("ticker", ""),
            t.get("insider", ""),
            t.get("date", ""),
            t.get("shares", ""),
        )
        if key not in seen:
            seen.add(key)
            unique.append(t)

    unique.sort(key=lambda x: x.get("date", ""), reverse=True)

    result = {
        "trades": unique[:200],
        "total": len(unique),
        "updated_at": now,
    }
    result["_ts"] = now
    _cache[cache_key] = result
    _cache_ttl[cache_key] = 45

    return {k: v for k, v in result.items() if k != "_ts"}
