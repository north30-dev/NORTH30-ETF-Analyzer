# -*- coding: utf-8 -*-
"""
数据源管理器单元测试模块

使用 unittest.mock 模拟数据源接口，测试 DataSourceManager 的注册、
故障转移、优先级排序和便捷方法委托功能。
"""

from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd
import pytest

from etf_analyzer.data_source_manager import DataSourceManager
from etf_analyzer.data_sources.base import BaseDataSource


def _make_mock_source(name, available=True):
    """创建一个 mock 数据源实例。

    Args:
        name: 数据源名称。
        available: 数据源是否可用。

    Returns:
        MagicMock: 模拟的数据源实例，实现了 BaseDataSource 的接口。
    """
    source = MagicMock(spec=BaseDataSource)
    type(source).name = PropertyMock(return_value=name)
    type(source).available = PropertyMock(return_value=available)
    source.health_check.return_value = {
        "name": name,
        "available": available,
        "response_time": 0.1 if available else None,
        "error": None if available else "不可用",
    }
    return source


# ============================================================
# 测试数据源注册
# ============================================================


class TestDataSourceRegistration:
    """数据源注册相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.manager = DataSourceManager()

    def test_register_single_source(self):
        """测试注册单个数据源。"""
        source = _make_mock_source("akshare")
        self.manager.register(source)

        assert len(self.manager._sources) == 1
        assert self.manager._sources[0].name == "akshare"
        assert "akshare" in self.manager._source_map

    def test_register_duplicate_source_skipped(self):
        """测试重复注册同名数据源时跳过。"""
        source1 = _make_mock_source("akshare")
        source2 = _make_mock_source("akshare")

        self.manager.register(source1)
        self.manager.register(source2)

        # 应只注册一次
        assert len(self.manager._sources) == 1
        assert self.manager._source_map["akshare"] is source1

    def test_register_multiple_different_sources(self):
        """测试注册多个不同名称的数据源。"""
        source_a = _make_mock_source("akshare")
        source_b = _make_mock_source("tushare")

        self.manager.register(source_a)
        self.manager.register(source_b)

        assert len(self.manager._sources) == 2
        assert "akshare" in self.manager._source_map
        assert "tushare" in self.manager._source_map


# ============================================================
# 测试故障转移
# ============================================================


class TestFailover:
    """故障转移相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.manager = DataSourceManager()
        # 禁用健康检查间隔限制
        self.manager._last_health_check_time = 0

    @patch("etf_analyzer.data_source_manager.DATASOURCE_HEALTH_CHECK_INTERVAL", 0)
    def test_failover_to_next_source_on_failure(self):
        """测试主数据源失败时自动切换到备选数据源。"""
        source_primary = _make_mock_source("akshare")
        source_backup = _make_mock_source("tushare")

        # 主数据源返回空数据，备选数据源返回有效数据
        source_primary.get_realtime_quote.return_value = {}
        source_backup.get_realtime_quote.return_value = {
            "symbol": "510300", "name": "沪深300ETF", "price": 3.856,
            "change_pct": 1.23, "change_amt": 0.047, "volume": 100000,
            "amount": 500000, "open": 3.8, "high": 3.9, "low": 3.7,
            "prev_close": 3.8,
        }

        self.manager.register(source_primary)
        self.manager.register(source_backup)

        # 将主数据源标记为不可用
        self.manager._health_status["akshare"] = {
            "name": "akshare", "available": False,
            "response_time": None, "error": "连接失败",
        }
        self.manager._health_status["tushare"] = {
            "name": "tushare", "available": True,
            "response_time": 0.1, "error": None,
        }

        result = self.manager.fetch("get_realtime_quote", symbol="510300")

        # 应从备选数据源获取到数据
        assert result != {}
        assert result["symbol"] == "510300"

    @patch("etf_analyzer.data_source_manager.DATASOURCE_HEALTH_CHECK_INTERVAL", 0)
    def test_all_sources_fail_returns_empty_data(self):
        """测试所有数据源失败时返回空数据。"""
        source_a = _make_mock_source("akshare")
        source_b = _make_mock_source("tushare")

        # 两个数据源都返回空数据
        source_a.get_realtime_quote.return_value = {}
        source_b.get_realtime_quote.return_value = {}

        self.manager.register(source_a)
        self.manager.register(source_b)

        # 标记两个数据源都不可用
        self.manager._health_status["akshare"] = {
            "name": "akshare", "available": False,
            "response_time": None, "error": "连接失败",
        }
        self.manager._health_status["tushare"] = {
            "name": "tushare", "available": False,
            "response_time": None, "error": "连接失败",
        }

        result = self.manager.fetch("get_realtime_quote", symbol="510300")

        # 所有数据源失败时应返回空字典
        assert result == {}

    @patch("etf_analyzer.data_source_manager.DATASOURCE_HEALTH_CHECK_INTERVAL", 0)
    def test_failover_on_exception(self):
        """测试数据源抛出异常时自动切换。"""
        source_primary = _make_mock_source("akshare")
        source_backup = _make_mock_source("tushare")

        # 主数据源抛出异常
        source_primary.get_realtime_quote.side_effect = ConnectionError("连接失败")
        source_backup.get_realtime_quote.return_value = {
            "symbol": "510300", "name": "沪深300ETF", "price": 3.856,
            "change_pct": 1.23, "change_amt": 0.047, "volume": 100000,
            "amount": 500000, "open": 3.8, "high": 3.9, "low": 3.7,
            "prev_close": 3.8,
        }

        self.manager.register(source_primary)
        self.manager.register(source_backup)

        # 两个数据源都标记为可用
        self.manager._health_status["akshare"] = {
            "name": "akshare", "available": True,
            "response_time": 0.1, "error": None,
        }
        self.manager._health_status["tushare"] = {
            "name": "tushare", "available": True,
            "response_time": 0.1, "error": None,
        }

        result = self.manager.fetch("get_realtime_quote", symbol="510300")

        # 应从备选数据源获取到数据
        assert result != {}
        assert result["symbol"] == "510300"


