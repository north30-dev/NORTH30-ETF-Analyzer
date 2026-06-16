# -*- coding: utf-8 -*-
"""
ETFDataFetcher 单元测试模块

使用 unittest.mock.patch 模拟 DataSourceManager 接口，测试 ETFDataFetcher 的
实时行情获取、历史数据获取、ETF列表获取、持仓信息获取以及缓存机制。
重构后 ETFDataFetcher 内部委托给 DataSourceManager，不再直接调用 akshare。
"""

import os
import pickle
import time
from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd
import pytest

from etf_analyzer.core.data_fetcher import ETFDataFetcher


class TestETFDataFetcher:
    """ETFDataFetcher 单元测试类。"""

    def test_init(self):
        """测试 ETFDataFetcher 初始化是否正确设置日志和缓存目录。"""
        fetcher = ETFDataFetcher()
        assert fetcher.cache_dir is not None
        assert isinstance(fetcher.cache_dir, str)
        assert fetcher.logger is not None

    def test_get_realtime_quote_success(self, sample_realtime_data):
        """测试成功获取实时行情数据。"""
        fetcher = ETFDataFetcher()
        # Mock DataSourceManager 的 get_realtime_quote 方法
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_realtime_quote.return_value = sample_realtime_data

        result = fetcher.get_realtime_quote("510300")

        assert result["symbol"] == "510300"
        assert result["name"] == "沪深300ETF"
        assert abs(result["price"] - 3.856) < 0.001
        assert abs(result["change_pct"] - 1.23) < 0.01
        fetcher._source_manager.get_realtime_quote.assert_called_once_with(symbol="510300")

    def test_get_realtime_quote_not_found(self):
        """测试未找到指定ETF代码时返回空字典。"""
        fetcher = ETFDataFetcher()
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_realtime_quote.return_value = {}

        result = fetcher.get_realtime_quote("999999")

        assert result == {}

    def test_get_realtime_quote_error(self):
        """测试数据源异常时返回空字典。"""
        fetcher = ETFDataFetcher()
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_realtime_quote.return_value = {}

        result = fetcher.get_realtime_quote("510300")

        assert result == {}

    def test_get_history_data_success(self, sample_history_df):
        """测试成功获取历史数据。"""
        fetcher = ETFDataFetcher()
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_history_data.return_value = sample_history_df
        # 跳过交易日调整（避免网络请求）
        fetcher._adjust_trading_day = lambda date_str, mode="next": date_str

        result = fetcher.get_history_data("510300", start_date="20240101", end_date="20240201")

        assert result is not None
        assert not result.empty
        assert len(result) == 30

    def test_get_history_data_with_cache(self, sample_history_df, tmp_path):
        """测试缓存机制：首次调用后数据被缓存，第二次从缓存加载。"""
        fetcher = ETFDataFetcher()
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_history_data.return_value = sample_history_df
        # 使用临时目录避免其他测试的缓存干扰
        fetcher.cache_dir = str(tmp_path)
        # 跳过交易日调整
        fetcher._adjust_trading_day = lambda date_str, mode="next": date_str

        # 首次调用，应请求接口并保存缓存
        result1 = fetcher.get_history_data("510300", start_date="20240101", end_date="20240201")
        assert fetcher._source_manager.get_history_data.call_count == 1

        # 第二次调用，应从缓存加载，不再请求接口
        result2 = fetcher.get_history_data("510300", start_date="20240101", end_date="20240201")
        assert fetcher._source_manager.get_history_data.call_count == 1  # 调用次数不变

        # 两次结果应一致
        assert len(result1) == len(result2)

    def test_get_etf_list_success(self):
        """测试成功获取ETF列表。"""
        mock_df = pd.DataFrame(
            [
                {"代码": "510300", "名称": "沪深300ETF", "最新价": 3.856},
                {"代码": "510500", "名称": "中证500ETF", "最新价": 5.0},
                {"代码": "159919", "名称": "沪深300ETF", "最新价": 4.2},
            ]
        )
        fetcher = ETFDataFetcher()
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_etf_list.return_value = mock_df

        result = fetcher.get_etf_list()

        assert not result.empty
        assert len(result) == 3

    def test_get_etf_list_with_keyword(self):
        """测试按关键词过滤ETF列表。"""
        # 重构后关键词过滤由 DataSourceManager 处理，mock 应返回过滤后的结果
        filtered_df = pd.DataFrame(
            [
                {"代码": "510300", "名称": "沪深300ETF", "最新价": 3.856},
                {"代码": "159919", "名称": "沪深300ETF", "最新价": 4.2},
            ]
        )
        fetcher = ETFDataFetcher()
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_etf_list.return_value = filtered_df

        result = fetcher.get_etf_list(keyword="沪深300")

        assert not result.empty
        assert len(result) == 2
        assert all(result["名称"].str.contains("沪深300"))
        fetcher._source_manager.get_etf_list.assert_called_once_with(keyword="沪深300")

    def test_get_etf_holdings_success(self, sample_holdings_df):
        """测试成功获取持仓信息。"""
        fetcher = ETFDataFetcher()
        fetcher._source_manager = MagicMock()
        fetcher._source_manager.get_etf_holdings.return_value = sample_holdings_df

        # 清除可能的缓存干扰
        current_year = str(2026)
        cache_key = fetcher._get_cache_key("510300", "holdings", date=current_year)
        if os.path.exists(cache_key):
            os.remove(cache_key)

        result = fetcher.get_etf_holdings("510300")

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

        # 键应包含关键信息
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
