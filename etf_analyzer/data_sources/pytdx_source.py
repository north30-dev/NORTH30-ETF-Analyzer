# -*- coding: utf-8 -*-
"""
Pytdx 数据源适配模块

将通达信(pytdx)接口封装为 BaseDataSource 的实现，提供 ETF 实时行情、
历史K线数据的获取功能。pytdx 不支持 ETF 列表和持仓查询，相关方法返回空数据。
"""

import time
from datetime import datetime

import pandas as pd

from etf_analyzer.config import PYTDX_HOST, PYTDX_PORT
from etf_analyzer.data_sources.base import BaseDataSource
from etf_analyzer.logger import setup_logger

# pytdx 列名到标准列名的映射
_COLUMN_MAP = {
    "open": "开盘",
    "close": "收盘",
    "high": "最高",
    "low": "最低",
    "vol": "成交量",
    "amount": "成交额",
    "swing": "振幅",
    "change_percent": "涨跌幅",
    "change": "涨跌额",
    "turnover": "换手率",
}


def _get_market(symbol: str) -> int:
    """根据ETF代码判断所属市场。

    代码以 5/6 开头为上海（市场1），以 0/1/3 开头为深圳（市场0）。

    Args:
        symbol: ETF代码，如 "510300"。

    Returns:
        int: 市场代码，1=上海，0=深圳。
    """
    first_char = symbol[0]
    if first_char in ("5", "6"):
        return 1
    return 0