# ============================================================
# 测试优先级排序
# ============================================================


class TestPrioritySorting:
    """优先级排序相关测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.manager = DataSourceManager()

    @patch("etf_analyzer.data_source_manager.DATASOURCE_PRIORITY",
           ["tushare", "akshare", "baostock", "pytdx"])
    def test_sources_sorted_by_config_priority(self):
        """测试按配置优先级排序数据源。"""
        source_a = _make_mock_source("akshare")
        source_b = _make_mock_source("tushare")
        source_c = _make_mock_source("baostock")

        # 按非优先级顺序注册
        self.manager.register(source_a)
        self.manager.register(source_b)
        self.manager.register(source_c)

        # 排序后 tushare 应排在第一位
        names = [s.name for s in self.manager._sources]
        assert names.index("tushare") < names.index("akshare")
        assert names.index("akshare") < names.index("baostock")

    @patch("etf_analyzer.data_source_manager.DATASOURCE_PRIORITY",
           ["akshare", "tushare"])
    def test_unknown_source_goes_to_end(self):
        """测试不在配置列表中的数据源排到末尾。"""
        source_a = _make_mock_source("akshare")
        source_unknown = _make_mock_source("unknown_source")

        self.manager.register(source_unknown)
        self.manager.register(source_a)

        names = [s.name for s in self.manager._sources]
        # akshare 应排在 unknown_source 前面
        assert names.index("akshare") < names.index("unknown_source")


# ============================================================
# 测试便捷方法
# ============================================================


class TestConvenienceMethods:
    """便捷方法委托测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.manager = DataSourceManager()
        self.source = _make_mock_source("akshare")
        self.manager.register(self.source)
        # 标记数据源为可用
        self.manager._health_status["akshare"] = {
            "name": "akshare", "available": True,
            "response_time": 0.1, "error": None,
        }

    @patch("etf_analyzer.data_source_manager.DATASOURCE_HEALTH_CHECK_INTERVAL", 0)
    def test_get_realtime_quote_delegates(self):
        """测试 get_realtime_quote 正确委托给 fetch。"""
        expected = {
            "symbol": "510300", "name": "沪深300ETF", "price": 3.856,
            "change_pct": 1.23, "change_amt": 0.047, "volume": 100000,
            "amount": 500000, "open": 3.8, "high": 3.9, "low": 3.7,
            "prev_close": 3.8,
        }
        self.source.get_realtime_quote.return_value = expected

        result = self.manager.get_realtime_quote("510300")

        assert result == expected
        self.source.get_realtime_quote.assert_called_once_with(symbol="510300")

    @patch("etf_analyzer.data_source_manager.DATASOURCE_HEALTH_CHECK_INTERVAL", 0)
    def test_get_history_data_delegates(self):
        """测试 get_history_data 正确委托给 fetch。"""
        expected = pd.DataFrame({
            "日期": ["2024-01-02"],
            "收盘": [3.856],
        })
        self.source.get_history_data.return_value = expected

        result = self.manager.get_history_data("510300", "20240101", "20240201")

        assert result.equals(expected)
        self.source.get_history_data.assert_called_once_with(
            symbol="510300", start_date="20240101", end_date="20240201", adjust="qfq",
        )

    @patch("etf_analyzer.data_source_manager.DATASOURCE_HEALTH_CHECK_INTERVAL", 0)
    def test_get_etf_list_delegates(self):
        """测试 get_etf_list 正确委托给 fetch。"""
        expected = pd.DataFrame({"代码": ["510300"], "名称": ["沪深300ETF"]})
        self.source.get_etf_list.return_value = expected

        result = self.manager.get_etf_list()

        assert result.equals(expected)
        self.source.get_etf_list.assert_called_once_with(keyword=None)

    @patch("etf_analyzer.data_source_manager.DATASOURCE_HEALTH_CHECK_INTERVAL", 0)
    def test_get_etf_holdings_delegates(self):
        """测试 get_etf_holdings 正确委托给 fetch。"""
        expected = pd.DataFrame({"股票代码": ["600519"], "股票名称": ["贵州茅台"]})
        self.source.get_etf_holdings.return_value = expected

        result = self.manager.get_etf_holdings("510300")

        assert result.equals(expected)
        self.source.get_etf_holdings.assert_called_once_with(symbol="510300")


