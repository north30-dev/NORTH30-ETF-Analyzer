# -*- coding: utf-8 -*-
"""
均值回归策略模块

基于布林带和Z-Score的均值回归策略。当价格偏离均线超过阈值时反向开仓，
当价格回归至均线附近时平仓。
"""

import numpy as np
import pandas as pd

from etf_analyzer.strategies import register_strategy
from etf_analyzer.strategies.base import BaseStrategy
from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("strategies.mean_reversion")


@register_strategy("mean_reversion")
class MeanReversionStrategy(BaseStrategy):
    """均值回归策略

    利用布林带和Z-Score判断价格偏离程度，在价格过度偏离时反向交易，
    在价格回归均值附近时平仓。

    参数:
        period: 均线周期，默认20日
        std_multiplier: 标准差倍数（布林带宽度），默认2.0
        entry_threshold: 入场阈值（Z-Score绝对值超过此值入场），默认2.0
        exit_zone: 出场区域（Z-Score绝对值低于此值平仓），默认0.5
    """

    def __init__(self, period: int = 20, std_multiplier: float = 2.0,
                 entry_threshold: float = 2.0, exit_zone: float = 0.5):
        params = {
            "period": period,
            "std_multiplier": std_multiplier,
            "entry_threshold": entry_threshold,
            "exit_zone": exit_zone,
        }
        super().__init__(**params)
        self._validate_and_raise(params)
        logger.info(
            "均值回归策略初始化: period=%d, std_multiplier=%.1f, "
            "entry_threshold=%.1f, exit_zone=%.1f",
            period, std_multiplier, entry_threshold, exit_zone,
        )

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """根据OHLCV数据生成均值回归交易信号。

        计算流程：
            1. 计算移动均线 SMA(period) 和标准差 std(period)
            2. 计算布林带上下轨
            3. 计算Z-Score = (close - SMA) / std
            4. 根据Z-Score与阈值的关系生成信号

        Args:
            data: 标准化OHLCV数据，包含 date, open, high, low, close, volume 列

        Returns:
            pd.DataFrame: 包含 date, signal, position 三列的信号DataFrame
        """
        period = self._params["period"]
        std_multiplier = self._params["std_multiplier"]
        entry_threshold = self._params["entry_threshold"]
        exit_zone = self._params["exit_zone"]

        close = data["close"].values
        dates = data["date"].values

        # 计算移动均线和标准差
        sma = pd.Series(close).rolling(window=period, min_periods=period).mean()
        std = pd.Series(close).rolling(window=period, min_periods=period).std(ddof=0)

        # 计算布林带上下轨
        upper = sma + std_multiplier * std
        lower = sma - std_multiplier * std

        # 计算Z-Score
        z_score = (close - sma) / std

        # 初始化信号和仓位
        signals = np.zeros(len(data), dtype=int)
        positions = np.full(len(data), 0.5)

        # 前 period 日无信号
        for i in range(period, len(data)):
            z = z_score.iloc[i]
            if np.isnan(z):
                signals[i] = 0
                positions[i] = 0.5
            elif z < -entry_threshold:
                # Z-Score 低于负入场阈值，买入信号
                signals[i] = 1
                positions[i] = 0.8
            elif z > entry_threshold:
                # Z-Score 超过入场阈值，卖出信号
                signals[i] = -1
                positions[i] = 0.2
            elif abs(z) < exit_zone:
                # Z-Score 回归至出场区域，平仓/持有
                signals[i] = 0
                positions[i] = 0.5
            else:
                # 其他情况持有
                signals[i] = 0
                positions[i] = 0.5

        result = pd.DataFrame({
            "date": dates,
            "signal": signals,
            "position": positions,
        })

        logger.info("均值回归信号生成完成，共 %d 条记录", len(result))
        return result

    def get_name(self) -> str:
        """返回策略名称。"""
        return "mean_reversion"

    def get_description(self) -> str:
        """返回策略描述。"""
        return (
            "均值回归策略：基于布林带和Z-Score，在价格过度偏离均线时反向开仓，"
            "在价格回归均值附近时平仓"
        )

    def _validate_parameters(self, params: dict) -> bool:
        """验证策略参数合法性。

        Args:
            params: 待验证的参数字典

        Returns:
            bool: 验证通过返回 True，否则返回 False
        """
        period = params.get("period", 20)
        std_multiplier = params.get("std_multiplier", 2.0)
        entry_threshold = params.get("entry_threshold", 2.0)
        exit_zone = params.get("exit_zone", 0.5)

        if not isinstance(period, (int, float)) or period <= 0:
            logger.warning("参数验证失败: period=%s，必须大于0", period)
            return False
        if not isinstance(std_multiplier, (int, float)) or std_multiplier <= 0:
            logger.warning("参数验证失败: std_multiplier=%s，必须大于0", std_multiplier)
            return False
        if not isinstance(entry_threshold, (int, float)):
            logger.warning("参数验证失败: entry_threshold=%s，必须为数值", entry_threshold)
            return False
        if not isinstance(exit_zone, (int, float)):
            logger.warning("参数验证失败: exit_zone=%s，必须为数值", exit_zone)
            return False
        if entry_threshold <= exit_zone:
            logger.warning(
                "参数验证失败: entry_threshold(%.2f) 必须大于 exit_zone(%.2f)",
                entry_threshold, exit_zone,
            )
            return False
        return True

    def _validate_and_raise(self, params: dict):
        """验证参数并在失败时抛出异常。

        Args:
            params: 待验证的参数字典

        Raises:
            ValueError: 参数验证失败时抛出
        """
        if not self._validate_parameters(params):
            raise ValueError(f"参数验证失败: {params}")
