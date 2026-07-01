import pandas as pd


def detect_support_resistance(df: pd.DataFrame, window: int = 20) -> dict:
    if len(df) < window:
        return {"support": 0, "resistance": 0}

    highs = df["high"].rolling(window=window, center=True).max()
    lows = df["low"].rolling(window=window, center=True).min()

    resistance = (
        float(highs.iloc[-1])
        if not pd.isna(highs.iloc[-1])
        else float(df["high"].max())
    )
    support = (
        float(lows.iloc[-1]) if not pd.isna(lows.iloc[-1]) else float(df["low"].min())
    )

    return {"support": support, "resistance": resistance}


def detect_volume_spike(df: pd.DataFrame, threshold: float = 2.0) -> bool:
    if len(df) < 20:
        return False
    avg_vol = df["volume"].tail(20).mean()
    current_vol = df["volume"].iloc[-1]
    return bool(current_vol > avg_vol * threshold)


def detect_rsi_divergence(df: pd.DataFrame, period: int = 14) -> str:
    if len(df) < period + 5:
        return "none"

    import talib

    rsi = talib.RSI(df["close"], timeperiod=period)
    prices = df["close"].values
    rsi_vals = rsi.values

    recent_prices = prices[-10:]
    recent_rsi = rsi_vals[-10:]

    if len(recent_prices) < 5:
        return "none"

    price_making_lower_low = recent_prices[-1] < recent_prices[-5]
    rsi_making_higher_low = recent_rsi[-1] > recent_rsi[-5]

    if price_making_lower_low and rsi_making_higher_low:
        return "bullish"

    price_making_higher_high = recent_prices[-1] > recent_prices[-5]
    rsi_making_lower_high = recent_rsi[-1] < recent_rsi[-5]

    if price_making_higher_high and rsi_making_lower_high:
        return "bearish"

    return "none"


def get_atr_regime(df: pd.DataFrame, period: int = 14) -> str:
    if len(df) < period * 2:
        return "unknown"
    import talib

    atr = talib.ATR(df["high"], df["low"], df["close"], timeperiod=period)
    current_atr = atr.iloc[-1]
    avg_atr = atr.tail(20).mean()
    if pd.isna(current_atr) or pd.isna(avg_atr):
        return "unknown"
    ratio = current_atr / avg_atr
    if ratio > 1.5:
        return "high_volatility"
    elif ratio < 0.5:
        return "low_volatility"
    return "normal"
