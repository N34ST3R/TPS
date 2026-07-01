import json
from src.analysis.patterns import detect_candlestick_patterns
from src.analysis.indicators import compute_indicators, get_indicator_signals
from src.analysis.custom_patterns import (
    detect_support_resistance,
    detect_volume_spike,
    detect_rsi_divergence,
)
from src.data.fetcher import fetch_stock


async def generate_signal(symbol: str, timeframe: str = "5m") -> dict:
    df = await fetch_stock(symbol, period="5d", interval=timeframe)
    if df.empty or len(df) < 20:
        return {
            "symbol": symbol,
            "score": 0,
            "label": "NOISE",
            "net_direction": 0,
            "patterns": [],
            "indicators": {},
        }

    patterns = await detect_candlestick_patterns(df)
    indicators = await compute_indicators(df)
    indicator_signals = await get_indicator_signals(indicators)
    sr = detect_support_resistance(df)
    vol_spike = detect_volume_spike(df)
    rsi_div = detect_rsi_divergence(df)

    score = 0
    net_direction = 0

    for p in patterns[:3]:
        score += 10
        if p["direction"] == "bullish":
            net_direction += 1
        elif p["direction"] == "bearish":
            net_direction -= 1
    score = min(score, 30)

    ind_score = 0
    for s in indicator_signals[:4]:
        ind_score += 5
        if s["direction"] == "bullish":
            net_direction += 1
        elif s["direction"] == "bearish":
            net_direction -= 1
    score += min(ind_score, 20)

    price = indicators.get("price", 0)
    if sr["support"] > 0 and sr["resistance"] > 0:
        range_size = sr["resistance"] - sr["support"]
        if range_size > 0:
            pos = (price - sr["support"]) / range_size
            if pos < 0.2:
                score += 15
                net_direction += 1
            elif pos > 0.8:
                score += 15
                net_direction -= 1

    if vol_spike:
        score += 10

    if rsi_div == "bullish":
        score += 15
        net_direction += 1
    elif rsi_div == "bearish":
        score += 15
        net_direction -= 1

    if len(patterns) > 3:
        contradictions = sum(
            1 for p in patterns[3:] if p["direction"] != patterns[0]["direction"]
        )
        if contradictions > 0:
            score -= 20
            net_direction = 0

    score = max(0, min(100, score))

    if score <= 20:
        label = "NOISE"
    elif score <= 40:
        label = "WATCH"
    elif score <= 60:
        label = "HOLD"
    elif score <= 80:
        label = "BUY" if net_direction > 0 else "SELL" if net_direction < 0 else "HOLD"
    else:
        label = (
            "STRONG BUY"
            if net_direction > 0
            else "STRONG SELL"
            if net_direction < 0
            else "HOLD"
        )

    return {
        "symbol": symbol,
        "score": score,
        "label": label,
        "net_direction": net_direction,
        "patterns": patterns,
        "indicators": indicators,
        "indicator_signals": indicator_signals,
        "support_resistance": sr,
        "volume_spike": vol_spike,
        "rsi_divergence": rsi_div,
        "timeframe": timeframe,
        "price": price,
    }


async def scan_watchlist(symbols: list[str], timeframe: str = "5m") -> list[dict]:
    import asyncio

    tasks = [generate_signal(s, timeframe) for s in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in results if not isinstance(r, Exception)]
    return sorted(valid, key=lambda x: x["score"], reverse=True)
