# -*- coding: utf-8 -*-
"""
ETF核心分析模块

本模块提供ETF的五大核心分析功能：净值走势分析、成分股构成分析、
行业分布统计、风险指标计算和绩效分析。通过组合使用 ETFDataFetcher
和 DataProcessor，完成从数据获取到指标计算的完整分析流程。
"""

import numpy as np
import pandas as pd

import akshare as ak

from etf_analyzer.config import RISK_FREE_RATE, SW_INDUSTRY_MAP, ZX_INDUSTRY_MAP
from etf_analyzer.logger import setup_logger
from etf_analyzer.data_fetcher import ETFDataFetcher
from etf_analyzer.data_processor import DataProcessor


class ETFAnalyzer:
    """ETF核心分析器，提供净值走势、成分股构成、行业分布、风险指标和绩效分析功能。

    通过 ETFDataFetcher 获取原始数据，经 DataProcessor 清洗验证后，
    计算各类分析指标并返回结构化结果。

    Attributes:
        fetcher: ETFDataFetcher 实例，用于获取ETF数据。
        processor: DataProcessor 实例，用于数据清洗和验证。
        logger: 日志记录器实例。
    """

    def __init__(self):
        """初始化ETFAnalyzer实例。

        创建数据获取器、数据处理器和日志记录器，为后续分析提供基础组件。
        """
        self.fetcher = ETFDataFetcher()
        self.processor = DataProcessor()
        self.logger = setup_logger("analyzer")
        self.logger.info("ETFAnalyzer 初始化完成")

    def analyze_nav_trend(self, symbol, start_date=None, end_date=None):
        """净值走势分析。

        获取ETF历史数据（前复权），计算累计收益率、年化收益率、日收益率序列，
        并基于20日均线和60日均线判断趋势方向。

        Args:
            symbol (str): ETF代码，如 "510300"。
            start_date (str, optional): 起始日期，格式为 YYYYMMDD。
                默认为 None，使用配置中的默认起始日期。
            end_date (str, optional): 结束日期，格式为 YYYYMMDD。
                默认为 None，使用当天日期。

        Returns:
            dict: 净值走势分析结果字典，包含以下键：
                - cumulative_return (float): 累计收益率（百分比形式），如 15.5 表示 15.5%。
                - annualized_return (float): 年化收益率（小数形式），如 0.08 表示 8%。
                - daily_returns (pandas.Series): 日收益率序列，索引为日期。
                - trend (str): 趋势判断结果，取值为 "上升趋势"、"下降趋势" 或 "震荡"。
                - nav_data (pandas.DataFrame): 净值数据，包含日期和收盘价列。
                如果分析失败则返回空字典。
        """
        self.logger.info("开始净值走势分析，ETF代码: %s", symbol)
        try:
            # 获取历史数据（前复权）
            df = self.fetcher.get_history_data(
                symbol, start_date=start_date, end_date=end_date, adjust="qfq",
            )
            if df is None or df.empty:
                self.logger.warning("获取历史数据为空，ETF代码: %s", symbol)
                return {}

            # 数据清洗
            df = self.processor.clean_data(df)
            if df.empty:
                self.logger.warning("数据清洗后为空，ETF代码: %s", symbol)
                return {}

            # 确定收盘价列名（akshare 返回的列名可能为"收盘"或"收盘价"）
            close_col = self._get_close_column(df)
            if close_col is None:
                self.logger.warning("未找到收盘价列，ETF代码: %s", symbol)
                return {}

            # 确定日期列
            date_col = self._get_date_column(df)
            if date_col is None:
                self.logger.warning("未找到日期列，ETF代码: %s", symbol)
                return {}

            # 确保按日期排序
            df = df.sort_values(by=date_col).reset_index(drop=True)

            close_prices = df[close_col].astype(float)

            # 计算累计收益率（百分比形式）
            cumulative_return = (close_prices.iloc[-1] / close_prices.iloc[0] - 1) * 100

            # 计算年化收益率（小数形式）
            trading_days = len(close_prices)
            if trading_days > 0 and close_prices.iloc[0] > 0:
                annualized_return = (
                    (1 + cumulative_return / 100) ** (252 / trading_days) - 1
                )
            else:
                annualized_return = 0.0

            # 计算日收益率序列
            daily_returns = close_prices.pct_change().dropna()
            daily_returns.index = df[date_col].iloc[1:].values

            # 趋势判断：基于20日均线和60日均线
            trend = "震荡"
            if len(close_prices) >= 60:
                ma20 = close_prices.rolling(window=20).mean()
                ma60 = close_prices.rolling(window=60).mean()
                current_ma20 = ma20.iloc[-1]
                current_ma60 = ma60.iloc[-1]
                if current_ma20 > current_ma60:
                    trend = "上升趋势"
                elif current_ma20 < current_ma60:
                    trend = "下降趋势"
                else:
                    trend = "震荡"
            elif len(close_prices) >= 20:
                ma20 = close_prices.rolling(window=20).mean()
                current_ma20 = ma20.iloc[-1]
                current_price = close_prices.iloc[-1]
                if current_price > current_ma20:
                    trend = "上升趋势"
                elif current_price < current_ma20:
                    trend = "下降趋势"
                else:
                    trend = "震荡"
                self.logger.info(
                    "数据不足60天，仅基于20日均线做简单判断，ETF代码: %s", symbol,
                )

            result = {
                "cumulative_return": cumulative_return,
                "annualized_return": annualized_return,
                "daily_returns": daily_returns,
                "trend": trend,
                "nav_data": df[[date_col, close_col]].copy(),
            }
            self.logger.info(
                "净值走势分析完成，ETF代码: %s，累计收益率: %.2f%%，趋势: %s",
                symbol, cumulative_return, trend,
            )
            return result

        except Exception as e:
            self.logger.error("净值走势分析失败，ETF代码: %s，异常: %s", symbol, e)
            return {}

    def analyze_holdings(self, symbol):
        """成分股构成分析。

        获取ETF持仓数据，计算前十大权重股及其占比，以及持仓集中度。

        Args:
            symbol (str): ETF代码，如 "510300"。

        Returns:
            dict: 成分股构成分析结果字典，包含以下键：
                - top10_holdings (pandas.DataFrame): 前十大权重股数据，
                  包含股票代码、股票名称、持仓占比等列。
                - concentration_ratio (float): 前十大权重股持仓集中度
                  （小数形式），如 0.65 表示 65%。
                如果分析失败则返回空字典。
        """
        self.logger.info("开始成分股构成分析，ETF代码: %s", symbol)
        try:
            df = self.fetcher.get_etf_holdings(symbol)
            if df is None or df.empty:
                self.logger.warning("获取持仓数据为空，ETF代码: %s", symbol)
                return {}

            # 确定持仓占比列名
            weight_col = self._get_weight_column(df)
            if weight_col is None:
                self.logger.warning("未找到持仓占比列，ETF代码: %s", symbol)
                return {}

            # 确保持仓占比为数值类型
            df[weight_col] = pd.to_numeric(df[weight_col], errors="coerce")
            df = df.dropna(subset=[weight_col])

            # 按持仓占比降序排列，取前十大
            df_sorted = df.sort_values(by=weight_col, ascending=False).reset_index(
                drop=True,
            )
            top10 = df_sorted.head(10)

            # 计算持仓集中度（前十大权重之和，小数形式）
            concentration_ratio = top10[weight_col].sum()

            result = {
                "top10_holdings": top10,
                "concentration_ratio": concentration_ratio,
            }
            self.logger.info(
                "成分股构成分析完成，ETF代码: %s，持仓集中度: %.4f",
                symbol, concentration_ratio,
            )
            return result

        except Exception as e:
            self.logger.error("成分股构成分析失败，ETF代码: %s，异常: %s", symbol, e)
            return {}

    def analyze_industry_distribution(self, symbol, classification="sw"):
        """行业分布统计。

        获取ETF持仓数据，将成分股按行业分类进行归类，
        计算各行业持仓占比和行业数量。

        Args:
            symbol (str): ETF代码，如 "510300"。
            classification (str): 行业分类标准，可选 "sw"（申万）或 "zx"（中信），
                默认为 "sw"。

        Returns:
            dict: 行业分布统计结果字典，包含以下键：
                - industry_distribution (pandas.DataFrame): 行业分布数据，
                  包含"行业名称"和"持仓占比"两列。
                - industry_count (int): 行业数量。
                如果分析失败则返回空字典。
        """
        classification_name = "申万" if classification == "sw" else "中信"
        self.logger.info(
            "开始行业分布统计，ETF代码: %s，行业分类标准: %s",
            symbol, classification_name,
        )
        try:
            df = self.fetcher.get_etf_holdings(symbol)
            if df is None or df.empty:
                self.logger.warning("获取持仓数据为空，ETF代码: %s", symbol)
                return {}

            # 确定持仓占比列名
            weight_col = self._get_weight_column(df)
            if weight_col is None:
                self.logger.warning("未找到持仓占比列，ETF代码: %s", symbol)
                return {}

            # 确保持仓占比为数值类型
            df[weight_col] = pd.to_numeric(df[weight_col], errors="coerce")
            df = df.dropna(subset=[weight_col])

            # 尝试确定行业列
            industry_col = self._get_industry_column(df)

            if industry_col is not None:
                # 持仓数据中已有行业信息，直接使用
                self.logger.info(
                    "持仓数据中存在行业列 '%s'，直接使用", industry_col,
                )
                industry_dist = (
                    df.groupby(industry_col)[weight_col]
                    .sum()
                    .reset_index()
                )
                industry_dist.columns = ["行业名称", "持仓占比"]
                industry_dist = industry_dist.sort_values(
                    by="持仓占比", ascending=False,
                ).reset_index(drop=True)
            else:
                # 持仓数据中没有行业信息，尝试通过股票代码获取行业
                self.logger.info(
                    "持仓数据中无行业列，尝试通过股票代码获取行业信息",
                )
                industry_dist = self._get_industry_from_stock_codes(df, weight_col)

                if industry_dist is None or industry_dist.empty:
                    self.logger.warning(
                        "无法获取行业信息，ETF代码: %s", symbol,
                    )
                    return {
                        "industry_distribution": pd.DataFrame(
                            columns=["行业名称", "持仓占比"],
                        ),
                        "industry_count": 0,
                    }

            industry_count = len(industry_dist)

            result = {
                "industry_distribution": industry_dist,
                "industry_count": industry_count,
            }
            self.logger.info(
                "行业分布统计完成，ETF代码: %s，行业数量: %d",
                symbol, industry_count,
            )
            return result

        except Exception as e:
            self.logger.error("行业分布统计失败，ETF代码: %s，异常: %s", symbol, e)
            return {}

    def calculate_risk_metrics(
        self, symbol, start_date=None, end_date=None, benchmark_symbol=None,
    ):
        """风险指标计算。

        获取ETF历史数据，计算日波动率、年化波动率、最大回撤、夏普比率等风险指标。
        如果提供了基准代码，还会计算信息比率。

        Args:
            symbol (str): ETF代码，如 "510300"。
            start_date (str, optional): 起始日期，格式为 YYYYMMDD。
                默认为 None，使用配置中的默认起始日期。
            end_date (str, optional): 结束日期，格式为 YYYYMMDD。
                默认为 None，使用当天日期。
            benchmark_symbol (str, optional): 基准指数代码，如 "000300"。
                如果提供，将计算信息比率。默认为 None。

        Returns:
            dict: 风险指标结果字典，包含以下键：
                - daily_volatility (float): 日波动率（小数形式）。
                - annualized_volatility (float): 年化波动率（小数形式）。
                - max_drawdown (float): 最大回撤（小数形式），如 0.15 表示 15%。
                - max_drawdown_start (str): 最大回撤起始日期，格式 YYYY-MM-DD。
                - max_drawdown_end (str): 最大回撤结束日期，格式 YYYY-MM-DD。
                - sharpe_ratio (float): 夏普比率。
                - information_ratio (float or None): 信息比率，仅当提供
                  benchmark_symbol 时计算，否则为 None。
                如果计算失败则返回包含默认值的字典。
        """
        self.logger.info("开始风险指标计算，ETF代码: %s", symbol)
        try:
            df = self.fetcher.get_history_data(
                symbol, start_date=start_date, end_date=end_date, adjust="qfq",
            )
            if df is None or df.empty:
                self.logger.warning("获取历史数据为空，ETF代码: %s", symbol)
                return self._default_risk_metrics()

            df = self.processor.clean_data(df)
            if df.empty:
                self.logger.warning("数据清洗后为空，ETF代码: %s", symbol)
                return self._default_risk_metrics()

            close_col = self._get_close_column(df)
            date_col = self._get_date_column(df)
            if close_col is None or date_col is None:
                self.logger.warning("未找到必要列，ETF代码: %s", symbol)
                return self._default_risk_metrics()

            df = df.sort_values(by=date_col).reset_index(drop=True)
            close_prices = df[close_col].astype(float)

            # 日收益率
            daily_returns = close_prices.pct_change().dropna()

            # 日波动率
            daily_volatility = daily_returns.std()

            # 年化波动率
            annualized_volatility = daily_volatility * np.sqrt(252)

            # 最大回撤
            cumulative = (1 + daily_returns).cumprod()
            running_max = cumulative.cummax()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()

            # 最大回撤起止日期
            end_idx = drawdown.idxmin()
            # 找到回撤起始点：在 end_idx 之前 cumulative 最后一次等于 running_max 的位置
            drawdown_period = drawdown.loc[:end_idx]
            running_max_period = running_max.loc[:end_idx]
            start_idx_candidates = running_max_period[
                running_max_period == running_max_period.iloc[-1]
            ].index
            start_idx = start_idx_candidates[0]

            max_drawdown_start = str(df[date_col].iloc[start_idx])[:10]
            max_drawdown_end = str(df[date_col].iloc[end_idx + 1])[:10] if end_idx + 1 < len(df) else str(df[date_col].iloc[end_idx])[:10]

            # 年化收益率
            trading_days = len(close_prices)
            cumulative_return = (close_prices.iloc[-1] / close_prices.iloc[0] - 1)
            if trading_days > 0 and close_prices.iloc[0] > 0:
                annualized_return = (
                    (1 + cumulative_return) ** (252 / trading_days) - 1
                )
            else:
                annualized_return = 0.0

            # 夏普比率
            if annualized_volatility > 0:
                sharpe_ratio = (
                    (annualized_return - RISK_FREE_RATE) / annualized_volatility
                )
            else:
                sharpe_ratio = 0.0

            # 信息比率（如果提供了基准代码）
            information_ratio = None
            if benchmark_symbol:
                information_ratio = self._calculate_information_ratio(
                    daily_returns, df, date_col, benchmark_symbol,
                    start_date, end_date,
                )

            result = {
                "daily_volatility": daily_volatility,
                "annualized_volatility": annualized_volatility,
                "max_drawdown": max_drawdown,
                "max_drawdown_start": max_drawdown_start,
                "max_drawdown_end": max_drawdown_end,
                "sharpe_ratio": sharpe_ratio,
                "information_ratio": information_ratio,
            }
            self.logger.info(
                "风险指标计算完成，ETF代码: %s，年化波动率: %.4f，"
                "最大回撤: %.4f，夏普比率: %.4f",
                symbol, annualized_volatility, max_drawdown, sharpe_ratio,
            )
            return result

        except Exception as e:
            self.logger.error("风险指标计算失败，ETF代码: %s，异常: %s", symbol, e)
            return self._default_risk_metrics()

    def analyze_performance(
        self, symbol, benchmark_symbol, start_date=None, end_date=None,
    ):
        """绩效分析。

        获取ETF和基准指数的历史数据，计算超额收益、跟踪误差、信息比率和胜率。

        Args:
            symbol (str): ETF代码，如 "510300"。
            benchmark_symbol (str): 基准指数代码，如 "000300"。
            start_date (str, optional): 起始日期，格式为 YYYYMMDD。
                默认为 None，使用配置中的默认起始日期。
            end_date (str, optional): 结束日期，格式为 YYYYMMDD。
                默认为 None，使用当天日期。

        Returns:
            dict: 绩效分析结果字典，包含以下键：
                - excess_return (float): 超额收益（百分比形式），
                  ETF累计收益率 - 基准累计收益率。
                - tracking_error (float): 跟踪误差（年化标准差，小数形式）。
                - information_ratio (float): 信息比率。
                - win_rate (float): 胜率（小数形式），ETF日收益率大于基准日收益率的天数占比。
                - etf_returns (pandas.Series): ETF日收益率序列。
                - benchmark_returns (pandas.Series): 基准日收益率序列。
                如果分析失败则返回空字典。
        """
        self.logger.info(
            "开始绩效分析，ETF代码: %s，基准代码: %s", symbol, benchmark_symbol,
        )
        try:
            # 获取ETF历史数据
            etf_df = self.fetcher.get_history_data(
                symbol, start_date=start_date, end_date=end_date, adjust="qfq",
            )
            if etf_df is None or etf_df.empty:
                self.logger.warning("获取ETF历史数据为空，ETF代码: %s", symbol)
                return {}

            etf_df = self.processor.clean_data(etf_df)
            if etf_df.empty:
                self.logger.warning("ETF数据清洗后为空，ETF代码: %s", symbol)
                return {}

            # 获取基准指数历史数据
            benchmark_df = self._get_benchmark_data(
                benchmark_symbol, start_date, end_date,
            )
            if benchmark_df is None or benchmark_df.empty:
                self.logger.warning(
                    "获取基准数据为空，基准代码: %s", benchmark_symbol,
                )
                return {}

            benchmark_df = self.processor.clean_data(benchmark_df)
            if benchmark_df.empty:
                self.logger.warning("基准数据清洗后为空，基准代码: %s", benchmark_symbol)
                return {}

            # 确定列名
            etf_close_col = self._get_close_column(etf_df)
            etf_date_col = self._get_date_column(etf_df)
            bench_close_col = self._get_close_column(benchmark_df)
            bench_date_col = self._get_date_column(benchmark_df)

            if any(
                col is None
                for col in [
                    etf_close_col, etf_date_col, bench_close_col, bench_date_col,
                ]
            ):
                self.logger.warning("未找到必要的收盘价或日期列")
                return {}

            # 排序
            etf_df = etf_df.sort_values(by=etf_date_col).reset_index(drop=True)
            benchmark_df = benchmark_df.sort_values(by=bench_date_col).reset_index(
                drop=True,
            )

            # 确保日期格式一致用于对齐
            etf_df["_date"] = pd.to_datetime(etf_df[etf_date_col])
            benchmark_df["_date"] = pd.to_datetime(benchmark_df[bench_date_col])

            # 按日期对齐
            merged = pd.merge(
                etf_df[["_date", etf_close_col]],
                benchmark_df[["_date", bench_close_col]],
                on="_date",
                how="inner",
            )
            if merged.empty:
                self.logger.warning("ETF与基准日期对齐后无交集数据")
                return {}

            merged = merged.sort_values(by="_date").reset_index(drop=True)

            etf_close = merged[etf_close_col].astype(float)
            bench_close = merged[bench_close_col].astype(float)

            # 计算日收益率
            etf_returns = etf_close.pct_change().dropna()
            benchmark_returns = bench_close.pct_change().dropna()

            # 对齐长度（pct_change后长度一致）
            min_len = min(len(etf_returns), len(benchmark_returns))
            etf_returns = etf_returns.iloc[:min_len].reset_index(drop=True)
            benchmark_returns = benchmark_returns.iloc[:min_len].reset_index(drop=True)

            # 超额收益 = ETF累计收益率 - 基准累计收益率（百分比形式）
            etf_cum_return = (etf_close.iloc[-1] / etf_close.iloc[0] - 1) * 100
            bench_cum_return = (bench_close.iloc[-1] / bench_close.iloc[0] - 1) * 100
            excess_return = etf_cum_return - bench_cum_return

            # 超额收益率序列
            excess_returns = etf_returns - benchmark_returns

            # 跟踪误差 = 超额收益率序列的年化标准差
            tracking_error = excess_returns.std() * np.sqrt(252)

            # 信息比率 = 超额收益均值 / 跟踪误差
            if tracking_error > 0:
                information_ratio = (
                    excess_returns.mean() * 252 / tracking_error
                )
            else:
                information_ratio = 0.0

            # 胜率 = ETF日收益率 > 基准日收益率的天数占比
            win_days = (etf_returns > benchmark_returns).sum()
            win_rate = win_days / len(etf_returns) if len(etf_returns) > 0 else 0.0

            result = {
                "excess_return": excess_return,
                "tracking_error": tracking_error,
                "information_ratio": information_ratio,
                "win_rate": win_rate,
                "etf_returns": etf_returns,
                "benchmark_returns": benchmark_returns,
            }
            self.logger.info(
                "绩效分析完成，ETF代码: %s，超额收益: %.2f%%，"
                "跟踪误差: %.4f，信息比率: %.4f，胜率: %.4f",
                symbol, excess_return, tracking_error, information_ratio, win_rate,
            )
            return result

        except Exception as e:
            self.logger.error("绩效分析失败，ETF代码: %s，异常: %s", symbol, e)
            return {}

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _get_close_column(self, df):
        """获取DataFrame中的收盘价列名。

        兼容 akshare 不同接口返回的列名差异，依次尝试常见的收盘价列名。

        Args:
            df (pandas.DataFrame): 数据表。

        Returns:
            str or None: 收盘价列名，如果未找到则返回 None。
        """
        candidates = ["收盘", "收盘价", "close", "Close", "最新价"]
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def _get_date_column(self, df):
        """获取DataFrame中的日期列名。

        兼容 akshare 不同接口返回的列名差异，依次尝试常见的日期列名。

        Args:
            df (pandas.DataFrame): 数据表。

        Returns:
            str or None: 日期列名，如果未找到则返回 None。
        """
        candidates = ["日期", "交易日期", "date", "Date"]
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def _get_weight_column(self, df):
        """获取DataFrame中的持仓占比列名。

        兼容 akshare 不同接口返回的列名差异，依次尝试常见的持仓占比列名。

        Args:
            df (pandas.DataFrame): 持仓数据表。

        Returns:
            str or None: 持仓占比列名，如果未找到则返回 None。
        """
        candidates = ["占净值比例", "持仓占比", "持仓比例", "权重", "weight"]
        for col in candidates:
            if col in df.columns:
                return col
        # 尝试模糊匹配包含"比例"或"占比"的列
        for col in df.columns:
            if "比例" in col or "占比" in col:
                return col
        return None

    def _get_industry_column(self, df):
        """获取DataFrame中的行业列名。

        在持仓数据中查找行业相关的列名，优先匹配申万一级行业列。

        Args:
            df (pandas.DataFrame): 持仓数据表。

        Returns:
            str or None: 行业列名，如果未找到则返回 None。
        """
        # 精确匹配
        candidates = [
            "申万一级行业", "中信一级行业", "行业", "行业名称", "一级行业",
            "所属行业", "industry", "Industry",
        ]
        for col in candidates:
            if col in df.columns:
                return col
        # 模糊匹配
        for col in df.columns:
            if "行业" in col:
                return col
        return None

    def _get_stock_code_column(self, df):
        """获取DataFrame中的股票代码列名。

        Args:
            df (pandas.DataFrame): 持仓数据表。

        Returns:
            str or None: 股票代码列名，如果未找到则返回 None。
        """
        candidates = ["股票代码", "代码", "证券代码", "code", "Code"]
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def _get_industry_from_stock_codes(self, df, weight_col):
        """通过股票代码获取行业信息并汇总行业分布。

        当持仓数据中没有行业列时，尝试通过 akshare 接口逐个获取股票的行业信息，
        然后按申万一级行业分类汇总持仓占比。

        Args:
            df (pandas.DataFrame): 持仓数据表。
            weight_col (str): 持仓占比列名。

        Returns:
            pandas.DataFrame or None: 行业分布数据，包含"行业名称"和"持仓占比"两列。
                如果获取失败则返回 None。
        """
        code_col = self._get_stock_code_column(df)
        if code_col is None:
            self.logger.warning("未找到股票代码列，无法获取行业信息")
            return None

        stock_industries = {}
        failed_count = 0

        for _, row in df.iterrows():
            stock_code = str(row[code_col]).strip()
            try:
                info = ak.stock_individual_info_em(symbol=stock_code)
                if info is not None and not info.empty:
                    # 在返回的信息中查找行业
                    industry_row = info[
                        info["item"].str.contains("行业", na=False)
                    ]
                    if not industry_row.empty:
                        industry_name = str(industry_row.iloc[0]["value"])
                        stock_industries[stock_code] = industry_name
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                self.logger.debug(
                    "获取股票 %s 行业信息失败: %s", stock_code, e,
                )

        if failed_count > 0:
            self.logger.info(
                "获取行业信息时 %d 只股票失败", failed_count,
            )

        if not stock_industries:
            self.logger.warning("未能获取任何股票的行业信息")
            return None

        # 将行业信息映射回持仓数据
        df_copy = df.copy()
        df_copy["行业名称"] = df_copy[code_col].astype(str).str.strip().map(
            stock_industries,
        )
        df_with_industry = df_copy.dropna(subset=["行业名称"])

        if df_with_industry.empty:
            self.logger.warning("行业信息映射后无有效数据")
            return None

        # 按行业汇总持仓占比
        industry_dist = (
            df_with_industry.groupby("行业名称")[weight_col].sum().reset_index()
        )
        industry_dist.columns = ["行业名称", "持仓占比"]
        industry_dist = industry_dist.sort_values(
            by="持仓占比", ascending=False,
        ).reset_index(drop=True)

        return industry_dist

    def _get_benchmark_data(self, benchmark_symbol, start_date=None, end_date=None):
        """获取基准指数历史数据。

        尝试使用 akshare 的指数历史数据接口获取基准指数的日K线数据，
        依次尝试 index_zh_a_hist 和 stock_zh_index_daily 接口。

        Args:
            benchmark_symbol (str): 基准指数代码，如 "000300"。
            start_date (str, optional): 起始日期，格式为 YYYYMMDD。
            end_date (str, optional): 结束日期，格式为 YYYYMMDD。

        Returns:
            pandas.DataFrame: 基准指数历史数据，如果获取失败则返回空 DataFrame。
        """
        self.logger.info("开始获取基准指数数据，代码: %s", benchmark_symbol)

        if start_date is None:
            start_date = "20200101"
        if end_date is None:
            from datetime import datetime
            end_date = datetime.now().strftime("%Y%m%d")

        # 尝试方法1：index_zh_a_hist
        try:
            df = ak.index_zh_a_hist(
                symbol=benchmark_symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                self.logger.info(
                    "通过 index_zh_a_hist 获取基准数据成功，共 %d 条",
                    len(df),
                )
                return df
        except Exception as e:
            self.logger.debug(
                "index_zh_a_hist 获取基准数据失败: %s，尝试其他接口", e,
            )

        # 尝试方法2：stock_zh_index_daily
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{benchmark_symbol}")
            if df is not None and not df.empty:
                # 过滤日期范围
                date_col = self._get_date_column(df)
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col])
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df[
                        (df[date_col] >= start_dt) & (df[date_col] <= end_dt)
                    ]
                self.logger.info(
                    "通过 stock_zh_index_daily 获取基准数据成功，共 %d 条",
                    len(df),
                )
                return df
        except Exception as e:
            self.logger.debug(
                "stock_zh_index_daily 获取基准数据失败: %s", e,
            )

        self.logger.warning("所有基准数据获取方法均失败，基准代码: %s", benchmark_symbol)
        return pd.DataFrame()

    def _calculate_information_ratio(
        self, etf_daily_returns, etf_df, date_col, benchmark_symbol,
        start_date, end_date,
    ):
        """计算信息比率（用于 calculate_risk_metrics 内部调用）。

        获取基准数据后，计算ETF相对于基准的信息比率：
        超额收益的均值 / 超额收益的标准差 * sqrt(252)。

        Args:
            etf_daily_returns (pandas.Series): ETF日收益率序列。
            etf_df (pandas.DataFrame): ETF历史数据。
            date_col (str): 日期列名。
            benchmark_symbol (str): 基准指数代码。
            start_date (str): 起始日期。
            end_date (str): 结束日期。

        Returns:
            float or None: 信息比率，如果计算失败则返回 None。
        """
        try:
            benchmark_df = self._get_benchmark_data(
                benchmark_symbol, start_date, end_date,
            )
            if benchmark_df is None or benchmark_df.empty:
                self.logger.warning("获取基准数据为空，无法计算信息比率")
                return None

            bench_close_col = self._get_close_column(benchmark_df)
            bench_date_col = self._get_date_column(benchmark_df)
            if bench_close_col is None or bench_date_col is None:
                self.logger.warning("基准数据中未找到必要列")
                return None

            benchmark_df = benchmark_df.sort_values(
                by=bench_date_col,
            ).reset_index(drop=True)
            bench_close = benchmark_df[bench_close_col].astype(float)
            bench_daily_returns = bench_close.pct_change().dropna()

            # 对齐长度
            min_len = min(len(etf_daily_returns), len(bench_daily_returns))
            if min_len == 0:
                return None

            etf_aligned = etf_daily_returns.iloc[:min_len].reset_index(drop=True)
            bench_aligned = bench_daily_returns.iloc[:min_len].reset_index(drop=True)

            excess_returns = etf_aligned - bench_aligned
            excess_std = excess_returns.std()

            if excess_std > 0:
                information_ratio = (
                    excess_returns.mean() / excess_std * np.sqrt(252)
                )
            else:
                information_ratio = 0.0

            self.logger.info("信息比率计算完成: %.4f", information_ratio)
            return information_ratio

        except Exception as e:
            self.logger.error("信息比率计算失败: %s", e)
            return None

    @staticmethod
    def _default_risk_metrics():
        """返回风险指标的默认值字典。

        当风险指标计算失败时，返回包含合理默认值的结果字典。

        Returns:
            dict: 包含默认风险指标值的字典。
        """
        return {
            "daily_volatility": 0.0,
            "annualized_volatility": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_start": "",
            "max_drawdown_end": "",
            "sharpe_ratio": 0.0,
            "information_ratio": None,
        }
