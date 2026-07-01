import aiosqlite
from pathlib import Path
from src.store.config import DB_PATH

_db = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(DB_PATH))
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _init_tables(_db)
    return _db


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            source TEXT DEFAULT 'auto',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            source TEXT NOT NULL,
            score INTEGER NOT NULL,
            label TEXT NOT NULL,
            net_direction INTEGER DEFAULT 0,
            patterns TEXT,
            indicators TEXT,
            timeframe TEXT DEFAULT '5m',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            signal_id INTEGER,
            alert_type TEXT NOT NULL,
            message TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            exit_price REAL,
            exit_time TIMESTAMP,
            exit_method TEXT,
            r_multiple REAL,
            signal_id INTEGER,
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            score INTEGER NOT NULL,
            label TEXT NOT NULL,
            outcome TEXT,
            win_rate REAL,
            expectancy REAL,
            profit_factor REAL,
            sample_size INTEGER DEFAULT 0,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await db.commit()