class PytdxDataSource(BaseDataSource):
    """基于通达信(pytdx)的数据源实现。

    通过 pytdx 的 TdxHq_API 连接通达信行情服务器，获取 ETF 实时行情
    和历史K线数据。pytdx 无 ETF 列表和持仓接口，相关方法返回空数据。

    Attributes:
        logger: 日志记录器实例。
        _host: 通达信服务器地址。
        _port: 通达信服务器端口。
        _pytdx_available: pytdx 库是否已安装。
    """

    def __init__(self):
        """初始化 PytdxDataSource 实例。"""
        self.logger = setup_logger("pytdx_source")
        self._host = PYTDX_HOST
        self._port = PYTDX_PORT
        self._pytdx_available = False
        try:
            from pytdx.hq import TdxHq_API  # noqa: F401
            self._pytdx_available = True
        except ImportError:
            self.logger.warning("pytdx 库未安装，PytdxDataSource 将不可用")

    @property
    def name(self) -> str:
        """数据源名称标识。"""
        return "pytdx"

    @property
    def available(self) -> bool:
        """pytdx 已安装则返回 True。"""
        return self._pytdx_available

    def _connect(self):
        """创建并连接通达信行情API实例。

        Returns:
            TdxHq_API: 已连接的API实例，连接失败返回 None。
        """
        if not self._pytdx_available:
            self.logger.warning("pytdx 库不可用，无法连接")
            return None

        from pytdx.hq import TdxHq_API

        api = TdxHq_API()
        try:
            if api.connect(self._host, self._port):
                self.logger.debug("成功连接通达信服务器 %s:%d", self._host, self._port)
                return api
            else:
                self.logger.warning("连接通达信服务器 %s:%d 失败", self._host, self._port)
                return None
        except Exception as e:
            self.logger.error("连接通达信服务器异常: %s", e)
            return None

    def get_realtime_quote(self, symbol: str) -> dict:
        """获取指定ETF的实时行情数据。

        通过 pytdx 的 get_security_quotes 接口获取实时行情。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            dict: 包含实时行情指标的字典，键包括：
                symbol, name, price, change_pct, change_amt,
                volume, amount, open, high, low, prev_close。
                获取失败返回空字典。
        """
        self.logger.info("开始获取ETF实时行情，代码: %s", symbol)

        api = self._connect()
        if api is None:
            return {}

        try:
            market = _get_market(symbol)
            quotes = api.get_security_quotes([(market, symbol)])

            if quotes is None or len(quotes) == 0:
                self.logger.warning("pytdx 返回空行情数据，代码: %s", symbol)
                return {}

            quote = quotes[0]
            result = {
                "symbol": symbol,
                "name": str(quote.get("name", "")),
                "price": float(quote.get("price", 0)),
                "change_pct": float(quote.get("price", 0)) - float(quote.get("last_close", 0))
                    if quote.get("last_close", 0) != 0 else 0,
                "change_amt": float(quote.get("price", 0)) - float(quote.get("last_close", 0)),
                "volume": float(quote.get("vol", 0)),
                "amount": float(quote.get("amount", 0)),
                "open": float(quote.get("open", 0)),
                "high": float(quote.get("high", 0)),
                "low": float(quote.get("low", 0)),
                "prev_close": float(quote.get("last_close", 0)),
            }
            # 修正涨跌幅为百分比
            prev_close = result["prev_close"]
            if prev_close != 0:
                result["change_pct"] = round(
                    (result["price"] - prev_close) / prev_close * 100, 3
                )
                result["change_amt"] = round(result["price"] - prev_close, 3)
            else:
                result["change_pct"] = 0.0
                result["change_amt"] = 0.0

            self.logger.info(
                "成功获取ETF %s(%s) 实时行情，最新价: %s",
                symbol, result["name"], result["price"],
            )
            return result

        except Exception as e:
            self.logger.error("获取ETF实时行情失败，代码: %s，异常: %s", symbol, e)
            return {}
        finally:
            api.disconnect()

    def get_history_data(self, symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取ETF历史行情数据。

        通过 pytdx 的 get_security_bars 接口获取日K线数据。
        pytdx 的 get_security_bars 是分页获取的，start=0 为最新数据，
        需要倒序拼接来获取指定时间范围的数据。

        注意：pytdx 不支持复权，adjust 参数将被忽略。

        Args:
            symbol: ETF代码，如 "510300"。
            start_date: 起始日期，格式 YYYYMMDD。
            end_date: 结束日期，格式 YYYYMMDD。
            adjust: 复权类型（pytdx 不支持，忽略此参数）。

        Returns:
            DataFrame: 历史行情数据，列包括：
                日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率。
                获取失败返回空 DataFrame。
        """
        self.logger.info(
            "开始获取ETF历史数据，代码: %s，起始: %s，结束: %s",
            symbol, start_date, end_date,
        )

        api = self._connect()
        if api is None:
            return pd.DataFrame()

        try:
            market = _get_market(symbol)
            # pytdx 每次最多获取 800 条数据
            page_size = 800
            all_data = []
            start = 0

            # 将日期字符串转为 datetime 用于过滤
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")

            while True:
                bars = api.get_security_bars(9, market, symbol, start, page_size)
                if bars is None or len(bars) == 0:
                    break

                df_page = api.to_df(bars)
                all_data.append(df_page)

                # 检查最早数据是否已早于起始日期
                if "datetime" in df_page.columns:
                    first_date_str = df_page["datetime"].iloc[0]
                    try:
                        first_dt = datetime.strptime(first_date_str, "%Y-%m-%d")
                    except (ValueError, TypeError):
                        try:
                            first_dt = datetime.strptime(str(first_date_str)[:10], "%Y-%m-%d")
                        except (ValueError, TypeError):
                            first_dt = start_dt

                    if first_dt <= start_dt:
                        break

                # 如果返回数据不足一页，说明已到最早数据
                if len(df_page) < page_size:
                    break

                start += page_size

            if not all_data:
                self.logger.warning("pytdx 返回空历史数据，代码: %s", symbol)
                return pd.DataFrame()

            # 拼接所有分页数据
            df = pd.concat(all_data, ignore_index=True)

            # 去重（分页边界可能重叠）
            if "datetime" in df.columns:
                df = df.drop_duplicates(subset=["datetime"], keep="first")

            # 标准化日期列名
            if "datetime" in df.columns:
                df = df.rename(columns={"datetime": "日期"})

            # 日期格式统一为字符串 YYYY-MM-DD
            if "日期" in df.columns:
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")

            # 按列名映射重命名
            df = df.rename(columns=_COLUMN_MAP)

            # 按日期范围过滤
            if "日期" in df.columns:
                df["_dt"] = pd.to_datetime(df["日期"])
                df = df[(df["_dt"] >= start_dt) & (df["_dt"] <= end_dt)]
                df = df.drop(columns=["_dt"])

            # 按日期升序排列
            if "日期" in df.columns:
                df = df.sort_values("日期").reset_index(drop=True)

            # 确保输出列顺序与基类定义一致
            standard_columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"]
            existing_cols = [col for col in standard_columns if col in df.columns]
            df = df[existing_cols]

            self.logger.info(
                "成功获取ETF历史数据，代码: %s，共 %d 条记录", symbol, len(df),
            )
            return df

        except Exception as e:
            self.logger.error("获取ETF历史数据失败，代码: %s，异常: %s", symbol, e)
            return pd.DataFrame()
        finally:
            api.disconnect()

    def get_etf_list(self, keyword: str = None) -> pd.DataFrame:
        """获取ETF列表。

        pytdx 无直接 ETF 列表接口，返回空 DataFrame。

        Args:
            keyword: 过滤关键词（未使用）。

        Returns:
            DataFrame: 空 DataFrame。
        """
        self.logger.info("pytdx 不支持 ETF 列表查询，返回空数据")
        return pd.DataFrame()

    def get_etf_holdings(self, symbol: str) -> pd.DataFrame:
        """获取ETF持仓信息。

        pytdx 无持仓接口，返回空 DataFrame。

        Args:
            symbol: ETF代码（未使用）。

        Returns:
            DataFrame: 空 DataFrame。
        """
        self.logger.info("pytdx 不支持 ETF 持仓查询，返回空数据")
        return pd.DataFrame()

    def health_check(self) -> dict:
        """检查数据源健康状态。

        通过连接通达信服务器检测可用性，并记录响应时间。

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

        if not self._pytdx_available:
            result["error"] = "pytdx 库未安装"
            return result

        api = None
        try:
            start_time = time.time()
            api = self._connect()
            elapsed = time.time() - start_time

            if api is not None:
                result["available"] = True
                result["response_time"] = round(elapsed, 3)
                self.logger.info("健康检查通过，响应时间: %.3f 秒", elapsed)
            else:
                result["error"] = "连接通达信服务器失败"
                self.logger.warning("健康检查失败：连接通达信服务器失败")

        except Exception as e:
            result["error"] = str(e)
            self.logger.error("健康检查异常: %s", e)
        finally:
            if api is not None:
                api.disconnect()

        return result
