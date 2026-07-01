import asyncio
import yfinance as yf
import pandas as pd
from src.data.cache import cache
from src.data.rate_limiter import rate_limiter
from src.data.normalize import normalize_ohlcv


async def fetch_stock(
    symbol: str, period: str = "5d", interval: str = "5m"
) -> pd.DataFrame:
    cache_key = f"stock:{symbol}:{period}:{interval}"
    cached = cache.get(cache_key, ttl=60)
    if cached is not None:
        return cached

    await rate_limiter.acquire("yahoo")

    def _fetch():
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period, interval=interval)

    df = await asyncio.get_event_loop().run_in_executor(None, _fetch)
    if df.empty:
        return pd.DataFrame()
    df = normalize_ohlcv(df, symbol, "yahoo")
    cache.set(cache_key, df)
    return df


async def fetch_stock_fundamentals(symbol: str) -> dict:
    await rate_limiter.acquire("yahoo")

    def _fetch():
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol,
            "name": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
        }

    return await asyncio.get_event_loop().run_in_executor(None, _fetch)


async def fetch_watchlist(
    symbols: list[str], period: str = "5d", interval: str = "5m"
) -> dict[str, pd.DataFrame]:
    tasks = [fetch_stock(s, period, interval) for s in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        s: r if not isinstance(r, Exception) else pd.DataFrame()
        for s, r in zip(symbols, results)
    }
