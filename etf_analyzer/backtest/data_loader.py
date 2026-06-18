# -*- coding: utf-8 -*-
"""
回测数据加载模块

提供从多种数据源（API、CSV文件、数据库）加载ETF历史数据的功能，
并将数据标准化为统一的回测格式。
"""

import os

import pandas as pd
from sqlalchemy import select

from db.database import get_session_factory
from db.models import HistoryDataCache
from etf_analyzer.core.data_fetcher import ETFDataFetcher
from etf_analyzer.utils.logger import setup_logger


# CSV列名自动映射表：原始列名 → 标准列名
_DEFAULT_COLUMN_MAPPING = {
    # 日期
    "日期": "date",
    "date": "date",
    "Date": "date",
    "交易日期": "date",
    # 开盘价
    "开盘": "open",
    "open": "open",
    "Open": "open",
    "开盘价": "open",
    # 最高价
    "最高": "high",
    "high": "high",
    "High": "high",
    "最高价": "high",
    # 最低价
    "最低": "low",
    "low": "low",
    "Low": "low",
    "最低价": "low",
    # 收盘价
    "收盘": "close",
    "close": "close",
    "Close": "close",
    "收盘价": "close",
    # 成交量
    "成交量": "volume",
    "volume": "volume",
    "Volume": "volume",
    "Vol": "volume",
}

# API返回的DataFrame列名映射到标准格式
_API_COLUMN_MAPPING = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
}

# 数据库模型字段映射到标准格式
_DB_COLUMN_MAPPING = {
    "trade_date": "date",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "volume": "volume",
}

# 标准输出列名
_STANDARD_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


