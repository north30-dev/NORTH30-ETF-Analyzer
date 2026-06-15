# -*- coding: utf-8 -*-
"""
ETF数据获取模块

本模块负责从数据源（akshare）获取ETF相关的行情数据、历史数据、
ETF列表和持仓信息，并提供本地缓存机制以减少重复请求。
"""

import os
import time
import pickle
from datetime import datetime

import akshare as ak
import pandas as pd

from etf_analyzer.config import CACHE_DIR_PATH, CACHE_EXPIRE_HOURS, DEFAULT_START_DATE, ensure_dirs
from etf_analyzer.logger import setup_logger


class ETFDataFetcher:
    """ETF数据获取器，提供实时行情、历史数据、ETF列表及持仓信息的获取功能。

    通过 akshare 接口获取数据，并支持基于文件的本地缓存机制，
    缓存过期时间由 config.CACHE_EXPIRE_HOURS 控制。

    Attributes:
        logger: 日志记录器实例。
        cache_dir: 缓存文件存放目录的绝对路径。
    """

    def __init__(self):
        """初始化ETFDataFetcher实例。

        设置日志记录器和缓存目录，并确保缓存目录存在。
        """
        self.logger = setup_logger("data_fetcher")
        self.cache_dir = CACHE_DIR_PATH
        ensure_dirs()
        self.logger.info("ETFDataFetcher 初始化完成，缓存目录: %s", self.cache_dir)

    def get_realtime_quote(self, symbol):
        """获取指定ETF的实时行情数据。

        通过 akshare 的 fund_etf_spot_em 接口获取全部ETF实时行情，
        然后从中筛选出指定代码的数据。

        Args:
            symbol (str): ETF代码，如 "510300"。

        Returns:
            dict: 包含实时行情指标的字典，键包括：
                - symbol: ETF代码
                - name: ETF名称
                - price: 最新价格
                - change_pct: 涨跌幅（%）
                - change_amt: 涨跌额
                - volume: 成交量（手）
                - amount: 成交额（元）
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - prev_close: 昨收价
                如果获取失败则返回空字典。

        Example:
            >>> fetcher = ETFDataFetcher()
            >>> quote = fetcher.get_realtime_quote("510300")
            >>> print(quote["name"], quote["price"])
        """
        self.logger.info("开始获取ETF实时行情，代码: %s", symbol)
        try:
            df = ak.fund_etf_spot_em()
            if df is None or df.empty:
                self.logger.warning("ak.fund_etf_spot_em() 返回空数据")
                return {}

            # 筛选指定代码的行
            row = df[df["代码"] == symbol]
            if row.empty:
                self.logger.warning("未找到代码为 %s 的ETF数据", symbol)
                return {}

            row = row.iloc[0]
            result = {
                "symbol": symbol,
                "name": str(row.get("名称", "")),
                "price": float(row.get("最新价", 0)),
                "change_pct": float(row.get("涨跌幅", 0)),
                "change_amt": float(row.get("涨跌额", 0)),
                "volume": float(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
                "open": float(row.get("开盘价", 0)),
                "high": float(row.get("最高价", 0)),
                "low": float(row.get("最低价", 0)),
                "prev_close": float(row.get("昨收", 0)),
            }
            self.logger.info(
                "成功获取ETF %s(%s) 实时行情，最新价: %s",
                symbol, result["name"], result["price"],
            )
            return result

        except Exception as e:
            self.logger.error("获取ETF实时行情失败，代码: %s，异常: %s", symbol, e)
            return {}

    def get_history_data(self, symbol, start_date=None, end_date=None, adjust="qfq"):
        """获取ETF历史行情数据。

        通过 akshare 的 fund_etf_hist_em 接口获取指定ETF的历史K线数据，
        并支持本地缓存机制以避免重复请求。

        Args:
            symbol (str): ETF代码，如 "510300"。
            start_date (str, optional): 起始日期，格式为 YYYYMMDD。
                默认使用 config.DEFAULT_START_DATE。
            end_date (str, optional): 结束日期，格式为 YYYYMMDD。
                默认使用当天日期。
            adjust (str, optional): 复权类型，"qfq" 为前复权，
                "hfq" 为后复权，"" 为不复权。默认为 "qfq"。

        Returns:
            pandas.DataFrame: 包含历史行情数据的 DataFrame，列包括：
                日期、开盘、收盘、最高、最低、成交量、成交额、振幅、
                涨跌幅、涨跌额、换手率。
                如果获取失败则返回空 DataFrame。

        Example:
            >>> fetcher = ETFDataFetcher()
            >>> df = fetcher.get_history_data("510300", start_date="20240101")
            >>> print(df.head())
        """
        if start_date is None:
            start_date = DEFAULT_START_DATE
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        self.logger.info(
            "开始获取ETF历史数据，代码: %s，起始: %s，结束: %s，复权: %s",
            symbol, start_date, end_date, adjust,
        )

        # 尝试从缓存加载
        cache_key = self._get_cache_key(
            symbol, "history", start_date=start_date, end_date=end_date, adjust=adjust,
        )
        cached = self._load_cache(cache_key)
        if cached is not None:
            self.logger.info("从缓存加载ETF历史数据，代码: %s", symbol)
            return cached

        try:
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
            if df is None or df.empty:
                self.logger.warning("ak.fund_etf_hist_em() 返回空数据，代码: %s", symbol)
                return pd.DataFrame()

            self.logger.info(
                "成功获取ETF历史数据，代码: %s，共 %d 条记录", symbol, len(df),
            )
            # 保存到缓存
            self._save_cache(cache_key, df)
            return df

        except Exception as e:
            self.logger.error(
                "获取ETF历史数据失败，代码: %s，异常: %s", symbol, e,
            )
            return pd.DataFrame()

    def get_etf_list(self, keyword=None):
        """获取ETF列表数据。

        通过 akshare 的 fund_etf_spot_em 接口获取全部ETF实时行情列表，
        可选按关键词对名称或代码进行过滤。

        Args:
            keyword (str, optional): 过滤关键词，用于匹配ETF名称或代码。
                如果为 None 则返回全部ETF。默认为 None。

        Returns:
            pandas.DataFrame: ETF列表数据，包含代码、名称、最新价、涨跌幅等列。
                如果获取失败则返回空 DataFrame。

        Example:
            >>> fetcher = ETFDataFetcher()
            >>> df = fetcher.get_etf_list(keyword="沪深300")
            >>> print(df.head())
        """
        self.logger.info("开始获取ETF列表，关键词: %s", keyword)
        try:
            df = ak.fund_etf_spot_em()
            if df is None or df.empty:
                self.logger.warning("ak.fund_etf_spot_em() 返回空数据")
                return pd.DataFrame()

            # 如果提供了关键词，按名称或代码过滤
            if keyword:
                mask = df["名称"].str.contains(keyword, na=False) | df["代码"].str.contains(
                    keyword, na=False,
                )
                df = df[mask]
                self.logger.info("按关键词 '%s' 过滤后，剩余 %d 条记录", keyword, len(df))

            self.logger.info("成功获取ETF列表，共 %d 条记录", len(df))
            return df

        except Exception as e:
            self.logger.error("获取ETF列表失败，异常: %s", e)
            return pd.DataFrame()

    def get_etf_holdings(self, symbol):
        """获取ETF成分股/持仓信息。

        通过 akshare 的 fund_etf_hold_em 接口获取指定ETF的持仓数据，
        日期参数使用当前年份。

        Args:
            symbol (str): ETF代码，如 "510300"。

        Returns:
            pandas.DataFrame: 持仓信息数据，包含股票代码、股票名称、持仓占比等列。
                如果获取失败则返回空 DataFrame。

        Example:
            >>> fetcher = ETFDataFetcher()
            >>> df = fetcher.get_etf_holdings("510300")
            >>> print(df.head())
        """
        current_year = str(datetime.now().year)
        self.logger.info("开始获取ETF持仓信息，代码: %s，日期: %s", symbol, current_year)

        # 尝试从缓存加载
        cache_key = self._get_cache_key(symbol, "holdings", date=current_year)
        cached = self._load_cache(cache_key)
        if cached is not None:
            self.logger.info("从缓存加载ETF持仓信息，代码: %s", symbol)
            return cached

        try:
            df = ak.fund_etf_hold_em(symbol=symbol, date=current_year)
            if df is None or df.empty:
                self.logger.warning(
                    "ak.fund_etf_hold_em() 返回空数据，代码: %s", symbol,
                )
                return pd.DataFrame()

            self.logger.info(
                "成功获取ETF持仓信息，代码: %s，共 %d 条记录", symbol, len(df),
            )
            # 保存到缓存
            self._save_cache(cache_key, df)
            return df

        except Exception as e:
            self.logger.error(
                "获取ETF持仓信息失败，代码: %s，异常: %s", symbol, e,
            )
            return pd.DataFrame()

    def _get_cache_key(self, symbol, data_type, **kwargs):
        """生成缓存键（缓存文件路径）。

        根据ETF代码、数据类型和额外参数生成唯一的缓存文件路径，
        确保不同参数组合对应不同的缓存文件。

        Args:
            symbol (str): ETF代码。
            data_type (str): 数据类型，如 "history"、"holdings"。
            **kwargs: 额外参数，将拼接到缓存文件名中以区分不同请求。

        Returns:
            str: 缓存文件的绝对路径字符串。

        Example:
            >>> fetcher = ETFDataFetcher()
            >>> key = fetcher._get_cache_key("510300", "history", start_date="20240101")
            >>> print(key)
        """
        # 构建文件名：symbol_type_key1_value1_key2_value2.pkl
        parts = [symbol, data_type]
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}_{v}")
        filename = "_".join(parts) + ".pkl"
        return os.path.join(self.cache_dir, filename)

    def _load_cache(self, cache_key):
        """加载缓存数据。

        检查缓存文件是否存在且未过期，如果有效则加载并返回数据。
        缓存过期时间由 config.CACHE_EXPIRE_HOURS 控制。

        Args:
            cache_key (str): 缓存文件路径，由 _get_cache_key 方法生成。

        Returns:
            pandas.DataFrame or None: 如果缓存有效则返回 DataFrame，
                如果缓存不存在或已过期则返回 None。

        Note:
            缓存文件的修改时间用于判断是否过期，如果文件修改时间
            距当前时间超过 CACHE_EXPIRE_HOURS 小时，则视为过期。
        """
        if not os.path.exists(cache_key):
            return None

        try:
            # 检查缓存是否过期
            file_mtime = os.path.getmtime(cache_key)
            expire_seconds = CACHE_EXPIRE_HOURS * 3600
            if time.time() - file_mtime > expire_seconds:
                self.logger.info("缓存已过期，文件: %s", cache_key)
                return None

            with open(cache_key, "rb") as f:
                data = pickle.load(f)

            self.logger.info("成功加载缓存，文件: %s", cache_key)
            return data

        except Exception as e:
            self.logger.warning("加载缓存失败，文件: %s，异常: %s", cache_key, e)
            return None

    def _save_cache(self, cache_key, data):
        """保存数据到缓存。

        将 DataFrame 以 pickle 格式保存到缓存目录，
        保存前确保缓存目录存在。

        Args:
            cache_key (str): 缓存文件路径，由 _get_cache_key 方法生成。
            data (pandas.DataFrame): 需要缓存的数据。

        Note:
            使用 pickle 格式存储，加载速度快，适合存储 DataFrame 对象。
        """
        try:
            # 确保缓存目录存在
            os.makedirs(os.path.dirname(cache_key), exist_ok=True)

            with open(cache_key, "wb") as f:
                pickle.dump(data, f)

            self.logger.info("成功保存缓存，文件: %s", cache_key)

        except Exception as e:
            self.logger.warning("保存缓存失败，文件: %s，异常: %s", cache_key, e)
