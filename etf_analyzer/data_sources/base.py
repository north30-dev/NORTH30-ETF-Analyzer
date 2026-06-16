# -*- coding: utf-8 -*-
"""
数据源抽象基类模块

定义所有数据源必须实现的统一接口，包括实时行情、历史数据、
ETF列表、持仓信息和健康检查等核心方法。
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseDataSource(ABC):
    """数据源抽象基类，所有数据源必须实现此接口。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称标识，如 'akshare', 'tushare' 等。"""
        pass

    @property
    @abstractmethod
    def available(self) -> bool:
        """数据源是否可用（配置是否完整、依赖是否安装）。"""
        pass

    @abstractmethod
    def get_realtime_quote(self, symbol: str) -> dict:
        """获取ETF实时行情数据。

        Args:
            symbol: ETF代码，如 "510300"

        Returns:
            dict: 包含实时行情指标的字典，键包括：
                symbol, name, price, change_pct, change_amt,
                volume, amount, open, high, low, prev_close
                获取失败返回空字典 {}
        """
        pass

    @abstractmethod
    def get_history_data(self, symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取ETF历史行情数据。

        Args:
            symbol: ETF代码
            start_date: 起始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            adjust: 复权类型 "qfq"/"hfq"/""

        Returns:
            DataFrame: 历史行情数据，列包括：
                日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
                获取失败返回空 DataFrame
        """
        pass

    @abstractmethod
    def get_etf_list(self, keyword: str = None) -> pd.DataFrame:
        """获取ETF列表。

        Args:
            keyword: 可选过滤关键词

        Returns:
            DataFrame: ETF列表数据
        """
        pass

    @abstractmethod
    def get_etf_holdings(self, symbol: str) -> pd.DataFrame:
        """获取ETF持仓信息。

        Args:
            symbol: ETF代码

        Returns:
            DataFrame: 持仓信息数据
        """
        pass

    @abstractmethod
    def health_check(self) -> dict:
        """检查数据源健康状态。

        Returns:
            dict: 包含以下键：
                name: 数据源名称
                available: 是否可用
                response_time: 响应时间（秒），不可用时为 None
                error: 错误信息，正常时为 None
        """
        pass
