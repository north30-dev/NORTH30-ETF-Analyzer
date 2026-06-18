# -*- coding: utf-8 -*-
"""
动量策略模块

基于价格动量生成交易信号。支持单周期和多周期两种模式：
- 单周期模式：根据N日动量与阈值比较生成信号
- 多周期模式：短周期和长周期动量方向一致时才产生信号
"""

import pandas as pd

from etf_analyzer.strategies import register_strategy
from etf_analyzer.strategies.base import BaseStrategy
from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("strategies.momentum")


@register_strategy("momentum")
class MomentumStrategy(BaseStrategy):
    """动量策略，根据价格动量生成买入/卖出信号。

    参数：
        period: 动量周期，默认20日
        buy_threshold: 买入阈值，默认0.02
        sell_threshold: 卖出阈值，默认-0.02
        use_multi_period: 是否启用多周期模式，默认False
        short_period: 短周期（多周期模式用），默认10日
        long_period: 长周期（多周期模式用），默认60日
    """

    def __init__(
        self,
        period: int = 20,
        buy_threshold: float = 0.02,
        sell_threshold: float = -0.02,
        use_multi_period: bool = False,
        short_period: int = 10,
        long_period: int = 60,
    ):
        params = {
            "period": period,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
            "use_multi_period": use_multi_period,
            "short_period": short_period,
            "long_period": long_period,
        }
        super().__init__(**params)
        if not self._validate_parameters(params):
            raise ValueError(f"参数验证失败: {params}")
        logger.info("动量策略初始化完成，参数: %s", params)

    def _validate_parameters(self, params: dict) -> bool:
        """验证策略参数合法性。"""
        period = params.get("period", 20)
        buy_threshold = params.get("buy_threshold", 0.02)
        sell_threshold = params.get("sell_threshold", -0.02)
        use_multi_period = params.get("use_multi_period", False)
        short_period = params.get("short_period", 10)
        long_period = params.get("long_period", 60)

        # 动量周期必须大于0
        if period <= 0:
            logger.error("动量周期必须大于0，当前值: %s", period)
            return False

        # 买入阈值必须大于卖出阈值
        if buy_threshold <= sell_threshold:
            logger.error(
                "买入阈值必须大于卖出阈值，当前买入: %s，卖出: %s",
                buy_threshold, sell_threshold,
            )
            return False

        # 多周期模式下短周期必须小于长周期
        if use_multi_period and short_period >= long_period:
            logger.error(
                "多周期模式下短周期必须小于长周期，当前短周期: %s，长周期: %s",
                short_period, long_period,
            )
            return False

        return True

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """根据OHLCV数据生成动量交易信号。

        Args:
            data: 标准OHLCV DataFrame，列：date, open, high, low, close, volume

        Returns:
            pd.DataFrame: 信号DataFrame，列：date, signal, position
        """
        period = self._params["period"]
        buy_threshold = self._params["buy_threshold"]
        sell_threshold = self._params["sell_threshold"]
        use_multi_period = self._params["use_multi_period"]
        short_period = self._params["short_period"]
        long_period = self._params["long_period"]

        close = data["close"].values
        dates = data["date"].values
        n = len(data)

        signals = [0] * n
        positions = [0.5] * n

        if use_multi_period:
            # 多周期模式：需要长周期数据才能产生信号
            warmup = long_period
            for i in range(warmup, n):
                short_momentum = (close[i] - close[i - short_period]) / close[i - short_period]
                long_momentum = (close[i] - close[i - long_period]) / close[i - long_period]

                # 短周期和长周期动量方向一致时才产生信号
                if short_momentum > buy_threshold and long_momentum > buy_threshold:
                    signals[i] = 1
                    positions[i] = 0.8
                elif short_momentum < sell_threshold and long_momentum < sell_threshold:
                    signals[i] = -1
                    positions[i] = 0.2
                else:
                    signals[i] = 0
                    positions[i] = 0.5
        else:
            # 单周期模式
            warmup = period
            for i in range(warmup, n):
                momentum = (close[i] - close[i - period]) / close[i - period]

                if momentum > buy_threshold:
                    signals[i] = 1
                    positions[i] = 0.8
                elif momentum < sell_threshold:
                    signals[i] = -1
                    positions[i] = 0.2
                else:
                    signals[i] = 0
                    positions[i] = 0.5

        result = pd.DataFrame({
            "date": dates,
            "signal": signals,
            "position": positions,
        })

        logger.info(
            "动量信号生成完成，数据量: %d，买入信号: %d，卖出信号: %d",
            n,
            sum(1 for s in signals if s == 1),
            sum(1 for s in signals if s == -1),
        )
        return result

    def get_name(self) -> str:
        """返回策略名称。"""
        return "momentum"

    def get_description(self) -> str:
        """返回策略描述。"""
        mode = "多周期" if self._params["use_multi_period"] else "单周期"
        return (
            f"动量策略（{mode}），周期: {self._params['period']}，"
            f"买入阈值: {self._params['buy_threshold']}，"
            f"卖出阈值: {self._params['sell_threshold']}"
        )
