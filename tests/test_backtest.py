# -*- coding: utf-8 -*-
"""
回测框架单元测试

测试数据加载器、回测引擎、网格搜索寻优器和信号生成器。
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from etf_analyzer.backtest.data_loader import BacktestDataLoader
from etf_analyzer.backtest.engine import BacktestEngine, BacktestResult
from etf_analyzer.backtest.optimizer import (
    GridSearchOptimizer,
    OptimizationResult,
    BacktestResult as OptimizerBacktestResult,
    create_param_range,
)
from etf_analyzer.backtest.signals import SignalGenerator
from etf_analyzer.strategies.momentum import MomentumStrategy
from etf_analyzer.strategies.mean_reversion import MeanReversionStrategy


# ============================================================
# 辅助函数
# ============================================================


def create_test_data(days=100, start_price=10.0, trend=0.001, volatility=0.02):
    """生成模拟ETF数据"""
    dates = pd.date_range(start="2024-01-01", periods=days, freq="B")
    np.random.seed(42)
    returns = np.random.normal(trend, volatility, days)
    close = start_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.01, days)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, days)))
    open_price = close * (1 + np.random.normal(0, 0.005, days))
    volume = np.random.randint(100000, 1000000, days)

    return pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


# ============================================================
# BacktestDataLoader 测试
# ============================================================


class TestBacktestDataLoader:
    """回测数据加载器测试"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.loader = BacktestDataLoader()

    def test_load_from_csv_with_chinese_columns(self):
        """验证CSV中文列名自动映射"""
        # 创建带中文列名的CSV文件
        data = create_test_data(days=30)
        csv_data = data.rename(columns={
            "date": "日期", "open": "开盘", "high": "最高",
            "low": "最低", "close": "收盘", "volume": "成交量",
        })

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            csv_data.to_csv(f, index=False)
            csv_path = f.name

        try:
            result = self.loader.load_from_csv(csv_path)
            assert not result.empty
            assert list(result.columns) == ["date", "open", "high", "low", "close", "volume"]
            assert pd.api.types.is_datetime64_any_dtype(result["date"])
        finally:
            os.unlink(csv_path)

    def test_load_from_csv_with_english_columns(self):
        """验证CSV英文列名自动映射"""
        data = create_test_data(days=30)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            data.to_csv(f, index=False)
            csv_path = f.name

        try:
            result = self.loader.load_from_csv(csv_path)
            assert not result.empty
            assert list(result.columns) == ["date", "open", "high", "low", "close", "volume"]
        finally:
            os.unlink(csv_path)

    def test_load_from_csv_with_custom_mapping(self):
        """验证自定义列名映射"""
        data = create_test_data(days=30)
        csv_data = data.rename(columns={
            "date": "trade_date", "open": "o", "high": "h",
            "low": "l", "close": "c", "volume": "v",
        })

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            csv_data.to_csv(f, index=False)
            csv_path = f.name

        try:
            custom_mapping = {
                "trade_date": "date", "o": "open", "h": "high",
                "l": "low", "c": "close", "v": "volume",
            }
            result = self.loader.load_from_csv(csv_path, column_mapping=custom_mapping)
            assert not result.empty
            assert list(result.columns) == ["date", "open", "high", "low", "close", "volume"]
        finally:
            os.unlink(csv_path)

    def test_load_from_csv_missing_columns_returns_empty(self):
        """验证缺少必要列时返回空DataFrame"""
        # 创建缺少close列的CSV
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10, freq="B"),
            "open": range(10),
            "volume": range(10),
        })

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            df.to_csv(f, index=False)
            csv_path = f.name

        try:
            result = self.loader.load_from_csv(csv_path)
            assert result.empty
        finally:
            os.unlink(csv_path)

    def test_load_from_nonexistent_csv_returns_empty(self):
        """验证不存在的CSV文件返回空DataFrame"""
        result = self.loader.load_from_csv("/nonexistent/path.csv")
        assert result.empty

    def test_standardize_data_drops_na(self):
        """验证标准化过程去除缺失值行"""
        data = create_test_data(days=30)
        # 添加缺失值
        data.loc[5, "close"] = np.nan
        data.loc[10, "volume"] = np.nan

        result = self.loader._standardize_data(data)
        assert not result.isna().any().any()
        assert len(result) < len(data)

    def test_standardize_data_sorts_by_date(self):
        """验证标准化过程按日期升序排列"""
        data = create_test_data(days=30)
        # 打乱顺序
        data_shuffled = data.sample(frac=1, random_state=42).reset_index(drop=True)

        result = self.loader._standardize_data(data_shuffled)
        dates = result["date"]
        assert dates.is_monotonic_increasing

    def test_standardize_data_numeric_types(self):
        """验证数值列转换为float类型"""
        data = create_test_data(days=30)
        result = self.loader._standardize_data(data)

        for col in ["open", "high", "low", "close", "volume"]:
            assert pd.api.types.is_numeric_dtype(result[col])

    def test_normalize_date_str_yyyymmdd(self):
        """验证YYYYMMDD格式日期标准化"""
        result = BacktestDataLoader._normalize_date_str("20240101")
        assert result == "2024-01-01"

    def test_normalize_date_str_yyyy_mm_dd(self):
        """验证YYYY-MM-DD格式日期不变"""
        result = BacktestDataLoader._normalize_date_str("2024-01-01")
        assert result == "2024-01-01"

    def test_load_from_csv_empty_file_returns_empty(self):
        """验证空CSV文件返回空DataFrame"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write("")
            csv_path = f.name

        try:
            result = self.loader.load_from_csv(csv_path)
            assert result.empty
        finally:
            os.unlink(csv_path)


# ============================================================
# BacktestEngine 测试
# ============================================================


class TestBacktestEngine:
    """回测引擎测试"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.engine = BacktestEngine()
        self.data = create_test_data(days=100)

    def test_run_single_strategy(self):
        """验证单策略回测执行"""
        strategy = MomentumStrategy()
        result = self.engine.run(strategy, self.data)

        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "momentum"
        assert isinstance(result.performance, dict)
        assert isinstance(result.trades, pd.DataFrame)
        assert isinstance(result.equity_curve, pd.DataFrame)
        assert isinstance(result.positions, pd.DataFrame)

    def test_performance_metrics_keys(self):
        """验证绩效指标包含所有必要字段"""
        strategy = MomentumStrategy()
        result = self.engine.run(strategy, self.data)

        expected_keys = [
            "total_return", "annualized_return", "sharpe_ratio",
            "max_drawdown", "max_drawdown_duration", "win_rate",
            "profit_loss_ratio", "trade_count", "calmar_ratio",
        ]
        for key in expected_keys:
            assert key in result.performance, f"缺少绩效指标: {key}"

    def test_equity_curve_format(self):
        """验证净值曲线格式"""
        strategy = MomentumStrategy()
        result = self.engine.run(strategy, self.data)

        assert "date" in result.equity_curve.columns
        assert "cash" in result.equity_curve.columns
        assert "market_value" in result.equity_curve.columns
        assert "total_equity" in result.equity_curve.columns
        assert len(result.equity_curve) > 0

    def test_trades_format(self):
        """验证交易记录格式"""
        strategy = MomentumStrategy()
        result = self.engine.run(strategy, self.data)

        if not result.trades.empty:
            assert "date" in result.trades.columns
            assert "direction" in result.trades.columns
            assert "price" in result.trades.columns
            assert "quantity" in result.trades.columns
            assert "commission" in result.trades.columns

    def test_commission_simulation(self):
        """验证交易成本模拟"""
        # 使用较高的佣金率以确保可观测
        engine = BacktestEngine(commission_rate=0.01, stamp_tax_rate=0.01, slippage=0.01)
        strategy = MomentumStrategy()
        result = engine.run(strategy, self.data)

        # 有交易时，佣金应大于0
        if not result.trades.empty:
            assert (result.trades["commission"] > 0).any()

    def test_initial_capital_preserved(self):
        """验证初始资金参数生效"""
        strategy = MomentumStrategy()
        result = self.engine.run(strategy, self.data, initial_capital=500000.0)

        # 净值曲线首日权益应接近初始资金
        first_equity = result.equity_curve["total_equity"].iloc[0]
        assert abs(first_equity - 500000.0) < 500000.0 * 0.1  # 允许10%误差（含滑点等）

    def test_run_comparison(self):
        """验证多策略对比回测"""
        strategies = [
            MomentumStrategy(),
            MeanReversionStrategy(),
        ]
        results = self.engine.run_comparison(strategies, self.data)

        assert isinstance(results, dict)
        assert "momentum" in results
        assert "mean_reversion" in results
        assert isinstance(results["momentum"], BacktestResult)
        assert isinstance(results["mean_reversion"], BacktestResult)

    def test_backtest_result_get_metric(self):
        """验证 BacktestResult.get_metric 方法"""
        strategy = MomentumStrategy()
        result = self.engine.run(strategy, self.data)

        # 获取存在的指标
        sharpe = result.get_metric("sharpe_ratio")
        assert isinstance(sharpe, float)

        # 获取不存在的指标返回0.0
        assert result.get_metric("nonexistent_metric") == 0.0

    def test_empty_signals_returns_empty_result(self):
        """验证策略无信号时返回空结果"""

        # 创建一个始终不产生信号的策略
        class NoSignalStrategy(MomentumStrategy):
            def generate_signals(self, data):
                return pd.DataFrame(columns=["date", "signal", "position"])

        from etf_analyzer.strategies.base import BaseStrategy

        class EmptyStrategy(BaseStrategy):
            def generate_signals(self, data):
                return pd.DataFrame(columns=["date", "signal", "position"])

            def get_name(self):
                return "empty"

            def get_description(self):
                return "空策略"

        strategy = EmptyStrategy()
        result = self.engine.run(strategy, self.data)

        assert result.strategy_name == "empty"
        assert result.performance["total_return"] == 0.0
        assert result.trades.empty

    def test_calculate_drawdown(self):
        """验证最大回撤计算"""
        equity = pd.Series([100, 110, 105, 95, 100, 90, 95])
        max_dd, duration = BacktestEngine._calculate_drawdown(equity)

        # 最大回撤应从110到90，约-18.18%
        assert max_dd < 0
        assert duration > 0

    def test_calculate_trade_stats(self):
        """验证交易统计计算"""
        trades = pd.DataFrame([
            {"direction": "buy", "price": 10.0, "quantity": 100},
            {"direction": "sell", "price": 12.0, "quantity": 100},
            {"direction": "buy", "price": 11.0, "quantity": 100},
            {"direction": "sell", "price": 10.0, "quantity": 100},
        ])

        win_rate, pl_ratio = BacktestEngine._calculate_trade_stats(trades)
        # 第一笔赚200，第二笔亏100，胜率50%
        assert win_rate == 0.5
        assert pl_ratio > 0

    def test_calculate_trade_stats_empty(self):
        """验证空交易记录统计返回0"""
        trades = pd.DataFrame(columns=["direction", "price", "quantity"])
        win_rate, pl_ratio = BacktestEngine._calculate_trade_stats(trades)
        assert win_rate == 0.0
        assert pl_ratio == 0.0


