import asyncio
import pytest
import pandas as pd
import numpy as np
from src.data.fetcher import fetch_stock
from src.data.cache import InMemoryCache


@pytest.fixture
def sample_ohlcv():
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


def test_cache_set_get():
    cache = InMemoryCache()
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_ttl():
    import time

    cache = InMemoryCache()
    cache.set("key1", "value1")
    assert cache.get("key1", ttl=0) is None


def test_cache_invalidate():
    cache = InMemoryCache()
    cache.set("key1", "value1")
    cache.invalidate("key1")
    assert cache.get("key1") is None
