import pytest
from src.analysis.signal import generate_signal


@pytest.mark.asyncio
async def test_generate_signal():
    signal = await generate_signal("AAPL", "5m")
    assert "symbol" in signal
    assert "score" in signal
    assert "label" in signal
    assert 0 <= signal["score"] <= 100
    assert signal["label"] in (
        "NOISE",
        "WATCH",
        "HOLD",
        "BUY",
        "SELL",
        "STRONG BUY",
        "STRONG SELL",
    )
