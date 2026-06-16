# -*- coding: utf-8 -*-
"""
数据源抽象层单元测试模块

使用 unittest.mock 模拟各数据源的外部依赖接口，测试 BaseDataSource 抽象类、
AkshareDataSource、TushareDataSource、BaostockDataSource 和 PytdxDataSource
的核心功能。
"""

from abc import ABC
from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd
import pytest

from etf_analyzer.data_sources.base import BaseDataSource
from etf_analyzer.data_sources.akshare_source import AkshareDataSource
from etf_analyzer.data_sources.tushare_source import TushareDataSource
from etf_analyzer.data_sources.baostock_source import BaostockDataSource
from etf_analyzer.data_sources.pytdx_source import PytdxDataSource


# ============================================================
# 测试 BaseDataSource 抽象类
# ============================================================


class TestBaseDataSource:
    """BaseDataSource 抽象类单元测试。"""

    def test_cannot_instantiate_directly(self):
        """验证不能直接实例化 BaseDataSource 抽象类。"""
        with pytest.raises(TypeError):
            BaseDataSource()

    def test_subclass_must_implement_all_abstract_methods(self):
        """验证子类必须实现所有抽象方法，否则无法实例化。"""

        # 只实现部分方法的子类，应无法实例化
        class IncompleteSource(BaseDataSource):
            @property
            def name(self) -> str:
                return "incomplete"

            # 缺少 available、get_realtime_quote 等方法的实现

        with pytest.raises(TypeError):
            IncompleteSource()

    def test_complete_subclass_can_instantiate(self):
        """验证实现了所有抽象方法的子类可以正常实例化。"""

        class CompleteSource(BaseDataSource):
            @property
            def name(self) -> str:
                return "complete"

            @property
            def available(self) -> bool:
                return True

            def get_realtime_quote(self, symbol: str) -> dict:
                return {}

            def get_history_data(self, symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
                return pd.DataFrame()

            def get_etf_list(self, keyword: str = None) -> pd.DataFrame:
                return pd.DataFrame()

            def get_etf_holdings(self, symbol: str) -> pd.DataFrame:
                return pd.DataFrame()

            def health_check(self) -> dict:
                return {"name": self.name, "available": True, "response_time": None, "error": None}

        source = CompleteSource()
        assert source.name == "complete"
        assert source.available is True


# ============================================================
# 测试 AkshareDataSource
# ============================================================


class TestAkshareDataSource:
    """AkshareDataSource 单元测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        self.source = AkshareDataSource()

    def test_name_returns_akshare(self):
        """测试 name 属性返回 'akshare'。"""
        assert self.source.name == "akshare"

    def test_available_returns_true(self):
        """测试 available 属性返回 True（akshare 无需认证）。"""
        assert self.source.available is True

    @patch("etf_analyzer.data_sources.akshare_source.ak.fund_etf_spot_em")
    @patch("etf_analyzer.data_sources.akshare_source.rate_limiter")
    def test_get_realtime_quote_returns_correct_format(self, mock_limiter, mock_spot_em):
        """测试 get_realtime_quote 返回正确格式的字典。"""
        mock_limiter.acquire = MagicMock()
        mock_df = pd.DataFrame([
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
        ])
        mock_spot_em.return_value = mock_df

        result = self.source.get_realtime_quote("510300")

        # 验证返回的字典包含所有必需的键
        expected_keys = {"symbol", "name", "price", "change_pct", "change_amt",
                         "volume", "amount", "open", "high", "low", "prev_close"}
        assert set(result.keys()) == expected_keys
        assert result["symbol"] == "510300"
        assert result["name"] == "沪深300ETF"
        assert abs(result["price"] - 3.856) < 0.001

    @patch("etf_analyzer.data_sources.akshare_source.ak.fund_etf_spot_em")
    @patch("etf_analyzer.data_sources.akshare_source.rate_limiter")
    def test_get_realtime_quote_not_found(self, mock_limiter, mock_spot_em):
        """测试未找到指定代码时返回空字典。"""
        mock_limiter.acquire = MagicMock()
        mock_df = pd.DataFrame([
            {"代码": "510500", "名称": "中证500ETF", "最新价": 5.0,
             "涨跌幅": 0.5, "涨跌额": 0.02, "成交量": 100000,
             "成交额": 500000, "开盘价": 4.98, "最高价": 5.02,
             "最低价": 4.95, "昨收": 4.98}
        ])
        mock_spot_em.return_value = mock_df

        result = self.source.get_realtime_quote("999999")
        assert result == {}

    @patch("etf_analyzer.data_sources.akshare_source.ak.fund_etf_hist_em")
    @patch("etf_analyzer.data_sources.akshare_source.rate_limiter")
    def test_get_history_data_returns_correct_format(self, mock_limiter, mock_hist_em):
        """测试 get_history_data 返回正确格式的 DataFrame。"""
        mock_limiter.acquire = MagicMock()
        mock_df = pd.DataFrame({
            "日期": pd.bdate_range("2024-01-02", periods=5),
            "开盘": [3.0, 3.1, 3.2, 3.3, 3.4],
            "收盘": [3.1, 3.2, 3.3, 3.4, 3.5],
            "最高": [3.2, 3.3, 3.4, 3.5, 3.6],
            "最低": [2.9, 3.0, 3.1, 3.2, 3.3],
            "成交量": [100000, 110000, 120000, 130000, 140000],
            "成交额": [310000, 352000, 396000, 442000, 490000],
            "振幅": [9.68, 9.38, 9.09, 8.82, 8.57],
            "涨跌幅": [1.0, 3.23, 3.12, 3.03, 3.03],
            "涨跌额": [0.1, 0.1, 0.1, 0.1, 0.1],
            "换手率": [0.5, 0.55, 0.6, 0.65, 0.7],
        })
        mock_hist_em.return_value = mock_df

        # mock 交易日调整
        with patch.object(self.source, "_adjust_trading_day", side_effect=lambda d, **kw: d):
            result = self.source.get_history_data("510300", start_date="20240102", end_date="20240108")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "日期" in result.columns
        assert "收盘" in result.columns

    @patch("etf_analyzer.data_sources.akshare_source.ak.fund_etf_spot_em")
    @patch("etf_analyzer.data_sources.akshare_source.rate_limiter")
    def test_health_check_returns_correct_format(self, mock_limiter, mock_spot_em):
        """测试 health_check 返回正确格式的字典。"""
        mock_limiter.acquire = MagicMock()
        mock_df = pd.DataFrame([{"代码": "510300", "名称": "沪深300ETF"}])
        mock_spot_em.return_value = mock_df

        result = self.source.health_check()

        assert "name" in result
        assert "available" in result
        assert "response_time" in result
        assert "error" in result
        assert result["name"] == "akshare"
        assert result["available"] is True
        assert result["response_time"] is not None
        assert result["error"] is None

    @patch("etf_analyzer.data_sources.akshare_source.ak.fund_etf_spot_em")
    @patch("etf_analyzer.data_sources.akshare_source.rate_limiter")
    def test_health_check_failure(self, mock_limiter, mock_spot_em):
        """测试健康检查失败时返回正确格式。"""
        mock_limiter.acquire = MagicMock()
        mock_spot_em.side_effect = ConnectionError("网络连接失败")

        result = self.source.health_check()

        assert result["name"] == "akshare"
        assert result["available"] is False
        assert result["response_time"] is None
        assert result["error"] is not None


# ============================================================
# 测试 TushareDataSource
# ============================================================


class TestTushareDataSource:
    """TushareDataSource 单元测试。"""

    @patch("etf_analyzer.data_sources.tushare_source.TUSHARE_TOKEN", None)
    @patch("etf_analyzer.data_sources.tushare_source.ts", None)
    def test_available_returns_false_when_token_not_configured(self):
        """测试 Token 未配置时 available 返回 False。"""
        with patch("etf_analyzer.data_sources.tushare_source.TUSHARE_TOKEN", None):
            source = TushareDataSource()
            assert source.available is False

    @patch("etf_analyzer.data_sources.tushare_source.TUSHARE_TOKEN", None)
    @patch("etf_analyzer.data_sources.tushare_source.ts", None)
    def test_name_returns_tushare(self):
        """测试 name 属性返回 'tushare'。"""
        source = TushareDataSource()
        assert source.name == "tushare"

    @patch("etf_analyzer.data_sources.tushare_source.TUSHARE_TOKEN", None)
    @patch("etf_analyzer.data_sources.tushare_source.ts", None)
    def test_unavailable_source_returns_empty_data(self):
        """测试不可用时各方法返回空数据。"""
        source = TushareDataSource()
        assert source.available is False

        # 不可用时，各方法应返回空数据
        assert source.get_realtime_quote("510300") == {}
        assert isinstance(source.get_history_data("510300", "20240101", "20240201"), pd.DataFrame)
        assert source.get_history_data("510300", "20240101", "20240201").empty
        assert isinstance(source.get_etf_list(), pd.DataFrame)
        assert source.get_etf_list().empty
        assert isinstance(source.get_etf_holdings("510300"), pd.DataFrame)
        assert source.get_etf_holdings("510300").empty

    def test_convert_symbol(self):
        """测试代码格式转换。"""
        # 6 开头为上海
        assert TushareDataSource._convert_symbol("600519") == "600519.SH"
        # 非6开头为深圳（510300 以5开头，归为深圳）
        assert TushareDataSource._convert_symbol("510300") == "510300.SZ"
        assert TushareDataSource._convert_symbol("159919") == "159919.SZ"
        # 已有后缀直接返回
        assert TushareDataSource._convert_symbol("510300.SH") == "510300.SH"

    def test_strip_symbol(self):
        """测试从 tushare 格式代码提取纯数字。"""
        assert TushareDataSource._strip_symbol("510300.SH") == "510300"
        assert TushareDataSource._strip_symbol("159919.SZ") == "159919"
        assert TushareDataSource._strip_symbol("510300") == "510300"


# ============================================================
# 测试 BaostockDataSource
# ============================================================


class TestBaostockDataSource:
    """BaostockDataSource 单元测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        # mock baostock 模块，使 BaostockDataSource 可用
        with patch("etf_analyzer.data_sources.baostock_source.BaostockDataSource.__init__", lambda self: None):
            self.source = BaostockDataSource()
            self.source.logger = MagicMock()
            self.source._bs = MagicMock()  # 模拟 baostock 已安装

    def test_name_returns_baostock(self):
        """测试 name 属性返回 'baostock'。"""
        assert self.source.name == "baostock"

    def test_available_returns_true_when_installed(self):
        """测试 baostock 已安装时 available 返回 True。"""
        assert self.source.available is True

    def test_get_realtime_quote_returns_empty_dict(self):
        """测试 get_realtime_quote 返回空字典（不支持实时行情）。"""
        result = self.source.get_realtime_quote("510300")
        assert result == {}

    def test_get_etf_list_returns_empty_dataframe(self):
        """测试 get_etf_list 返回空 DataFrame（不支持ETF列表）。"""
        result = self.source.get_etf_list()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_get_etf_holdings_returns_empty_dataframe(self):
        """测试 get_etf_holdings 返回空 DataFrame（不支持持仓查询）。"""
        result = self.source.get_etf_holdings("510300")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_convert_symbol(self):
        """测试代码格式转换。"""
        # 6 开头为上海
        assert self.source._convert_symbol("600519") == "sh.600519"
        # 非6开头为深圳（510300 以5开头，归为深圳）
        assert self.source._convert_symbol("510300") == "sz.510300"
        assert self.source._convert_symbol("159919") == "sz.159919"

    def test_convert_adjust_flag(self):
        """测试复权类型转换。"""
        assert self.source._convert_adjust_flag("qfq") == "2"
        assert self.source._convert_adjust_flag("hfq") == "1"
        assert self.source._convert_adjust_flag("") == "3"

    def test_available_returns_false_when_not_installed(self):
        """测试 baostock 未安装时 available 返回 False。"""
        with patch("etf_analyzer.data_sources.baostock_source.BaostockDataSource.__init__", lambda self: None):
            source = BaostockDataSource()
            source.logger = MagicMock()
            source._bs = None  # 模拟 baostock 未安装
            assert source.available is False


# ============================================================
# 测试 PytdxDataSource
# ============================================================


class TestPytdxDataSource:
    """PytdxDataSource 单元测试。"""

    def setup_method(self):
        """每个测试方法执行前的初始化。"""
        with patch("etf_analyzer.data_sources.pytdx_source.PytdxDataSource.__init__", lambda self: None):
            self.source = PytdxDataSource()
            self.source.logger = MagicMock()
            self.source._host = "119.147.212.81"
            self.source._port = 7709
            self.source._pytdx_available = True  # 模拟 pytdx 已安装

    def test_name_returns_pytdx(self):
        """测试 name 属性返回 'pytdx'。"""
        assert self.source.name == "pytdx"

    def test_available_returns_true_when_installed(self):
        """测试 pytdx 已安装时 available 返回 True。"""
        assert self.source.available is True

    def test_available_returns_false_when_not_installed(self):
        """测试 pytdx 未安装时 available 返回 False。"""
        self.source._pytdx_available = False
        assert self.source.available is False

    def test_get_etf_list_returns_empty_dataframe(self):
        """测试 get_etf_list 返回空 DataFrame（不支持ETF列表）。"""
        result = self.source.get_etf_list()
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_get_etf_holdings_returns_empty_dataframe(self):
        """测试 get_etf_holdings 返回空 DataFrame（不支持持仓查询）。"""
        result = self.source.get_etf_holdings("510300")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_unavailable_source_returns_empty_realtime_quote(self):
        """测试不可用时 get_realtime_quote 返回空字典。"""
        self.source._pytdx_available = False
        # 不可用时 _connect 返回 None
        with patch.object(self.source, "_connect", return_value=None):
            result = self.source.get_realtime_quote("510300")
            assert result == {}

    def test_unavailable_source_returns_empty_history_data(self):
        """测试不可用时 get_history_data 返回空 DataFrame。"""
        self.source._pytdx_available = False
        with patch.object(self.source, "_connect", return_value=None):
            result = self.source.get_history_data("510300", "20240101", "20240201")
            assert isinstance(result, pd.DataFrame)
            assert result.empty

    def test_health_check_returns_error_when_not_available(self):
        """测试不可用时健康检查返回错误。"""
        self.source._pytdx_available = False
        result = self.source.health_check()
        assert result["name"] == "pytdx"
        assert result["available"] is False
        assert result["error"] is not None
