import asyncio
import signal as sig
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.store.database import get_db, close_db
from src.delivery.dashboard import app as dashboard_app
from src.delivery.mcp_server import mcp
from src.analysis.signal import scan_watchlist as do_scan_watchlist


async def background_scanner():
    while True:
        try:
            db = await get_db()
            cursor = await db.execute("SELECT symbol FROM watchlist")
            rows = await cursor.fetchall()
            symbols = [r[0] for r in rows]
            if symbols:
                results = await do_scan_watchlist(symbols)
                for r in results:
                    await db.execute(
                        "INSERT INTO signals (symbol, source, score, label, net_direction, patterns, indicators, timeframe) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            r["symbol"],
                            "yahoo",
                            r["score"],
                            r["label"],
                            r["net_direction"],
                            str(r.get("patterns", [])),
                            str(r.get("indicators", {})),
                            r.get("timeframe", "5m"),
                        ),
                    )
                await db.commit()
        except Exception as e:
            print(f"Scanner error: {e}")
        await asyncio.sleep(300)


async def run_dashboard():
    await dashboard_app.run_task(host="0.0.0.0", port=5000)


async def run_mcp():
    await mcp.run_async()


async def main():
    await get_db()
    print("Trading Pattern Scanner starting...")
    print("Dashboard: http://localhost:5000")
    print("MCP Server: http://localhost:8001")

    tasks = [
        asyncio.create_task(background_scanner()),
        asyncio.create_task(run_dashboard()),
        asyncio.create_task(run_mcp()),
    ]

    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for s in (sig.SIGINT, sig.SIGTERM):
            loop.add_signal_handler(s, lambda: [t.cancel() for t in tasks])

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        await close_db()
        print("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