# ============================================================
# GridSearchOptimizer 测试
# ============================================================


class TestGridSearchOptimizer:
    """网格搜索寻优器测试"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.data = create_test_data(days=100)

    def test_create_param_range_integer(self):
        """验证整数参数范围生成"""
        result = create_param_range(10, 30, 10)
        assert result == [10, 20, 30]

    def test_create_param_range_float(self):
        """验证浮点参数范围生成"""
        result = create_param_range(0.01, 0.03, 0.01)
        assert len(result) == 3
        assert abs(result[0] - 0.01) < 1e-9
        assert abs(result[1] - 0.02) < 1e-9
        assert abs(result[2] - 0.03) < 1e-9

    def test_create_param_range_single_value(self):
        """验证单值参数范围"""
        result = create_param_range(20, 20, 1)
        assert result == [20]

    def test_optimize_basic(self):
        """验证基本寻优执行"""
        optimizer = GridSearchOptimizer()
        param_grid = {"period": [10, 20], "buy_threshold": [0.01, 0.02]}

        result = optimizer.optimize(
            MomentumStrategy, self.data, param_grid, metric="sharpe_ratio", top_n=2
        )

        assert isinstance(result, OptimizationResult)
        assert isinstance(result.best_params, dict)
        assert isinstance(result.best_metric_value, float)
        assert result.total_combinations == 4
        assert len(result.top_results) <= 2

    def test_optimize_results_sorted_descending(self):
        """验证寻优结果按指标降序排列"""
        optimizer = GridSearchOptimizer()
        param_grid = {"period": [10, 20, 30]}

        result = optimizer.optimize(
            MomentumStrategy, self.data, param_grid, metric="total_return", top_n=3
        )

        # 验证结果降序排列
        metric_values = [item[1] for item in result.top_results]
        assert metric_values == sorted(metric_values, reverse=True)

    def test_optimize_with_engine(self):
        """验证使用外部回测引擎的寻优"""
        engine = BacktestEngine()
        optimizer = GridSearchOptimizer(engine=engine)
        param_grid = {"period": [10, 20]}

        result = optimizer.optimize(
            MomentumStrategy, self.data, param_grid, metric="total_return"
        )

        assert isinstance(result, OptimizationResult)
        assert result.best_params is not None

    def test_optimize_empty_grid_raises(self):
        """验证空参数网格抛出 ValueError"""
        optimizer = GridSearchOptimizer()
        with pytest.raises(ValueError, match="参数网格不能为空"):
            optimizer.optimize(MomentumStrategy, self.data, {})

    def test_optimize_top_n_limit(self):
        """验证 top_n 限制返回结果数量"""
        optimizer = GridSearchOptimizer()
        param_grid = {"period": [10, 15, 20, 25, 30]}

        result = optimizer.optimize(
            MomentumStrategy, self.data, param_grid, top_n=3
        )

        assert len(result.top_results) <= 3

    def test_optimizer_backtest_result_get_metric(self):
        """验证 OptimizerBacktestResult.get_metric 方法"""
        result = OptimizerBacktestResult(total_return=0.1, sharpe_ratio=1.5)
        assert result.get_metric("total_return") == 0.1
        assert result.get_metric("sharpe_ratio") == 1.5
        assert result.get_metric("nonexistent") == 0.0


# ============================================================
# SignalGenerator 测试
# ============================================================


class TestSignalGenerator:
    """信号生成器测试"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.generator = SignalGenerator()
        self.data = create_test_data(days=100)

    def test_generate_signal(self):
        """验证实时信号计算"""
        strategy = MomentumStrategy()
        result = self.generator.generate_signal(strategy, self.data)

        assert isinstance(result, dict)
        assert "signal" in result
        assert "position" in result
        assert "signal_strength" in result
        assert "timestamp" in result
        assert "strategy_name" in result
        assert result["signal"] in [1, 0, -1]
        assert 0.0 <= result["position"] <= 1.0
        assert 0.0 <= result["signal_strength"] <= 1.0
        assert result["strategy_name"] == "momentum"

    def test_generate_signal_with_empty_data(self):
        """验证空数据时信号生成返回默认值"""
        strategy = MomentumStrategy()
        empty_data = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        result = self.generator.generate_signal(strategy, empty_data)

        assert result["signal"] == 0
        assert result["position"] == 0.0
        assert result["signal_strength"] == 0.0

    def test_generate_position_advice_buy(self):
        """验证买入信号仓位建议"""
        advice = self.generator.generate_position_advice(
            signal=1, position=0.8, current_position=0.0
        )

        assert advice["action"] == "buy"
        assert advice["target_position"] >= 0.3
        assert advice["adjustment"] > 0

    def test_generate_position_advice_sell(self):
        """验证卖出信号仓位建议"""
        advice = self.generator.generate_position_advice(
            signal=-1, position=0.2, current_position=0.8
        )

        assert advice["action"] == "sell"
        assert advice["target_position"] <= 0.3
        assert advice["adjustment"] < 0

    def test_generate_position_advice_hold(self):
        """验证持有信号仓位建议"""
        advice = self.generator.generate_position_advice(
            signal=0, position=0.5, current_position=0.5
        )

        assert advice["action"] == "hold"
        assert advice["adjustment"] == 0.0

    def test_generate_position_advice_risk_levels(self):
        """验证仓位建议风险等级"""
        # 小幅调整 → low
        advice_low = self.generator.generate_position_advice(
            signal=1, position=0.5, current_position=0.4
        )
        assert advice_low["risk_level"] == "low"

        # 中等调整 → medium
        advice_medium = self.generator.generate_position_advice(
            signal=1, position=0.8, current_position=0.3
        )
        assert advice_medium["risk_level"] == "medium"

        # 大幅调整 → high
        advice_high = self.generator.generate_position_advice(
            signal=1, position=1.0, current_position=0.0
        )
        assert advice_high["risk_level"] == "high"

    def test_generate_report(self):
        """验证策略执行报告生成"""
        strategy = MomentumStrategy()
        report = self.generator.generate_report(strategy, self.data)

        assert isinstance(report, dict)
        assert "current_signal" in report
        assert "signal_statistics" in report
        assert "recent_trades" in report
        assert "risk_warnings" in report
        assert "strategy_info" in report

    def test_generate_report_current_signal(self):
        """验证报告中当前信号格式"""
        strategy = MomentumStrategy()
        report = self.generator.generate_report(strategy, self.data)

        current = report["current_signal"]
        assert "signal" in current
        assert "position" in current
        assert "signal_strength" in current

    def test_generate_report_signal_statistics(self):
        """验证报告中信号统计格式"""
        strategy = MomentumStrategy()
        report = self.generator.generate_report(strategy, self.data)

        stats = report["signal_statistics"]
        assert "total" in stats
        assert "buy_count" in stats
        assert "sell_count" in stats
        assert "hold_count" in stats
        assert "buy_ratio" in stats
        assert "sell_ratio" in stats
        assert "hold_ratio" in stats
        assert stats["total"] > 0

    def test_generate_report_strategy_info(self):
        """验证报告中策略信息格式"""
        strategy = MomentumStrategy()
        report = self.generator.generate_report(strategy, self.data)

        info = report["strategy_info"]
        assert info["name"] == "momentum"
        assert "description" in info
        assert "parameters" in info

    def test_signal_strength_calculation(self):
        """验证信号强度计算"""
        strategy = MomentumStrategy()
        signals_df = strategy.generate_signals(self.data)
        strength = self.generator._calculate_signal_strength(signals_df)

        assert 0.0 <= strength <= 1.0

    def test_signal_strength_with_single_row(self):
        """验证单行数据信号强度返回0"""
        signals_df = pd.DataFrame({"signal": [1]})
        strength = self.generator._calculate_signal_strength(signals_df)
        assert strength == 0.0

    def test_extract_recent_trades(self):
        """验证近期交易建议提取"""
        strategy = MomentumStrategy()
        signals_df = strategy.generate_signals(self.data)
        trades = self.generator._extract_recent_trades(signals_df, recent_days=30)

        assert isinstance(trades, list)
        # 每条交易建议应包含必要字段
        for trade in trades:
            assert "date" in trade
            assert "signal" in trade
            assert "action" in trade
            assert "position" in trade

    def test_risk_warnings_frequent_trading(self):
        """验证频繁交易风险提示"""
        # 构造频繁变化的信号
        signals_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10, freq="B"),
            "signal": [1, -1, 1, -1, 1, -1, 1, -1, 1, -1],
            "position": [0.8, 0.2, 0.8, 0.2, 0.8, 0.2, 0.8, 0.2, 0.8, 0.2],
        })
        current_signal = {"signal": 1, "position": 0.8, "signal_strength": 0.5}
        warnings = self.generator._generate_risk_warnings(
            signals_df, current_signal, recent_days=10
        )

        # 应该有频繁交易风险提示
        assert any("频繁交易" in w for w in warnings)

    def test_risk_warnings_high_position(self):
        """验证高仓位风险提示"""
        signals_df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30, freq="B"),
            "signal": [1] * 30,
            "position": [0.9] * 30,
        })
        current_signal = {"signal": 1, "position": 0.9, "signal_strength": 0.8}
        warnings = self.generator._generate_risk_warnings(
            signals_df, current_signal, recent_days=30
        )

        assert any("仓位集中度" in w for w in warnings)
