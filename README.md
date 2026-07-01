## Future Idea
- LLM to see bad & good or moderate 
- New Design
- New Insider

## Step 1: Prerequisites

| What | Why | How to get it |
|------|-----|---------------|
| Python 3.11+ | Core runtime | [python.org](https://python.org) or `brew install python` |
| TA-Lib C library | Pattern detection engine | See Step 2 below |
| Git | Clone the repo | [git-scm.com](https://git-scm.com) |

### Installing TA-Lib (the hard part)

TA-Lib has a C dependency. Pick ONE method:

**Option A - Pre-built wheel (Windows, easiest):**
```bash
pip install TA-Lib --find-links https://github.com/cgohlke/talib-build/releases
```

**Option B - Conda (any OS):**
```bash
conda install -c conda-forge ta-lib
```

**Option C - Build from source (Linux/Mac):**
```bash
# Ubuntu/Debian
sudo apt-get install build-essential wget
wget https://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib
./configure --prefix=/usr
make
sudo make install

# Mac
brew install ta-lib
```

If TA-Lib install fails, the scanner still works - it just won't detect candlestick patterns. Indicators (RSI, MACD, etc.) use only pandas/numpy.

---

## Step 2: Install the Project

```bash
# Clone or navigate to the project
cd trading-scraper

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Install Python dependencies
pip install -r requirements.txt
```

---

## Step 3: Configure Your Settings

```bash
cp .env.example .env
```

Open `.env` in any editor. Here's what each line does:

| Variable | Required? | What it does |
|----------|-----------|-------------|
| `ACCOUNT_SIZE` | Yes | Your account size in USD - used for position sizing recommendations (1-2% risk per trade) |
| `WEBULL_ACCOUNT_ID` | No | Only if you have a Webull account and want real-time quotes |
| `WEBULL_ACCESS_TOKEN` | No | Your Webull API token |
| `WALLET_ADDRESSES` | No | Comma-separated Solana wallet addresses to track (e.g. `AbCd...,XyZ...`) |
| `SOLANA_RPC` | No | Solana RPC endpoint - default works, but a free Helius/QuickNode key is faster |
| `BIRDEYE_API_KEY` | No | Free Birdeye API key for Solana token prices - get one at birdeye.so |
| `DISCORD_WEBHOOK_URL` | No | Discord webhook URL for alerts - create one in Discord Server Settings > Integrations |
| `SCRAPE_URLS` | No | Comma-separated URLs to scrape for data (e.g. news sites, price aggregators) |

**Minimum viable config** - just set `ACCOUNT_SIZE` and you're good:
```env
ACCOUNT_SIZE=100
```

---

## Step 4: Run It

```bash
python src/main.py
```

You'll see:
```
Trading Pattern Scanner starting...
Dashboard: http://localhost:5000
MCP Server: http://localhost:8001
```

Open **http://localhost:5000** in your browser.

---

## Step 5: Use the Dashboard

### Stocks Tab
1. **Quick Scan** - Type a ticker (e.g. `AAPL`), pick a timeframe, click **Scan**
2. **Watchlist** - Add tickers you want to track, click **Scan All** to rank them by signal strength

### Polymarket Tab
- Click **Refresh** to see active prediction markets with volume and end dates

### Solana Tab
- Paste any Solana wallet address to see SOL balance and token holdings

### Alerts Tab
- View all triggered alerts with timestamps

---

## How the Signal System Works

Every scan produces a **score from 0 to 100**:

| Score | Label | What it means |
|-------|-------|--------------|
| 0-20 | NOISE | Nothing happening |
| 21-40 | WATCH | Potential setup forming - keep an eye on it |
| 41-60 | HOLD | Mixed signals - wait for clarity |
| 61-80 | BUY / SELL | Actionable signal - check the details |
| 81-100 | STRONG BUY / STRONG SELL | High-confidence signal |

### What adds points:
- **Candlestick patterns** (Engulfing, Hammer, Doji, etc.) - +10 each, max 30
- **Indicator confirmations** (RSI, MACD, EMA crossovers) - +5 each, max 20
- **Support/resistance proximity** - +15
- **Volume spikes** - +10
- **RSI divergence** - +15
- **Contradictory patterns** - -20 (resets direction)

The **net_direction** counter tracks bullish (+1) vs bearish (-1) signals to decide if a high score means BUY or SELL.

---

## Project Structure

```
trading-scraper/
├── src/
│   ├── data/                    # Data fetching layer
│   │   ├── fetcher.py           # Yahoo Finance + Webull (async)
│   │   ├── polymarket.py        # Polymarket Gamma API
│   │   ├── wallet.py            # Solana RPC + Birdeye
│   │   ├── scraper.py           # httpx + BeautifulSoup
│   │   ├── cache.py             # In-memory TTL cache
│   │   ├── rate_limiter.py      # Per-source rate limiting
│   │   └── normalize.py         # Common schema normalization
│   ├── analysis/                # Pattern detection
│   │   ├── patterns.py          # TA-Lib candlestick patterns
│   │   ├── indicators.py        # RSI, MACD, EMA, Bollinger, etc.
│   │   ├── custom_patterns.py   # Support/resistance, volume spikes
│   │   └── signal.py            # Score-driven signal generator
│   ├── delivery/                # Output layer
│   │   ├── dashboard.py         # Quart web API
│   │   ├── mcp_server.py        # FastMCP for AI tools
│   │   ├── alerts.py            # Desktop + Discord notifications
│   │   └── templates/index.html # Dashboard UI
│   ├── store/                   # Data persistence
│   │   ├── database.py          # SQLite async (aiosqlite)
│   │   └── config.py            # .env configuration
│   └── main.py                  # Entry point
├── tests/                       # Test suite
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Endpoints

The dashboard exposes these REST endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/watchlist` | List all watched tickers |
| POST | `/api/watchlist` | Add a ticker `{"symbol": "AAPL"}` |
| DELETE | `/api/watchlist/<symbol>` | Remove a ticker |
| GET | `/api/scan/<symbol>` | Scan one ticker for patterns |
| GET | `/api/scan/watchlist` | Scan all watched tickers |
| GET | `/api/polymarket` | Active Polymarket markets |
| GET | `/api/wallet/<address>` | Solana wallet portfolio |
| GET | `/api/scrape?url=...&selector=...` | Scrape a public website |
| GET | `/api/alerts` | Recent alert history |
| GET | `/api/stats` | Dashboard statistics |

---

## MCP Server (for AI Tools)

The MCP server runs on port 8001 and exposes these tools:

- `scan_ticker(symbol, source, timeframe)` - Scan one stock
- `scan_watchlist(timeframe)` - Scan entire watchlist
- `scan_polymarket(query, limit)` - Scan Polymarket
- `scan_wallet(address, chain)` - Analyze a wallet
- `scrape_page(url, selector)` - Scrape a website
- `get_alert_history(limit)` - Recent alerts
- `get_market_overview()` - Cross-market summary

**Security:** Don't expose port 8001 externally - the scraper tool can hit any URL including localhost.

---

## Background Scanner

The scanner runs automatically every 5 minutes and:
1. Pulls your watchlist from the database
2. Fetches the latest OHLCV data for each ticker
3. Runs pattern detection + indicator analysis
4. Generates signals and stores them in SQLite
5. Triggers alerts for BUY/SELL signals

---

## Testing

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `TA-Lib import error` | Install the C library first (see Step 1) |
| `yfinance returns empty` | Market might be closed - try a different ticker or check your internet |
| `Solana RPC timeout` | Switch to a paid RPC provider (Helius, QuickNode) |
| `Discord alerts not sending` | Check your webhook URL is correct and the channel exists |
| `Dashboard won't start` | Make sure port 5000 isn't in use by another process |

---

## v1 Limits

- No automated trading (signals only)
- No ML (rule-based patterns, VADER sentiment)
- No Polymarket order execution (read-only)
- No EVM chain support (Solana only - ETH/Base in v2)
- Single user, one timeframe per scan
