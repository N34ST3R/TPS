import asyncio
import json
from src.store.database import get_db
from src.store.config import DISCORD_WEBHOOK_URL
import httpx
import platform
import subprocess


async def send_desktop_alert(title: str, message: str):
    def _send():
        try:
            from plyer import notification

            notification.notify(
                title=title,
                message=message[:256],
                timeout=10,
            )
        except Exception:
            if platform.system() == "Windows":
                subprocess.run(
                    ["msg", "*", "/TIME:10", f"{title}\n{message[:200]}"],
                    capture_output=True,
                )

    await asyncio.get_event_loop().run_in_executor(None, _send)


async def send_discord_alert(title: str, message: str, color: int = 0x00FF00):
    if not DISCORD_WEBHOOK_URL:
        return

    embed = {
        "embeds": [
            {
                "title": title,
                "description": message[:2000],
                "color": color,
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        await client.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)


async def alert_signal(signal: dict):
    if signal["label"] in ("NOISE", "HOLD"):
        return

    db = await get_db()
    color = (
        0x00FF00
        if "BUY" in signal["label"]
        else 0xFF0000
        if "SELL" in signal["label"]
        else 0xFFFF00
    )
    title = f"{signal['label']}: {signal['symbol']}"
    message = f"Score: {signal['score']}/100\nPrice: ${signal.get('price', 0):.2f}\n"
    if signal["patterns"]:
        message += (
            f"Patterns: {', '.join(p['pattern'] for p in signal['patterns'][:3])}\n"
        )
    message += f"Timeframe: {signal.get('timeframe', '5m')}"

    await db.execute(
        "INSERT INTO alerts (symbol, alert_type, message) VALUES (?, ?, ?)",
        (signal["symbol"], signal["label"], message),
    )
    await db.commit()

    await asyncio.gather(
        send_desktop_alert(title, message),
        send_discord_alert(title, message, color),
        return_exceptions=True,
    )


async def get_alert_history(limit: int = 50) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT symbol, alert_type, message, sent_at FROM alerts ORDER BY sent_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [
        {"symbol": r[0], "type": r[1], "message": r[2], "sent_at": r[3]} for r in rows
    ]