class BacktestDataLoader:
    """回测数据加载器，支持多种数据源。

    提供从API、CSV文件和MySQL数据库加载ETF历史数据的统一接口，
    所有数据源返回的DataFrame均标准化为统一格式：
    列名为 date, open, high, low, close, volume，
    date 列为 datetime 类型，数值列为 float 类型，
    按日期升序排列，去除缺失值行。

    Attributes:
        logger: 日志记录器实例。
    """

    def __init__(self):
        """初始化 BacktestDataLoader 实例。"""
        self.logger = setup_logger("backtest_data_loader")

    def load_from_api(self, symbol: str, start_date: str = None,
                      end_date: str = None) -> pd.DataFrame:
        """通过现有数据源管理器获取ETF历史数据，转换为标准格式。

        复用 ETFDataFetcher 的 get_history_data 方法获取数据，
        然后将返回的DataFrame转换为回测标准格式。

        Args:
            symbol: ETF代码，如 "510300"。
            start_date: 起始日期，格式为 YYYYMMDD，默认使用配置中的默认值。
            end_date: 结束日期，格式为 YYYYMMDD，默认为当天日期。

        Returns:
            标准化后的 DataFrame，列名为 date, open, high, low, close, volume。
            获取失败时返回空 DataFrame。
        """
        self.logger.info("从API加载数据，代码: %s，起始: %s，结束: %s",
                         symbol, start_date, end_date)

        try:
            fetcher = ETFDataFetcher()
            df = fetcher.get_history_data(
                symbol=symbol, start_date=start_date, end_date=end_date,
            )
        except Exception as e:
            self.logger.error("从API获取数据失败，代码: %s，异常: %s", symbol, e)
            return pd.DataFrame()

        if df is None or df.empty:
            self.logger.warning("从API获取数据为空，代码: %s", symbol)
            return pd.DataFrame()

        # 将API返回的列名映射到标准格式
        return self._standardize_data(df, column_mapping=_API_COLUMN_MAPPING)

    def load_from_csv(self, file_path: str,
                      column_mapping: dict = None) -> pd.DataFrame:
        """从CSV文件加载数据，自动识别列名映射。

        读取CSV文件后，使用提供的映射或默认映射将列名转换为标准格式。
        支持自动识别常见的中英文列名。

        Args:
            file_path: CSV文件的绝对路径或相对路径。
            column_mapping: 自定义列名映射字典，键为原始列名，值为标准列名。
                为 None 时使用默认映射表自动识别。

        Returns:
            标准化后的 DataFrame，列名为 date, open, high, low, close, volume。
            文件不存在或加载失败时返回空 DataFrame。
        """
        self.logger.info("从CSV加载数据，文件: %s", file_path)

        if not os.path.exists(file_path):
            self.logger.error("CSV文件不存在: %s", file_path)
            return pd.DataFrame()

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            self.logger.error("读取CSV文件失败: %s，异常: %s", file_path, e)
            return pd.DataFrame()

        if df.empty:
            self.logger.warning("CSV文件为空: %s", file_path)
            return pd.DataFrame()

        self.logger.info("CSV文件加载成功，共 %d 行，列: %s", len(df), list(df.columns))
        return self._standardize_data(df, column_mapping=column_mapping)

    def load_from_database(self, symbol: str, start_date: str = None,
                           end_date: str = None) -> pd.DataFrame:
        """从MySQL数据库读取历史数据缓存。

        使用 SQLAlchemy 从 HistoryDataCache 模型读取数据，
        支持按ETF代码和日期范围过滤。

        Args:
            symbol: ETF代码，如 "510300"。
            start_date: 起始日期，格式为 YYYY-MM-DD 或 YYYYMMDD，默认不过滤。
            end_date: 结束日期，格式为 YYYY-MM-DD 或 YYYYMMDD，默认不过滤。

        Returns:
            标准化后的 DataFrame，列名为 date, open, high, low, close, volume。
            数据库不可用或查询失败时返回空 DataFrame。
        """
        self.logger.info("从数据库加载数据，代码: %s，起始: %s，结束: %s",
                         symbol, start_date, end_date)

        try:
            SessionLocal = get_session_factory()
            session = SessionLocal()

            try:
                # 构建查询条件
                stmt = select(HistoryDataCache).where(
                    HistoryDataCache.symbol == symbol,
                )

                # 日期范围过滤
                if start_date is not None:
                    start_str = self._normalize_date_str(start_date)
                    stmt = stmt.where(HistoryDataCache.trade_date >= start_str)
                if end_date is not None:
                    end_str = self._normalize_date_str(end_date)
                    stmt = stmt.where(HistoryDataCache.trade_date <= end_str)

                # 按交易日期排序
                stmt = stmt.order_by(HistoryDataCache.trade_date)

                results = session.execute(stmt).scalars().all()

                if not results:
                    self.logger.warning(
                        "数据库中无数据，代码: %s，起始: %s，结束: %s",
                        symbol, start_date, end_date,
                    )
                    return pd.DataFrame()

                # 将ORM对象转换为DataFrame
                rows = []
                for row in results:
                    rows.append({
                        "trade_date": row.trade_date,
                        "open": row.open,
                        "close": row.close,
                        "high": row.high,
                        "low": row.low,
                        "volume": row.volume,
                    })

                df = pd.DataFrame(rows)
                self.logger.info(
                    "从数据库加载成功，代码: %s，共 %d 条记录", symbol, len(df),
                )
                return self._standardize_data(df, column_mapping=_DB_COLUMN_MAPPING)

            finally:
                session.close()

        except Exception as e:
            self.logger.warning("从数据库加载数据失败，代码: %s，异常: %s", symbol, e)
            return pd.DataFrame()

    def _standardize_data(self, df: pd.DataFrame,
                          column_mapping: dict = None) -> pd.DataFrame:
        """将数据标准化为统一格式。

        根据列名映射重命名列，确保标准列存在且类型正确，
        按日期升序排列并去除缺失值行。

        标准化规则：
        - 列名统一为：date, open, high, low, close, volume
        - date 列为 datetime 类型
        - 数值列为 float 类型
        - 按日期升序排列
        - 去除缺失值行

        Args:
            df: 原始数据 DataFrame。
            column_mapping: 列名映射字典，键为原始列名，值为标准列名。
                为 None 时使用默认映射表自动识别。

        Returns:
            标准化后的 DataFrame。如果缺少必要列则返回空 DataFrame。
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 合并映射表：自定义映射优先于默认映射
        mapping = dict(_DEFAULT_COLUMN_MAPPING)
        if column_mapping is not None:
            mapping.update(column_mapping)

        # 重命名列：仅重命名当前DataFrame中存在的列
        rename_map = {}
        for col in df.columns:
            if col in mapping:
                rename_map[col] = mapping[col]

        df = df.rename(columns=rename_map)

        # 检查必要列是否存在
        missing_cols = [col for col in _STANDARD_COLUMNS if col not in df.columns]
        if missing_cols:
            self.logger.error("数据缺少必要列: %s，现有列: %s",
                              missing_cols, list(df.columns))
            return pd.DataFrame()

        # 仅保留标准列
        df = df[_STANDARD_COLUMNS].copy()

        # 转换 date 列为 datetime 类型
        try:
            df["date"] = pd.to_datetime(df["date"])
        except Exception as e:
            self.logger.error("日期列转换失败: %s", e)
            return pd.DataFrame()

        # 转换数值列为 float 类型
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 去除缺失值行
        original_len = len(df)
        df = df.dropna()
        if len(df) < original_len:
            self.logger.info("去除缺失值行，原始: %d 行，保留: %d 行",
                             original_len, len(df))

        # 按日期升序排列
        df = df.sort_values("date").reset_index(drop=True)

        return df

    @staticmethod
    def _normalize_date_str(date_str: str) -> str:
        """将日期字符串标准化为 YYYY-MM-DD 格式。

        支持输入格式：YYYYMMDD、YYYY-MM-DD。

        Args:
            date_str: 日期字符串。

        Returns:
            标准化后的日期字符串，格式为 YYYY-MM-DD。
        """
        # 去除可能的前后空格
        date_str = date_str.strip()
        # 如果是 YYYYMMDD 格式，转换为 YYYY-MM-DD
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str
