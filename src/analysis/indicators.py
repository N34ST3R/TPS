import asyncio
import pandas as pd


async def compute_indicators(df: pd.DataFrame) -> dict:
    def _compute():
        import talib

        if len(df) < 20:
            return {}

        c = df["close"]
        h = df["high"]
        l = df["low"]
        v = df["volume"]

        indicators = {}

        rsi = talib.RSI(c, timeperiod=14)
        indicators["rsi"] = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

        macd, signal, hist = talib.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)
        indicators["macd"] = (
            float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else None
        )
        indicators["macd_signal"] = (
            float(signal.iloc[-1]) if not pd.isna(signal.iloc[-1]) else None
        )
        indicators["macd_hist"] = (
            float(hist.iloc[-1]) if not pd.isna(hist.iloc[-1]) else None
        )

        ema9 = talib.EMA(c, timeperiod=9)
        ema21 = talib.EMA(c, timeperiod=21)
        ema50 = talib.EMA(c, timeperiod=50)
        indicators["ema9"] = (
            float(ema9.iloc[-1]) if not pd.isna(ema9.iloc[-1]) else None
        )
        indicators["ema21"] = (
            float(ema21.iloc[-1]) if not pd.isna(ema21.iloc[-1]) else None
        )
        indicators["ema50"] = (
            float(ema50.iloc[-1]) if not pd.isna(ema50.iloc[-1]) else None
        )

        upper, middle, lower = talib.BBANDS(c, timeperiod=20, nbdevup=2, nbdevdn=2)
        indicators["bb_upper"] = (
            float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None
        )
        indicators["bb_middle"] = (
            float(middle.iloc[-1]) if not pd.isna(middle.iloc[-1]) else None
        )
        indicators["bb_lower"] = (
            float(lower.iloc[-1]) if not pd.isna(lower.iloc[-1]) else None
        )

        stoch_k, stoch_d = talib.STOCH(h, l, c)
        indicators["stoch_k"] = (
            float(stoch_k.iloc[-1]) if not pd.isna(stoch_k.iloc[-1]) else None
        )
        indicators["stoch_d"] = (
            float(stoch_d.iloc[-1]) if not pd.isna(stoch_d.iloc[-1]) else None
        )

        obv = talib.OBV(c, v)
        indicators["obv"] = float(obv.iloc[-1]) if not pd.isna(obv.iloc[-1]) else None

        atr = talib.ATR(h, l, c, timeperiod=14)
        indicators["atr"] = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else None

        indicators["price"] = float(c.iloc[-1])
        indicators["volume"] = float(v.iloc[-1])
        indicators["avg_volume"] = (
            float(v.tail(20).mean()) if len(v) >= 20 else float(v.mean())
        )

        return indicators

    return await asyncio.get_event_loop().run_in_executor(None, _compute)


async def get_indicator_signals(indicators: dict) -> list[dict]:
    signals = []
    if not indicators:
        return signals

    price = indicators.get("price", 0)

    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi < 30:
            signals.append(
                {
                    "indicator": "RSI",
                    "direction": "bullish",
                    "value": rsi,
                    "detail": f"RSI oversold at {rsi:.1f}",
                }
            )
        elif rsi > 70:
            signals.append(
                {
                    "indicator": "RSI",
                    "direction": "bearish",
                    "value": rsi,
                    "detail": f"RSI overbought at {rsi:.1f}",
                }
            )

    macd = indicators.get("macd")
    macd_signal = indicators.get("macd_signal")
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            signals.append(
                {
                    "indicator": "MACD",
                    "direction": "bullish",
                    "value": macd,
                    "detail": "MACD above signal line",
                }
            )
        elif macd < macd_signal:
            signals.append(
                {
                    "indicator": "MACD",
                    "direction": "bearish",
                    "value": macd,
                    "detail": "MACD below signal line",
                }
            )

    ema9 = indicators.get("ema9")
    ema21 = indicators.get("ema21")
    if ema9 is not None and ema21 is not None:
        if ema9 > ema21:
            signals.append(
                {
                    "indicator": "EMA_CROSS",
                    "direction": "bullish",
                    "value": ema9,
                    "detail": "EMA9 above EMA21",
                }
            )
        elif ema9 < ema21:
            signals.append(
                {
                    "indicator": "EMA_CROSS",
                    "direction": "bearish",
                    "value": ema9,
                    "detail": "EMA9 below EMA21",
                }
            )

    stoch_k = indicators.get("stoch_k")
    stoch_d = indicators.get("stoch_d")
    if stoch_k is not None and stoch_d is not None:
        if stoch_k < 20 and stoch_k > stoch_d:
            signals.append(
                {
                    "indicator": "STOCH",
                    "direction": "bullish",
                    "value": stoch_k,
                    "detail": f"Stochastic oversold crossover at {stoch_k:.1f}",
                }
            )
        elif stoch_k > 80 and stoch_k < stoch_d:
            signals.append(
                {
                    "indicator": "STOCH",
                    "direction": "bearish",
                    "value": stoch_k,
                    "detail": f"Stochastic overbought crossover at {stoch_k:.1f}",
                }
            )

    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    if bb_upper is not None and bb_lower is not None:
        if price <= bb_lower:
            signals.append(
                {
                    "indicator": "BOLLINGER",
                    "direction": "bullish",
                    "value": price,
                    "detail": "Price at lower Bollinger Band",
                }
            )
        elif price >= bb_upper:
            signals.append(
                {
                    "indicator": "BOLLINGER",
                    "direction": "bearish",
                    "value": price,
                    "detail": "Price at upper Bollinger Band",
                }
            )

    avg_vol = indicators.get("avg_volume")
    vol = indicators.get("volume")
    if avg_vol and vol and avg_vol > 0:
        vol_ratio = vol / avg_vol
        if vol_ratio > 2.0:
            signals.append(
                {
                    "indicator": "VOLUME",
                    "direction": "neutral",
                    "value": vol_ratio,
                    "detail": f"Volume spike: {vol_ratio:.1f}x average",
                }
            )

    return signals
