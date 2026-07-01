import asyncio
import time
import yfinance as yf

_cache = {}
_cache_ttl = 60

INSIDER_TICKERS = [
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
    "PLTR",
    "SOFI",
    "RIVN",
    "LCID",
    "NIO",
    "COIN",
    "MSTR",
    "SQ",
    "SHOP",
]


async def fetch_insider() -> dict:
    now = time.time()
    cache_key = "insider"
    if cache_key in _cache and now - _cache[cache_key]["_ts"] < _cache_ttl:
        return {k: v for k, v in _cache[cache_key].items() if k != "_ts"}

    all_trades = []

    def _fetch():
        import re

        for ticker in INSIDER_TICKERS[:75]:
            try:
                t = yf.Ticker(ticker)
                insider = t.insider_transactions
                if insider is None or insider.empty:
                    continue
                for _, row in insider.head(5).iterrows():
                    text = str(row.get("Text", ""))
                    raw_shares = row.get("Shares")
                    raw_value = row.get("Value")
                    shares = (
                        int(raw_shares)
                        if raw_shares and raw_shares == raw_shares
                        else 0
                    )
                    value = (
                        float(raw_value) if raw_value and raw_value == raw_value else 0
                    )

                    price_match = re.search(r"at price ([\d.]+)", text)
                    text_price = float(price_match.group(1)) if price_match else 0
                    price = (
                        round(value / shares, 2)
                        if shares > 0 and value > 0
                        else text_price
                    )

                    owns = str(row.get("Ownership", ""))
                    insider_name = str(row.get("Insider", ""))
                    position = str(row.get("Position", ""))
                    start = str(row.get("Start Date", ""))

                    text_lower = text.lower()
                    is_buy = "purchase" in text_lower or "buy" in text_lower
                    is_sell = "sale" in text_lower or "sell" in text_lower
                    is_gift = (
                        "gift" in text_lower
                        or "award" in text_lower
                        or "grant" in text_lower
                    )
                    trade_type = (
                        "buy"
                        if is_buy
                        else ("sell" if is_sell else ("gift" if is_gift else "other"))
                    )

                    all_trades.append(
                        {
                            "ticker": ticker,
                            "insider": insider_name,
                            "title": position,
                            "trade_type": trade_type,
                            "price": price if trade_type != "gift" else 0,
                            "shares": shares,
                            "owned": owns,
                            "delta_ownership": "",
                            "value": value if trade_type != "gift" else 0,
                            "date": start,
                            "source": "Yahoo Finance",
                            "detail": text[:120] if text else "",
                        }
                    )
            except Exception:
                pass

    await asyncio.to_thread(_fetch)

    result = {"trades": all_trades[:200], "total": len(all_trades), "updated_at": now}
    result["_ts"] = now
    _cache[cache_key] = result
    return {k: v for k, v in result.items() if k != "_ts"}
