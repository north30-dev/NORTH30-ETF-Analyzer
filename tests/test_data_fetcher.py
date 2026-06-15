# -*- coding: utf-8 -*-
"""
ETFDataFetcher 单元测试模块

使用 unittest.mock.patch 模拟 akshare 接口，测试 ETFDataFetcher 的
实时行情获取、历史数据获取、ETF列表获取、持仓信息获取以及缓存机制。
"""

import os
import pickle
import time
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from etf_analyzer.data_fetcher import ETFDataFetcher


class TestETFDataFetcher:
    """ETFDataFetcher 单元测试类。"""

    def test_init(self):
        """测试 ETFDataFetcher 初始化是否正确设置日志和缓存目录。"""
        fetcher = ETFDataFetcher()
        assert fetcher.cache_dir is not None
        assert isinstance(fetcher.cache_dir, str)
        assert fetcher.logger is not None

    @patch("etf_analyzer.data_fetcher.ak.fund_etf_spot_em")
    def test_get_realtime_quote_success(self, mock_spot_em, sample_realtime_data):
        """测试成功获取实时行情数据。"""
        # 构造模拟返回的 DataFrame
        mock_df = pd.DataFrame(
            [
                {
                    "代码": "510300",
                    "名称": "沪深300ETF",
                    "最新价": 3.856,
                    "涨跌幅": 1.23,
                    "涨跌额": 0.047,
                    "成交量": 12345678,
                    "成交额": 47654321,
                    "开盘价": 3.812,
                    "最高价": 3.878,
                    "最低价": 3.798,
                    "昨收": 3.809,
                }
            ]
        )
        mock_spot_em.return_value = mock_df

        fetcher = ETFDataFetcher()
        result = fetcher.get_realtime_quote("510300")

        assert result["symbol"] == "510300"
        assert result["name"] == "沪深300ETF"
        assert abs(result["price"] - 3.856) < 0.001
        assert abs(result["change_pct"] - 1.23) < 0.01

    @patch("etf_analyzer.data_fetcher.ak.fund_etf_spot_em")
    def test_get_realtime_quote_not_found(self, mock_spot_em):
        """测试未找到指定ETF代码时返回空字典。"""
        mock_df = pd.DataFrame(
            [
                {
                    "代码": "510500",
                    "名称": "中证500ETF",
                    "最新价": 5.0,
                    "涨跌幅": 0.5,
                    "涨跌额": 0.02,
                    "成交量": 100000,
                    "成交额": 500000,
                    "开盘价": 4.98,
                    "最高价": 5.02,
                    "最低价": 4.95,
                    "昨收": 4.98,
                }
            ]
        )
        mock_spot_em.return_value = mock_df

        fetcher = ETFDataFetcher()
        result = fetcher.get_realtime_quote("999999")

        assert result == {}

    @patch("etf_analyzer.data_fetcher.ak.fund_etf_spot_em")
    def test_get_realtime_quote_error(self, mock_spot_em):
        """测试网络异常时返回空字典。"""
        mock_spot_em.side_effect = ConnectionError("网络连接失败")

        fetcher = ETFDataFetcher()
        result = fetcher.get_realtime_quote("510300")

        assert result == {}

    @patch("etf_analyzer.data_fetcher.ak.fund_etf_hist_em")
    def test_get_history_data_success(self, mock_hist_em, sample_history_df):
        """测试成功获取历史数据。"""
        mock_hist_em.return_value = sample_history_df

        fetcher = ETFDataFetcher()
        # 清除可能的缓存干扰
        result = fetcher.get_history_data("510300", start_date="20240101", end_date="20240201")

        assert result is not None
        assert not result.empty
        assert len(result) == 30

    @patch("etf_analyzer.data_fetcher.ak.fund_etf_hist_em")
    def test_get_history_data_with_cache(self, mock_hist_em, sample_history_df, tmp_path):
        """测试缓存机制：首次调用后数据被缓存，第二次从缓存加载。"""
        mock_hist_em.return_value = sample_history_df

        fetcher = ETFDataFetcher()
        # 使用临时目录避免其他测试的缓存干扰
        fetcher.cache_dir = str(tmp_path)

        # 首次调用，应请求接口并保存缓存
        result1 = fetcher.get_history_data("510300", start_date="20240101", end_date="20240201")
        assert mock_hist_em.call_count == 1

        # 第二次调用，应从缓存加载，不再请求接口
        result2 = fetcher.get_history_data("510300", start_date="20240101", end_date="20240201")
        assert mock_hist_em.call_count == 1  # 调用次数不变

        # 两次结果应一致
        assert len(result1) == len(result2)

    @patch("etf_analyzer.data_fetcher.ak.fund_etf_spot_em")
    def test_get_etf_list_success(self, mock_spot_em):
        """测试成功获取ETF列表。"""
        mock_df = pd.DataFrame(
            [
                {"代码": "510300", "名称": "沪深300ETF", "最新价": 3.856},
                {"代码": "510500", "名称": "中证500ETF", "最新价": 5.0},
                {"代码": "159919", "名称": "沪深300ETF", "最新价": 4.2},
            ]
        )
        mock_spot_em.return_value = mock_df

        fetcher = ETFDataFetcher()
        result = fetcher.get_etf_list()

        assert not result.empty
        assert len(result) == 3

    @patch("etf_analyzer.data_fetcher.ak.fund_etf_spot_em")
    def test_get_etf_list_with_keyword(self, mock_spot_em):
        """测试按关键词过滤ETF列表。"""
        mock_df = pd.DataFrame(
            [
                {"代码": "510300", "名称": "沪深300ETF", "最新价": 3.856},
                {"代码": "510500", "名称": "中证500ETF", "最新价": 5.0},
                {"代码": "159919", "名称": "沪深300ETF", "最新价": 4.2},
            ]
        )
        mock_spot_em.return_value = mock_df

        fetcher = ETFDataFetcher()
        result = fetcher.get_etf_list(keyword="沪深300")

        assert not result.empty
        assert len(result) == 2
        assert all(result["名称"].str.contains("沪深300"))

    def test_get_etf_holdings_success(self, sample_holdings_df):
        """测试成功获取持仓信息。"""
        import akshare as ak

        fetcher = ETFDataFetcher()

        # 动态为 akshare 模块添加 mock 方法，因为该属性可能不存在于当前版本
        mock_func = MagicMock(return_value=sample_holdings_df)
        original_attr = getattr(ak, "fund_etf_hold_em", None)
        setattr(ak, "fund_etf_hold_em", mock_func)

        # 清除可能的缓存干扰
        cache_key = fetcher._get_cache_key(
            "510300", "holdings", date=str(2026)
        )
        if os.path.exists(cache_key):
            os.remove(cache_key)

        try:
            result = fetcher.get_etf_holdings("510300")
        finally:
            # 恢复原始属性
            if original_attr is not None:
                setattr(ak, "fund_etf_hold_em", original_attr)
            else:
                delattr(ak, "fund_etf_hold_em")

        assert result is not None
        assert not result.empty
        assert len(result) == 15
        assert "股票代码" in result.columns
        assert "股票名称" in result.columns

    def test_cache_key_generation(self):
        """测试缓存键生成逻辑，确保不同参数产生不同的键。"""
        fetcher = ETFDataFetcher()

        key1 = fetcher._get_cache_key("510300", "history", start_date="20240101", end_date="20240201")
        key2 = fetcher._get_cache_key("510300", "history", start_date="20240101", end_date="20240301")
        key3 = fetcher._get_cache_key("510500", "history", start_date="20240101", end_date="20240201")
        key4 = fetcher._get_cache_key("510300", "holdings", date="2024")

        # 不同参数应产生不同的键
        assert key1 != key2
        assert key1 != key3
        assert key1 != key4

        # 锁应包含关键信息
        assert "510300" in key1
        assert "history" in key1
        assert key1.endswith(".pkl")

    def test_cache_save_and_load(self, sample_history_df, tmp_path):
        """测试缓存保存和加载功能。"""
        fetcher = ETFDataFetcher()
        # 使用临时目录作为缓存目录
        fetcher.cache_dir = str(tmp_path)

        cache_key = fetcher._get_cache_key("510300", "history", start_date="20240101", end_date="20240201")

        # 保存缓存
        fetcher._save_cache(cache_key, sample_history_df)

        # 验证缓存文件已创建
        assert os.path.exists(cache_key)

        # 加载缓存
        loaded = fetcher._load_cache(cache_key)
        assert loaded is not None
        assert len(loaded) == len(sample_history_df)
        assert list(loaded.columns) == list(sample_history_df.columns)
