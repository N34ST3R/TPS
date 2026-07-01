import json
import time
import os
from pathlib import Path
import httpx

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"

DEFAULT_PORTFOLIO = {
    "cash": 100000.00,
    "starting_cash": 100000.00,
    "positions": {},
    "created_at": time.time(),
    "last_updated": time.time(),
}

DEFAULT_WATCHLIST = [
    "AAPL",
    "NVDA",
    "TSLA",
    "GOOGL",
    "AMZN",
    "MSFT",
    "META",
    "SPY",
    "QQQ",
    "BTC-USD",
]


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_portfolio() -> dict:
    _ensure_data_dir()
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    save_portfolio(DEFAULT_PORTFOLIO)
    return DEFAULT_PORTFOLIO.copy()


def save_portfolio(portfolio: dict):
    _ensure_data_dir()
    portfolio["last_updated"] = time.time()
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)


def load_transactions() -> list:
    _ensure_data_dir()
    if TRANSACTIONS_FILE.exists():
        with open(TRANSACTIONS_FILE, "r") as f:
            return json.load(f)
    return []


def save_transactions(transactions: list):
    _ensure_data_dir()
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(transactions, f, indent=2)


def load_watchlist() -> list:
    _ensure_data_dir()
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)
    save_watchlist(DEFAULT_WATCHLIST)
    return DEFAULT_WATCHLIST.copy()


def save_watchlist(watchlist: list):
    _ensure_data_dir()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


async def get_current_price(symbol: str) -> dict:
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
        prev_close = float(
            info.get("previousClose", 0) or info.get("previous_close", 0) or price
        )
        change = price - prev_close
        pct_change = (change / prev_close * 100) if prev_close else 0
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(pct_change, 2),
            "prev_close": round(prev_close, 2),
        }
    except Exception:
        return {"symbol": symbol, "price": 0, "change": 0, "change_pct": 0}


def execute_buy(symbol: str, quantity: int, price: float) -> dict:
    portfolio = load_portfolio()
    total_cost = quantity * price

    if total_cost > portfolio["cash"]:
        return {
            "success": False,
            "error": f"Insufficient cash. Need ${total_cost:,.2f}, have ${portfolio['cash']:,.2f}",
        }

    portfolio["cash"] -= total_cost

    if symbol in portfolio["positions"]:
        pos = portfolio["positions"][symbol]
        old_total = pos["quantity"] * pos["avg_cost"]
        new_total = old_total + total_cost
        pos["quantity"] += quantity
        pos["avg_cost"] = new_total / pos["quantity"]
    else:
        portfolio["positions"][symbol] = {
            "quantity": quantity,
            "avg_cost": price,
            "first_bought": time.time(),
        }

    save_portfolio(portfolio)

    tx = {
        "type": "BUY",
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "total": total_cost,
        "timestamp": time.time(),
    }
    transactions = load_transactions()
    transactions.insert(0, tx)
    save_transactions(transactions[:500])

    return {
        "success": True,
        "message": f"Bought {quantity} {symbol} @ ${price:.2f}",
        "total": total_cost,
    }


def execute_sell(symbol: str, quantity: int, price: float) -> dict:
    portfolio = load_portfolio()

    if symbol not in portfolio["positions"]:
        return {"success": False, "error": f"No position in {symbol}"}

    pos = portfolio["positions"][symbol]
    if quantity > pos["quantity"]:
        return {
            "success": False,
            "error": f"Only have {pos['quantity']} shares of {symbol}",
        }

    total_value = quantity * price
    portfolio["cash"] += total_value
    pos["quantity"] -= quantity

    if pos["quantity"] == 0:
        del portfolio["positions"][symbol]

    save_portfolio(portfolio)

    tx = {
        "type": "SELL",
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "total": total_value,
        "timestamp": time.time(),
    }
    transactions = load_transactions()
    transactions.insert(0, tx)
    save_transactions(transactions[:500])

    return {
        "success": True,
        "message": f"Sold {quantity} {symbol} @ ${price:.2f}",
        "total": total_value,
    }


async def get_portfolio_summary() -> dict:
    portfolio = load_portfolio()
    total_value = portfolio["cash"]
    positions_detail = []

    for symbol, pos in portfolio["positions"].items():
        current = await get_current_price(symbol)
        market_value = current["price"] * pos["quantity"]
        unrealized_pnl = market_value - (pos["avg_cost"] * pos["quantity"])
        unrealized_pnl_pct = (
            (unrealized_pnl / (pos["avg_cost"] * pos["quantity"]) * 100)
            if pos["avg_cost"] * pos["quantity"] > 0
            else 0
        )

        total_value += market_value
        positions_detail.append(
            {
                "symbol": symbol,
                "quantity": pos["quantity"],
                "avg_cost": round(pos["avg_cost"], 2),
                "current_price": current["price"],
                "market_value": round(market_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
                "change_today": current["change_pct"],
            }
        )

    total_pnl = total_value - portfolio["starting_cash"]
    total_pnl_pct = (
        (total_pnl / portfolio["starting_cash"] * 100)
        if portfolio["starting_cash"] > 0
        else 0
    )

    return {
        "cash": round(portfolio["cash"], 2),
        "total_value": round(total_value, 2),
        "starting_cash": portfolio["starting_cash"],
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "positions": positions_detail,
        "position_count": len(positions_detail),
    }


def get_transactions(limit: int = 50) -> list:
    return load_transactions()[:limit]


def reset_portfolio() -> dict:
    save_portfolio(DEFAULT_PORTFOLIO.copy())
    save_transactions([])
    return {"success": True, "message": "Portfolio reset to $100,000"}
