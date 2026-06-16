# -*- coding: utf-8 -*-
"""
Akshare 数据源适配模块

将 akshare 接口封装为 BaseDataSource 的实现，提供 ETF 实时行情、
历史数据、ETF列表和持仓信息的获取功能，内置重试与速率限制机制。
"""

import time
from datetime import datetime

import akshare as ak
import numpy as np
import pandas as pd

from etf_analyzer.config import DEFAULT_START_DATE
from etf_analyzer.data_sources.base import BaseDataSource
from etf_analyzer.logger import setup_logger
from etf_analyzer.retry import retry, rate_limiter


class AkshareDataSource(BaseDataSource):
    """基于 akshare 的数据源实现。

    通过 akshare 接口获取 ETF 相关数据，支持重试和速率限制，
    并提供交易日自动调整功能。

    Attributes:
        logger: 日志记录器实例。
        _trade_calendar: 缓存的A股交易日历 DataFrame。
    """

    def __init__(self):
        """初始化 AkshareDataSource 实例。"""
        self.logger = setup_logger("akshare_source")
        self._trade_calendar = None

    @property
    def name(self) -> str:
        """数据源名称标识。"""
        return "akshare"

    @property
    def available(self) -> bool:
        """akshare 无需认证，始终可用。"""
        return True

    def get_realtime_quote(self, symbol: str) -> dict:
        """获取指定ETF的实时行情数据。

        通过 akshare 的 fund_etf_spot_em 接口获取全部ETF实时行情，
        然后从中筛选出指定代码的数据。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            dict: 包含实时行情指标的字典，键包括：
                symbol, name, price, change_pct, change_amt,
                volume, amount, open, high, low, prev_close。
                获取失败返回空字典。
        """
        self.logger.info("开始获取ETF实时行情，代码: %s", symbol)
        try:
            @retry()
            def _fetch_spot():
                rate_limiter.acquire()
                return ak.fund_etf_spot_em()

            df = _fetch_spot()
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

    def get_history_data(self, symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取ETF历史行情数据。

        通过 akshare 的 fund_etf_hist_em 接口获取指定ETF的历史K线数据，
        自动调整起止日期至最近的交易日。

        Args:
            symbol: ETF代码，如 "510300"。
            start_date: 起始日期，格式 YYYYMMDD。
            end_date: 结束日期，格式 YYYYMMDD。
            adjust: 复权类型，"qfq" 前复权，"hfq" 后复权，"" 不复权。默认 "qfq"。

        Returns:
            DataFrame: 历史行情数据，列包括：
                日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率。
                获取失败返回空 DataFrame。
        """
        if start_date is None:
            start_date = DEFAULT_START_DATE
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # 交易日自动调整
        adjusted_start = self._adjust_trading_day(start_date, mode="next")
        adjusted_end = self._adjust_trading_day(end_date, mode="prev")

        self.logger.info(
            "开始获取ETF历史数据，代码: %s，起始: %s，结束: %s，复权: %s",
            symbol, adjusted_start, adjusted_end, adjust,
        )

        try:
            @retry()
            def _fetch_history():
                rate_limiter.acquire()
                return ak.fund_etf_hist_em(
                    symbol=symbol,
                    period="daily",
                    start_date=adjusted_start,
                    end_date=adjusted_end,
                    adjust=adjust,
                )

            df = _fetch_history()
            if df is None or df.empty:
                self.logger.warning("ak.fund_etf_hist_em() 返回空数据，代码: %s", symbol)
                return pd.DataFrame()

            self.logger.info(
                "成功获取ETF历史数据，代码: %s，共 %d 条记录", symbol, len(df),
            )
            return df

        except Exception as e:
            self.logger.error(
                "获取ETF历史数据失败，代码: %s，异常: %s", symbol, e,
            )
            return pd.DataFrame()

    def get_etf_list(self, keyword: str = None) -> pd.DataFrame:
        """获取ETF列表数据。

        通过 akshare 的 fund_etf_spot_em 接口获取全部ETF实时行情列表，
        可选按关键词对名称或代码进行过滤。

        Args:
            keyword: 过滤关键词，用于匹配ETF名称或代码。为 None 则返回全部。

        Returns:
            DataFrame: ETF列表数据，包含代码、名称、最新价、涨跌幅等列。
                获取失败返回空 DataFrame。
        """
        self.logger.info("开始获取ETF列表，关键词: %s", keyword)
        try:
            @retry()
            def _fetch_list():
                rate_limiter.acquire()
                return ak.fund_etf_spot_em()

            df = _fetch_list()
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

    def get_etf_holdings(self, symbol: str) -> pd.DataFrame:
        """获取ETF成分股/持仓信息。

        通过 akshare 的 fund_etf_hold_em 接口获取指定ETF的持仓数据，
        日期参数使用当前年份。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            DataFrame: 持仓信息数据，包含股票代码、股票名称、持仓占比等列。
                获取失败返回空 DataFrame。
        """
        current_year = str(datetime.now().year)
        self.logger.info("开始获取ETF持仓信息，代码: %s，日期: %s", symbol, current_year)

        try:
            @retry()
            def _fetch_holdings():
                rate_limiter.acquire()
                return ak.fund_etf_hold_em(symbol=symbol, date=current_year)

            df = _fetch_holdings()
            if df is None or df.empty:
                self.logger.warning(
                    "ak.fund_etf_hold_em() 返回空数据，代码: %s", symbol,
                )
                return pd.DataFrame()

            self.logger.info(
                "成功获取ETF持仓信息，代码: %s，共 %d 条记录", symbol, len(df),
            )
            return df

        except Exception as e:
            self.logger.error(
                "获取ETF持仓信息失败，代码: %s，异常: %s", symbol, e,
            )
            return pd.DataFrame()

    def health_check(self) -> dict:
        """检查数据源健康状态。

        通过调用 ak.fund_etf_spot_em() 发起简单请求来检测可用性，
        并记录响应时间。

        Returns:
            dict: 包含以下键：
                name: 数据源名称
                available: 是否可用
                response_time: 响应时间（秒），不可用时为 None
                error: 错误信息，正常时为 None
        """
        result = {
            "name": self.name,
            "available": False,
            "response_time": None,
            "error": None,
        }
        try:
            start_time = time.time()
            rate_limiter.acquire()
            df = ak.fund_etf_spot_em()
            elapsed = time.time() - start_time

            if df is not None and not df.empty:
                result["available"] = True
                result["response_time"] = round(elapsed, 3)
                self.logger.info(
                    "健康检查通过，响应时间: %.3f 秒", elapsed,
                )
            else:
                result["error"] = "数据源返回空数据"
                self.logger.warning("健康检查失败：数据源返回空数据")

        except Exception as e:
            result["error"] = str(e)
            self.logger.error("健康检查异常: %s", e)

        return result

    def _adjust_trading_day(self, date_str, mode="next"):
        """调整日期至最近的交易日。

        如果指定日期不是A股交易日，将其调整至最近的交易日。
        - mode="next"：向前调整到下一个交易日（用于开始日期）
        - mode="prev"：向后调整到上一个交易日（用于结束日期）

        Args:
            date_str: 日期字符串，格式 YYYYMMDD。
            mode: 调整模式，"next" 或 "prev"，默认为 "next"。

        Returns:
            str: 调整后的日期字符串，格式 YYYYMMDD。
        """
        try:
            # 首次调用时获取并缓存交易日历
            if self._trade_calendar is None:
                @retry()
                def _fetch_calendar():
                    rate_limiter.acquire()
                    return ak.tool_trade_date_hist_sina()

                self._trade_calendar = _fetch_calendar()
                self._trade_calendar["trade_date"] = pd.to_datetime(
                    self._trade_calendar["trade_date"],
                ).dt.date
                self._trade_calendar = self._trade_calendar.sort_values("trade_date")
                self.logger.info(
                    "成功加载A股交易日历，共 %d 个交易日",
                    len(self._trade_calendar),
                )

            target_date = pd.to_datetime(date_str).date()
            trade_dates = self._trade_calendar["trade_date"].values

            # 检查是否已是交易日（使用二分查找）
            idx = np.searchsorted(trade_dates, target_date)
            if idx < len(trade_dates) and trade_dates[idx] == target_date:
                return date_str

            if mode == "next":
                # 查找下一个交易日（>= target_date）
                mask = trade_dates >= target_date
            else:
                # 查找上一个交易日（<= target_date）
                mask = trade_dates <= target_date

            matched = trade_dates[mask]
            if len(matched) == 0:
                self.logger.warning(
                    "未找到日期 %s 的%s交易日，使用原日期", date_str,
                    "下一个" if mode == "next" else "上一个",
                )
                return date_str

            adjusted = matched[0] if mode == "next" else matched[-1]
            adjusted_str = adjusted.strftime("%Y%m%d")

            self.logger.info(
                "日期 %s 不是交易日，%s至 %s",
                date_str, "延顺" if mode == "next" else "回退", adjusted_str,
            )
            return adjusted_str

        except Exception as e:
            self.logger.warning("交易日调整失败，使用原日期 %s，异常: %s", date_str, e)
            return date_str
