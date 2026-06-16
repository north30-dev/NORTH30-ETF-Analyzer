# -*- coding: utf-8 -*-
"""
Baostock 数据源适配模块

将 baostock 接口封装为 BaseDataSource 的实现，提供 ETF 历史K线数据获取功能。
Baostock 不支持实时行情、ETF列表和持仓查询，相关方法返回空数据。
"""

import time

import pandas as pd

from etf_analyzer.data_sources.base import BaseDataSource
from etf_analyzer.utils.logger import setup_logger


class BaostockDataSource(BaseDataSource):
    """基于 baostock 的数据源实现。

    通过 baostock 接口获取 ETF 历史K线数据，不支持实时行情、
    ETF列表和持仓查询。每次查询前需 login，查询后 logout。

    Attributes:
        logger: 日志记录器实例。
    """

    def __init__(self):
        """初始化 BaostockDataSource 实例，检查 baostock 是否已安装。"""
        self.logger = setup_logger("baostock_source")
        self._bs = None
        try:
            import baostock as bs
            self._bs = bs
        except ImportError:
            self.logger.warning("baostock 库未安装，BaostockDataSource 将不可用")

    @property
    def name(self) -> str:
        """数据源名称标识。"""
        return "baostock"

    @property
    def available(self) -> bool:
        """baostock 已安装则返回 True。"""
        return self._bs is not None

    def _convert_symbol(self, symbol: str) -> str:
        """将ETF代码转换为 baostock 格式。

        6开头的代码使用 sh 前缀，其他使用 sz 前缀。
        例如 "510300" -> "sh.510300"，"159919" -> "sz.159919"。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            str: baostock 格式的代码，如 "sh.510300"。
        """
        if symbol.startswith("6"):
            return f"sh.{symbol}"
        return f"sz.{symbol}"

    def _convert_adjust_flag(self, adjust: str) -> str:
        """将复权类型转换为 baostock 的 adjustflag 参数。

        Args:
            adjust: 复权类型，"qfq" 前复权，"hfq" 后复权，"" 不复权。

        Returns:
            str: baostock 的 adjustflag 值，"2" 前复权，"1" 后复权，"3" 不复权。
        """
        mapping = {"qfq": "2", "hfq": "1", "": "3"}
        return mapping.get(adjust, "2")

    def get_realtime_quote(self, symbol: str) -> dict:
        """Baostock 不支持实时行情接口。

        Args:
            symbol: ETF代码，如 "510300"。

        Returns:
            dict: 空字典。
        """
        self.logger.info("Baostock 不支持实时行情查询，代码: %s", symbol)
        return {}

    def get_history_data(self, symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        """获取ETF历史K线数据。

        通过 baostock 的 query_history_k_data_plus 接口获取历史K线数据，
        查询前自动 login，查询后自动 logout。

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
        if not self.available:
            self.logger.error("baostock 未安装，无法获取历史数据")
            return pd.DataFrame()

        bs_symbol = self._convert_symbol(symbol)
        adjust_flag = self._convert_adjust_flag(adjust)

        self.logger.info(
            "开始获取ETF历史数据，代码: %s（baostock格式: %s），起始: %s，结束: %s，复权: %s",
            symbol, bs_symbol, start_date, end_date, adjust,
        )

        try:
            # 登录
            lg = self._bs.login()
            if lg.error_code != "0":
                self.logger.error("baostock 登录失败: %s", lg.error_msg)
                return pd.DataFrame()

            # 查询历史K线
            rs = self._bs.query_history_k_data_plus(
                bs_symbol,
                "date,open,high,low,close,volume,amount,turn,pctChg,change",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag=adjust_flag,
            )

            if rs.error_code != "0":
                self.logger.error(
                    "baostock 查询历史数据失败: %s，代码: %s", rs.error_msg, symbol,
                )
                self._bs.logout()
                return pd.DataFrame()

            # 将结果转为 DataFrame
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                self.logger.warning("baostock 返回空数据，代码: %s", symbol)
                self._bs.logout()
                return pd.DataFrame()

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 登出
            self._bs.logout()

            # 列名标准化映射
            column_mapping = {
                "date": "日期",
                "open": "开盘",
                "close": "收盘",
                "high": "最高",
                "low": "最低",
                "volume": "成交量",
                "amount": "成交额",
                "turn": "换手率",
                "pctChg": "涨跌幅",
                "change": "涨跌额",
            }
            df = df.rename(columns=column_mapping)

            # baostock 返回的数据多为字符串类型，需要转换为数值类型
            numeric_columns = ["开盘", "收盘", "最高", "最低", "成交量", "成交额", "换手率", "涨跌幅", "涨跌额"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # 添加振幅列（baostock 不直接返回振幅，根据最高最低价计算）
            if "振幅" not in df.columns and "最高" in df.columns and "最低" in df.columns:
                prev_close = df["收盘"].shift(1)
                df["振幅"] = ((df["最高"] - df["最低"]) / prev_close * 100).round(2)
                df.loc[df.index[0], "振幅"] = 0.0

            self.logger.info(
                "成功获取ETF历史数据，代码: %s，共 %d 条记录", symbol, len(df),
            )
            return df

        except Exception as e:
            self.logger.error(
                "获取ETF历史数据失败，代码: %s，异常: %s", symbol, e,
            )
            # 确保异常时也登出
            try:
                self._bs.logout()
            except Exception:
                pass
            return pd.DataFrame()

    def get_etf_list(self, keyword: str = None) -> pd.DataFrame:
        """Baostock 无直接ETF列表接口。

        Args:
            keyword: 过滤关键词（未使用）。

        Returns:
            DataFrame: 空 DataFrame。
        """
        self.logger.info("Baostock 不支持ETF列表查询")
        return pd.DataFrame()

    def get_etf_holdings(self, symbol: str) -> pd.DataFrame:
        """Baostock 无持仓接口。

        Args:
            symbol: ETF代码（未使用）。

        Returns:
            DataFrame: 空 DataFrame。
        """
        self.logger.info("Baostock 不支持ETF持仓查询，代码: %s", symbol)
        return pd.DataFrame()

    def health_check(self) -> dict:
        """检查数据源健康状态。

        通过 baostock 的 login 接口检测连接可用性。

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
            result["error"] = "baostock 库未安装"
            self.logger.warning("健康检查失败：baostock 库未安装")
            return result

        try:
            start_time = time.time()
            lg = self._bs.login()
            elapsed = time.time() - start_time

            if lg.error_code == "0":
                result["available"] = True
                result["response_time"] = round(elapsed, 3)
                self.logger.info(
                    "健康检查通过，响应时间: %.3f 秒", elapsed,
                )
            else:
                result["error"] = lg.error_msg
                self.logger.warning("健康检查失败：baostock 登录返回错误: %s", lg.error_msg)

            self._bs.logout()

        except Exception as e:
            result["error"] = str(e)
            self.logger.error("健康检查异常: %s", e)

        return result
