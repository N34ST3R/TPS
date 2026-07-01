from quart import Quart, render_template, request, jsonify
from quart.json.provider import DefaultJSONProvider
from src.store.database import get_db
from src.analysis.signal import generate_signal, scan_watchlist as do_scan_watchlist
from src.data.polymarket import get_active_markets
from src.data.wallet import get_wallet_portfolio
from src.data.scraper import scrape_url
from src.delivery.alerts import get_alert_history
from src.store.config import ACCOUNT_SIZE
from src.data.live.news import fetch_news
from src.data.live.social import fetch_social
from src.data.live.crypto import fetch_crypto
from src.data.live.calendar import fetch_calendar
from src.data.live.options_flow import fetch_options_flow
from src.data.live.insider import fetch_insider
from src.data.live.analyst import fetch_analyst
from src.data.live.stock_list import fetch_all_stocks
from src.delivery.simulation import (
    execute_buy,
    execute_sell,
    get_portfolio_summary,
    get_transactions,
    reset_portfolio,
    get_current_price,
    load_watchlist,
    save_watchlist,
)
import time
import asyncio
import numpy as np


class NumpyJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


app = Quart(__name__, template_folder="templates", static_folder="static")
app.json_provider_class = NumpyJSONProvider
app.json = NumpyJSONProvider(app)


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/api/watchlist", methods=["GET"])
async def get_watchlist():
    db = await get_db()
    cursor = await db.execute(
        "SELECT symbol, source, added_at FROM watchlist ORDER BY added_at DESC"
    )
    rows = await cursor.fetchall()
    return jsonify([{"symbol": r[0], "source": r[1], "added_at": r[2]} for r in rows])


@app.route("/api/watchlist", methods=["POST"])
async def add_to_watchlist():
    data = await request.get_json()
    symbol = data.get("symbol", "").upper()
    source = data.get("source", "auto")
    if not symbol:
        return jsonify({"error": "Symbol required"}), 400
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO watchlist (symbol, source) VALUES (?, ?)",
        (symbol, source),
    )
    await db.commit()
    return jsonify({"status": "added", "symbol": symbol})


@app.route("/api/watchlist/<symbol>", methods=["DELETE"])
async def remove_from_watchlist(symbol):
    db = await get_db()
    await db.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
    await db.commit()
    return jsonify({"status": "removed", "symbol": symbol.upper()})


@app.route("/api/scan/<symbol>")
async def scan_ticker(symbol):
    timeframe = request.args.get("timeframe", "5m")
    try:
        signal = await generate_signal(symbol.upper(), timeframe)
        return jsonify(signal)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan/watchlist")
async def scan_all():
    timeframe = request.args.get("timeframe", "5m")
    db = await get_db()
    cursor = await db.execute("SELECT symbol FROM watchlist")
    rows = await cursor.fetchall()
    symbols = [r[0] for r in rows]
    if not symbols:
        return jsonify([])
    results = await do_scan_watchlist(symbols, timeframe)
    return jsonify(results)


@app.route("/api/polymarket")
async def polymarket():
    markets = await get_active_markets()
    return jsonify(markets)


@app.route("/api/wallet/<address>")
async def wallet(address):
    portfolio = await get_wallet_portfolio(address)
    return jsonify(portfolio)


@app.route("/api/scrape")
async def scrape():
    url = request.args.get("url")
    selector = request.args.get("selector")
    if not url:
        return jsonify({"error": "URL required"}), 400
    result = await scrape_url(url, selector)
    return jsonify(result)


@app.route("/api/alerts")
async def alerts():
    limit = request.args.get("limit", 50, type=int)
    history = await get_alert_history(limit)
    return jsonify(history)


@app.route("/api/stats")
async def stats():
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM watchlist")
    watchlist_count = (await cursor.fetchone())[0]
    cursor = await db.execute("SELECT COUNT(*) FROM signals")
    signal_count = (await cursor.fetchone())[0]
    cursor = await db.execute("SELECT COUNT(*) FROM alerts")
    alert_count = (await cursor.fetchone())[0]
    return jsonify(
        {
            "watchlist_count": watchlist_count,
            "signal_count": signal_count,
            "alert_count": alert_count,
            "account_size": ACCOUNT_SIZE,
        }
    )


@app.route("/api/live/news")
async def live_news():
    try:
        return jsonify(await fetch_news())
    except Exception as e:
        return jsonify({"articles": [], "error": str(e)})


@app.route("/api/live/social")
async def live_social():
    try:
        return jsonify(await fetch_social())
    except Exception as e:
        return jsonify({"posts": [], "error": str(e)})


@app.route("/api/live/crypto")
async def live_crypto():
    try:
        return jsonify(await fetch_crypto())
    except Exception as e:
        return jsonify({"coins": [], "error": str(e)})


@app.route("/api/live/calendar")
async def live_calendar():
    try:
        return jsonify(await fetch_calendar())
    except Exception as e:
        return jsonify({"events": [], "error": str(e)})


