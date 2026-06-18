# -*- coding: utf-8 -*-
"""
量化策略单元测试

测试策略基类、策略工厂、动量策略、均值回归策略、行业轮动策略和多因子策略。
"""

import numpy as np
import pandas as pd
import pytest

from etf_analyzer.strategies import (
    BaseStrategy,
    register_strategy,
    get_strategy,
    list_strategies,
    _STRATEGY_REGISTRY,
)
from etf_analyzer.strategies.momentum import MomentumStrategy
from etf_analyzer.strategies.mean_reversion import MeanReversionStrategy
from etf_analyzer.strategies.sector_rotation import SectorRotationStrategy
from etf_analyzer.strategies.multi_factor import MultiFactorStrategy


# ============================================================
# 辅助函数：生成模拟 ETF 数据
# ============================================================


def create_test_data(days=100, start_price=10.0, trend=0.001, volatility=0.02):
    """生成模拟ETF数据

    Args:
        days: 数据天数
        start_price: 起始价格
        trend: 日均趋势
        volatility: 日波动率

    Returns:
        pd.DataFrame: 包含 date, open, high, low, close, volume 列
    """
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
# BaseStrategy 抽象类测试
# ============================================================


class TestBaseStrategy:
    """BaseStrategy 抽象类测试"""

    def test_cannot_instantiate_directly(self):
        """验证抽象类不能直接实例化"""
        with pytest.raises(TypeError):
            BaseStrategy()

    def test_subclass_must_implement_abstract_methods(self):
        """验证子类必须实现所有抽象方法"""

        # 缺少 generate_signals
        class IncompleteStrategy1(BaseStrategy):
            def get_name(self):
                return "incomplete1"

            def get_description(self):
                return "不完整策略1"

        with pytest.raises(TypeError):
            IncompleteStrategy1()

        # 缺少 get_name
        class IncompleteStrategy2(BaseStrategy):
            def generate_signals(self, data):
                return pd.DataFrame()

            def get_description(self):
                return "不完整策略2"

        with pytest.raises(TypeError):
            IncompleteStrategy2()

    def test_complete_subclass_can_instantiate(self):
        """验证完整实现所有抽象方法的子类可以实例化"""

        class CompleteStrategy(BaseStrategy):
            def generate_signals(self, data):
                return pd.DataFrame()

            def get_name(self):
                return "complete"

            def get_description(self):
                return "完整策略"

        strategy = CompleteStrategy()
        assert strategy.get_name() == "complete"

    def test_get_parameters(self):
        """验证获取参数返回正确字典"""
        strategy = MomentumStrategy(period=15, buy_threshold=0.03)
        params = strategy.get_parameters()
        assert params["period"] == 15
        assert params["buy_threshold"] == 0.03

    def test_set_parameters(self):
        """验证更新参数功能"""
        strategy = MomentumStrategy()
        strategy.set_parameters({"period": 30})
        params = strategy.get_parameters()
        assert params["period"] == 30
        # 其他参数保持不变
        assert params["buy_threshold"] == 0.02

    def test_set_parameters_invalid_type(self):
        """验证传入非字典参数抛出 ValueError"""
        strategy = MomentumStrategy()
        with pytest.raises(ValueError, match="参数必须是字典类型"):
            strategy.set_parameters("not_a_dict")

    def test_set_parameters_validation_failure(self):
        """验证参数验证失败时抛出 ValueError"""
        strategy = MomentumStrategy()
        with pytest.raises(ValueError, match="参数验证失败"):
            strategy.set_parameters({"period": -1})


# ============================================================
# 策略工厂测试
# ============================================================


