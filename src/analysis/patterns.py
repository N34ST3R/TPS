import asyncio
import pandas as pd


async def detect_candlestick_patterns(df: pd.DataFrame) -> list[dict]:
    def _detect():
        import talib

        if len(df) < 5:
            return []

        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        patterns = {
            "CDL2CROWS": ("Two Crows", "bearish"),
            "CDL3BLACKCROWS": ("Three Black Crows", "bearish"),
            "CDL3INSIDE": ("Three Inside Up/Down", "bullish"),
            "CDL3LINESTRIKE": ("Three-Line Strike", "bullish"),
            "CDL3STARSINSOUTH": ("Three Stars In The South", "bullish"),
            "CDL3WHITESOLDIERS": ("Three White Soldiers", "bullish"),
            "CDLABANDONEDBABY": ("Abandoned Baby", "bullish"),
            "CDLDOJI": ("Doji", "neutral"),
            "CDLDOJISTAR": ("Doji Star", "neutral"),
            "CDLDRAGONFLYDOJI": ("Dragonfly Doji", "bullish"),
            "CDLENGULFING": ("Engulfing Pattern", "reversal"),
            "CDLEVENINGSTAR": ("Evening Star", "bearish"),
            "CDLHAMMER": ("Hammer", "bullish"),
            "CDLHANGINGMAN": ("Hanging Man", "bearish"),
            "CDLHARAMI": ("Harami Pattern", "reversal"),
            "CDLINVERTEDHAMMER": ("Inverted Hammer", "bullish"),
            "CDLMARUBOZU": ("Marubozu", "continuation"),
            "CDLMORNINGSTAR": ("Morning Star", "bullish"),
            "CDLPIERCING": ("Piercing Pattern", "bullish"),
            "CDLSHOOTINGSTAR": ("Shooting Star", "bearish"),
            "CDLSPINNINGTOP": ("Spinning Top", "neutral"),
            "CDLSTICKSANDWICH": ("Stick Sandwich", "bullish"),
            "CDLTRISTAR": ("Tristar Pattern", "reversal"),
        }

        detected = []
        for func_name, (name, direction) in patterns.items():
            func = getattr(talib, func_name, None)
            if func:
                result = func(o, h, l, c)
                if result.iloc[-1] != 0:
                    detected.append(
                        {
                            "pattern": name,
                            "direction": "bullish"
                            if result.iloc[-1] > 0
                            else "bearish",
                            "signal": int(result.iloc[-1]),
                            "strength": abs(result.iloc[-1]),
                        }
                    )
        return detected

    return await asyncio.get_event_loop().run_in_executor(None, _detect)
