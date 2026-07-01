from fastmcp import FastMCP
from src.analysis.signal import generate_signal, scan_watchlist as do_scan_watchlist
from src.data.polymarket import get_active_markets
from src.data.wallet import get_wallet_portfolio
from src.data.scraper import scrape_url
from src.delivery.alerts import get_alert_history
from src.store.database import get_db
import json

mcp = FastMCP("Trading Pattern Scanner")


@mcp.tool()
async def scan_ticker(symbol: str, source: str = "auto", timeframe: str = "5m") -> str:
    """Scan a stock ticker for patterns and signals."""
    signal = await generate_signal(symbol.upper(), timeframe)
    return json.dumps(signal, indent=2, default=str)


@mcp.tool()
async def scan_watchlist(timeframe: str = "5m") -> str:
    """Scan all watched stocks ranked by signal strength."""
    db = await get_db()
    cursor = await db.execute("SELECT symbol FROM watchlist")
    rows = await cursor.fetchall()
    symbols = [r[0] for r in rows]
    if not symbols:
        return json.dumps({"message": "Watchlist is empty"})
    results = await do_scan_watchlist(symbols, timeframe)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
async def scan_polymarket(query: str = None, limit: int = 20) -> str:
    """Scan Polymarket for active markets with pattern signals."""
    markets = await get_active_markets()
    return json.dumps(markets, indent=2, default=str)


@mcp.tool()
async def scan_wallet(address: str, chain: str = "solana") -> str:
    """Analyze any wallet's holdings by public address."""
    portfolio = await get_wallet_portfolio(address)
    return json.dumps(portfolio, indent=2, default=str)


@mcp.tool()
async def scrape_page(url: str, selector: str = None) -> str:
    """Scrape a public website and extract data for pattern analysis."""
    result = await scrape_url(url, selector)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def get_alert_history(limit: int = 50) -> str:
    """Get recent triggered alerts with timestamps."""
    history = await get_alert_history(limit)
    return json.dumps(history, indent=2, default=str)


@mcp.tool()
async def get_market_overview() -> str:
    """Get cross-market sentiment summary."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT symbol, score, label, created_at FROM signals ORDER BY created_at DESC LIMIT 10"
    )
    rows = await cursor.fetchall()
    signals = [
        {"symbol": r[0], "score": r[1], "label": r[2], "created_at": r[3]} for r in rows
    ]
    return json.dumps({"recent_signals": signals}, indent=2, default=str)