class TestStrategyFactory:
    """策略工厂测试"""

    def test_list_strategies_contains_registered(self):
        """验证已注册策略出现在列表中"""
        names = list_strategies()
        assert "momentum" in names
        assert "mean_reversion" in names
        assert "sector_rotation" in names
        assert "multi_factor" in names

    def test_get_strategy_returns_correct_instance(self):
        """验证通过工厂获取策略实例"""
        strategy = get_strategy("momentum")
        assert isinstance(strategy, MomentumStrategy)
        assert strategy.get_name() == "momentum"

    def test_get_strategy_with_params(self):
        """验证通过工厂获取带参数的策略实例"""
        strategy = get_strategy("momentum", period=30, buy_threshold=0.05)
        params = strategy.get_parameters()
        assert params["period"] == 30
        assert params["buy_threshold"] == 0.05

    def test_get_strategy_not_found(self):
        """验证获取未注册策略抛出 KeyError"""
        with pytest.raises(KeyError, match="未注册"):
            get_strategy("nonexistent_strategy")

    def test_register_strategy_decorator(self):
        """验证装饰器模式注册策略"""

        @register_strategy("test_strategy_decorator")
        class TestStrategyDecorator(BaseStrategy):
            def generate_signals(self, data):
                return pd.DataFrame()

            def get_name(self):
                return "test_strategy_decorator"

            def get_description(self):
                return "测试装饰器注册"

        assert "test_strategy_decorator" in list_strategies()
        # 清理注册表
        _STRATEGY_REGISTRY.pop("test_strategy_decorator", None)

    def test_register_strategy_function_call(self):
        """验证函数调用模式注册策略"""

        class TestStrategyFuncCall(BaseStrategy):
            def generate_signals(self, data):
                return pd.DataFrame()

            def get_name(self):
                return "test_strategy_func"

            def get_description(self):
                return "测试函数调用注册"

        register_strategy("test_strategy_func", TestStrategyFuncCall)
        assert "test_strategy_func" in list_strategies()
        # 清理注册表
        _STRATEGY_REGISTRY.pop("test_strategy_func", None)

    def test_register_duplicate_name_raises(self):
        """验证重复注册同名策略抛出 ValueError"""

        class DummyStrategy(BaseStrategy):
            def generate_signals(self, data):
                return pd.DataFrame()

            def get_name(self):
                return "dummy"

            def get_description(self):
                return "测试"

        register_strategy("dummy_dup_test", DummyStrategy)
        with pytest.raises(ValueError, match="已被注册"):
            register_strategy("dummy_dup_test", DummyStrategy)
        # 清理注册表
        _STRATEGY_REGISTRY.pop("dummy_dup_test", None)

    def test_register_non_basestrategy_raises(self):
        """验证注册非 BaseStrategy 子类抛出 TypeError"""

        class NotAStrategy:
            pass

        with pytest.raises(TypeError, match="必须继承 BaseStrategy"):
            register_strategy("bad_strategy", NotAStrategy)


# ============================================================
# MomentumStrategy 测试
# ============================================================


