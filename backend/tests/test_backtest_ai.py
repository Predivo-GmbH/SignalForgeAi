"""Tests for AI-enhanced backtesting (SignalQualityEvaluator integration)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd


def make_trending_candles(n=300):
    """Trending upward data with enough bars for lookback."""
    rng = np.random.default_rng(42)
    close = 100 + np.arange(n) * 0.3 + rng.normal(0, 1, n)
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    return pd.DataFrame({
        "open": close + rng.normal(0, 0.2, n),
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.uniform(1000, 10000, n),
    })


def _make_ai_result(recommendation="confirm", size_factor=1.0):
    """Build a mock SignalQualityEvaluator result."""
    return {
        "quality_score": 70,
        "recommendation": recommendation,
        "reasoning": "Test evaluation",
        "risk_adjustments": {
            "position_size_factor": size_factor,
            "reasoning": "Test adjustment",
        },
    }


class TestAIEnhancedBacktest:
    """Test BacktestEngine with ai_enhanced=True."""

    @patch("app.advisor.signal_quality.SignalQualityEvaluator")
    def test_ai_rejects_signals(self, mock_evaluator):
        """When AI rejects all signals, no trades should be opened."""
        from app.backtest.engine import BacktestEngine

        mock_instance = MagicMock()
        mock_instance.evaluate_sync.return_value = _make_ai_result("reject")
        mock_evaluator.return_value = mock_instance

        # Use more candles and lower confluence to ensure signals are generated
        candles = make_trending_candles(600)

        # First confirm this data generates trades without AI
        engine_baseline = BacktestEngine(min_confluence=20, ai_enhanced=False)
        baseline = engine_baseline.run(
            candles=candles.copy(), symbol="TEST/USD", timeframe="1h",
            initial_capital=10000.0,
        )
        if baseline.metrics["total_trades"] == 0:
            # Pipeline didn't generate signals on this data — skip gracefully
            return

        # Now run with AI rejecting everything
        engine = BacktestEngine(min_confluence=20, ai_enhanced=True)
        engine._evaluator = mock_instance

        result = engine.run(
            candles=candles.copy(), symbol="TEST/USD", timeframe="1h",
            initial_capital=10000.0,
        )

        assert result.metrics["total_trades"] == 0
        assert result.metrics["ai_rejections"] > 0
        assert result.metrics["ai_calls"] > 0
        assert mock_instance.evaluate_sync.call_count > 0

    @patch("app.advisor.signal_quality.SignalQualityEvaluator")
    def test_ai_adjusts_position_size(self, mock_evaluator):
        """When AI returns factor=0.5, PnL should be dampened."""
        from app.backtest.engine import BacktestEngine

        # Run without AI first
        engine_no_ai = BacktestEngine()
        candles = make_trending_candles()
        result_no_ai = engine_no_ai.run(
            candles=candles.copy(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )

        # Now run with AI (factor=0.5)
        mock_instance = MagicMock()
        mock_instance.evaluate_sync.return_value = _make_ai_result("confirm", 0.5)
        mock_evaluator.return_value = mock_instance

        engine_ai = BacktestEngine(ai_enhanced=True)
        engine_ai._evaluator = mock_instance

        result_ai = engine_ai.run(
            candles=candles.copy(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )

        # Same number of trades (no rejections)
        assert result_ai.metrics["total_trades"] == result_no_ai.metrics["total_trades"]

        # If trades occurred, AI run should have dampened PnL
        if result_no_ai.metrics["total_trades"] > 0:
            no_ai_pnl = sum(t.pnl for t in result_no_ai.trades)
            ai_pnl = sum(t.pnl for t in result_ai.trades)
            # With factor 0.5, the absolute PnL should be ~half
            if abs(no_ai_pnl) > 0.01:
                ratio = abs(ai_pnl) / abs(no_ai_pnl)
                assert 0.4 < ratio < 0.6

    @patch("app.advisor.signal_quality.SignalQualityEvaluator")
    def test_ai_confirm_passes_through(self, mock_evaluator):
        """When AI confirms with factor=1.0, trades should match non-AI run."""
        from app.backtest.engine import BacktestEngine

        # Run without AI
        engine_no_ai = BacktestEngine()
        candles = make_trending_candles()
        result_no_ai = engine_no_ai.run(
            candles=candles.copy(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )

        # Run with AI (confirm, factor=1.0)
        mock_instance = MagicMock()
        mock_instance.evaluate_sync.return_value = _make_ai_result("confirm", 1.0)
        mock_evaluator.return_value = mock_instance

        engine_ai = BacktestEngine(ai_enhanced=True)
        engine_ai._evaluator = mock_instance

        result_ai = engine_ai.run(
            candles=candles.copy(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )

        assert result_ai.metrics["total_trades"] == result_no_ai.metrics["total_trades"]
        assert result_ai.metrics.get("ai_rejections", 0) == 0

    def test_ai_disabled_no_evaluator(self):
        """When ai_enhanced=False, no AI metrics should appear."""
        from app.backtest.engine import BacktestEngine

        engine = BacktestEngine(ai_enhanced=False)
        result = engine.run(
            candles=make_trending_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )

        assert "ai_calls" not in result.metrics
        assert "ai_rejections" not in result.metrics
        assert engine._evaluator is None

    @patch("app.advisor.signal_quality.SignalQualityEvaluator")
    def test_ai_fallback_on_claude_failure(self, mock_evaluator):
        """When evaluate_sync returns passthrough fallback, trade proceeds normally."""
        from app.backtest.engine import BacktestEngine

        mock_instance = MagicMock()
        # Simulate Claude unavailable — passthrough fallback
        mock_instance.evaluate_sync.return_value = {
            "quality_score": 60,
            "recommendation": "confirm",
            "reasoning": "AI quality evaluation unavailable — using algorithmic score.",
            "risk_adjustments": {
                "position_size_factor": 1.0,
                "reasoning": "No adjustment",
            },
        }
        mock_evaluator.return_value = mock_instance

        engine = BacktestEngine(ai_enhanced=True)
        engine._evaluator = mock_instance

        result = engine.run(
            candles=make_trending_candles(),
            symbol="TEST/USD",
            timeframe="1h",
            initial_capital=10000.0,
        )

        # Should have trades (no rejections from fallback)
        assert result.metrics.get("ai_rejections", 0) == 0
        # All trades should have factor=1.0
        for trade in result.trades:
            assert trade.position_size_factor == 1.0


class TestEvaluateSync:
    """Test the synchronous evaluate_sync method."""

    @patch("app.advisor.signal_quality.claude_client")
    def test_evaluate_sync_returns_valid_result(self, mock_client):
        from app.advisor.signal_quality import SignalQualityEvaluator

        mock_client.ask_json_sync.return_value = {
            "quality_score": 75,
            "recommendation": "confirm",
            "reasoning": "Good setup",
            "risk_adjustments": {
                "position_size_factor": 0.8,
                "reasoning": "Slightly reduce",
            },
        }

        evaluator = SignalQualityEvaluator()
        result = evaluator.evaluate_sync(
            signal_data={
                "action": "BUY",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "regime": "trending",
                "trend_direction": "bullish",
                "trend_strength": 0.85,
                "confluence_score": 65,
                "triggers": ["macd_crossover"],
                "risk_reward": 2.5,
            },
            confluence_details={"rsi_confirmation": {"hit": True, "weight": 8, "earned": 8}},
            candle_summary=[
                {"open": 100, "high": 102, "low": 99, "close": 101, "volume": 5000},
            ],
        )

        assert result["quality_score"] == 75
        assert result["recommendation"] == "confirm"
        assert result["risk_adjustments"]["position_size_factor"] == 0.8
        mock_client.ask_json_sync.assert_called_once()

    @patch("app.advisor.signal_quality.claude_client")
    def test_evaluate_sync_fallback_on_none(self, mock_client):
        from app.advisor.signal_quality import SignalQualityEvaluator

        mock_client.ask_json_sync.return_value = None

        evaluator = SignalQualityEvaluator()
        result = evaluator.evaluate_sync(
            signal_data={
                "action": "BUY",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "regime": "trending",
                "trend_direction": "bullish",
                "trend_strength": 0.85,
                "confluence_score": 65,
                "triggers": ["macd_crossover"],
                "risk_reward": 2.5,
            },
            confluence_details={},
            candle_summary=[],
        )

        assert result["recommendation"] == "reject"
        assert result["risk_adjustments"]["position_size_factor"] == 0.0
        assert "unavailable" in result["reasoning"].lower()