# ============================================================
# 测试辅助方法
# ============================================================


class TestHelperMethods:
    """辅助方法测试。"""

    def test_is_empty_result_with_none(self):
        """测试 None 结果被视为空。"""
        assert DataSourceManager._is_empty_result(None) is True

    def test_is_empty_result_with_empty_dict(self):
        """测试空字典被视为空。"""
        assert DataSourceManager._is_empty_result({}) is True

    def test_is_empty_result_with_non_empty_dict(self):
        """测试非空字典不被视为空。"""
        assert DataSourceManager._is_empty_result({"key": "value"}) is False

    def test_is_empty_result_with_empty_dataframe(self):
        """测试空 DataFrame 被视为空。"""
        assert DataSourceManager._is_empty_result(pd.DataFrame()) is True

    def test_is_empty_result_with_non_empty_dataframe(self):
        """测试非空 DataFrame 不被视为空。"""
        df = pd.DataFrame({"a": [1]})
        assert DataSourceManager._is_empty_result(df) is False

    def test_empty_result_for_method_realtime_quote(self):
        """测试 get_realtime_quote 方法返回空字典。"""
        assert DataSourceManager._empty_result_for_method("get_realtime_quote") == {}

    def test_empty_result_for_method_other(self):
        """测试其他方法返回空 DataFrame。"""
        result = DataSourceManager._empty_result_for_method("get_history_data")
        assert isinstance(result, pd.DataFrame)
        assert result.empty