class TestMomentumStrategy:
    """动量策略测试"""

    def test_default_parameters(self):
        """验证默认参数值"""
        strategy = MomentumStrategy()
        params = strategy.get_parameters()
        assert params["period"] == 20
        assert params["buy_threshold"] == 0.02
        assert params["sell_threshold"] == -0.02
        assert params["use_multi_period"] is False
        assert params["short_period"] == 10
        assert params["long_period"] == 60

    def test_custom_parameters(self):
        """验证自定义参数"""
        strategy = MomentumStrategy(
            period=15, buy_threshold=0.05, sell_threshold=-0.03
        )
        params = strategy.get_parameters()
        assert params["period"] == 15
        assert params["buy_threshold"] == 0.05
        assert params["sell_threshold"] == -0.03

    def test_generate_signals_returns_correct_format(self):
        """验证信号输出包含 date, signal, position 三列"""
        data = create_test_data(days=100)
        strategy = MomentumStrategy()
        signals = strategy.generate_signals(data)

        assert isinstance(signals, pd.DataFrame)
        assert "date" in signals.columns
        assert "signal" in signals.columns
        assert "position" in signals.columns
        assert len(signals) == len(data)

    def test_signal_values_in_valid_range(self):
        """验证信号值在合法范围内"""
        data = create_test_data(days=100)
        strategy = MomentumStrategy()
        signals = strategy.generate_signals(data)

        assert set(signals["signal"].unique()).issubset({1, 0, -1})
        assert (signals["position"] >= 0.0).all()
        assert (signals["position"] <= 1.0).all()

    def test_buy_signal_when_momentum_above_threshold(self):
        """验证动量>买入阈值时产生买入信号"""
        # 构造持续上涨的数据，确保动量超过阈值
        days = 50
        dates = pd.date_range(start="2024-01-01", periods=days, freq="B")
        close = pd.Series(range(10, 10 + days), dtype=float)
        close = close * 1.0  # 每天涨1元，动量远超0.02

        data = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 500000,
        })

        strategy = MomentumStrategy(period=5, buy_threshold=0.01)
        signals = strategy.generate_signals(data)

        # 在warmup期后，应该有买入信号
        buy_signals = signals[signals["signal"] == 1]
        assert len(buy_signals) > 0

    def test_sell_signal_when_momentum_below_threshold(self):
        """验证动量<卖出阈值时产生卖出信号"""
        # 构造持续下跌的数据
        days = 50
        dates = pd.date_range(start="2024-01-01", periods=days, freq="B")
        close = pd.Series(range(100, 100 - days, -1), dtype=float)

        data = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 500000,
        })

        strategy = MomentumStrategy(period=5, sell_threshold=-0.01)
        signals = strategy.generate_signals(data)

        # 在warmup期后，应该有卖出信号
        sell_signals = signals[signals["signal"] == -1]
        assert len(sell_signals) > 0

    def test_hold_signal_when_momentum_in_range(self):
        """验证动量在阈值之间时产生持有信号"""
        # 构造平稳数据，动量接近0
        days = 50
        dates = pd.date_range(start="2024-01-01", periods=days, freq="B")
        close = pd.Series([10.0] * days)

        data = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": 500000,
        })

        strategy = MomentumStrategy(period=5, buy_threshold=0.02, sell_threshold=-0.02)
        signals = strategy.generate_signals(data)

        # warmup期后，应该全部是持有信号
        hold_signals = signals.iloc[5:][signals["signal"].iloc[5:] == 0]
        assert len(hold_signals) > 0

    def test_multi_period_mode(self):
        """验证多周期模式"""
        data = create_test_data(days=150)
        strategy = MomentumStrategy(
            use_multi_period=True, short_period=10, long_period=30
        )
        signals = strategy.generate_signals(data)

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns
        # 前30天（长周期warmup）无信号
        assert signals["signal"].iloc[:30].sum() == 0

    def test_invalid_period_raises(self):
        """验证非法周期参数抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MomentumStrategy(period=0)

    def test_invalid_threshold_raises(self):
        """验证买入阈值<=卖出阈值抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MomentumStrategy(buy_threshold=0.01, sell_threshold=0.02)

    def test_invalid_multi_period_raises(self):
        """验证多周期模式下短周期>=长周期抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MomentumStrategy(
                use_multi_period=True, short_period=30, long_period=10
            )

    def test_get_name_and_description(self):
        """验证策略名称和描述"""
        strategy = MomentumStrategy()
        assert strategy.get_name() == "momentum"
        assert "动量策略" in strategy.get_description()
        assert "单周期" in strategy.get_description()

    def test_multi_period_description(self):
        """验证多周期模式描述"""
        strategy = MomentumStrategy(use_multi_period=True)
        assert "多周期" in strategy.get_description()


# ============================================================
# MeanReversionStrategy 测试
# ============================================================


class TestMeanReversionStrategy:
    """均值回归策略测试"""

    def test_default_parameters(self):
        """验证默认参数值"""
        strategy = MeanReversionStrategy()
        params = strategy.get_parameters()
        assert params["period"] == 20
        assert params["std_multiplier"] == 2.0
        assert params["entry_threshold"] == 2.0
        assert params["exit_zone"] == 0.5

    def test_generate_signals_returns_correct_format(self):
        """验证信号输出格式"""
        data = create_test_data(days=100)
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(data)

        assert isinstance(signals, pd.DataFrame)
        assert "date" in signals.columns
        assert "signal" in signals.columns
        assert "position" in signals.columns
        assert len(signals) == len(data)

    def test_signal_values_in_valid_range(self):
        """验证信号值在合法范围内"""
        data = create_test_data(days=100)
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(data)

        assert set(signals["signal"].unique()).issubset({1, 0, -1})
        assert (signals["position"] >= 0.0).all()
        assert (signals["position"] <= 1.0).all()

    def test_buy_signal_when_zscore_below_negative_threshold(self):
        """验证Z-Score低于负入场阈值时产生买入信号"""
        # 构造数据：先平稳后突然大幅下跌，使Z-Score低于-2
        days = 40
        dates = pd.date_range(start="2024-01-01", periods=days, freq="B")
        close = np.concatenate([
            np.full(30, 10.0),  # 前30天平稳
            np.full(10, 5.0),   # 后10天大幅下跌
        ])

        data = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 500000,
        })

        strategy = MeanReversionStrategy(period=20, entry_threshold=1.5)
        signals = strategy.generate_signals(data)

        # 后10天应该有买入信号
        buy_signals = signals.iloc[30:][signals["signal"].iloc[30:] == 1]
        assert len(buy_signals) > 0

    def test_sell_signal_when_zscore_above_threshold(self):
        """验证Z-Score超过入场阈值时产生卖出信号"""
        # 构造数据：先平稳后突然大幅上涨
        days = 40
        dates = pd.date_range(start="2024-01-01", periods=days, freq="B")
        close = np.concatenate([
            np.full(30, 10.0),  # 前30天平稳
            np.full(10, 20.0),  # 后10天大幅上涨
        ])

        data = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 500000,
        })

        strategy = MeanReversionStrategy(period=20, entry_threshold=1.5)
        signals = strategy.generate_signals(data)

        # 后10天应该有卖出信号
        sell_signals = signals.iloc[30:][signals["signal"].iloc[30:] == -1]
        assert len(sell_signals) > 0

    def test_exit_zone_signal(self):
        """验证Z-Score回归至出场区域时产生持有信号"""
        data = create_test_data(days=100)
        strategy = MeanReversionStrategy(entry_threshold=2.0, exit_zone=0.5)
        signals = strategy.generate_signals(data)

        # 信号中应包含持有信号
        hold_signals = signals[signals["signal"] == 0]
        assert len(hold_signals) > 0

    def test_invalid_period_raises(self):
        """验证非法周期参数抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MeanReversionStrategy(period=0)

    def test_invalid_std_multiplier_raises(self):
        """验证非法标准差倍数抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MeanReversionStrategy(std_multiplier=0)

    def test_invalid_threshold_relationship_raises(self):
        """验证入场阈值<=出场区域抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MeanReversionStrategy(entry_threshold=0.3, exit_zone=0.5)

    def test_get_name_and_description(self):
        """验证策略名称和描述"""
        strategy = MeanReversionStrategy()
        assert strategy.get_name() == "mean_reversion"
        assert "均值回归" in strategy.get_description()


