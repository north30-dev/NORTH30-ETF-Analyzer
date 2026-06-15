# -*- coding: utf-8 -*-
"""
ETFAnalyzer 单元测试模块

使用 unittest.mock.patch 模拟数据获取，测试 ETFAnalyzer 的
净值走势分析、成分股分析、行业分布分析、风险指标计算和绩效分析功能。
"""

from unittest.mock import patch, MagicMock, PropertyMock

import numpy as np
import pandas as pd
import pytest

from etf_analyzer.analyzer import ETFAnalyzer


class TestETFAnalyzer:
    """ETFAnalyzer 单元测试类。"""

    def test_init(self):
        """测试 ETFAnalyzer 初始化是否正确创建 fetcher、processor 和 logger。"""
        analyzer = ETFAnalyzer()
        assert analyzer.fetcher is not None
        assert analyzer.processor is not None
        assert analyzer.logger is not None

    @patch.object(
        ETFAnalyzer, "_get_close_column", return_value="收盘"
    )
    @patch.object(
        ETFAnalyzer, "_get_date_column", return_value="日期"
    )
    def test_analyze_nav_trend(
        self, mock_date_col, mock_close_col, sample_history_df
    ):
        """测试净值走势分析，应返回包含累计收益率、年化收益率、趋势等键的字典。"""
        analyzer = ETFAnalyzer()

        with patch.object(
            analyzer.fetcher, "get_history_data", return_value=sample_history_df
        ):
            result = analyzer.analyze_nav_trend("510300", start_date="20240101", end_date="20240201")

        assert isinstance(result, dict)
        assert "cumulative_return" in result
        assert "annualized_return" in result
        assert "daily_returns" in result
        assert "trend" in result
        assert "nav_data" in result
        assert isinstance(result["cumulative_return"], float)
        assert isinstance(result["trend"], str)

    def test_analyze_holdings(self, sample_holdings_df):
        """测试成分股构成分析，应返回包含前十大权重股和持仓集中度的字典。"""
        analyzer = ETFAnalyzer()

        with patch.object(
            analyzer.fetcher, "get_etf_holdings", return_value=sample_holdings_df
        ):
            result = analyzer.analyze_holdings("510300")

        assert isinstance(result, dict)
        assert "top10_holdings" in result
        assert "concentration_ratio" in result
        assert len(result["top10_holdings"]) == 10
        assert isinstance(result["concentration_ratio"], float)
        assert result["concentration_ratio"] > 0

    def test_analyze_industry_distribution(self, sample_holdings_df):
        """测试行业分布分析，应返回包含行业分布数据和行业数量的字典。"""
        # 为持仓数据添加行业列
        holdings_with_industry = sample_holdings_df.copy()
        holdings_with_industry["申万一级行业"] = [
            "食品饮料", "食品饮料", "银行", "非银金融", "家用电器",
            "医药生物", "休闲服务", "家用电器", "非银金融", "银行",
            "食品饮料", "食品饮料", "银行", "银行", "房地产",
        ]

        analyzer = ETFAnalyzer()

        with patch.object(
            analyzer.fetcher, "get_etf_holdings", return_value=holdings_with_industry
        ):
            result = analyzer.analyze_industry_distribution("510300")

        assert isinstance(result, dict)
        assert "industry_distribution" in result
        assert "industry_count" in result
        assert result["industry_count"] > 0
        assert not result["industry_distribution"].empty
        assert "行业名称" in result["industry_distribution"].columns
        assert "持仓占比" in result["industry_distribution"].columns

    @patch.object(
        ETFAnalyzer, "_get_close_column", return_value="收盘"
    )
    @patch.object(
        ETFAnalyzer, "_get_date_column", return_value="日期"
    )
    def test_calculate_risk_metrics(
        self, mock_date_col, mock_close_col, sample_history_df
    ):
        """测试风险指标计算，应返回包含波动率、最大回撤、夏普比率等键的字典。"""
        analyzer = ETFAnalyzer()

        with patch.object(
            analyzer.fetcher, "get_history_data", return_value=sample_history_df
        ):
            result = analyzer.calculate_risk_metrics(
                "510300", start_date="20240101", end_date="20240201"
            )

        assert isinstance(result, dict)
        assert "daily_volatility" in result
        assert "annualized_volatility" in result
        assert "max_drawdown" in result
        assert "max_drawdown_start" in result
        assert "max_drawdown_end" in result
        assert "sharpe_ratio" in result
        assert "information_ratio" in result
        assert result["daily_volatility"] >= 0
        assert result["annualized_volatility"] >= 0
        assert result["max_drawdown"] <= 0
        assert result["information_ratio"] is None  # 未提供基准代码

    def test_analyze_performance(self, sample_history_df):
        """测试绩效分析，应返回包含超额收益、跟踪误差、信息比率和胜率的字典。"""
        analyzer = ETFAnalyzer()

        # 构造基准数据，与ETF数据日期对齐，使用不同的收盘列名避免merge冲突
        benchmark_df = sample_history_df.copy()
        benchmark_df = benchmark_df.rename(columns={"收盘": "收盘价"})
        benchmark_df["收盘价"] = benchmark_df["收盘价"] * 1.1

        # 让 _get_close_column 根据DataFrame的列返回正确的列名
        original_get_close = ETFAnalyzer._get_close_column
        original_get_date = ETFAnalyzer._get_date_column

        def mock_get_close(self, df):
            if "收盘价" in df.columns:
                return "收盘价"
            return original_get_close(self, df)

        def mock_get_date(self, df):
            return "日期"

        with patch.object(
            analyzer.fetcher, "get_history_data", return_value=sample_history_df
        ), patch.object(
            analyzer, "_get_benchmark_data", return_value=benchmark_df
        ), patch.object(
            analyzer.processor, "clean_data", side_effect=lambda df, **kw: df
        ), patch.object(
            ETFAnalyzer, "_get_close_column", mock_get_close
        ), patch.object(
            ETFAnalyzer, "_get_date_column", mock_get_date
        ):
            result = analyzer.analyze_performance(
                "510300", "000300", start_date="20240101", end_date="20240201"
            )

        assert isinstance(result, dict)
        assert "excess_return" in result
        assert "tracking_error" in result
        assert "information_ratio" in result
        assert "win_rate" in result
        assert "etf_returns" in result
        assert "benchmark_returns" in result
        assert isinstance(result["excess_return"], float)
        assert result["tracking_error"] >= 0
        assert 0.0 <= result["win_rate"] <= 1.0
