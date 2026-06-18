# -*- coding: utf-8 -*-
"""
多因子策略模块

综合动量、波动率、成交量和趋势四个因子，通过加权评分生成交易信号。
"""

import numpy as np
import pandas as pd

from etf_analyzer.strategies import BaseStrategy, register_strategy
from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("strategies.multi_factor")


@register_strategy("multi_factor")
class MultiFactorStrategy(BaseStrategy):
    """多因子策略，综合多个因子评分生成交易信号。

    因子包括：动量、波动率、成交量、趋势，通过加权求和得到综合评分，
    再根据买入/卖出阈值生成信号和仓位建议。
    """

    # 默认因子权重
    DEFAULT_FACTOR_WEIGHTS = {
        "momentum": 0.3,
        "volatility": 0.2,
        "volume": 0.2,
        "trend": 0.3,
    }

    def __init__(
        self,
        factor_weights: dict = None,
        buy_threshold: float = 0.6,
        sell_threshold: float = 0.4,
        window: int = 20,
    ):
        """初始化多因子策略。

        Args:
            factor_weights: 因子权重字典，键为因子名，值为权重
            buy_threshold: 买入阈值，综合评分超过此值时买入
            sell_threshold: 卖出阈值，综合评分低于此值时卖出
            window: 评分窗口天数
        """
        if factor_weights is None:
            factor_weights = dict(self.DEFAULT_FACTOR_WEIGHTS)

        params = {
            "factor_weights": factor_weights,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
            "window": window,
        }

        # 先验证再初始化
        if not self._validate_parameters(params):
            raise ValueError(f"参数验证失败: {params}")

        super().__init__(**params)

        self.factor_weights = factor_weights
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.window = window

        logger.info(
            "多因子策略初始化完成: weights=%s, buy=%.2f, sell=%.2f, window=%d",
            factor_weights, buy_threshold, sell_threshold, window,
        )

    def _validate_parameters(self, params: dict) -> bool:
        """验证策略参数合法性。

        Args:
            params: 待验证的参数字典

        Returns:
            bool: 验证通过返回 True
        """
        window = params.get("window", self.window if hasattr(self, "window") else 20)
        if not isinstance(window, (int, float)) or window <= 0:
            logger.error("window 必须为正数，当前值: %s", window)
            return False

        buy_threshold = params.get(
            "buy_threshold",
            self.buy_threshold if hasattr(self, "buy_threshold") else 0.6,
        )
        sell_threshold = params.get(
            "sell_threshold",
            self.sell_threshold if hasattr(self, "sell_threshold") else 0.4,
        )
        if not isinstance(buy_threshold, (int, float)) or \
           not isinstance(sell_threshold, (int, float)):
            logger.error("阈值必须为数值类型")
            return False
        if buy_threshold <= sell_threshold:
            logger.error(
                "buy_threshold(%s) 必须大于 sell_threshold(%s)",
                buy_threshold, sell_threshold,
            )
            return False

        factor_weights = params.get(
            "factor_weights",
            self.factor_weights if hasattr(self, "factor_weights") else self.DEFAULT_FACTOR_WEIGHTS,
        )
        if not isinstance(factor_weights, dict) or len(factor_weights) == 0:
            logger.error("factor_weights 必须为非空字典")
            return False

        for key, value in factor_weights.items():
            if not isinstance(value, (int, float)) or value <= 0:
                logger.error("因子权重必须为正数，%s=%s", key, value)
                return False

        # 允许微小误差，权重总和应接近1
        weight_sum = sum(factor_weights.values())
        if abs(weight_sum - 1.0) > 1e-6:
            logger.error("因子权重总和必须为1，当前总和: %s", weight_sum)
            return False

        return True

    def _normalize(self, series: pd.Series) -> pd.Series:
        """将序列归一化到 0~1 范围。

        Args:
            series: 待归一化的序列

        Returns:
            pd.Series: 归一化后的序列，全相同时返回0.5
        """
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return pd.Series(0.5, index=series.index)
        return (series - min_val) / (max_val - min_val)

    def _calc_momentum(self, data: pd.DataFrame) -> pd.Series:
        """计算动量因子：N日收益率，归一化到0~1。

        Args:
            data: OHLCV数据

        Returns:
            pd.Series: 归一化后的动量因子得分
        """
        # N日收益率
        momentum = data["close"].pct_change(self.window)
        return self._normalize(momentum)

    def _calc_volatility(self, data: pd.DataFrame) -> pd.Series:
        """计算波动率因子：N日波动率的倒数（低波动率得分高），归一化到0~1。

        Args:
            data: OHLCV数据

        Returns:
            pd.Series: 归一化后的波动率因子得分
        """
        # N日收益率的标准差作为波动率
        daily_returns = data["close"].pct_change()
        volatility = daily_returns.rolling(window=self.window).std()
        # 取倒数：低波动率得分高
        inv_volatility = 1.0 / volatility.replace(0, np.nan)
        return self._normalize(inv_volatility)

    def _calc_volume(self, data: pd.DataFrame) -> pd.Series:
        """计算成交量因子：当前成交量相对N日平均成交量的比率，归一化到0~1。

        Args:
            data: OHLCV数据

        Returns:
            pd.Series: 归一化后的成交量因子得分
        """
        avg_volume = data["volume"].rolling(window=self.window).mean()
        volume_ratio = data["volume"] / avg_volume.replace(0, np.nan)
        return self._normalize(volume_ratio)

    def _calc_trend(self, data: pd.DataFrame) -> pd.Series:
        """计算趋势因子：MA5/MA20比率（>1为上升趋势），归一化到0~1。

        Args:
            data: OHLCV数据

        Returns:
            pd.Series: 归一化后的趋势因子得分
        """
        ma5 = data["close"].rolling(window=5).mean()
        ma20 = data["close"].rolling(window=20).mean()
        trend_ratio = ma5 / ma20.replace(0, np.nan)
        return self._normalize(trend_ratio)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """根据多因子评分生成交易信号。

        Args:
            data: 标准OHLCV数据，包含 date, open, high, low, close, volume 列

        Returns:
            pd.DataFrame: 信号DataFrame，包含 date, signal, position 列
        """
        if len(data) < self.window:
            logger.warning("数据长度不足window(%d)天，无法生成信号", self.window)
            return pd.DataFrame(columns=["date", "signal", "position"])

        # 计算各因子得分
        momentum_score = self._calc_momentum(data)
        volatility_score = self._calc_volatility(data)
        volume_score = self._calc_volume(data)
        trend_score = self._calc_trend(data)

        # 综合评分 = sum(factor_score * weight)
        composite_score = (
            momentum_score * self.factor_weights.get("momentum", 0)
            + volatility_score * self.factor_weights.get("volatility", 0)
            + volume_score * self.factor_weights.get("volume", 0)
            + trend_score * self.factor_weights.get("trend", 0)
        )

        # 生成信号和仓位
        signals = pd.DataFrame()
        signals["date"] = data["date"]
        signals["signal"] = 0
        signals["position"] = 0.5

        # 买入：综合评分 > buy_threshold
        buy_mask = composite_score > self.buy_threshold
        signals.loc[buy_mask, "signal"] = 1
        signals.loc[buy_mask, "position"] = (
            (composite_score[buy_mask] - self.buy_threshold)
            / (1.0 - self.buy_threshold) * 0.7 + 0.3
        ).clip(upper=1.0)

        # 卖出：综合评分 < sell_threshold
        sell_mask = composite_score < self.sell_threshold
        signals.loc[sell_mask, "signal"] = -1
        signals.loc[sell_mask, "position"] = (
            composite_score[sell_mask] / self.sell_threshold * 0.3
        ).clip(lower=0.0)

        # 前window日无信号
        signals.iloc[:self.window, signals.columns.get_loc("signal")] = 0
        signals.iloc[:self.window, signals.columns.get_loc("position")] = 0.0

        logger.info("多因子信号生成完成，共 %d 条记录", len(signals))
        return signals

    def get_name(self) -> str:
        """返回策略名称。"""
        return "multi_factor"

    def get_description(self) -> str:
        """返回策略描述。"""
        return (
            "多因子策略：综合动量、波动率、成交量和趋势四个因子，"
            "通过加权评分生成交易信号"
        )