# ============================================================
# SectorRotationStrategy 测试
# ============================================================


class TestSectorRotationStrategy:
    """行业轮动策略测试"""

    def test_default_parameters(self):
        """验证默认参数值"""
        strategy = SectorRotationStrategy()
        params = strategy.get_parameters()
        assert params["momentum_period"] == 20
        assert params["top_n"] == 3
        assert params["rebalance_freq"] == "monthly"
        assert params["drop_threshold"] == 3  # 默认等于top_n

    def test_drop_threshold_defaults_to_top_n(self):
        """验证 drop_threshold 默认等于 top_n"""
        strategy = SectorRotationStrategy(top_n=5)
        params = strategy.get_parameters()
        assert params["drop_threshold"] == 5

    def test_single_etf_signal_generation(self):
        """验证单ETF模式信号生成"""
        data = create_test_data(days=100)
        strategy = SectorRotationStrategy()
        signals = strategy.generate_signals(data)

        assert isinstance(signals, pd.DataFrame)
        assert "date" in signals.columns
        assert "signal" in signals.columns
        assert "position" in signals.columns
        assert len(signals) == len(data)

    def test_single_etf_signal_values(self):
        """验证单ETF模式信号值合法"""
        data = create_test_data(days=100)
        strategy = SectorRotationStrategy()
        signals = strategy.generate_signals(data)

        assert set(signals["signal"].unique()).issubset({1, 0, -1})
        assert (signals["position"] >= 0.0).all()
        assert (signals["position"] <= 1.0).all()

    def test_multi_etf_signal_generation(self):
        """验证多ETF模式信号生成"""
        # 构造3只ETF的数据
        data_dict = {
            "ETF_A": create_test_data(days=100, start_price=10.0, trend=0.002),
            "ETF_B": create_test_data(days=100, start_price=15.0, trend=0.001),
            "ETF_C": create_test_data(days=100, start_price=20.0, trend=-0.001),
        }

        strategy = SectorRotationStrategy(top_n=2, momentum_period=10)
        signals = strategy.generate_signals(data_dict)

        assert isinstance(signals, pd.DataFrame)
        assert "date" in signals.columns
        assert "symbol" in signals.columns
        assert "signal" in signals.columns
        assert "position" in signals.columns
        # 应该包含3只ETF的信号
        assert set(signals["symbol"].unique()) == {"ETF_A", "ETF_B", "ETF_C"}

    def test_multi_etf_position_allocation(self):
        """验证多ETF模式仓位分配"""
        data_dict = {
            "ETF_A": create_test_data(days=100, start_price=10.0, trend=0.002),
            "ETF_B": create_test_data(days=100, start_price=15.0, trend=0.001),
        }

        top_n = 1
        strategy = SectorRotationStrategy(top_n=top_n, momentum_period=10)
        signals = strategy.generate_signals(data_dict)

        # 买入信号的仓位应为 1.0/top_n
        buy_signals = signals[signals["signal"] == 1]
        if not buy_signals.empty:
            assert (buy_signals["position"] == round(1.0 / top_n, 4)).all()

    def test_invalid_momentum_period_raises(self):
        """验证非法动量周期抛出 ValueError"""
        with pytest.raises(ValueError, match="momentum_period 必须大于0"):
            SectorRotationStrategy(momentum_period=0)

    def test_invalid_top_n_raises(self):
        """验证非法持仓数量抛出 ValueError"""
        with pytest.raises(ValueError, match="top_n 必须大于0"):
            SectorRotationStrategy(top_n=0)

    def test_invalid_drop_threshold_raises(self):
        """验证 drop_threshold < top_n 抛出 ValueError"""
        with pytest.raises(ValueError, match="drop_threshold 必须大于等于top_n"):
            SectorRotationStrategy(top_n=5, drop_threshold=3)

    def test_invalid_rebalance_freq_raises(self):
        """验证非法调仓频率抛出 ValueError"""
        with pytest.raises(ValueError, match="rebalance_freq 必须为"):
            SectorRotationStrategy(rebalance_freq="daily")

    def test_get_name_and_description(self):
        """验证策略名称和描述"""
        strategy = SectorRotationStrategy()
        assert strategy.get_name() == "sector_rotation"
        assert "行业轮动" in strategy.get_description()

    def test_weekly_rebalance_freq(self):
        """验证周频调仓模式"""
        strategy = SectorRotationStrategy(rebalance_freq="weekly")
        params = strategy.get_parameters()
        assert params["rebalance_freq"] == "weekly"


