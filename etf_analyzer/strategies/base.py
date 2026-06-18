# -*- coding: utf-8 -*-
"""
量化策略抽象基类模块

定义所有量化策略必须实现的统一接口，包括信号生成、参数管理和验证等核心方法。
所有具体策略必须继承 BaseStrategy 并实现其抽象方法。
"""

from abc import ABC, abstractmethod
import pandas as pd

from etf_analyzer.utils.logger import setup_logger

logger = setup_logger("strategies.base")


class BaseStrategy(ABC):
    """量化策略抽象基类，所有策略必须继承此类并实现抽象方法。

    子类必须实现以下抽象方法：
        - generate_signals: 生成交易信号
        - get_name: 返回策略名称
        - get_description: 返回策略描述

    信号输出格式标准化：
        generate_signals 返回的 DataFrame 必须包含三列：
            - date: 日期
            - signal: 信号值，1=买入，-1=卖出，0=持有
            - position: 建议仓位比例，0.0~1.0
    """

    def __init__(self, **params):
        """初始化策略，接受可变参数作为策略参数。

        Args:
            **params: 策略参数键值对
        """
        self._params = params

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """根据标准化OHLCV数据生成交易信号。

        Args:
            data: 标准化OHLCV数据，应包含以下列：
                - date: 日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量

        Returns:
            pd.DataFrame: 信号DataFrame，必须包含以下三列：
                - date: 日期
                - signal: 信号值，1=买入，-1=卖出，0=持有
                - position: 建议仓位比例，0.0~1.0
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """返回策略名称。

        Returns:
            str: 策略名称，如 "momentum"、"mean_reversion" 等
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """返回策略描述。

        Returns:
            str: 策略的简要描述
        """
        pass

    def get_parameters(self) -> dict:
        """返回当前策略参数字典。

        Returns:
            dict: 当前参数的深拷贝，避免外部修改内部状态
        """
        return dict(self._params)

    def set_parameters(self, params: dict):
        """更新策略参数，自动验证合法性。

        Args:
            params: 需要更新的参数字典，将与现有参数合并

        Raises:
            ValueError: 参数验证失败时抛出
        """
        if not isinstance(params, dict):
            raise ValueError(f"参数必须是字典类型，当前类型: {type(params).__name__}")

        merged = dict(self._params)
        merged.update(params)

        if not self._validate_parameters(merged):
            raise ValueError(f"参数验证失败: {params}")

        self._params = merged
        logger.info("策略 %s 参数已更新: %s", self.get_name(), params)

    def _validate_parameters(self, params: dict) -> bool:
        """参数验证方法，子类可覆盖以实现自定义验证逻辑。

        Args:
            params: 待验证的参数字典

        Returns:
            bool: 验证通过返回 True，否则返回 False
        """
        return True
