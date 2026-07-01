import pytest
import pandas as pd
import numpy as np
from src.analysis.patterns import detect_candlestick_patterns
from src.analysis.indicators import compute_indicators, get_indicator_signals


@pytest.fixture
def sample_df():
    dates = pd.date_range("2024-01-01", periods=100, freq="5min")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(100) * 0.5)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close + np.random.randn(100) * 0.1,
            "high": close + abs(np.random.randn(100) * 0.5),
            "low": close - abs(np.random.randn(100) * 0.5),
            "close": close,
            "volume": np.random.randint(1000, 10000, 100),
        }
    )


@pytest.mark.asyncio
async def test_detect_patterns(sample_df):
    patterns = await detect_candlestick_patterns(sample_df)
    assert isinstance(patterns, list)


@pytest.mark.asyncio
async def test_compute_indicators(sample_df):
    indicators = await compute_indicators(sample_df)
    assert isinstance(indicators, dict)
    assert "rsi" in indicators
    assert "macd" in indicators