# ============================================================
# MultiFactorStrategy 测试
# ============================================================


class TestMultiFactorStrategy:
    """多因子策略测试"""

    def test_default_parameters(self):
        """验证默认参数值"""
        strategy = MultiFactorStrategy()
        params = strategy.get_parameters()
        assert params["buy_threshold"] == 0.6
        assert params["sell_threshold"] == 0.4
        assert params["window"] == 20
        assert params["factor_weights"]["momentum"] == 0.3
        assert params["factor_weights"]["volatility"] == 0.2
        assert params["factor_weights"]["volume"] == 0.2
        assert params["factor_weights"]["trend"] == 0.3

    def test_generate_signals_returns_correct_format(self):
        """验证信号输出格式"""
        data = create_test_data(days=100)
        strategy = MultiFactorStrategy()
        signals = strategy.generate_signals(data)

        assert isinstance(signals, pd.DataFrame)
        assert "date" in signals.columns
        assert "signal" in signals.columns
        assert "position" in signals.columns
        assert len(signals) == len(data)

    def test_signal_values_in_valid_range(self):
        """验证信号值在合法范围内"""
        data = create_test_data(days=100)
        strategy = MultiFactorStrategy()
        signals = strategy.generate_signals(data)

        assert set(signals["signal"].unique()).issubset({1, 0, -1})
        assert (signals["position"] >= 0.0).all()
        assert (signals["position"] <= 1.0).all()

    def test_four_factors_calculated(self):
        """验证四个因子计算"""
        data = create_test_data(days=100)
        strategy = MultiFactorStrategy(window=20)

        momentum = strategy._calc_momentum(data)
        volatility = strategy._calc_volatility(data)
        volume = strategy._calc_volume(data)
        trend = strategy._calc_trend(data)

        # 各因子应返回与数据等长的Series
        assert len(momentum) == len(data)
        assert len(volatility) == len(data)
        assert len(volume) == len(data)
        assert len(trend) == len(data)

        # 归一化后值在0~1之间（忽略NaN）
        for factor in [momentum, volatility, volume, trend]:
            valid = factor.dropna()
            assert (valid >= 0.0).all()
            assert (valid <= 1.0).all()

    def test_composite_score_and_signals(self):
        """验证综合评分与信号生成"""
        data = create_test_data(days=100)
        strategy = MultiFactorStrategy(buy_threshold=0.5, sell_threshold=0.4)
        signals = strategy.generate_signals(data)

        # 应该包含买入、卖出或持有信号
        assert len(signals) > 0
        # 前 window 日无信号
        assert (signals["signal"].iloc[:20] == 0).all()

    def test_insufficient_data_returns_empty(self):
        """验证数据不足时返回空DataFrame"""
        data = create_test_data(days=10)
        strategy = MultiFactorStrategy(window=20)
        signals = strategy.generate_signals(data)

        assert signals.empty

    def test_invalid_window_raises(self):
        """验证非法窗口参数抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MultiFactorStrategy(window=0)

    def test_invalid_threshold_raises(self):
        """验证买入阈值<=卖出阈值抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MultiFactorStrategy(buy_threshold=0.3, sell_threshold=0.5)

    def test_invalid_factor_weights_raises(self):
        """验证非法因子权重抛出 ValueError"""
        # 权重总和不为1
        with pytest.raises(ValueError, match="参数验证失败"):
            MultiFactorStrategy(factor_weights={"momentum": 0.5, "volatility": 0.3})

    def test_negative_factor_weight_raises(self):
        """验证负因子权重抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MultiFactorStrategy(factor_weights={
                "momentum": -0.3, "volatility": 0.5, "volume": 0.4, "trend": 0.4
            })

    def test_empty_factor_weights_raises(self):
        """验证空因子权重抛出 ValueError"""
        with pytest.raises(ValueError, match="参数验证失败"):
            MultiFactorStrategy(factor_weights={})

    def test_get_name_and_description(self):
        """验证策略名称和描述"""
        strategy = MultiFactorStrategy()
        assert strategy.get_name() == "multi_factor"
        assert "多因子" in strategy.get_description()

    def test_normalize_constant_series(self):
        """验证归一化常量序列返回0.5"""
        strategy = MultiFactorStrategy()
        constant_series = pd.Series([5.0] * 10)
        normalized = strategy._normalize(constant_series)
        assert (normalized == 0.5).all()

    def test_custom_factor_weights(self):
        """验证自定义因子权重"""
        custom_weights = {
            "momentum": 0.4,
            "volatility": 0.1,
            "volume": 0.1,
            "trend": 0.4,
        }
        strategy = MultiFactorStrategy(factor_weights=custom_weights)
        params = strategy.get_parameters()
        assert params["factor_weights"]["momentum"] == 0.4
        assert params["factor_weights"]["trend"] == 0.4
