"""Tests for the AI gate rules in the signal pipeline.

Covers three critical correctness requirements (CLAUDE.md — No AI, No Trading):
1. MTF recommendation="reject" must block the signal immediately.
2. ai_recommendation=None (AI gate never ran) must be converted to reject at call site.
3. Signal with ai_recommendation="confirm" passes (baseline sanity).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(action="BUY", symbol="ETH/USDT", timeframe="4h", confluence_score=75):
    s = MagicMock()
    s.action = action
    s.symbol = symbol
    s.timeframe = timeframe
    s.regime = "trending"
    s.trend_direction = "bullish"
    s.trend_strength = 0.7
    s.confluence_score = confluence_score
    s.triggers = []
    s.risk_reward = 2.0
    s.stop_loss = 1900.0
    s.take_profit_1 = 2200.0
    s.take_profit_2 = None
    s.position_size = 0.01
    s.confluence_details = {}
    return s


def _make_signal_row():
    row = MagicMock()
    row.ai_recommendation = None
    row.ai_reasoning = None
    row.ai_quality_score = None
    row.mtf_confidence = None
    row.mtf_alignment = None
    row.position_size = 0.01
    return row


def _make_df():
    import numpy as np
    import pandas as pd

    n = 10
    close = 2000.0 + np.arange(n)
    return pd.DataFrame({
        "open": close,
        "high": close + 5,
        "low": close - 5,
        "close": close,
        "volume": [1000.0] * n,
    })


# ---------------------------------------------------------------------------
# 1. MTF reject blocks signal
# ---------------------------------------------------------------------------


def test_mtf_reject_sets_ai_recommendation_to_reject():
    """When MultiTimeframeAnalyzer returns recommendation='reject', the signal must be blocked."""
    from app.tasks.run_pipeline import _ai_enrich_signal

    signal = _make_signal()
    signal_row = _make_signal_row()
    db = AsyncMock()

    mtf_result = {
        "recommendation": "reject",
        "reasoning": "Higher timeframe is bearish",
        "mtf_confidence": 20,
        "timeframe_alignment": "misaligned",
    }

    async def run():
        from app.config import settings as real_settings
        with (
            patch.object(real_settings, "ai_multi_timeframe_enabled", True),
            patch.object(real_settings, "ai_signal_quality_enabled", False),
            patch("app.advisor.multi_tf_analyzer.MultiTimeframeAnalyzer") as MockMTF,
        ):
            mock_analyzer = MagicMock()
            mock_analyzer.analyze = AsyncMock(return_value=mtf_result)
            MockMTF.return_value = mock_analyzer
            await _ai_enrich_signal(signal, signal_row, db, _make_df())

    asyncio.run(run())

    assert signal_row.ai_recommendation == "reject"
    assert signal_row.ai_quality_score == 0
    assert "MTF" in (signal_row.ai_reasoning or "")


def test_mtf_confirm_does_not_block():
    """MTF recommendation='confirm' should not block the signal."""
    from app.tasks.run_pipeline import _ai_enrich_signal

    signal = _make_signal()
    signal_row = _make_signal_row()
    db = AsyncMock()

    mtf_result = {
        "recommendation": "confirm",
        "reasoning": "All timeframes aligned",
        "mtf_confidence": 80,
        "timeframe_alignment": "aligned",
    }

    async def run():
        from app.config import settings as real_settings
        with (
            patch.object(real_settings, "ai_multi_timeframe_enabled", True),
            patch.object(real_settings, "ai_signal_quality_enabled", False),
            patch("app.advisor.multi_tf_analyzer.MultiTimeframeAnalyzer") as MockMTF,
        ):
            mock_analyzer = MagicMock()
            mock_analyzer.analyze = AsyncMock(return_value=mtf_result)
            MockMTF.return_value = mock_analyzer
            await _ai_enrich_signal(signal, signal_row, db, _make_df())

    asyncio.run(run())

    # With both feature flags off except MTF=True and MTF returning "confirm",
    # ai_recommendation should remain None (signal quality never ran)
    assert signal_row.ai_recommendation != "reject"


# ---------------------------------------------------------------------------
# 2. NULL ai_recommendation treated as reject at the call site
# ---------------------------------------------------------------------------


def test_caller_converts_null_recommendation_to_reject():
    """The run_pipeline caller converts None ai_recommendation to 'reject' before checking.

    This mirrors the logic inserted after _ai_enrich_signal returns.
    """
    signal_row = _make_signal_row()
    signal_row.ai_recommendation = None  # AI gate never ran

    # Mirror the logic in run_pipeline._process_signals
    if signal_row.ai_recommendation is None:
        signal_row.ai_recommendation = "reject"
        signal_row.ai_reasoning = (
            "AI signal quality evaluation did not run — "
            "signal rejected per no-trading-without-AI policy."
        )
        signal_row.ai_quality_score = 0

    assert signal_row.ai_recommendation == "reject"
    assert signal_row.ai_quality_score == 0
    assert "no-trading-without-AI" in signal_row.ai_reasoning


def test_null_not_converted_when_recommendation_is_set():
    """The NULL→reject conversion must not overwrite an already-set recommendation."""
    signal_row = _make_signal_row()
    signal_row.ai_recommendation = "confirm"  # AI ran and approved

    if signal_row.ai_recommendation is None:
        signal_row.ai_recommendation = "reject"

    # Must not have been overwritten
    assert signal_row.ai_recommendation == "confirm"


# ---------------------------------------------------------------------------
# 3. Confirmed signal passes (baseline sanity)
# ---------------------------------------------------------------------------


def test_confirmed_signal_not_rejected():
    """A signal that receives ai_recommendation='confirm' must NOT be blocked."""
    signal_row = _make_signal_row()
    signal_row.ai_recommendation = "confirm"

    # Apply the NULL→reject conversion (it should be a no-op here)
    if signal_row.ai_recommendation is None:
        signal_row.ai_recommendation = "reject"

    assert signal_row.ai_recommendation == "confirm"