@app.route("/api/live/options")
async def live_options():
    try:
        return jsonify(await fetch_options_flow())
    except Exception as e:
        return jsonify({"flow": [], "error": str(e)})


@app.route("/api/live/insider")
async def live_insider():
    try:
        return jsonify(await fetch_insider())
    except Exception as e:
        return jsonify({"trades": [], "error": str(e)})


@app.route("/api/live/analyst")
async def live_analyst():
    try:
        return jsonify(await fetch_analyst())
    except Exception as e:
        return jsonify({"ratings": [], "error": str(e)})


@app.route("/api/live/stocks")
async def live_stocks():
    try:
        return jsonify(await fetch_all_stocks())
    except Exception as e:
        return jsonify({"stocks": [], "error": str(e)})


@app.route("/api/simulation/portfolio")
async def sim_portfolio():
    try:
        return jsonify(await get_portfolio_summary())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/simulation/buy", methods=["POST"])
async def sim_buy():
    data = await request.get_json()
    symbol = data.get("symbol", "").upper()
    quantity = data.get("quantity", 0)
    if not symbol or quantity <= 0:
        return jsonify({"error": "Symbol and valid quantity required"}), 400
    price_data = await get_current_price(symbol)
    if price_data["price"] <= 0:
        return jsonify({"error": f"Could not get price for {symbol}"}), 400
    result = execute_buy(symbol, quantity, price_data["price"])
    result["price"] = price_data["price"]
    return jsonify(result)


@app.route("/api/simulation/sell", methods=["POST"])
async def sim_sell():
    data = await request.get_json()
    symbol = data.get("symbol", "").upper()
    quantity = data.get("quantity", 0)
    if not symbol or quantity <= 0:
        return jsonify({"error": "Symbol and valid quantity required"}), 400
    price_data = await get_current_price(symbol)
    if price_data["price"] <= 0:
        return jsonify({"error": f"Could not get price for {symbol}"}), 400
    result = execute_sell(symbol, quantity, price_data["price"])
    result["price"] = price_data["price"]
    return jsonify(result)


@app.route("/api/simulation/transactions")
async def sim_transactions():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(get_transactions(limit))


@app.route("/api/simulation/reset", methods=["POST"])
async def sim_reset():
    return jsonify(reset_portfolio())


@app.route("/api/simulation/price/<symbol>")
async def sim_price(symbol):
    return jsonify(await get_current_price(symbol.upper()))


@app.route("/api/watchlist-sim", methods=["GET"])
async def get_watchlist_sim():
    return jsonify(load_watchlist())


@app.route("/api/watchlist-sim", methods=["POST"])
async def add_watchlist_sim():
    data = await request.get_json()
    symbol = data.get("symbol", "").upper()
    if not symbol:
        return jsonify({"error": "Symbol required"}), 400
    wl = load_watchlist()
    if symbol not in wl:
        wl.append(symbol)
        save_watchlist(wl)
    return jsonify({"status": "added", "symbol": symbol, "watchlist": wl})


@app.route("/api/watchlist-sim/<symbol>", methods=["DELETE"])
async def remove_watchlist_sim(symbol):
    wl = load_watchlist()
    wl = [s for s in wl if s != symbol.upper()]
    save_watchlist(wl)
    return jsonify({"status": "removed", "symbol": symbol.upper(), "watchlist": wl})


@app.route("/api/alerts/check")
async def alerts_check():
    try:
        portfolio = await get_portfolio_summary()
        alerts = []
        for pos in portfolio.get("positions", []):
            pct = pos.get("unrealized_pnl_pct", 0)
            if pct <= -5:
                alerts.append(
                    {
                        "type": "warning",
                        "title": f"{pos['symbol']} Down {pct:.1f}%",
                        "message": f"Position in {pos['symbol']} is down {pct:.1f}% from cost basis. Consider cutting losses.",
                        "symbol": pos["symbol"],
                        "timestamp": time.time(),
                    }
                )
            elif pct >= 10:
                alerts.append(
                    {
                        "type": "success",
                        "title": f"{pos['symbol']} Up {pct:.1f}%",
                        "message": f"Position in {pos['symbol']} is up {pct:.1f}%. Consider taking profits.",
                        "symbol": pos["symbol"],
                        "timestamp": time.time(),
                    }
                )
        if portfolio.get("total_pnl_pct", 0) <= -10:
            alerts.append(
                {
                    "type": "danger",
                    "title": "Portfolio Down Significantly",
                    "message": f"Portfolio is down {portfolio['total_pnl_pct']:.1f}% overall. Review positions.",
                    "symbol": "PORTFOLIO",
                    "timestamp": time.time(),
                }
            )
        if not alerts:
            alerts.append(
                {
                    "type": "info",
                    "title": "All Clear",
                    "message": "No alerts triggered. Portfolio is within normal parameters.",
                    "symbol": "SYSTEM",
                    "timestamp": time.time(),
                }
            )
        return jsonify({"alerts": alerts, "count": len(alerts)})
    except Exception as e:
        return jsonify({"alerts": [], "count": 0, "error": str(e)})
