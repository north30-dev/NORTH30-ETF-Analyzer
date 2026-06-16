# -*- coding: utf-8 -*-
"""
Tushare 数据源适配模块

将 tushare 接口封装为 BaseDataSource 的实现，提供 ETF 实时行情、
历史数据、ETF列表和持仓信息的获取功能，内置重试与速率限制机制。
"""

import time
from datetime import datetime

import pandas as pd

from config import TUSHARE_TOKEN, DEFAULT_START_DATE
from etf_analyzer.data_sources.base import BaseDataSource
from etf_analyzer.utils.logger import setup_logger
from etf_analyzer.utils.retry import retry, rate_limiter

# 尝试导入 tushare，未安装时置为 None
try:
    import tushare as ts
except ImportError:
    ts = None


class TushareDataSource(BaseDataSource):
    """基于 tushare 的数据源实现。

    通过 tushare Pro 接口获取 ETF 相关数据，支持重试和速率限制。
    需要 TUSHARE_TOKEN 配置才能使用，Token 从 etf_analyzer.config 获取。

    Attributes:
        logger: 日志记录器实例。
        _pro: tushare Pro API 实例，Token 未配置时为 None。
    """

    def __init__(self):
        """初始化 TushareDataSource 实例。"""
        self.logger = setup_logger("tushare_source")
        self._pro = None
        self._init_pro_api()

    def _init_pro_api(self):
        """初始化 tushare Pro API 实例。

        仅在 tushare 已安装且 Token 已配置时初始化，
        否则记录警告日志。
        """
        if ts is None:
            self.logger.warning("tushare 未安装，TushareDataSource 不可用")
            return
        if not TUSHARE_TOKEN:
            self.logger.warning("TUSHARE_TOKEN 未配置，TushareDataSource 不可用")
            return
        try:
            self._pro = ts.pro_api(TUSHARE_TOKEN)
            self.logger.info("tushare Pro API 初始化成功")
        except Exception as e:
            self.logger.error("tushare Pro API 初始化失败: %s", e)
            self._pro = None

    @property
    def name(self) -> str:
        """数据源名称标识。"""
        return "tushare"

    @property
    def available(self) -> bool:
        """数据源是否可用（tushare 已安装且 Token 已配置）。"""
        return ts is not None and TUSHARE_TOKEN is not None and self._pro is not None

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """将纯数字 ETF 代码转换为 tushare 格式。

        tushare 使用 "代码.市场" 格式，如 "510300.SH"、"159919.SZ"。
        规则：6 开头的为上海（SH），其余为深圳（SZ）。

        Args:
            symbol: 纯数字 ETF 代码，如 "510300"。

        Returns:
            str: tushare 格式的代码，如 "510300.SH"。
        """
        symbol = symbol.strip()
        # 如果已经包含后缀，直接返回
        if "." in symbol:
            return symbol
        # 6 开头为上海，其余为深圳
        suffix = "SH" if symbol.startswith("6") else "SZ"
        return f"{symbol}.{suffix}"

    @staticmethod
    def _strip_symbol(ts_code: str) -> str:
        """将 tushare 格式代码转换为纯数字代码。

        Args:
            ts_code: tushare 格式代码，如 "510300.SH"。

        Returns:
            str: 纯数字代码，如 "510300"。
        """
        return ts_code.split(".")[0] if "." in ts_code else ts_code

    def get_realtime_quote(self, symbol: str) -> dict:
        """获取指定ETF的实时行情数据。

        通过 tushare 的 fund_daily 接口获取最近交易日的行情数据，
        同时通过 fund_basic 获取基金名称。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            dict: 包含实时行情指标的字典，键包括：
                symbol, name, price, change_pct, change_amt,
                volume, amount, open, high, low, prev_close。
                获取失败返回空字典。
        """
        if not self.available:
            self.logger.warning("TushareDataSource 不可用，跳过获取实时行情")
            return {}

        ts_code = self._convert_symbol(symbol)
        self.logger.info("开始获取ETF实时行情，代码: %s（tushare格式: %s）", symbol, ts_code)

        try:
            # 获取最近交易日数据
            @retry()
            def _fetch_daily():
                rate_limiter.acquire()
                return self._pro.fund_daily(
                    ts_code=ts_code,
                    start_date=datetime.now().strftime("%Y%m%d"),
                    end_date=datetime.now().strftime("%Y%m%d"),
                )

            df = _fetch_daily()

            # 如果当天没有数据，尝试获取最近几天的数据
            if df is None or df.empty:
                self.logger.info("当日无数据，尝试获取最近交易日数据: %s", ts_code)

                @retry()
                def _fetch_recent():
                    rate_limiter.acquire()
                    # 获取最近5个交易日的数据
                    from datetime import timedelta
                    start = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
                    end = datetime.now().strftime("%Y%m%d")
                    return self._pro.fund_daily(
                        ts_code=ts_code,
                        start_date=start,
                        end_date=end,
                    )

                df = _fetch_recent()

            if df is None or df.empty:
                self.logger.warning("未找到代码为 %s 的ETF行情数据", symbol)
                return {}

            # 取最新一行（tushare fund_daily 按日期降序排列）
            row = df.iloc[0]

            # 获取基金名称
            name = self._get_fund_name(ts_code)

            result = {
                "symbol": symbol,
                "name": name,
                "price": float(row.get("close", 0)),
                "change_pct": float(row.get("pct_chg", 0)),
                "change_amt": float(row.get("change", 0)),
                "volume": float(row.get("vol", 0)),
                "amount": float(row.get("amount", 0)),
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "prev_close": float(row.get("pre_close", 0)),
            }
            self.logger.info(
                "成功获取ETF %s(%s) 实时行情，最新价: %s",
                symbol, result["name"], result["price"],
            )
            return result

        except Exception as e:
            self.logger.error("获取ETF实时行情失败，代码: %s，异常: %s", symbol, e)
            return {}

    def _get_fund_name(self, ts_code: str) -> str:
        """获取基金名称。

        通过 tushare 的 fund_basic 接口查询基金基本信息，
        获取名称字段。

        Args:
            ts_code: tushare 格式的基金代码，如 "510300.SH"。

        Returns:
            str: 基金名称，获取失败返回空字符串。
        """
        try:
            @retry()
            def _fetch_basic():
                rate_limiter.acquire()
                return self._pro.fund_basic(ts_code=ts_code, fields="ts_code,name")

            df = _fetch_basic()
            if df is not None and not df.empty:
                return str(df.iloc[0].get("name", ""))
        except Exception as e:
            self.logger.warning("获取基金名称失败，代码: %s，异常: %s", ts_code, e)
        return ""

    def get_history_data(self, symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取ETF历史行情数据。

        通过 tushare 的 fund_daily 接口获取指定ETF的历史K线数据，
        并将列名标准化为统一格式。

        Args:
            symbol: ETF代码，如 "510300"。
            start_date: 起始日期，格式 YYYYMMDD。
            end_date: 结束日期，格式 YYYYMMDD。
            adjust: 复权类型，"qfq" 前复权，"hfq" 后复权，"" 不复权。默认 "qfq"。
                注意：tushare fund_daily 不直接支持复权参数，
                此处仅做接口兼容，实际返回未复权数据。

        Returns:
            DataFrame: 历史行情数据，列包括：
                日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率。
                获取失败返回空 DataFrame。
        """
        if not self.available:
            self.logger.warning("TushareDataSource 不可用，跳过获取历史数据")
            return pd.DataFrame()

        if start_date is None:
            start_date = DEFAULT_START_DATE
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        ts_code = self._convert_symbol(symbol)
        self.logger.info(
            "开始获取ETF历史数据，代码: %s（tushare格式: %s），起始: %s，结束: %s",
            symbol, ts_code, start_date, end_date,
        )

        try:
            @retry()
            def _fetch_history():
                rate_limiter.acquire()
                return self._pro.fund_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                )

            df = _fetch_history()
            if df is None or df.empty:
                self.logger.warning("tushare fund_daily() 返回空数据，代码: %s", symbol)
                return pd.DataFrame()

            # 列名标准化映射
            column_map = {
                "trade_date": "日期",
                "open": "开盘",
                "close": "收盘",
                "high": "最高",
                "low": "最低",
                "vol": "成交量",
                "amount": "成交额",
                "pct_chg": "涨跌幅",
                "change": "涨跌额",
            }
            df = df.rename(columns=column_map)

            # 计算振幅（tushare fund_daily 不直接提供振幅字段）
            if "振幅" not in df.columns and "最高" in df.columns and "最低" in df.columns:
                prev_close_col = "pre_close" if "pre_close" in df.columns else "昨收价"
                if prev_close_col in df.columns:
                    df["振幅"] = ((df["最高"] - df["最低"]) / df[prev_close_col] * 100).round(2)
                else:
                    df["振幅"] = 0.0

            # 添加换手率列（tushare fund_daily 不提供换手率）
            if "换手率" not in df.columns:
                df["换手率"] = 0.0

            # 确保日期列格式统一
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")

            # 按日期升序排列
            df = df.sort_values("日期").reset_index(drop=True)

            # 选择标准列
            standard_columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            available_columns = [col for col in standard_columns if col in df.columns]
            df = df[available_columns]

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

        通过 tushare 的 fund_basic 接口获取场内基金列表，
        可选按关键词对名称或代码进行过滤。

        Args:
            keyword: 过滤关键词，用于匹配ETF名称或代码。为 None 则返回全部。

        Returns:
            DataFrame: ETF列表数据，包含代码、名称等列。
                获取失败返回空 DataFrame。
        """
        if not self.available:
            self.logger.warning("TushareDataSource 不可用，跳过获取ETF列表")
            return pd.DataFrame()

        self.logger.info("开始获取ETF列表，关键词: %s", keyword)
        try:
            @retry()
            def _fetch_list():
                rate_limiter.acquire()
                return self._pro.fund_basic(market="E")

            df = _fetch_list()
            if df is None or df.empty:
                self.logger.warning("tushare fund_basic() 返回空数据")
                return pd.DataFrame()

            # 如果提供了关键词，按名称或代码过滤
            if keyword:
                mask = (
                    df["name"].str.contains(keyword, na=False)
                    | df["ts_code"].str.contains(keyword, na=False)
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

        通过 tushare 的 fund_portfolio 接口获取指定ETF的持仓数据。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            DataFrame: 持仓信息数据，包含股票代码、股票名称、持仓占比等列。
                获取失败返回空 DataFrame。
        """
        if not self.available:
            self.logger.warning("TushareDataSource 不可用，跳过获取持仓信息")
            return pd.DataFrame()

        ts_code = self._convert_symbol(symbol)
        self.logger.info("开始获取ETF持仓信息，代码: %s（tushare格式: %s）", symbol, ts_code)

        try:
            @retry()
            def _fetch_holdings():
                rate_limiter.acquire()
                return self._pro.fund_portfolio(ts_code=ts_code)

            df = _fetch_holdings()
            if df is None or df.empty:
                self.logger.warning(
                    "tushare fund_portfolio() 返回空数据，代码: %s", symbol,
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

        通过调用 tushare 的 fund_basic 接口发起简单请求来检测可用性，
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

        if not self.available:
            if ts is None:
                result["error"] = "tushare 未安装"
            elif not TUSHARE_TOKEN:
                result["error"] = "TUSHARE_TOKEN 未配置"
            else:
                result["error"] = "tushare Pro API 初始化失败"
            self.logger.warning("健康检查失败: %s", result["error"])
            return result

        try:
            start_time = time.time()
            rate_limiter.acquire()
            df = self._pro.fund_basic(market="E", limit=1)
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
